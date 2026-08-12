#!/usr/bin/env python3
"""Run a build123d model, measure it, check it, export it, and render it.

    python inspect_part.py model.py --out build/

The model file must expose a build123d shape at module level. The script looks
for, in order: the name given by --var, then `result`, `part`, `assembly`,
`RESULT`, `PART`; failing that it calls a module-level `build()`.

An optional module-level `EXPECT` dict turns design intent into pass/fail
assertions:

    EXPECT = {
        "bbox": (80.0, 60.0, 12.0),   # mm, X Y Z
        "volume": 38200.0,            # mm^3
        "solids": 1,
        "watertight": True,
        "min_wall": 1.2,              # mm, floor
        "max_overhang_deg": 45.0,
        "tol": 0.01,                  # relative tolerance for bbox/volume
    }

Exit code is 1 if any check fails, so this works as a build gate.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import math
import sys

import traceback
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import meshtools  # noqa: E402

CANDIDATE_NAMES = ("result", "part", "assembly", "RESULT", "PART", "shape")

DENSITIES_G_CM3 = {
    "pla": 1.24,
    "petg": 1.27,
    "abs": 1.04,
    "asa": 1.07,
    "tpu": 1.21,
    "nylon": 1.14,
    "pc": 1.20,
    "resin": 1.15,
    "aluminium": 2.70,
    "steel": 7.85,
}


# --------------------------------------------------------------------------


class Results:
    def __init__(self):
        self.lines = []
        self.failed = 0
        self.warned = 0

    def add(self, status: str, label: str, detail: str = ""):
        if status == "FAIL":
            self.failed += 1
        elif status == "WARN":
            self.warned += 1
        self.lines.append({"status": status, "check": label, "detail": detail})

    def check(self, ok: bool, label: str, detail: str = "", warn_only: bool = False):
        self.add("PASS" if ok else ("WARN" if warn_only else "FAIL"), label, detail)

    def print(self):
        icons = {"PASS": "  ok ", "WARN": " warn", "FAIL": " FAIL"}
        for line in self.lines:
            detail = f"  -  {line['detail']}" if line["detail"] else ""
            print(f"{icons[line['status']]}  {line['check']}{detail}")


def load_shape(model_path: Path, var: str | None):
    spec = importlib.util.spec_from_file_location(model_path.stem, model_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {model_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    sys.path.insert(0, str(model_path.resolve().parent))
    spec.loader.exec_module(module)

    names = [var] if var else list(CANDIDATE_NAMES)
    for name in names:
        obj = getattr(module, name, None)
        if obj is not None:
            return unwrap(obj, name), module
    builder = getattr(module, "build", None)
    if callable(builder):
        return unwrap(builder(), "build()"), module
    raise RuntimeError(
        f"no shape found in {model_path.name}: expose one of {CANDIDATE_NAMES} "
        "or a build() function, or pass --var"
    )


def unwrap(obj, name):
    """Accept a Shape, or a Builder (BuildPart/BuildSketch/BuildLine)."""
    if hasattr(obj, "wrapped"):
        return obj
    for attr in ("part", "sketch", "line"):
        inner = getattr(obj, attr, None)
        if inner is not None and hasattr(inner, "wrapped"):
            return inner
    raise RuntimeError(f"`{name}` is a {type(obj).__name__}, not a build123d shape")


def jsonable(obj):
    """json.dumps writes bare Infinity, which most parsers reject."""
    if isinstance(obj, float):
        return None if not math.isfinite(obj) else obj
    if isinstance(obj, dict):
        return {k: jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [jsonable(v) for v in obj]
    return obj


def approx(actual, expected, tol):
    if expected == 0:
        return abs(actual) <= tol
    return abs(actual - expected) <= abs(expected) * tol


# --------------------------------------------------------------------------


def cad_measurements(shape, res: Results) -> dict:
    bb = shape.bounding_box()
    solids = shape.solids()
    faces = shape.faces()
    edges = shape.edges()

    try:
        centre = shape.center()
        centre = [round(centre.X, 4), round(centre.Y, 4), round(centre.Z, 4)]
    except Exception:
        centre = None

    edge_lengths = []
    for e in edges:
        try:
            edge_lengths.append(e.length)
        except Exception:
            pass

    m = {
        "bbox_min": [round(bb.min.X, 4), round(bb.min.Y, 4), round(bb.min.Z, 4)],
        "bbox_max": [round(bb.max.X, 4), round(bb.max.Y, 4), round(bb.max.Z, 4)],
        "bbox_size": [round(bb.size.X, 4), round(bb.size.Y, 4), round(bb.size.Z, 4)],
        "volume_mm3": round(shape.volume, 4),
        "area_mm2": round(shape.area, 4),
        "center_of_mass": centre,
        "solids": len(solids),
        "faces": len(faces),
        "edges": len(edges),
        "shortest_edge_mm": round(min(edge_lengths), 5) if edge_lengths else None,
    }

    res.check(bool(shape.is_valid), "kernel reports a valid shape")
    res.check(m["volume_mm3"] > 0, "volume is positive", f"{m['volume_mm3']:.2f} mm^3")
    res.check(m["solids"] == 1, "single solid body", f"{m['solids']} solid(s)", warn_only=True)
    if m["shortest_edge_mm"] is not None:
        res.check(
            m["shortest_edge_mm"] > 1e-3,
            "no degenerate edges",
            f"shortest edge {m['shortest_edge_mm']:.4f} mm",
        )
    return m


def mesh_measurements(shape, args, res: Results) -> tuple[dict, object]:
    v, f = meshtools.tessellate(shape, args.tol, args.angular_tol)
    f, flipped = meshtools.orient_outward(v, f)
    topo = meshtools.topology(v, f)
    over = meshtools.overhangs(v, f, args.build_dir, args.overhang_angle)
    thick = meshtools.wall_thickness(v, f, samples=args.samples)

    res.check(topo.watertight, "mesh is watertight",
              f"{topo.boundary_edges} boundary / {topo.nonmanifold_edges} non-manifold edges")
    res.check(topo.consistent_winding, "mesh winding is consistent", warn_only=True)
    res.check(not flipped, "mesh normals point outward",
              "winding was inverted and has been corrected" if flipped else "", warn_only=True)

    mesh_vol = abs(meshtools.signed_volume(v, f))
    res.check(
        approx(mesh_vol, shape.volume, 0.02),
        "mesh volume agrees with kernel volume",
        f"mesh {mesh_vol:.1f} vs kernel {shape.volume:.1f} mm^3",
        warn_only=True,
    )

    if args.min_wall:
        res.check(
            thick.min_thickness >= args.min_wall,
            f"min wall >= {args.min_wall} mm",
            f"sampled min {thick.min_thickness:.3f} mm (p05 {thick.p05:.3f})",
        )
    res.check(
        over.overhang_fraction < 0.02,
        f"no unsupported overhang beyond {args.overhang_angle} deg",
        f"{over.overhang_area:.1f} mm^2 "
        f"({100 * over.overhang_fraction:.1f}% of surface), worst {over.max_overhang_deg:.0f} deg",
        warn_only=True,
    )
    res.check(
        over.bed_contact_area > 0,
        "part has a flat face on the build plate",
        f"{over.bed_contact_area:.1f} mm^2 contact",
        warn_only=True,
    )

    data = {
        "triangles": int(len(f)),
        "vertices": int(len(v)),
        "watertight": topo.watertight,
        "boundary_edges": topo.boundary_edges,
        "nonmanifold_edges": topo.nonmanifold_edges,
        "mesh_shells": topo.shells,
        "mesh_volume_mm3": round(mesh_vol, 4),
        "overhang": {
            "threshold_deg": over.threshold_deg,
            "area_mm2": round(over.overhang_area, 3),
            "fraction": round(over.overhang_fraction, 5),
            "worst_deg": round(over.max_overhang_deg, 2),
            "bed_contact_mm2": round(over.bed_contact_area, 3),
        },
        "wall_thickness": {k: v2 for k, v2 in asdict(thick).items()},
    }
    return data, (v, f, over)


def check_expectations(expect: dict, cad: dict, mesh: dict, res: Results):
    tol = float(expect.get("tol", 0.01))
    if "bbox" in expect:
        want = list(expect["bbox"])
        got = cad["bbox_size"]
        ok = all(approx(g, w, tol) for g, w in zip(got, want))
        res.check(ok, "EXPECT bbox", f"got {got} want {want} (tol {tol:.1%})")
    if "volume" in expect:
        res.check(
            approx(cad["volume_mm3"], float(expect["volume"]), tol),
            "EXPECT volume",
            f"got {cad['volume_mm3']:.1f} want {float(expect['volume']):.1f} mm^3",
        )
    if "solids" in expect:
        res.check(cad["solids"] == int(expect["solids"]), "EXPECT solids",
                  f"got {cad['solids']} want {expect['solids']}")
    if "watertight" in expect:
        res.check(mesh["watertight"] == bool(expect["watertight"]), "EXPECT watertight")
    if "min_wall" in expect:
        got = mesh["wall_thickness"]["min_thickness"]
        res.check(got >= float(expect["min_wall"]), "EXPECT min_wall",
                  f"sampled {got:.3f} mm >= {expect['min_wall']} mm")
    if "max_overhang_deg" in expect:
        got = mesh["overhang"]["worst_deg"]
        res.check(got <= float(expect["max_overhang_deg"]), "EXPECT max_overhang_deg",
                  f"worst {got:.1f} deg")


def do_exports(shape, out: Path, stem: str, formats: list[str], res: Results) -> dict:
    written = {}
    for fmt in formats:
        target = out / f"{stem}.{fmt}"
        try:
            if fmt == "step":
                from build123d import export_step

                export_step(shape, str(target))
            elif fmt == "stl":
                from build123d import export_stl

                export_stl(shape, str(target), tolerance=1e-3, angular_tolerance=0.1)
            elif fmt == "3mf":
                from build123d import Mesher

                mesher = Mesher()
                mesher.add_shape(shape)
                mesher.write(str(target))
            elif fmt == "brep":
                from build123d import export_brep

                export_brep(shape, str(target))
            else:
                res.add("WARN", f"export .{fmt}", "unknown format, skipped")
                continue
            written[fmt] = str(target)
            res.check(target.exists() and target.stat().st_size > 0, f"export .{fmt}", target.name)
        except Exception as exc:  # noqa: BLE001
            res.add("FAIL", f"export .{fmt}", f"{type(exc).__name__}: {exc}")
    return written


def do_sections(shape, out: Path, stem: str, res: Results):
    """Mid-plane cross sections, drawn from the real B-rep (not the mesh)."""
    import numpy as np

    try:
        from build123d import Plane, section

        bb = shape.bounding_box()
        cx = (bb.min.X + bb.max.X) / 2
        cy = (bb.min.Y + bb.max.Y) / 2
        cz = (bb.min.Z + bb.max.Z) / 2
        centre = (cx, cy, cz)
        planes = [
            (f"section XZ (y={cy:.1f})", Plane(origin=centre, z_dir=(0, 1, 0))),
            (f"section YZ (x={cx:.1f})", Plane(origin=centre, z_dir=(1, 0, 0))),
            (f"section XY (z={cz:.1f})", Plane(origin=centre, z_dir=(0, 0, 1))),
        ]
        drawings = []
        for label, plane in planes:
            sketch = section(shape, section_by=plane)
            loops = []
            for edge in sketch.edges():
                try:
                    n = max(2, min(96, int(edge.length / 0.4)))
                except Exception:
                    n = 24
                pts = []
                for i in range(n + 1):
                    local = plane.to_local_coords(edge @ (i / n))
                    pts.append((local.X, local.Y))
                if pts:
                    loops.append(np.array(pts))
            if loops:
                drawings.append((label, loops))
        if not drawings:
            return None
        path = out / f"{stem}_sections.png"
        meshtools.render_sections(drawings, path, title=f"{stem} - cross sections")
        res.add("PASS", "cross sections rendered", path.name)
        return str(path)
    except Exception as exc:  # noqa: BLE001
        res.add("WARN", "cross sections", f"{type(exc).__name__}: {exc}")
        return None


# --------------------------------------------------------------------------


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("model", type=Path, help="python file defining the part")
    ap.add_argument("--out", type=Path, default=Path("build"), help="output directory")
    ap.add_argument("--var", default=None, help="module attribute holding the shape")
    ap.add_argument("--formats", default="step,stl,3mf", help="comma separated: step,stl,3mf,brep")
    ap.add_argument("--tol", type=float, default=0.05, help="tessellation linear deflection, mm")
    ap.add_argument("--angular-tol", type=float, default=0.2)
    ap.add_argument("--samples", type=int, default=400, help="wall thickness ray samples")
    ap.add_argument("--min-wall", type=float, default=None, help="fail below this wall thickness, mm")
    ap.add_argument("--overhang-angle", type=float, default=45.0, help="slicer support threshold, deg")
    ap.add_argument("--build-dir", default="0,0,1", help="build direction, e.g. 0,0,1")
    ap.add_argument("--bed", default=None, help="build volume WxDxH in mm, e.g. 256x256x256")
    ap.add_argument("--material", default="pla", help=f"one of {', '.join(DENSITIES_G_CM3)}")
    ap.add_argument("--infill", type=float, default=1.0, help="0-1, scales the mass estimate")
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--no-sections", action="store_true")
    ap.add_argument("--views", default="iso,front,right,top")
    args = ap.parse_args()
    args.build_dir = tuple(float(x) for x in args.build_dir.split(","))

    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    stem = args.model.stem
    res = Results()

    print(f"\n=== {args.model} ===")
    try:
        shape, module = load_shape(args.model, args.var)
    except Exception:
        traceback.print_exc()
        print("\nFAILED: the model did not build.")
        return 1
    res.add("PASS", "model built", type(shape).__name__)

    cad = cad_measurements(shape, res)
    mesh, mesh_arrays = mesh_measurements(shape, args, res)

    density = DENSITIES_G_CM3.get(args.material.lower())
    mass_g = None
    if density:
        mass_g = cad["volume_mm3"] / 1000.0 * density * args.infill

    if args.bed:
        try:
            bed = [float(x) for x in args.bed.lower().replace("*", "x").split("x")]
            fits = all(s <= b + 1e-9 for s, b in zip(sorted(cad["bbox_size"]), sorted(bed)))
            res.check(fits, "fits the build volume", f"{cad['bbox_size']} vs {bed}")
        except ValueError:
            res.add("WARN", "build volume", f"could not parse --bed {args.bed}")

    expect = getattr(module, "EXPECT", None)
    if isinstance(expect, dict):
        check_expectations(expect, cad, mesh, res)
    else:
        res.add("WARN", "EXPECT block", "none defined - design intent is unverified")

    written = do_exports(shape, out, stem, [f.strip() for f in args.formats.split(",") if f.strip()], res)

    render_paths = {}
    if not args.no_render:
        v, f, over = mesh_arrays
        try:
            p = out / f"{stem}_views.png"
            meshtools.render_views(v, f, p, views=[x.strip() for x in args.views.split(",")],
                                   title=f"{stem}  {cad['bbox_size']} mm")
            render_paths["views"] = str(p)
            res.add("PASS", "views rendered", p.name)
            p2 = out / f"{stem}_overhangs.png"
            meshtools.render_views(v, f, p2, views=["iso", "iso_rear", "front", "bottom"],
                                   highlight=over.mask,
                                   title=f"{stem}  red = overhang > {args.overhang_angle:.0f} deg")
            render_paths["overhangs"] = str(p2)
            res.add("PASS", "overhang map rendered", p2.name)
        except ImportError:
            res.add("WARN", "rendering", "matplotlib not installed (pip install matplotlib)")
        except Exception as exc:  # noqa: BLE001
            res.add("WARN", "rendering", f"{type(exc).__name__}: {exc}")
    if not args.no_sections:
        sec = do_sections(shape, out, stem, res)
        if sec:
            render_paths["sections"] = sec

    report = {
        "model": str(args.model),
        "cad": cad,
        "mesh": mesh,
        "mass_estimate_g": round(mass_g, 2) if mass_g else None,
        "material": args.material,
        "exports": written,
        "renders": render_paths,
        "checks": res.lines,
        "failed": res.failed,
        "warned": res.warned,
    }
    (out / f"{stem}_report.json").write_text(json.dumps(jsonable(report), indent=2))

    print(f"\nbbox      {cad['bbox_size'][0]:.2f} x {cad['bbox_size'][1]:.2f} x {cad['bbox_size'][2]:.2f} mm")
    print(f"volume    {cad['volume_mm3']:.1f} mm^3    area {cad['area_mm2']:.1f} mm^2")
    if mass_g:
        print(f"mass      ~{mass_g:.1f} g solid {args.material}" +
              (f" x {args.infill:.0%} infill" if args.infill != 1.0 else ""))
    tw = mesh["wall_thickness"]
    if tw["samples"]:
        print(f"wall      min {tw['min_thickness']:.2f} mm   p05 {tw['p05']:.2f}   median {tw['median']:.2f}")
    print(f"overhang  {mesh['overhang']['area_mm2']:.1f} mm^2 above {args.overhang_angle:.0f} deg\n")
    res.print()
    print(f"\n{res.failed} failed, {res.warned} warnings -> {out}/{stem}_report.json")
    if render_paths:
        print("Look at the renders before you call this done:")
        for k, p in render_paths.items():
            print(f"  {k}: {p}")
    return 1 if res.failed else 0


if __name__ == "__main__":
    sys.exit(main())
