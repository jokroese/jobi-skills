# build123d troubleshooting

Symptom → cause → fix. Work down the list before rewriting the model.

---

## Kernel failures

**`StdFail_NotDone` / `BRep_API: command not done` from `fillet`**
The radius is too large for the local geometry, or the edge chain is
inconsistent. Fix: reduce the radius, fillet fewer edges per call, or use
`part.max_fillet(edges)` to find the largest workable radius. Better: do the
rounding in 2D with `FilletPolyline` or a sketch fillet before extruding.

**`fillet` works alone but fails after another fillet**
The first fillet changed the edge you selected. Re-select from the *current*
shape between operations, and apply the largest fillets first.

**`Standard_ConstructionError` from `offset` with a negative amount**
The shell wall is thicker than the smallest internal radius, so the offset
surface self-intersects. Fix: reduce `amount`, or increase the internal fillets
before shelling.

**`loft` fails / produces a twisted solid**
Sections have different vertex counts, different hole counts, or mismatched
start points. Fix: make sections topologically identical (same number of edges),
or use `ruled=True`, or fall back to `sweep` / stacked extrudes.

**`sweep` fails on a path with sharp corners**
Try `transition=Transition.ROUND`, or fillet the path first, or split the sweep
into segments and fuse them.

**Helical / threaded shape reports valid but behaves badly**
A helix that touches itself after one revolution creates a self-intersecting
topology. Split it into ≤180° segments and fuse, per the build123d docs.

---

## Wrong result, no error

**Sketch features land in the wrong corner**
`BuildSketch` always builds on a *local* `Plane.XY` regardless of the plane you
passed. `sort_by(Axis.Z)` inside a sketch sorts points that are all at Z=0 and
returns an arbitrary one. Sort by `Axis.X` / `Axis.Y` in sketch-local terms.

**A nested `BuildLine(Plane.XZ)` inside `BuildSketch` gives a rotated face**
Builders do not inherit their parent's placement. Leave nested `BuildLine` on
the default plane and place the finished sketch instead.

**Selector picks a different edge after a parameter change**
You used a bare index. Replace `edges()[3]` with a topological narrowing:
select the face first, then `filter_by(GeomType.CIRCLE)` or
`group_by(Axis.Z)[-1]`.

**A feature floats just above the face it should sit on**
`Box(40, 40, 4)` is **centred**, so its top face is at z = 2, not z = 4.
`BuildSketch(Plane.XY.offset(4))` then puts the boss 2 mm into thin air, the
fuse does nothing, and the render still looks plausible from most angles. Two
tells: `len(part.solids()) == 2`, and the volume is exactly the sum of the two
pieces. Fix: `align=(Align.CENTER, Align.CENTER, Align.MIN)` so the top face is
at the thickness you typed, or offset by half.

**Boolean leaves a coplanar seam / stray internal face**
Call `.clean()` on the result, or build the union in one operation instead of
several. Check `len(part.solids())` — more than one means the fuse did not
actually merge.

**Part looks right but volume is wrong**
Almost always a subtraction that missed: the cutting solid did not reach through
the material. Give cutters extra length (`height + 2 * EPS`) so they poke out
both sides, and never let a cutter face be exactly coplanar with a part face.

**Result is empty / `None`**
In builder mode an operation ran with `mode=Mode.SUBTRACT` before anything was
added, or `extrude` consumed pending faces you expected to still be there.
Check `part.part is not None` and print `len(part.solids())` as you go.

---

## Coplanar and zero-thickness traps

Never let two faces be exactly coincident in a boolean. Use a small epsilon:

```python
EPS = 0.01   # mm, keeps booleans off coincident faces
cutter = Cylinder(radius=r, height=thickness + 2 * EPS)
```

Zero-length edges and zero-area faces come from a parameter that collapsed
(a fillet radius equal to half the width, a slot as long as it is wide). The
`shortest_edge_mm` line in the inspection report catches these.

---

## Performance

- Do 2D work before 3D. Sketch, fillet in 2D, then extrude once.
- Apply fillets and chamfers **last**, and only to the edges that need them.
- `Mode.PRIVATE` for construction geometry so it does not enter the part.
- Use shallow copies for repeated components in an assembly.
- Tessellation tolerance: `0.05` for inspection, `1e-3` only for final STL.
- If a model takes minutes, the usual culprit is a fillet applied to a
  `.edges()` list that contains hundreds of edges from an already-rounded shape.

---

## Environment

```
pip install build123d          # pulls in cadquery-ocp (large, ~500 MB)
pip install numpy matplotlib   # for the inspection scripts
```

`build123d` needs a 64-bit Python 3.10+. On headless Linux nothing here needs a
display: the renderer uses the matplotlib `Agg` backend and the geometry checks
are pure numpy.

If `import build123d` fails with an OCP symbol error, the `cadquery-ocp` wheel
does not match the interpreter — recreate the venv rather than pinning around it.

---

## When the CAD kernel simply will not do it

From the build123d docs: not every describable part can be built. If a
multi-section `sweep` fails, try `loft`. If `loft` fails, try stacked extrudes
with a `draft`. If a 3D fillet fails, move it into the sketch. Changing the
construction strategy is normal and is usually faster than fighting OCCT.
