# build123d API reference

Verified against the build123d `dev` docs and source, and exercised against
build123d 0.11.1. Signatures show real parameter names — pass them as keywords,
because positional order changes between similar objects.

## Contents

1. [The two modes](#1-the-two-modes) — algebra vs builder, and the operators
2. [Objects](#2-objects) — primitives for 3D, 2D and 1D
3. [Operations](#3-operations) — extrude, revolve, loft, sweep, fillet, offset
4. [Selectors](#4-selectors) — picking edges and faces that survive a parameter change
5. [Planes, locations, placement](#5-planes-locations-placement)
6. [Sketching on a part face](#6-sketching-on-a-part-face)
7. [Measurement and validation](#7-measurement-and-validation)
8. [Export and import](#8-export-and-import)
9. [Assemblies and joints](#9-assemblies-and-joints)
10. [Enums worth memorising](#10-enums-worth-memorising)

---

## 1. The two modes

**Algebra mode** — stateless, uses operators. Best for small parts, scripting,
and anything you want to compose from functions.

```python
from build123d import *

result = Box(80, 60, 10) - Pos(20, 15) * Cylinder(radius=1.7, height=20)
```

**Builder mode** — stateful context managers. Best when you need selectors that
refer to "what I just made", or `Hole` / `GridLocations` style placement.

```python
with BuildPart() as plate:
    Box(80, 60, 10)
    with GridLocations(60, 40, 2, 2):
        Hole(radius=1.7)
    fillet(plate.edges().filter_by(Axis.Z), radius=4)
result = plate.part
```

Mixing is fine: build a `Sketch` in algebra mode and `add()` it inside a
builder, or call `extrude(sketch, amount=5)` outside any builder.

### Algebra operators

| Op | Meaning |
|----|---------|
| `a + b` | fuse |
| `a - b` | cut |
| `a & b` | intersect |
| `plane * obj` | place object on plane |
| `Pos(x, y, z) * obj` | translate |
| `Rot(x, y, z) * obj` | rotate about the plane's axes, degrees |
| `Location((1,2,3), (0,90,45)) * obj` | same as `Pos * Rot` |

`*` binds tighter than `+ - &`, so `Plane.XZ * Box(1,2,3) + Cylinder(1,5)` needs
no brackets. Placement composes left to right: `Plane.XZ * Pos(1,2,3) * Rot(0,90,0) * obj`
means "on the XZ plane, moved in that plane's coordinates, then rotated there".

---

## 2. Objects

### 3D (`BuildPart` / algebra)

```python
Box(length, width, height, rotation=(0,0,0), align=(CENTER,CENTER,CENTER), mode=Mode.ADD)
Cylinder(radius, height, arc_size=360, rotation=..., align=..., mode=...)
Cone(bottom_radius, top_radius, height, arc_size=360, ...)
Sphere(radius, arc_size1=-90, arc_size2=90, arc_size3=360, ...)
Torus(major_radius, minor_radius, ...)
Wedge(xsize, ysize, zsize, xmin, zmin, xmax, zmax, ...)
ConvexPolyhedron(points, ...)                 # convex hull of points
```

Builder-only hole operations (they default to `Mode.SUBTRACT` and cut through
the part when `depth=None`; place them with a `Locations` context):

```python
Hole(radius, depth=None, mode=Mode.SUBTRACT)
CounterBoreHole(radius, counter_bore_radius, counter_bore_depth, depth=None)
CounterSinkHole(radius, counter_sink_radius, depth=None, counter_sink_angle=82)
```

In algebra mode there is no `Hole`; subtract a `Cylinder` instead.

### 2D (`BuildSketch` / algebra)

```python
Rectangle(width, height, rotation=0, align=(CENTER,CENTER), mode=Mode.ADD)
RectangleRounded(width, height, radius, ...)
Circle(radius, ...)
Ellipse(x_radius, y_radius, ...)
Polygon(*pts, ...)
RegularPolygon(radius, side_count, major_radius=True, ...)
Triangle(a=, b=, c=, A=, B=, C=, ...)         # any 3 of 6, SSS/SAS/ASA
Trapezoid(width, height, left_side_angle, right_side_angle=None, ...)
SlotOverall(width, height, rotation=0, ...)   # total length x width
SlotCenterToCenter(center_separation, height, ...)
SlotCenterPoint(center, point, height, ...)
SlotArc(arc, height, ...)
Text(txt, font_size, font="Arial", align=..., ...)
```

`RegularPolygon(radius=..., major_radius=False)` gives the **across-flats**
inscribed radius — that is what you want for a hex nut pocket.

### 1D (`BuildLine` / algebra)

```python
Line(pt1, pt2)                     Polyline(*pts, close=False)
CenterArc(center, radius, start_angle, arc_size)
RadiusArc(start, end, radius)      SagittaArc(start, end, sagitta)
ThreePointArc(p1, p2, p3)          TangentArc(*pts, tangent=, tangent_from_first=True)
JernArc(start, tangent, radius, arc_size)      # arc from a point + direction
Spline(*pts, tangents=None, ...)   Bezier(*cntl_pnts, weights=None)
Helix(pitch, height, radius, center=(0,0,0), direction=(0,0,1), ...)
FilletPolyline(*pts, radius, close=False)
PolarLine(start, length, angle=None, direction=None, length_mode=LengthMode.DIAGONAL)
IntersectingLine(start, direction, other)
```

`FilletPolyline` is the shortcut for a rounded 2D outline — cheaper and far more
reliable than filleting the extruded solid.

---

## 3. Operations

```python
extrude(to_extrude=None, amount=None, dir=None, until=None, target=None,
        both=False, taper=0.0, clean=True, mode=Mode.ADD) -> Part
revolve(profiles=None, axis=Axis.Z, revolution_arc=360.0, clean=True, mode=Mode.ADD)
loft(sections=None, ruled=False, clean=True, mode=Mode.ADD)
sweep(sections=None, path=None, multisection=False, is_frenet=False,
      transition=Transition.TRANSFORMED, normal=None, binormal=None, ...)
thicken(to_thicken=None, amount=None, normal_override=None, both=False, ...)
section(obj=None, section_by=Plane.XZ, height=0.0, clean=True, mode=Mode.PRIVATE) -> Sketch
draft(faces, neutral_plane, angle) -> Part
make_brake_formed(thickness, station_widths, line=None, side=Side.LEFT, kind=Kind.ARC, ...)

fillet(objects, radius) -> Sketch | Part | Curve
chamfer(objects, length, length2=None, angle=None, reference=None)
offset(objects=None, amount=0, openings=None, kind=Kind.ARC, side=Side.BOTH,
       closed=True, min_edge_length=None, mode=Mode.REPLACE)
mirror(objects=None, about=Plane.XZ, mode=Mode.ADD)
scale(objects=None, by=1, about=None, mode=Mode.REPLACE)
split(objects=None, bisect_by=Plane.XZ, keep=Keep.TOP, mode=Mode.REPLACE)
project(objects=None, workplane=None, target=None, mode=Mode.ADD)
add(objects, rotation=None, clean=True, mode=Mode.ADD)
bounding_box(objects=None, mode=Mode.PRIVATE)

make_face(edges=None, mode=Mode.ADD)     # BuildSketch: close a BuildLine into a face
make_hull(edges=None, mode=Mode.ADD)
full_round(edge, ...)                    # 2D: round off a tab completely
trace(lines=None, line_width=1, mode=Mode.ADD)
```

Notes that save time:

- `extrude(amount=-5)` goes the other way. `both=True` goes both ways from the
  sketch plane. `taper=` is a draft angle in degrees, positive shrinks.
- `extrude(until=Until.NEXT, target=...)` / `Until.LAST` builds up-to-face
  features that survive parameter changes. Prefer it over a computed length.
- `offset(part, amount=-2, openings=top_face)` is how you **shell** a box.
  Negative amount hollows inward; `openings` is the face (or list) to leave open.
- `fillet` radius must be less than half the local material width or OCCT fails.
- `chamfer(..., length2=)` or `angle=` for asymmetric chamfers, plus `reference=`
  to say which side `length` is measured from.
- `split(part, bisect_by=Plane.XZ, keep=Keep.BOTH)` returns both halves — useful
  for printing a big part in two pieces.

---

## 4. Selectors

Every builder and shape gives you `ShapeList`s:

```python
part.vertices()  part.edges()  part.wires()  part.faces()  part.solids()
```

Inside a builder you can restrict to what changed:
`plate.faces(Select.LAST)` / `Select.NEW` / `Select.ALL`.

### Methods

```python
.filter_by(Axis.Z | Plane.XY | GeomType.CIRCLE | callable, reverse=False, tolerance=1e-5)
.filter_by_position(axis, minimum, maximum, inclusive=(True, True))
.sort_by(Axis.Z | SortBy.AREA | Edge | Wire, reverse=False)
.sort_by_distance(other, reverse=False)
.group_by(Axis.Z | SortBy.AREA | callable, reverse=False, tol_digits=6)  # -> list of ShapeList
.first  .last
```

### Operator shorthand

| Operator | Equivalent |
|---|---|
| `edges() > Axis.Z` | `sort_by(Axis.Z)` |
| `edges() < Axis.Z` | `sort_by(Axis.Z, reverse=True)` |
| `edges() >> Axis.Z` | `group_by(Axis.Z)[-1]` — the topmost group |
| `edges() << Axis.Z` | `group_by(Axis.Z)[0]` — the bottommost group |
| `faces() \| Axis.Z` | `filter_by(Axis.Z)` — faces normal to Z |
| `edges() \| GeomType.CIRCLE` | circular edges only |

`SortBy` values: `LENGTH, RADIUS, AREA, VOLUME, DISTANCE`.
`GeomType` values: `LINE, CIRCLE, ELLIPSE, BSPLINE, BEZIER, PLANE, CYLINDER, CONE, SPHERE, TORUS, EXTRUSION, REVOLUTION, HYPERBOLA, PARABOLA, OFFSET, OTHER`.

### Select from the top down

Index-based selection (`edges()[3]`) breaks the moment a parameter changes.
Narrow by topology first, then filter:

```python
top = part.faces().sort_by(Axis.Z)[-1]
hole_edges = top.edges().filter_by(GeomType.CIRCLE)
chamfer(hole_edges, length=0.5)
```

`group_by` is the robust way to say "all the edges at one height":

```python
bottom_edges = part.edges().group_by(Axis.Z)[0]
```

---

## 5. Planes, locations, placement

```python
Plane.XY  Plane.YZ  Plane.XZ  Plane.YX  Plane.ZX  Plane.ZY   # and negated: -Plane.XY
Plane(origin=(0,0,10), z_dir=(0,0,1), x_dir=None)
Plane(some_face)                        # workplane on a face of the part
Plane.XY.offset(10)                     # parallel plane 10 mm up
Plane.XY.rotated((0, 30, 0))
plane.to_local_coords(shape_or_vector)  # global -> plane coordinates
plane.from_local_coords(...)            # plane -> global
```

Location contexts (builder mode) — everything created inside is replicated:

```python
Locations((10, 0), (-10, 0), Plane.XY.offset(5))
GridLocations(x_spacing, y_spacing, x_count, y_count, align=(CENTER, CENTER))
PolarLocations(radius, count, start_angle=0, angular_range=360, rotate=True)
HexLocations(radius, x_count, y_count, major_radius=False)
```

`Locations` accepts points, `Location`s, `Plane`s, `Vertex`s and `Face`s. In
algebra mode use `for loc in GridLocations(...): result += loc * feature`.

Edge/wire parameter operators, for placing things along a curve:

```python
edge @ 0.5   # position_at  -> Vector at the midpoint
edge % 0.5   # tangent_at   -> Vector
edge ^ 0.5   # location_at  -> Location (position + orientation)
```

`Axis.X / Axis.Y / Axis.Z`, or `Axis((0,0,0), (1,1,0))`.

---

## 6. Sketching on a part face

```python
with BuildPart() as p:
    Box(60, 40, 10)
    top = p.faces().sort_by(Axis.Z)[-1]
    with BuildSketch(Plane(top)) as boss:
        Circle(8)
    extrude(amount=6)
```

A sketch is always drawn in its **own local XY plane** and only placed on the
given plane when the `BuildSketch` context exits. So inside `BuildSketch(Plane.XZ)`
a `sort_by(Axis.Z)` selector is meaningless — everything is at Z=0. Sort by
`Axis.X` / `Axis.Y` in sketch-local terms instead. Same applies to a `BuildLine`
nested in a `BuildSketch`: leave it on the default plane.

---

## 7. Measurement and validation

```python
shape.is_valid            # property, bool - kernel self-check
shape.volume              # mm^3
shape.area                # mm^2
shape.bounding_box()      # -> BoundBox: .min .max .size .diagonal (Vectors)
shape.center()            # Vector, centre of mass for solids
shape.solids()            # should be length 1 for a printable part
shape.matrix_of_inertia   shape.radius_of_gyration()   shape.principal_properties
shape.distance_to(other)  shape.closest_points(other)
shape.clean()             # remove coplanar internal edges
shape.fix()               # attempt repair of an invalid shape
shape.show_topology()     # printable topology tree - great for debugging
Mixin3D.max_fillet(edges, tolerance=0.1, max_iterations=10)   # largest radius that works
```

Assert on these. `assert isclose(part.volume, expected, rel_tol=1e-3)` catches a
mis-typed parameter far faster than staring at a render.

---

## 8. Export and import

```python
export_step(shape, "part.step", unit=Unit.MM)   # the interchange format - always emit one
export_stl(shape, "part.stl", tolerance=1e-3, angular_tolerance=0.1)
export_brep(shape, "part.brep")
export_gltf(shape, "part.gltf", binary=False)

from build123d import Mesher                     # 3MF: colours, units, multi-body
m = Mesher(); m.add_shape(shape); m.write("part.3mf")

import_step("in.step")  import_stl("in.stl")  import_brep(...)  import_svg(...)
```

For 3D printing prefer **3MF** — it carries units and colour, so no
millimetre/inch ambiguity at the slicer. Keep the STEP as the source of truth.

`tolerance` in `export_stl` is the chord deviation in mm. `1e-3` is fine for
functional parts; loosen to `0.01` only for huge models.

2D drawing output:

```python
visible, hidden = part.project_to_viewport((-100, -50, 30))
exporter = ExportSVG(scale=2)
exporter.add_layer("Visible")
exporter.add_layer("Hidden", line_color=(99, 99, 99), line_type=LineType.ISO_DOT)
exporter.add_shape(visible, layer="Visible")
exporter.add_shape(hidden, layer="Hidden")
exporter.write("part.svg")
```

---

## 9. Assemblies and joints

```python
from build123d import Compound, RigidJoint, RevoluteJoint, LinearJoint

RigidJoint("mount", to_part=base, joint_location=Location((0, 0, 10)))
RigidJoint("base", to_part=arm, joint_location=Location((0, 0, 0)))
base.joints["mount"].connect_to(arm.joints["base"])

assembly = Compound(label="gizmo", children=[base, arm])
export_step(assembly, "gizmo.step")   # keeps labels and colours
```

Joint types: `RigidJoint`, `RevoluteJoint` (one rotation), `LinearJoint`,
`CylindricalJoint`, `BallJoint`. Set `shape.label` and `shape.color` before
export so the STEP tree is readable.

Repeated parts: use a shallow copy (`copy.copy`) rather than a deep copy so 200
screws do not become 200 B-reps.

`pack(shapes, padding, align_z=True)` lays parts out side by side on the plate.

---

## 10. Enums worth memorising

```
Align:  MIN, CENTER, MAX
Mode:   ADD, SUBTRACT, INTERSECT, REPLACE, PRIVATE
Keep:   ALL, TOP, BOTTOM, BOTH, INSIDE, OUTSIDE
Kind:   ARC, INTERSECTION, TANGENT          # offset corner treatment
Side:   BOTH, LEFT, RIGHT
Until:  FIRST, LAST, NEXT, PREVIOUS
Select: ALL, LAST, NEW
Transition: RIGHT, ROUND, TRANSFORMED
Unit:   MC, MM, CM, M, IN, FT
CenterOf: GEOMETRY, MASS, BOUNDING_BOX
```
