"""L-bracket - template for a parametric, printable build123d part.

Copy this file, replace the geometry, keep the structure:

    1. a docstring stating what the part mates with and how it prints
    2. a frozen Params dataclass - every number named, with units and a source
    3. build(params) -> Part, pure, no side effects
    4. module-level `result` so the inspector can find it
    5. EXPECT with the design intent the inspector must verify

Check it with:

    python scripts/inspect_part.py assets/part_template.py --out build --min-wall 1.6

Mates with: two M3 socket screws into a 24 mm pitch pattern on each leg.
Prints: as modelled, base flat on the plate, no support. The two holes in the
upright leg are horizontal and bridge their own ceilings at 3.4 mm - see EXPECT.
"""

from dataclasses import dataclass

from build123d import (
    Align,
    Axis,
    Box,
    BuildPart,
    BuildSketch,
    Circle,
    Locations,
    Mode,
    Part,
    Plane,
    Polygon,
    chamfer,
    extrude,
)

# --- process assumptions -------------------------------------------------
NOZZLE = 0.4                       # mm
LAYER = 0.2                        # mm
EXTRUSION_W = NOZZLE * 1.05        # mm, actual bead width
BED_CHAMFER = 0.5                  # mm, kills the elephant foot


@dataclass(frozen=True)
class Params:
    """Every dimension the part depends on. No magic numbers below this line."""

    width: float = 40.0            # mm, X - across both legs
    depth: float = 35.0            # mm, Y - base leg reach
    height: float = 35.0           # mm, Z - upright leg reach
    thickness: float = 4.0         # mm, wall of both legs (10 x extrusion width)

    bolt_clearance_d: float = 3.4  # mm, M3 medium clearance hole, ISO 273
    hole_pitch: float = 24.0       # mm, X spacing of the mounting pattern
    hole_offset: float = 12.0      # mm, from the inside corner along each leg

    gusset: float = 18.0           # mm, leg length of the triangular gusset
    gusset_thickness: float = 2.4  # mm, ~0.6 x wall so it does not sink


P = Params()


def build(p: Params = P) -> Part:
    """Return the bracket as a single solid, base sitting on Z = 0."""
    corner = p.thickness  # inside corner sits at y = z = thickness

    with BuildPart() as bracket:
        # Base leg, lying on the build plate.
        Box(p.width, p.depth, p.thickness,
            align=(Align.CENTER, Align.MIN, Align.MIN))
        # Upright leg, sharing the y = 0 face.
        Box(p.width, p.thickness, p.height,
            align=(Align.CENTER, Align.MIN, Align.MIN))

        # Triangular gusset in the inside corner. Drawn on Plane.YZ, where the
        # sketch's local X is global Y and local Y is global Z.
        with BuildSketch(Plane.YZ):
            Polygon(
                (corner, corner),
                (corner + p.gusset, corner),
                (corner, corner + p.gusset),
                align=None,
            )
        extrude(amount=p.gusset_thickness / 2, both=True)

        # Mounting holes in the base leg, cut down through the plate.
        with BuildSketch(Plane.XY.offset(p.thickness)):
            with Locations((-p.hole_pitch / 2, corner + p.hole_offset),
                           (p.hole_pitch / 2, corner + p.hole_offset)):
                Circle(p.bolt_clearance_d / 2)
        extrude(amount=-p.thickness, mode=Mode.SUBTRACT)

        # Mounting holes in the upright leg. Plane.XZ sits at y = 0 with local
        # Y running along global Z, so `both=True` cuts cleanly through.
        with BuildSketch(Plane.XZ):
            with Locations((-p.hole_pitch / 2, corner + p.hole_offset),
                           (p.hole_pitch / 2, corner + p.hole_offset)):
                Circle(p.bolt_clearance_d / 2)
        extrude(amount=p.thickness, both=True, mode=Mode.SUBTRACT)

        # Chamfer every edge touching the build plate.
        bed_face = bracket.faces().sort_by(Axis.Z)[0]
        chamfer(bed_face.edges(), length=BED_CHAMFER)

    part = bracket.part
    part.label = "l_bracket"
    return part


result = build()

EXPECT = {
    "bbox": (P.width, P.depth, P.height),
    "volume": 10782.0,          # mm^3, measured once the part was right;
                                # now guards against a silently failed boolean
    "solids": 1,
    "watertight": True,
    "min_wall": 2.0,            # mm, thinnest feature is the gusset at 2.4
    # The inspector flags 29 mm^2 of surface past 45 deg: the ceilings of the
    # two horizontal M3 clearance holes in the upright leg. At 3.4 mm they
    # self-bridge, so this is accepted rather than fixed. That is what this
    # entry records - a judgement, not a rubber stamp. If the holes were
    # larger, the teardrop recipe in references/recipes.md is the fix.
    "max_overhang_deg": 90.0,
    "tol": 0.001,
}


if __name__ == "__main__":
    from build123d import Mesher, export_step, export_stl

    export_step(result, "l_bracket.step")
    export_stl(result, "l_bracket.stl")
    mesher = Mesher()
    mesher.add_shape(result)
    mesher.write("l_bracket.3mf")
    print(f"bbox {result.bounding_box().size}  volume {result.volume:.1f} mm^3")
