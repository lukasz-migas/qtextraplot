from __future__ import annotations

import math
import typing as ty
from dataclasses import dataclass

import numpy as np
import scipy.sparse as sp
from vispy import app, scene
from vispy.color import get_colormap
from vispy.geometry import Rect
from vispy.gloo import IndexBuffer, Texture2D, VertexBuffer
from vispy.scene.visuals import create_visual_node
from vispy.visuals import transforms
from vispy.visuals.shaders import Function
from vispy.visuals.visual import Visual

ArrayLike = np.ndarray
Sparse2D = sp.csr_matrix | sp.csc_matrix


# -----------------------------------------------------------------------------
# Data model
# -----------------------------------------------------------------------------


@dataclass(slots=True)
class SparseImageLevel:
    data: Sparse2D
    x_edges: np.ndarray
    y_edges: np.ndarray
    level: int
    x_downsample: int
    y_downsample: int

    @property
    def shape(self) -> tuple[int, int]:
        return self.data.shape

    @property
    def width(self) -> float:
        return float(self.x_edges[-1] - self.x_edges[0])

    @property
    def height(self) -> float:
        return float(self.y_edges[-1] - self.y_edges[0])


class SparsePyramid:
    """Pyramid over a sparse matrix with irregular X pixel widths.

    Assumptions
    -----------
    * Rows are ion mobility bins (regular or at least represented by edges).
    * Columns are mass bins.
    * X pixels may have different widths; Y pixels may also be irregular.
    * Coarser pyramid levels are built by block reduction.
    """

    def __init__(
        self,
        base: Sparse2D,
        x_edges: np.ndarray,
        y_edges: np.ndarray,
        max_levels: int = 8,
        min_size: int = 512,
    ) -> None:
        if not sp.isspmatrix(base):
            raise TypeError("base must be a scipy sparse matrix")
        if base.ndim != 2:
            raise ValueError("base must be 2D")
        if x_edges.ndim != 1 or y_edges.ndim != 1:
            raise ValueError("x_edges and y_edges must be 1D")
        if len(x_edges) != base.shape[1] + 1:
            raise ValueError("len(x_edges) must be ncols + 1")
        if len(y_edges) != base.shape[0] + 1:
            raise ValueError("len(y_edges) must be nrows + 1")
        if not np.all(np.diff(x_edges) > 0):
            raise ValueError("x_edges must be strictly increasing")
        if not np.all(np.diff(y_edges) > 0):
            raise ValueError("y_edges must be strictly increasing")

        base = base.tocsr().astype(np.float32)
        self.levels: list[SparseImageLevel] = [
            SparseImageLevel(
                data=base,
                x_edges=np.asarray(x_edges, dtype=np.float64),
                y_edges=np.asarray(y_edges, dtype=np.float64),
                level=0,
                x_downsample=1,
                y_downsample=1,
            ),
        ]
        self._build(max_levels=max_levels, min_size=min_size)

    def _build(self, max_levels: int, min_size: int) -> None:
        current = self.levels[0]
        for level in range(1, max_levels):
            h, w = current.data.shape
            if max(h, w) <= min_size:
                break
            next_level = self._downsample_level(current, level=level)
            self.levels.append(next_level)
            current = next_level

    @staticmethod
    def _downsample_level(src: SparseImageLevel, level: int) -> SparseImageLevel:
        """2x downsample by summing 2x2 blocks.

        For sparse matrices, matrix multiplication with aggregation matrices is a
        neat way to avoid densifying the full image.
        """
        data = src.data.tocsr()
        h, w = data.shape
        h2 = math.ceil(h / 2)
        w2 = math.ceil(w / 2)

        row_ids = np.arange(h, dtype=np.int32)
        col_ids = np.arange(w, dtype=np.int32)

        row_groups = row_ids // 2
        col_groups = col_ids // 2

        R = sp.csr_matrix(
            (np.ones(h, dtype=np.float32), (row_groups, row_ids)),
            shape=(h2, h),
        )
        C = sp.csr_matrix(
            (np.ones(w, dtype=np.float32), (col_ids, col_groups)),
            shape=(w, w2),
        )

        reduced = (R @ data @ C).tocsr()

        # Coarsen coordinates by taking every second edge and preserving the end.
        x_edges = src.x_edges
        y_edges = src.y_edges
        x_new = np.empty(w2 + 1, dtype=np.float64)
        y_new = np.empty(h2 + 1, dtype=np.float64)
        x_new[:-1] = x_edges[::2][:w2]
        x_new[-1] = x_edges[-1]
        y_new[:-1] = y_edges[::2][:h2]
        y_new[-1] = y_edges[-1]

        return SparseImageLevel(
            data=reduced,
            x_edges=x_new,
            y_edges=y_new,
            level=level,
            x_downsample=src.x_downsample * 2,
            y_downsample=src.y_downsample * 2,
        )

    def choose_level(self, view_rect_world: Rect, canvas_px: tuple[int, int]) -> SparseImageLevel:
        """Choose the coarsest level that still oversamples the current view.

        We compare world-units-per-screen-pixel to median cell size in each level.
        """
        canvas_h, canvas_w = canvas_px
        canvas_w = max(int(canvas_w), 1)
        canvas_h = max(int(canvas_h), 1)

        world_per_px_x = max(view_rect_world.width / canvas_w, 1e-12)
        world_per_px_y = max(view_rect_world.height / canvas_h, 1e-12)

        chosen = self.levels[-1]
        for level in self.levels:
            dx = np.median(np.diff(level.x_edges))
            dy = np.median(np.diff(level.y_edges))
            # Require the level to be no coarser than ~1.5 screen pixels per texel.
            if dx <= world_per_px_x * 1.5 and dy <= world_per_px_y * 1.5:
                chosen = level
                break
        return chosen


# -----------------------------------------------------------------------------
# Tile extraction
# -----------------------------------------------------------------------------


@dataclass(slots=True)
class TileRequest:
    level: SparseImageLevel
    row0: int
    row1: int
    col0: int
    col1: int


@dataclass(slots=True)
class TilePayload:
    image: np.ndarray
    x0: float
    x1: float
    y0: float
    y1: float


class SparseTileProvider:
    def __init__(
        self,
        pyramid: SparsePyramid,
        tile_shape: tuple[int, int] = (256, 512),
        log_scale: bool = True,
        fill_value: float = 0.0,
    ) -> None:
        self.pyramid = pyramid
        self.tile_shape = tile_shape
        self.log_scale = log_scale
        self.fill_value = fill_value

    def visible_tiles(
        self,
        level: SparseImageLevel,
        view_rect_world: Rect,
    ) -> list[TileRequest]:
        x_edges = level.x_edges
        y_edges = level.y_edges
        tile_h, tile_w = self.tile_shape

        # Find visible cell span in index space.
        col0 = max(int(np.searchsorted(x_edges, view_rect_world.left, side="right") - 1), 0)
        col1 = min(int(np.searchsorted(x_edges, view_rect_world.right, side="left") + 1), level.shape[1])
        row0 = max(int(np.searchsorted(y_edges, view_rect_world.bottom, side="right") - 1), 0)
        row1 = min(int(np.searchsorted(y_edges, view_rect_world.top, side="left") + 1), level.shape[0])

        if col1 <= col0 or row1 <= row0:
            return []

        tile_requests: list[TileRequest] = []
        for r0 in range((row0 // tile_h) * tile_h, row1, tile_h):
            for c0 in range((col0 // tile_w) * tile_w, col1, tile_w):
                tile_requests.append(
                    TileRequest(
                        level=level,
                        row0=r0,
                        row1=min(r0 + tile_h, level.shape[0]),
                        col0=c0,
                        col1=min(c0 + tile_w, level.shape[1]),
                    ),
                )
        return tile_requests

    def fetch_tile(self, req: TileRequest) -> TilePayload:
        sub = req.level.data[req.row0 : req.row1, req.col0 : req.col1]
        dense = np.asarray(sub.toarray(), dtype=np.float32)
        if self.log_scale:
            dense = np.log1p(np.maximum(dense, 0.0))
        if self.fill_value != 0.0:
            dense[dense == 0.0] = self.fill_value

        return TilePayload(
            image=dense,
            x0=float(req.level.x_edges[req.col0]),
            x1=float(req.level.x_edges[req.col1]),
            y0=float(req.level.y_edges[req.row0]),
            y1=float(req.level.y_edges[req.row1]),
        )


# -----------------------------------------------------------------------------
# Non-uniform quad visual
# -----------------------------------------------------------------------------


_VERTEX_SHADER = """
attribute vec2 a_position;
attribute vec2 a_texcoord;
varying vec2 v_texcoord;
void main() {
    v_texcoord = a_texcoord;
    gl_Position = $transform(vec4(a_position, 0.0, 1.0));
}
"""

_FRAGMENT_SHADER = """
uniform sampler2D u_texture;
uniform vec2 u_clim;
varying vec2 v_texcoord;

void main() {
    float v = texture2D(u_texture, v_texcoord).r;
    float t = clamp((v - u_clim.x) / max(u_clim.y - u_clim.x, 1e-12), 0.0, 1.0);
    gl_FragColor = vec4(t, t, t, 1.0);
}
"""


class TexturedQuadVisual(Visual):
    """Single textured quad in world coordinates.

    This is enough for each tile because the tile itself is rendered on a regular
    grid in texture space; the non-uniform pixel spacing is represented by the
    tile's world-space bounds.
    """

    def __init__(
        self,
        image: np.ndarray,
        bounds: tuple[float, float, float, float],
        clim: tuple[float, float],
        cmap: str = "viridis",
    ) -> None:
        super().__init__(vcode=_VERTEX_SHADER, fcode=_FRAGMENT_SHADER)
        x0, x1, y0, y1 = bounds
        vertices = np.array(
            [
                [x0, y0],
                [x1, y0],
                [x1, y1],
                [x0, y1],
            ],
            dtype=np.float32,
        )
        tex = np.array(
            [
                [0.0, 0.0],
                [1.0, 0.0],
                [1.0, 1.0],
                [0.0, 1.0],
            ],
            dtype=np.float32,
        )
        faces = np.array([0, 1, 2, 0, 2, 3], dtype=np.uint32)

        structured = np.zeros(
            4,
            dtype=[("a_position", np.float32, 2), ("a_texcoord", np.float32, 2)],
        )
        structured["a_position"] = vertices
        structured["a_texcoord"] = tex
        self._vbo = VertexBuffer(structured)
        self._ibo = IndexBuffer(faces)
        self.shared_program["a_position"] = self._vbo["a_position"]
        self.shared_program["a_texcoord"] = self._vbo["a_texcoord"]
        # self.shared_program["u_texture"] = image.astype(np.float32)
        self._texture = Texture2D(
            image.astype(np.float32),
            interpolation="nearest",
            wrapping="clamp_to_edge",
        )
        self.shared_program["u_texture"] = self._texture
        self.shared_program["u_clim"] = tuple(map(float, clim))
        # self.shared_program.frag["cmap"] = Function(get_colormap(cmap).glsl_map)
        self._draw_mode = "triangles"
        self._index_buffer = self._ibo

        self.set_gl_state("translucent", depth_test=False, cull_face=False)

    def _prepare_transforms(self, view) -> None:
        self.shared_program.vert["transform"] = view.get_transform()

    def _prepare_draw(self, view) -> bool:
        return True


TexturedQuad = create_visual_node(TexturedQuadVisual)


# -----------------------------------------------------------------------------
# Viewer controller
# -----------------------------------------------------------------------------


class SparseImageViewer(scene.SceneCanvas):
    def __init__(
        self,
        pyramid: SparsePyramid,
        tile_shape: tuple[int, int] = (256, 512),
        cmap: str = "viridis",
        clim: tuple[float, float] | None = None,
        title: str = "Sparse pyramid viewer",
    ) -> None:
        super().__init__(keys="interactive", size=(1400, 800), show=True, title=title)
        self.unfreeze()
        self.pyramid = pyramid
        self.provider = SparseTileProvider(pyramid, tile_shape=tile_shape)
        self.cmap = cmap

        self.view = self.central_widget.add_view()
        self.view.camera = scene.PanZoomCamera(aspect=1)
        self.view.camera.flip = (False, False, False)

        full = self.pyramid.levels[0]
        self.view.camera.set_range(
            x=(full.x_edges[0], full.x_edges[-1]),
            y=(full.y_edges[0], full.y_edges[-1]),
            margin=0.0,
        )

        if clim is None:
            # Estimate from non-zero values only.
            sample = full.data.data
            if sample.size == 0:
                clim = (0.0, 1.0)
            else:
                vals = np.log1p(np.maximum(sample.astype(np.float32), 0.0))
                clim = (float(np.percentile(vals, 1.0)), float(np.percentile(vals, 99.5)))
        # self.clim = clim
        self.clim = (0.0, 1.0)

        self._tile_nodes: dict[tuple[int, int, int, int, int], scene.Node] = {}
        self._last_key: tuple[int, int, int, int, int, int] | None = None
        self.events.draw.connect(self._on_draw)
        self.events.resize.connect(self._on_view_change)
        # PanZoomCamera does not expose a generic `changed` emitter on all VisPy versions.
        # Redraws already happen during pan/zoom interactions, so updating tiles from draw
        # is sufficient and more version-robust.
        # If you want more eager updates later, subclass the camera and override
        # `view_changed()` to notify the viewer.

        self.freeze()

    def _world_rect(self) -> Rect:
        rect = self.view.camera.rect
        return Rect(rect.left, rect.bottom, rect.width, rect.height)

    def _state_key(self, level: SparseImageLevel, rect: Rect) -> tuple[int, int, int, int, int, int]:
        # Quantize the rect a bit to avoid constant redraw churn while panning.
        qx = max(rect.width / 50.0, 1e-9)
        qy = max(rect.height / 50.0, 1e-9)
        return (
            level.level,
            int(round(rect.left / qx)),
            int(round(rect.right / qx)),
            int(round(rect.bottom / qy)),
            int(round(rect.top / qy)),
            int(self.size[0] + self.size[1]),
        )

    def _on_draw(self, event) -> None:
        self._update_tiles()

    def _on_view_change(self, event=None) -> None:
        self._update_tiles()
        self.update()

    def _update_tiles(self) -> None:
        rect = self._world_rect()
        level = self.pyramid.choose_level(rect, canvas_px=(int(self.size[1]), int(self.size[0])))
        state_key = self._state_key(level, rect)
        if state_key == self._last_key:
            return
        self._last_key = state_key

        requests = self.provider.visible_tiles(level, rect)
        keep: set[tuple[int, int, int, int, int]] = set()

        for req in requests:
            key = (req.level.level, req.row0, req.row1, req.col0, req.col1)
            keep.add(key)
            if key in self._tile_nodes:
                continue

            payload = self.provider.fetch_tile(req)
            node = TexturedQuad(
                payload.image,
                bounds=(payload.x0, payload.x1, payload.y0, payload.y1),
                clim=self.clim,
                cmap=self.cmap,
                parent=self.view.scene,
            )
            self._tile_nodes[key] = node

        for key in list(self._tile_nodes):
            if key not in keep:
                node = self._tile_nodes.pop(key)
                node.parent = None


# -----------------------------------------------------------------------------
# Example synthetic dataset
# -----------------------------------------------------------------------------


def make_progressive_mass_edges(n: int, x0: float = 100.0, growth: float = 1.00002) -> np.ndarray:
    """Create monotonically increasing edges with progressively larger bins."""
    widths = x0 * (growth ** np.arange(n, dtype=np.float64))
    widths /= widths.mean()
    widths *= 1.0
    edges = np.empty(n + 1, dtype=np.float64)
    edges[0] = 0.0
    edges[1:] = np.cumsum(widths)
    return edges


def make_regular_edges(n: int, step: float = 1.0) -> np.ndarray:
    return np.arange(n + 1, dtype=np.float64) * step


def make_demo_sparse(shape: tuple[int, int], density: float = 2e-4, seed: int = 0) -> sp.csr_matrix:
    rng = np.random.default_rng(seed)
    h, w = shape
    mat = sp.random(h, w, density=density, format="csr", dtype=np.float32, random_state=rng)

    # Add a few structured ridges/features.
    rows = np.arange(h, dtype=np.int32)
    cols = np.linspace(0, w - 1, h).astype(np.int32)
    ridge = sp.csr_matrix((np.full(h, 20.0, dtype=np.float32), (rows, cols)), shape=shape)

    rows2 = rng.integers(0, h, size=5000)
    cols2 = rng.integers(0, w, size=5000)
    blobs = sp.csr_matrix((rng.uniform(5.0, 100.0, size=5000).astype(np.float32), (rows2, cols2)), shape=shape)
    return (mat * 5.0 + ridge + blobs).tocsr()


def run_demo() -> None:
    # Replace with your real shape, e.g. (4000, 300000)
    shape = (4000, 30_000)
    sparse_img = make_demo_sparse(shape, density=5e-6)
    x_edges = make_progressive_mass_edges(shape[1], x0=1.0, growth=1.00001)
    y_edges = make_regular_edges(shape[0], step=1.0)

    pyramid = SparsePyramid(sparse_img, x_edges=x_edges, y_edges=y_edges, max_levels=10, min_size=256)
    viewer = SparseImageViewer(pyramid, tile_shape=(256, 512), cmap="magma")
    viewer.show()
    app.run()


if __name__ == "__main__":
    run_demo()
