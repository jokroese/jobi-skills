---
name: build123d
description: Design parametric 3D-printable mechanical parts as build123d Python code, then verify them by running the model headlessly - measuring bounding box, volume, watertightness, wall thickness and overhangs, exporting STEP/STL/3MF, and rendering PNG views to look at. Use for any request to model, design, CAD, or generate a part, bracket, enclosure, adapter, jig, fixture, mount or fitting in build123d, CadQuery-style Python CAD, or code-CAD generally, and for editing, parameterising, debugging or checking existing build123d models.
---

# build123d parts that are right, not just plausible

A CAD model that imports without error can still be the wrong size, fall apart
into two bodies, have a 0.3 mm wall, or be unprintable. **Write the model, then
run it and look at it.** The scripts here make that a single command.

## Quick start

```bash
pip install build123d numpy matplotlib
python scripts/inspect_part.py my_part.py --out build --min-wall 1.2
```

Then **read the PNGs it writes**. Renders are not decoration — they are the only
check that catches "the boss is on the wrong face".

---

## The loop

### 1. Pin down the spec before writing code

Most bad parts come from a guessed dimension, not bad code. Get, or explicitly
assume in writing:

- what it mates with, and the mating dimensions (fastener sizes, PCB outline,
  shaft diameter, hole pattern pitch)
- load direction and rough magnitude
- material and printer (nozzle, layer height, build volume)
- which face goes on the build plate

Ask for anything load-bearing you cannot derive. State every assumption you had
to make at the top of the file, so the user can correct one number instead of
the whole part.

### 2. Write one file, parameters first

Copy `assets/part_template.py`. The structure that matters:

```python
@dataclass(frozen=True)
class Params:
    plate_t: float = 4.0        # mm, 10 x extrusion width
    bolt_d: float = 3.4         # mm, M3 medium clearance, ISO 273

def build(p: Params = Params()) -> Part: ...

result = build()
EXPECT = {"bbox": (80, 60, 12), "solids": 1, "watertight": True, "min_wall": 1.2}
```

`result` at module level is how the inspector finds the part. `EXPECT` is how it
knows what you meant.

### 3. Inspect

```bash
python scripts/inspect_part.py my_part.py --out build \
    --min-wall 1.2 --overhang-angle 45 --bed 256x256x256 --material petg
```

It runs the model and reports: kernel validity, solid count, bbox, volume, area,
centre of mass, watertightness, sampled minimum wall thickness, overhang area
and worst angle, bed contact area, mass estimate, and every `EXPECT` assertion.
It writes STEP + STL + 3MF, a JSON report, and three PNGs:

| File | What to look for |
|---|---|
| `*_views.png` | iso / front / right / top — is this the part you described? |
| `*_overhangs.png` | red = needs support. Red anywhere you did not intend it is a design bug. |
| `*_sections.png` | cross sections — internal cavities, wall thickness, hidden voids |

Exit code is non-zero when a check fails, so it works as a build gate.

### 4. Fix and re-run

Change a parameter, not a coordinate. If you find yourself typing a number that
should have been derived (`hole_y = 16.0` instead of `corner + hole_offset`),
that is the bug.

### 5. Deliver

The STEP is the source of truth, the 3MF goes to the slicer. Hand over the model
file, the exports, the renders, and a short parameter table with the print
orientation and the assumptions you made.

---

## Rules that keep parts accurate

**Every number is named and sourced.** `3.4  # M3 medium clearance, ISO 273`,
not a bare `3.4`. If a number came from a guess, the comment says so.

**Separate nominal from allowance.** `hole_d = BOLT_D + FIT_CLEARANCE`. Never
bake a fit into a single literal — the user will need to tune it for their
printer, and they can only do that if the allowance has its own name.

**Derive positions, never eyeball them.** A feature at `x = 23.5` is a latent
bug. It should be `wall + boss_r + margin`.

**Build 2D first, extrude once.** Sketch, fillet the sketch, then extrude.
3D booleans are slower and fail more often. Round outlines with
`FilletPolyline` rather than filleting the solid.

**Fillets and chamfers last**, on selectors, never on bare indices. Radius must
be under half the local material width or OCCT will refuse.

**Select topologically.** `part.faces().sort_by(Axis.Z)[-1].edges().filter_by(GeomType.CIRCLE)`
survives a parameter change; `part.edges()[7]` does not.

**Keep cutters oversize.** Give every subtracting solid an extra `2 * EPS` so no
two faces end up exactly coplanar — that is the number one cause of a boolean
that silently leaves a skin.

**Check `len(part.solids()) == 1`.** Two solids means a fuse that did not touch.
The renders will look fine and the print will fall apart.

**Assert the volume.** Once the part is right, copy the reported volume into
`EXPECT["volume"]`. Every later edit is then guarded against a silent collapse.

---

## Rules that keep parts printable

Full tables in `references/printing.md`. The short version:

- Walls: multiples of the extrusion width. 0.84 mm minimum, 1.6 mm structural.
- Overhangs: nothing beyond 45° from vertical without support. Replace overhangs
  with chamfers; they are free.
- Holes print undersize, pegs oversize. Model the clearance: 0.2 mm snug,
  0.3–0.4 mm free running, 0.5 mm loose.
- Horizontal holes want a teardrop top. Vertical holes want nothing.
- Chamfer 0.5 mm on every edge touching the bed.
- Threads: heat-set insert > captive nut > tapped > printed.
- Layer adhesion is about half the in-plane strength. Orient loads in-plane.
- Fillet internal corners; they are where printed parts crack.

---

## Reference files

Read the one you need, when you need it.

| File | Contents |
|---|---|
| `references/api.md` | Objects, operations, selectors, planes, locations, export — real signatures |
| `references/recipes.md` | Working code for plates, enclosures, bosses, nut pockets, teardrops, bearings, gussets, splits |
| `references/printing.md` | FDM design rules, clearance / fastener / insert tables, materials, orientation |
| `references/troubleshooting.md` | Kernel errors and silent wrong results, with fixes |
| `assets/part_template.py` | Complete worked example to copy |

`scripts/meshtools.py` is importable if you want the mesh analysis
(`tessellate`, `topology`, `overhangs`, `wall_thickness`, `render_views`)
inside your own script. Running it directly self-tests the numeric core against
a shape with known answers — a quick way to tell a broken environment from a
broken model, and it needs only numpy:

```bash
python3 scripts/meshtools.py
```

---

## Two things that catch most beginner mistakes

**Sketches are always local.** `BuildSketch(Plane.XZ)` still builds on a local
`Plane.XY` and is only placed when the context exits. So a `sort_by(Axis.Z)`
selector inside that sketch sorts points that are all at Z = 0 and returns an
arbitrary one. Sort in sketch-local X/Y. Nested builders never inherit their
parent's placement.

**Algebra mode composes left to right.** `Plane.XZ * Pos(1, 2, 3) * Rot(0, 90, 0) * Box(...)`
means "on the XZ plane, moved in *that plane's* coordinates, then rotated
there". `*` binds tighter than `+ - &`, so brackets are rarely needed.

---

## When you cannot run the model

If build123d is not installed and cannot be, say so plainly and mark the model
as unverified rather than implying it was checked. Then at minimum: keep the
parameter block, keep `EXPECT`, and hand over the exact command the user should
run. Never present an unrun model as a finished part.
