#!/usr/bin/env python3
"""Mesh analysis and headless rendering helpers for build123d parts.

Everything here works on a welded triangle mesh (numpy arrays), so it does not
depend on any OCP call beyond ``Shape.tessellate``. That keeps it stable across
build123d releases and makes the geometry checks independent of the CAD kernel's
own opinion of the shape.

Import it from your own script, or run it directly for a self-test of the
numeric core (no build123d needed):

    python3 scripts/meshtools.py

Requires: numpy. Rendering additionally requires matplotlib.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

# --------------------------------------------------------------------------
# Tessellation
# --------------------------------------------------------------------------


def tessellate(shape, tolerance: float = 0.05, angular_tolerance: float = 0.2):
    """Return (vertices, triangles) as welded numpy arrays.

    ``Shape.tessellate`` emits a separate vertex list per face, so boundary
    vertices are duplicated. Welding is required before any topology check.
    """
    verts, tris = shape.tessellate(tolerance, angular_tolerance)
    v = np.array([[p.X, p.Y, p.Z] for p in verts], dtype=float)
    f = np.array(tris, dtype=np.int64).reshape(-1, 3)
    return weld(v, f)


def weld(v: np.ndarray, f: np.ndarray, decimals: int = 6):
    """Merge coincident vertices and drop degenerate triangles."""
    if len(v) == 0:
        return v, f
    key = np.round(v, decimals)
    _, unique_idx, inverse = np.unique(key, axis=0, return_index=True, return_inverse=True)
    inverse = np.asarray(inverse).reshape(-1)  # numpy 2.0 returned a column here
    v_new = v[unique_idx]
    f_new = inverse[f]
    keep = (
        (f_new[:, 0] != f_new[:, 1])
        & (f_new[:, 1] != f_new[:, 2])
        & (f_new[:, 0] != f_new[:, 2])
    )
    return v_new, f_new[keep]


# --------------------------------------------------------------------------
# Basic mesh geometry
# --------------------------------------------------------------------------


def triangle_normals(v: np.ndarray, f: np.ndarray):
    """Unit normals and areas, one per triangle."""
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    cross = np.cross(b - a, c - a)
    norm = np.linalg.norm(cross, axis=1)
    areas = 0.5 * norm
    safe = np.where(norm > 1e-12, norm, 1.0)
    return cross / safe[:, None], areas


def signed_volume(v: np.ndarray, f: np.ndarray) -> float:
    """Signed volume via the divergence theorem. Positive for outward normals."""
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    return float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0)


def orient_outward(v: np.ndarray, f: np.ndarray):
    """Flip winding if the mesh is inside-out. Returns (f, was_flipped)."""
    if signed_volume(v, f) < 0:
        return f[:, ::-1].copy(), True
    return f, False


@dataclass
class MeshTopology:
    watertight: bool
    consistent_winding: bool
    boundary_edges: int
    nonmanifold_edges: int
    shells: int


def topology(v: np.ndarray, f: np.ndarray) -> MeshTopology:
    """Edge-use analysis: the standard watertight / manifold test."""
    directed = np.vstack([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]])
    undirected = np.sort(directed, axis=1)
    _, counts = np.unique(undirected, axis=0, return_counts=True)
    boundary = int((counts == 1).sum())
    nonmanifold = int((counts > 2).sum())
    # Consistent winding: every undirected edge is traversed once in each direction.
    _, dcounts = np.unique(directed, axis=0, return_counts=True)
    consistent = bool((dcounts == 1).all())
    return MeshTopology(
        watertight=(boundary == 0 and nonmanifold == 0),
        consistent_winding=consistent,
        boundary_edges=boundary,
        nonmanifold_edges=nonmanifold,
        shells=count_shells(v, f),
    )


def count_shells(v: np.ndarray, f: np.ndarray) -> int:
    """Connected components of the face adjacency graph (union-find on vertices)."""
    n = len(v)
    if n == 0:
        return 0
    parent = np.arange(n)

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for tri in f:
        r0 = find(int(tri[0]))
        for other in tri[1:]:
            r1 = find(int(other))
            if r0 != r1:
                parent[r1] = r0
    used = np.unique(f)
    return len({find(int(i)) for i in used})


# --------------------------------------------------------------------------
# Printability analysis
# --------------------------------------------------------------------------


@dataclass
class OverhangReport:
    build_dir: tuple
    threshold_deg: float
    overhang_area: float
    total_area: float
    bed_contact_area: float
    max_overhang_deg: float
    mask: np.ndarray = field(repr=False, default=None)

    @property
    def overhang_fraction(self) -> float:
        return self.overhang_area / self.total_area if self.total_area else 0.0


def overhangs(
    v: np.ndarray,
    f: np.ndarray,
    build_dir=(0.0, 0.0, 1.0),
    threshold_deg: float = 45.0,
    bed_tol: float = 0.05,
) -> OverhangReport:
    """Find down-facing surfaces steeper than the slicer's support threshold.

    ``threshold_deg`` is measured the way slicers report it: the angle between
    the wall and the build direction. A vertical wall is 0 deg, a horizontal
    ceiling is 90 deg. Anything above the threshold needs support unless it is a
    bridge or is sitting on the bed.
    """
    up = np.array(build_dir, dtype=float)
    up /= np.linalg.norm(up)
    normals, areas = triangle_normals(v, f)
    total = float(areas.sum())

    # cos of the angle between the outward normal and -build_dir
    down = -normals @ up
    # angle of the surface away from vertical, in the slicer sense
    angle = np.degrees(np.arcsin(np.clip(down, -1.0, 1.0)))

    heights = (v @ up)[f].mean(axis=1)
    on_bed = heights <= heights.min() + bed_tol
    bed_contact = float(areas[on_bed & (down > 0.99)].sum())

    # A surface sitting exactly on the threshold (a 45 deg chamfer against a
    # 45 deg limit) is not an overhang; float noise must not make it one.
    mask = (angle > threshold_deg + 0.1) & ~on_bed
    return OverhangReport(
        build_dir=tuple(up),
        threshold_deg=threshold_deg,
        overhang_area=float(areas[mask].sum()),
        total_area=total,
        bed_contact_area=bed_contact,
        max_overhang_deg=float(angle[mask].max()) if mask.any() else 0.0,
        mask=mask,
    )


def _ray_triangles(origin, direction, va, edge1, edge2, eps=1e-6):
    """Moller-Trumbore: one ray against all triangles. Returns hit distances."""
    h = np.cross(direction, edge2)
    a = np.einsum("ij,ij->i", edge1, h)
    parallel = np.abs(a) < eps
    a_safe = np.where(parallel, 1.0, a)
    inv = 1.0 / a_safe
    s = origin - va
    u = inv * np.einsum("ij,ij->i", s, h)
    q = np.cross(s, edge1)
    vv = inv * (q @ direction)
    t = inv * np.einsum("ij,ij->i", edge2, q)
    ok = (~parallel) & (u >= -1e-9) & (u <= 1 + 1e-9) & (vv >= -1e-9) & (u + vv <= 1 + 1e-9) & (t > eps)
    return np.where(ok, t, np.inf)


@dataclass
class ThicknessReport:
    samples: int
    min_thickness: float
    p01: float
    p05: float
    median: float
    thin_points: list


def wall_thickness(
    v: np.ndarray,
    f: np.ndarray,
    samples: int = 400,
    offset: float = 1e-4,
    seed: int = 0,
) -> ThicknessReport:
    """Estimate local material thickness by ray casting into the solid.

    From each sampled triangle centroid a ray is fired along the inward normal;
    the distance to the first hit is the local thickness. Triangles are sampled
    with probability proportional to area, so large faces are not under-sampled.
    This is a sampled estimate, not a proof: it can miss a thin spot smaller
    than the sample spacing. Raise ``samples`` for a tighter bound.
    """
    normals, areas = triangle_normals(v, f)
    if len(f) == 0 or areas.sum() <= 0:
        return ThicknessReport(0, math.inf, math.inf, math.inf, math.inf, [])

    rng = np.random.default_rng(seed)
    n = min(samples, len(f) * 4)
    probs = areas / areas.sum()
    idx = rng.choice(len(f), size=n, p=probs)

    centroids = v[f].mean(axis=1)
    va = v[f[:, 0]]
    edge1 = v[f[:, 1]] - va
    edge2 = v[f[:, 2]] - va

    results = []
    for i in idx:
        d = -normals[i]
        o = centroids[i] + d * offset
        t = _ray_triangles(o, d, va, edge1, edge2)
        t[i] = np.inf  # never hit the originating triangle
        hit = t.min()
        if np.isfinite(hit):
            results.append((float(hit), centroids[i].tolist()))

    if not results:
        return ThicknessReport(0, math.inf, math.inf, math.inf, math.inf, [])

    results.sort(key=lambda r: r[0])
    vals = np.array([r[0] for r in results])

    # Report distinct locations, not eight samples of the same thin rib.
    distinct, seen = [], []
    for t, p in results:
        if all(np.linalg.norm(np.array(p) - np.array(q)) > 2.0 for q in seen):
            distinct.append((t, p))
            seen.append(p)
        if len(distinct) >= 8:
            break
    return ThicknessReport(
        samples=len(results),
        min_thickness=float(vals[0]),
        p01=float(np.percentile(vals, 1)),
        p05=float(np.percentile(vals, 5)),
        median=float(np.median(vals)),
        thin_points=[{"thickness": round(t, 4), "at": [round(c, 3) for c in p]} for t, p in distinct],
    )


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

VIEWS = {
    "iso": ((1.0, -1.0, 0.8), (0.0, 0.0, 1.0)),
    "iso_rear": ((-1.0, 1.0, 0.8), (0.0, 0.0, 1.0)),
    "front": ((0.0, -1.0, 0.0), (0.0, 0.0, 1.0)),
    "right": ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0)),
    "top": ((0.0, 0.0, 1.0), (0.0, 1.0, 0.0)),
    "bottom": ((0.0, 0.0, -1.0), (0.0, 1.0, 0.0)),
}


def edge_adjacency(f: np.ndarray):
    """Unique undirected edges plus the (up to two) triangles on either side.

    Returns (edges, tri_a, tri_b) where tri_b is -1 for a boundary edge.
    """
    e = np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]], axis=0)
    tri = np.tile(np.arange(len(f)), 3)
    e = np.sort(e, axis=1)
    uniq, inverse = np.unique(e, axis=0, return_inverse=True)
    inverse = np.asarray(inverse).reshape(-1)

    order = np.argsort(inverse, kind="stable")
    inv_sorted, tri_sorted = inverse[order], tri[order]
    counts = np.bincount(inv_sorted, minlength=len(uniq))
    starts = np.concatenate([[0], np.cumsum(counts)[:-1]])

    tri_a = tri_sorted[starts]
    tri_b = np.full(len(uniq), -1, dtype=np.int64)
    has_pair = counts >= 2
    tri_b[has_pair] = tri_sorted[starts[has_pair] + 1]
    return uniq, tri_a, tri_b


def _feature_edges(v, f, normals, crease_deg=22.0):
    """Edges worth drawing: creases and boundaries. Silhouettes are per-view."""
    edges, ta, tb = edge_adjacency(f)
    boundary = tb < 0
    dot = np.ones(len(edges))
    pair = ~boundary
    dot[pair] = np.einsum("ij,ij->i", normals[ta[pair]], normals[tb[pair]])
    crease = dot < math.cos(math.radians(crease_deg))
    return edges, ta, tb, (crease | boundary)


def _camera(eye_dir, up):
    """Orthographic basis. Returns (right, up, forward) with forward = view dir."""
    forward = -np.array(eye_dir, dtype=float)
    forward /= np.linalg.norm(forward)
    up = np.array(up, dtype=float)
    if abs(forward @ up) > 0.999:  # degenerate for top/bottom views
        up = np.array([0.0, 1.0, 0.0])
    right = np.cross(forward, up)
    right /= np.linalg.norm(right)
    true_up = np.cross(right, forward)
    return right, true_up, forward


def render_views(
    v: np.ndarray,
    f: np.ndarray,
    path,
    views=("iso", "front", "right", "top"),
    highlight: np.ndarray | None = None,
    title: str | None = None,
    dpi: int = 110,
):
    """Write a contact sheet PNG. ``highlight`` is a per-triangle boolean mask
    drawn in red (used for the overhang map)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection, PolyCollection

    normals, _ = triangle_normals(v, f)
    # Painter's algorithm: sorting on the farthest vertex beats the centroid
    # when a large background triangle meets a small foreground one.
    tri_depth_src = v[f]
    light = np.array([0.4, -0.7, 0.6])
    light /= np.linalg.norm(light)

    edges, tri_a, tri_b, static_feature = _feature_edges(v, f, normals)

    cols = min(len(views), 2)
    rows = math.ceil(len(views) / cols)
    fig, axes = plt.subplots(rows, cols, figsize=(5.2 * cols, 4.6 * rows))
    axes = np.atleast_1d(axes).ravel()

    for ax, name in zip(axes, views):
        eye_dir, up = VIEWS[name]
        right, true_up, forward = _camera(eye_dir, up)

        depth = (tri_depth_src @ forward).max(axis=1)
        facing = normals @ forward < 0  # keep front faces only
        order = np.argsort(-depth)
        order = order[facing[order]]

        pts2d = np.stack([v @ right, v @ true_up], axis=1)
        polys = pts2d[f[order]]

        shade = np.clip(normals[order] @ light, 0, 1) * 0.72 + 0.26
        colors = np.stack([shade * 0.72, shade * 0.78, shade * 0.86], axis=1)
        if highlight is not None and highlight.any():
            hot = highlight[order]
            colors[hot] = np.stack(
                [shade[hot] * 0.95, shade[hot] * 0.30, shade[hot] * 0.28], axis=1
            )

        # Outline: creases, boundaries, and this view's silhouette. Drawing
        # every mesh edge would bury the part in triangulation noise.
        has_pair = tri_b >= 0
        tb_safe = np.maximum(tri_b, 0)
        silhouette = has_pair & (facing[tri_a] != facing[tb_safe])
        draw = static_feature | silhouette
        visible = draw & (facing[tri_a] | (has_pair & facing[tb_safe]))
        vis_edges = edges[visible]
        edge_depth = (v[vis_edges] @ forward).mean(axis=1)

        # Interleave faces and lines in depth slabs so that outlines behind the
        # part are painted over, instead of showing through it.
        ordered_depth = depth[order]
        d_hi, d_lo = ordered_depth.max(), ordered_depth.min()
        slabs = 48 if d_hi > d_lo else 1
        bounds = np.linspace(d_hi, d_lo, slabs + 1)
        bounds[-1] -= 1e-9
        for k in range(slabs):
            top, bot = bounds[k], bounds[k + 1]
            sel = (ordered_depth <= top) & (ordered_depth > bot)
            if sel.any():
                ax.add_collection(
                    PolyCollection(polys[sel], facecolors=colors[sel],
                                   edgecolors="face", linewidths=0.3, zorder=2 * k)
                )
            esel = (edge_depth <= top) & (edge_depth > bot)
            if esel.any():
                ax.add_collection(
                    LineCollection(pts2d[vis_edges[esel]], colors="#20242b",
                                   linewidths=0.55, zorder=2 * k + 1)
                )

        lo, hi = polys.reshape(-1, 2).min(axis=0), polys.reshape(-1, 2).max(axis=0)
        pad = 0.06 * max(hi - lo).max() if (hi - lo).max() > 0 else 1.0
        ax.set_xlim(lo[0] - pad, hi[0] + pad)
        ax.set_ylim(lo[1] - pad, hi[1] + pad)
        ax.set_aspect("equal")
        ax.set_title(name, fontsize=10)
        ax.tick_params(labelsize=7)
        ax.grid(alpha=0.15, linewidth=0.4)

    for ax in axes[len(views):]:
        ax.axis("off")
    if title:
        fig.suptitle(title, fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=dpi)
    plt.close(fig)
    return path


def box_mesh(a: float, b: float, c: float, origin=(0.0, 0.0, 0.0)):
    """An axis-aligned box with outward winding. Used by the self-test."""
    ox, oy, oz = origin
    v = np.array(
        [
            [ox, oy, oz], [ox + a, oy, oz], [ox + a, oy + b, oz], [ox, oy + b, oz],
            [ox, oy, oz + c], [ox + a, oy, oz + c],
            [ox + a, oy + b, oz + c], [ox, oy + b, oz + c],
        ],
        dtype=float,
    )
    f = np.array(
        [
            [0, 2, 1], [0, 3, 2],      # bottom, -Z
            [4, 5, 6], [4, 6, 7],      # top, +Z
            [0, 1, 5], [0, 5, 4],      # front, -Y
            [3, 7, 6], [3, 6, 2],      # back, +Y
            [0, 4, 7], [0, 7, 3],      # left, -X
            [1, 2, 6], [1, 6, 5],      # right, +X
        ],
        dtype=np.int64,
    )
    return v, f


def _self_test() -> int:
    """Check the numeric core against a shape whose answers are known."""
    failures = []

    def check(label, got, want, tol=1e-6):
        ok = abs(got - want) <= tol if isinstance(want, float) else got == want
        print(f"{'  ok  ' if ok else ' FAIL '} {label}: {got!r} (want {want!r})")
        if not ok:
            failures.append(label)

    v, f = box_mesh(20.0, 20.0, 2.0)
    topo = topology(v, f)
    check("watertight", topo.watertight, True)
    check("consistent winding", topo.consistent_winding, True)
    check("shells", topo.shells, 1)
    check("signed volume", signed_volume(v, f), 800.0, 1e-9)
    check("surface area", float(triangle_normals(v, f)[1].sum()), 960.0, 1e-9)

    _, flipped = orient_outward(v, f)
    check("normals already outward", flipped, False)

    over = overhangs(v, f)
    check("overhang area", over.overhang_area, 0.0, 1e-9)
    check("bed contact", over.bed_contact_area, 400.0, 1e-9)

    thick = wall_thickness(v, f, samples=120)
    check("min wall thickness", round(thick.min_thickness, 3), 2.0, 1e-3)

    v2, f2 = box_mesh(5.0, 5.0, 5.0, origin=(50.0, 0.0, 0.0))
    both_v = np.vstack([v, v2])
    both_f = np.vstack([f, f2 + len(v)])
    check("two disjoint bodies", topology(both_v, both_f).shells, 2)

    print("\nself-test:", "FAILED " + ", ".join(failures) if failures else "OK")
    return 1 if failures else 0


def render_sections(section_polylines, path, title=None, dpi: int = 110):
    """Draw 2D cross sections. ``section_polylines`` is a list of
    (label, [array(n,2), ...]) - closed loops in plane-local mm coordinates."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    n = len(section_polylines)
    if n == 0:
        return None
    fig, axes = plt.subplots(1, n, figsize=(5.0 * n, 4.6))
    axes = np.atleast_1d(axes).ravel()

    # Give every panel the same scale, otherwise a small section is drawn as
    # large as a big one and the sheet is misleading.
    span = 0.0
    for _, loops in section_polylines:
        pts = np.vstack(loops)
        span = max(span, (pts.max(axis=0) - pts.min(axis=0)).max())
    span = (span or 1.0) * 1.1

    for ax, (label, loops) in zip(axes, section_polylines):
        for loop in loops:
            ax.plot(loop[:, 0], loop[:, 1], linewidth=1.1, color="#1f4e79")
        pts = np.vstack(loops)
        mid = (pts.max(axis=0) + pts.min(axis=0)) / 2
        ax.set_xlim(mid[0] - span / 2, mid[0] + span / 2)
        ax.set_ylim(mid[1] - span / 2, mid[1] + span / 2)
        ax.set_aspect("equal")
        ax.set_title(label, fontsize=10)
        ax.grid(alpha=0.2, linewidth=0.4)
        ax.tick_params(labelsize=7)
    if title:
        fig.suptitle(title, fontsize=11)
    fig.tight_layout()
    fig.savefig(path, dpi=dpi)
    plt.close(fig)
    return path


if __name__ == "__main__":
    import sys

    sys.exit(_self_test())
