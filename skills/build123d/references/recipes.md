# Recipes

Working patterns for the features that come up in almost every mechanical part.
All dimensions in mm. Copy, rename the parameters, keep the comments.

---

## Mounting plate with counterbored holes

```python
from build123d import *

L, W, T = 80.0, 60.0, 6.0
BOLT = 3.4          # M3 medium clearance
CB_D, CB_H = 6.0, 3.2   # DIN 912 M3 head + 0.2
PITCH_X, PITCH_Y = 60.0, 40.0

with BuildPart() as plate:
    Box(L, W, T)
    with GridLocations(PITCH_X, PITCH_Y, 2, 2):
        CounterBoreHole(radius=BOLT / 2, counter_bore_radius=CB_D / 2,
                        counter_bore_depth=CB_H)
    fillet(plate.edges().filter_by(Axis.Z), radius=5)
    # elephant-foot chamfer on the bed face
    chamfer(plate.faces().sort_by(Axis.Z)[0].edges(), length=0.5)

result = plate.part
```

Counterbores are cut from the **top** face (+Z). Flip the box or use
`Plane.XY.offset(T)` mirrored if you want them underneath.

---

## Rounded outline in 2D, then extrude

Cheaper and far more robust than filleting the solid.

```python
with BuildPart() as bracket:
    with BuildSketch() as profile:
        with BuildLine():
            FilletPolyline((0, 0), (40, 0), (40, 25), (0, 25), radius=4, close=True)
        make_face()
    extrude(amount=5)
```

---

## Shelled enclosure with a lid lip

```python
WALL = 2.0
BODY_L, BODY_W, BODY_H = 70.0, 50.0, 30.0
LIP_H, LIP_CLEAR = 3.0, 0.2     # 0.2 mm snug sliding fit

with BuildPart() as box:
    Box(BODY_L, BODY_W, BODY_H, align=(Align.CENTER, Align.CENTER, Align.MIN))
    fillet(box.edges().filter_by(Axis.Z), radius=4)
    top = box.faces().sort_by(Axis.Z)[-1]
    offset(amount=-WALL, openings=top)          # hollow it, leave the top open

with BuildPart() as lid:
    Box(BODY_L, BODY_W, WALL, align=(Align.CENTER, Align.CENTER, Align.MIN))
    fillet(lid.edges().filter_by(Axis.Z), radius=4)
    with BuildSketch(Plane.XY.offset(WALL)) as lip:
        RectangleRounded(BODY_L - 2 * WALL - LIP_CLEAR,
                         BODY_W - 2 * WALL - LIP_CLEAR, radius=2)
        RectangleRounded(BODY_L - 4 * WALL - LIP_CLEAR,
                         BODY_W - 4 * WALL - LIP_CLEAR, radius=1, mode=Mode.SUBTRACT)
    extrude(amount=LIP_H)
```

`offset(amount=-WALL, openings=face)` is the shell operation. The lip is drawn
as two nested rounded rectangles rather than offsetting a wire — more reliable.

---

## Boss for a heat-set insert

```python
INSERT_D, INSERT_L = 4.0, 5.7    # ruthex M3 x 5.7 -> 4.0 mm hole
BOSS_WALL = 1.8                  # >= 1.6 mm around the insert

with BuildPart() as part:
    # align MIN so the top face is at z = 4 and the boss sketch lands on it
    Box(40, 40, 4, align=(Align.CENTER, Align.CENTER, Align.MIN))
    with BuildSketch(Plane.XY.offset(4)) as boss_sk:
        Circle(INSERT_D / 2 + BOSS_WALL)
    extrude(amount=INSERT_L + 1.0)
    top = part.faces().sort_by(Axis.Z)[-1]
    with BuildSketch(Plane(top)):
        Circle(INSERT_D / 2)
    extrude(amount=-(INSERT_L + 1.0), mode=Mode.SUBTRACT)
    chamfer(part.faces().sort_by(Axis.Z)[-1].edges().filter_by(GeomType.CIRCLE)
            .sort_by(SortBy.RADIUS)[0], length=0.5)   # lead-in for the insert
```

Hole depth is insert length + 1 mm so displaced plastic has somewhere to go.

---

## Captive hex nut pocket

```python
NUT_AF, NUT_T = 5.7, 2.6      # M3 across flats + 0.2, thickness + 0.2
BOLT = 3.4

with BuildPart() as part:
    Box(30, 20, 12)
    Hole(radius=BOLT / 2)                     # bolt axis is Z
    # The nut lies perpendicular to the bolt, so the pocket is a hex prism
    # along Z. The rectangle is the slot you drop the nut in through.
    with BuildSketch(Plane.XY) as pocket:
        RegularPolygon(radius=NUT_AF / 2, side_count=6, major_radius=False)
        Rectangle(NUT_AF, 10, align=(Align.CENTER, Align.MAX))   # out to -Y
    extrude(amount=NUT_T, mode=Mode.SUBTRACT)
```

`major_radius=False` makes `radius` the across-flats dimension — that is how
nuts are specified. The pocket ceiling is a flat bridge over `NUT_AF`, which
prints fine; keep the slot no wider than the nut so it stays captive.

---

## Teardrop horizontal hole

A round horizontal hole droops. A teardrop prints cleanly.

```python
R, LEN = 2.5, 40.0

profile = Circle(R) + Polygon((-R, 0), (R, 0), (0, R * 1.5), align=None)
cutter = Plane.XZ * extrude(profile, amount=LEN / 2, both=True)
result = Box(40, LEN, 20) - cutter
```

`Plane.XZ`'s local +Y is global +Z, so the point of the teardrop ends up
uppermost, which is what makes it bridge.

---

## Rib / gusset

```python
RIB_T = 1.2         # ~0.6 x wall, avoids sink marks
with BuildPart() as part:
    Box(40, 40, 4, align=(Align.CENTER, Align.CENTER, Align.MIN))
    Box(4, 40, 30, align=(Align.CENTER, Align.CENTER, Align.MIN))
    with BuildSketch(Plane.YZ) as gusset:
        Triangle(a=20, b=20, C=90, align=(Align.MIN, Align.MIN))
    extrude(amount=RIB_T / 2, both=True)
    fillet(part.edges().filter_by(Axis.Y).group_by(Axis.Z)[0], radius=1)
```

---

## Adjustment slot instead of a tight tolerance

```python
SLOT_TRAVEL = 6.0
with BuildPart() as part:
    Box(50, 20, 4)
    with BuildSketch(Plane.XY.offset(4)):
        SlotOverall(width=SLOT_TRAVEL + 3.4, height=3.4)   # total length x width
    extrude(amount=-4, mode=Mode.SUBTRACT)
```

If a stack of printed features has to hit better than ±0.3 mm, add a slot.

---

## Bearing seat (608: 22 OD × 7 ID × 8 wide)

```python
BEARING_OD, BEARING_W = 22.0, 8.0
SEAT_CLEAR = 0.05          # light press; use 0.15 for a slip fit
SHOULDER = 1.5             # lip the outer race sits against

with BuildPart() as housing:
    Cylinder(radius=BEARING_OD / 2 + 3, height=BEARING_W + SHOULDER,
             align=(Align.CENTER, Align.CENTER, Align.MIN))
    with BuildSketch(Plane.XY.offset(BEARING_W + SHOULDER)):
        Circle((BEARING_OD + SEAT_CLEAR) / 2)
    extrude(amount=-BEARING_W, mode=Mode.SUBTRACT)
    with BuildSketch():
        Circle(BEARING_OD / 2 - SHOULDER)
    extrude(amount=SHOULDER, mode=Mode.SUBTRACT)
```

Print the bore axis vertical; a press fit into a horizontally-printed bore
never seats squarely.

---

## Polar pattern

```python
with BuildPart() as flange:
    Cylinder(radius=40, height=6)
    with PolarLocations(radius=30, count=6):
        Hole(radius=2.2)
```

`PolarLocations(radius, count, start_angle=0, angular_range=360, rotate=True)`.
`rotate=False` keeps each instance's own orientation.

---

## Revolve a profile

```python
with BuildPart() as knob:
    with BuildSketch(Plane.XZ) as profile:
        with BuildLine():
            Polyline((0, 0), (15, 0), (15, 8), (9, 14), (0, 14), close=True)
        make_face()
    revolve(axis=Axis.Z)
```

The profile must sit entirely on one side of the axis and touch it, or the
revolve produces a hollow torus instead of a solid.

---

## Sweep along a path

```python
with BuildPart() as duct:
    # The BuildLine plane must contain the path. A vertical line plus a bend
    # lives in XZ; on the default Plane.XY the JernArc has no solution.
    with BuildLine(Plane.XZ) as path:
        l1 = Line((0, 0), (0, 40))
        l2 = JernArc(start=l1 @ 1, tangent=l1 % 1, radius=20, arc_size=90)
    with BuildSketch(Plane(origin=path.line @ 0, z_dir=path.line % 0)):
        Circle(8)
        Circle(6, mode=Mode.SUBTRACT)
    sweep()
```

`@` is position along the curve, `%` is tangent — that is how you build a
workplane perpendicular to the start of a path. `JernArc` takes no plane of its
own; it uses the enclosing `BuildLine` workplane, and fails with
`GC_MakeArcOfCircle::Value() - no result` if the tangent leaves that plane.

---

## Split a part too big for the bed, with alignment pins

```python
PIN_D, PIN_L, PIN_FIT = 4.0, 8.0, 0.15

with BuildPart() as whole:
    Box(300, 60, 20)

halves = split(whole.part, bisect_by=Plane.YZ, keep=Keep.BOTH)
left, right = halves.solids()

pin = Plane.YZ * Cylinder(radius=PIN_D / 2, height=PIN_L)
socket = Plane.YZ * Cylinder(radius=(PIN_D + PIN_FIT) / 2, height=PIN_L + 0.5)
left = left + pin
right = right - socket
result = pack([left, right], padding=5, align_z=True)
```

---

## Text label

```python
with BuildPart() as part:
    Box(60, 20, 3, align=(Align.CENTER, Align.CENTER, Align.MIN))
    with BuildSketch(Plane.XY.offset(3)):     # must land exactly on the top face
        Text("REV B", font_size=6)
    extrude(amount=0.6)          # emboss; use mode=Mode.SUBTRACT and -0.4 to engrave
```

Keep stroke width ≥0.8 mm. Text on a vertical face prints badly — put it on the
top face or accept the layer lines.

---

## Measure and assert

```python
from math import isclose

result = build()
bb = result.bounding_box()
assert isclose(bb.size.X, L, abs_tol=1e-6), bb.size
assert len(result.solids()) == 1, "part fell apart into separate bodies"
assert result.is_valid, "invalid B-rep"
assert isclose(result.volume, EXPECTED_VOLUME, rel_tol=0.01)
```

Better still, declare `EXPECT = {...}` at module level and let
`scripts/inspect_part.py` check it, so the same assertions also gate exports
and renders.
