# Designing parts that actually print (FDM)

Numbers below assume a well-tuned FDM machine, 0.4 mm nozzle, 0.2 mm layers,
PLA or PETG. They are starting points, not physics. State the assumption in the
model file and tell the user to print a test coupon before committing to a fit.

---

## 1. Derive everything from a nozzle/layer parameter block

Put this at the top of every model so a nozzle change re-derives the part:

```python
NOZZLE = 0.4          # mm
LAYER = 0.2           # mm
EXTRUSION_W = NOZZLE * 1.05      # ~0.42 mm actual bead width
WALL_MIN = 2 * EXTRUSION_W       # 0.84 mm - two perimeters, cosmetic only
WALL_STRUCTURAL = 4 * EXTRUSION_W  # ~1.7 mm - load bearing
```

Wall thickness should be an integer multiple of the extrusion width. A 1.0 mm
wall on a 0.42 mm bead gives two perimeters plus a 0.16 mm gap the slicer will
either drop or smear.

| Feature | Minimum | Comfortable |
|---|---|---|
| Vertical wall | 0.84 mm (2 perimeters) | 1.6–2.0 mm |
| Load-bearing wall / boss | 1.6 mm | 2.5–3 mm |
| Horizontal solid floor/ceiling | 4 layers (0.8 mm) | 5–6 layers |
| Free-standing pin | 2 mm dia | 3 mm dia |
| Embossed text stroke | 0.8 mm wide × 0.4 mm proud | 1.2 mm × 0.6 mm |
| Engraved text | 0.6 mm wide × 0.4 mm deep | 1.0 × 0.6 mm |
| Rib thickness | 0.6 × adjoining wall | avoids sink marks |

---

## 2. Clearances and fits

Printed holes come out **undersize** and printed pegs come out **oversize**
(elephant foot, over-extrusion, corner rounding). Never model a nominal fit.

| Fit | Diametral clearance | Use |
|---|---|---|
| Interference / press | −0.05 to 0.0 mm | permanent, needs force |
| Tight push fit | +0.10 mm | dowels, alignment pins |
| Snug sliding | +0.20 mm | lids, drawers, keyed parts |
| Free running | +0.30 to 0.40 mm | shafts, hinges |
| Loose / self-clearing | +0.50 mm | tolerant assemblies, first try |

Always name the value:

```python
FIT_SLIDING = 0.20     # mm total diametral clearance, tune per printer
shaft_hole_d = SHAFT_D + FIT_SLIDING
```

**Small holes shrink most.** For holes below ~5 mm add 0.1–0.2 mm on top of the
fit clearance, or drill/ream after printing and say so in the notes.

---

## 3. Fasteners

### Screw clearance holes (ISO 273 medium, plus print allowance)

| Thread | Close | Medium (default) | Model as |
|---|---|---|---|
| M2 | 2.2 | 2.4 | 2.5 |
| M2.5 | 2.7 | 2.9 | 3.0 |
| M3 | 3.2 | 3.4 | 3.4 |
| M4 | 4.3 | 4.5 | 4.5 |
| M5 | 5.3 | 5.5 | 5.5 |
| M6 | 6.4 | 6.6 | 6.6 |

### Socket head cap screw counterbores (DIN 912 head Ø / height)

| Thread | Head Ø | Head h | Counterbore Ø | Counterbore depth |
|---|---|---|---|---|
| M3 | 5.5 | 3.0 | 6.0 | 3.2 |
| M4 | 7.0 | 4.0 | 7.5 | 4.2 |
| M5 | 8.5 | 5.0 | 9.0 | 5.2 |

### Hex nut pockets (across flats, add 0.2 mm)

| Thread | AF nominal | Pocket AF | Nut thickness | Pocket depth |
|---|---|---|---|---|
| M3 | 5.5 | 5.7 | 2.4 | 2.6 |
| M4 | 7.0 | 7.2 | 3.2 | 3.4 |
| M5 | 8.0 | 8.2 | 4.7 | 4.9 |

Model with `RegularPolygon(radius=pocket_af/2, side_count=6, major_radius=False)`
— `major_radius=False` means the radius is across flats, which is what a nut is
specified by. Orient one flat down so the pocket does not need support.

### Heat-set inserts (brass, knurled)

Use the insert manufacturer's stated hole size. For the common ruthex /
CNC Kitchen style inserts:

| Thread | Insert | Hole Ø | Hole depth |
|---|---|---|---|
| M3 | 4.6 × 5.7 mm | 4.0 | insert length + 1.0 |
| M4 | 5.6 × 8.1 mm | 5.6 | insert length + 1.0 |
| M5 | 6.4 × 9.5 mm | 6.4 | insert length + 1.0 |

Leave ≥1.6 mm of wall around the insert, and add a 0.5 mm lead-in chamfer so
the insert self-centres.

### Self-tapping into plastic

Pilot ≈ 0.8 × thread major diameter (M3 → 2.5 mm). Good for a handful of
assembly cycles, no more.

### Printed threads

Last resort. Only M6 and up, add 0.25 mm radial clearance, print the threaded
axis vertical, and expect to chase it with a tap. Preference order for anything
that gets undone twice: **heat-set insert > captive nut > tapped hole > printed thread**.

---

## 4. Geometry the printer can build

- **45° rule.** Any down-facing surface more than 45° from vertical needs
  support. Replace overhangs with chamfers wherever you can — a 45° chamfer is
  free, support is not.
- **Horizontal holes** print as a droopy oval. Either orient them vertically, or
  make them a teardrop / diamond: two 45° facets meeting above the bore. For a
  through-bolt this rarely matters below Ø5.
- **Bridges** up to ~30 mm print cleanly between two anchored walls. A bridged
  ceiling over a pocket beats support every time.
- **Elephant foot.** Add a 0.4–0.6 mm × 45° chamfer to every edge touching the
  bed. This is the single highest-value detail in an FDM part; it also makes the
  part sit flat.
- **First-layer contact.** Aim for a flat face on the plate. Tall, narrow parts
  need a brim or a printed foot — flag it rather than silently designing a part
  that tips over.
- **Sharp internal corners are crack starters.** Fillet load-bearing internal
  corners ≥1 mm; 0.25 × wall thickness is a reasonable default.
- **Anisotropy.** Layer adhesion is roughly half the in-plane strength. Orient
  the part so tensile and bending loads run *along* layers, not across them. A
  cantilever bracket printed lying on its back will snap at the root.
- **Big flat areas warp**, especially ABS/ASA. Break them with ribs or a slight
  crown, and keep the footprint under ~150 mm where you can.

---

## 5. Orientation is a design decision

Decide it in CAD, not in the slicer, and write it down:

```python
PRINT_ORIENTATION = "as modelled, largest flat face on the bed, +Z up"
```

Then check it: the overhang map from `inspect_part.py` renders down-facing
surfaces in red from below. If the red is anywhere other than places you chose,
either the orientation or the geometry is wrong.

If the part only works in one orientation for strength reasons, say why.

---

## 6. Material quick reference

| Material | Density g/cm³ | Notes |
|---|---|---|
| PLA | 1.24 | stiff, brittle, creeps above 50 °C |
| PETG | 1.27 | tougher, layer adhesion good, stringy |
| ABS | 1.04 | warps, needs enclosure, solvent weldable |
| ASA | 1.07 | ABS with UV resistance |
| TPU 95A | 1.21 | flexible; clearances need +0.1 mm more |
| PA (nylon) | 1.14 | tough, hygroscopic, dries before printing |
| PC | 1.20 | strong and heat resistant, needs high temps |

Mass estimate from the tool is for a solid part. Multiply by roughly
`(perimeter+top/bottom fraction) + infill × remainder`; for a typical 15 % infill
chunky part, 0.35–0.55 of solid mass is a reasonable band.

---

## 7. Tolerance stack

Assume ±0.15 mm per printed dimension on a tuned machine, worse across layers
and on the first few layers. If a stack of three features has to hit ±0.2 mm,
the design is wrong — add an adjustment slot, a shim, or a post-print reaming
operation instead.
