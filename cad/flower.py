# pyright: reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
# pyright: reportUnknownParameterType=false
# pyright: reportPrivateUsage=false
# pylint: disable=duplicate-code

import math
import os
import re
from dataclasses import dataclass
import sys
from pathlib import Path
from typing import Iterator, List
import subprocess
import solid as s

# To auto watch and run:
# bun x nodemon --exec "python cad/flower.py" --watch "cad/flower.py"

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DEBUG = True
PETAL_X = 12
Y0_CONTACT_EXTRUDE_DEPTH = 10
PETAL_HEIGHT_MIN = 76
PETAL_HEIGHT_MAX = 84
RESOLUTION_DEBUG = 24
RESOLUTION_DETAILED = 50
# Sweep profile density: path_sweep2d cost scales with this × sweep segments; keep debug low.
SPLINE_STEPS_DEBUG = 4
SPLINE_STEPS_PRINT = 24

# Flower layout (tune): concentric rings around origin in XY, petals face the center.
NUM_RINGS = 1
MIN_SCALE = 0.5
INNER_RING_RADIUS = 32.0
RING_SPACING = 20.0
# Target arc length along each ring per petal — smaller ⇒ more petals on that ring.
PETAL_ARC_MM = 30.0
# Extra Z rotation so petal local “forward” points radially inward after placement.
FACE_CENTER_Z_DEG = 300.0
PETAL_ROTATE = 45.0

OPENSCAD_PATH = '/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'

beziers = s.import_scad("BOSL2/beziers.scad")
lists = s.import_scad("BOSL2/lists.scad")
skin = s.import_scad("BOSL2/skin.scad")
transforms = s.import_scad("BOSL2/transforms.scad")
drawing = s.import_scad("BOSL2/drawing.scad")


def generate_petal(debug: bool) -> s.OpenSCADObject:
    outer_bezpath = lists.flatten(
        [
            beziers.bez_begin([0, 0], [0, 0]),
            beziers.bez_joint([-12, 50], [0, -20], [0, 20]),
            beziers.bez_joint([0, 80], [-4, -4], [4, 4]),
            beziers.bez_end([PETAL_X, PETAL_HEIGHT_MAX], [0, 0]),
        ]
    )
    inner_bezpath = lists.flatten(
        [
            beziers.bez_begin([PETAL_X, PETAL_HEIGHT_MIN], [5, 0]),
            beziers.bez_joint([2, 72], [5, 5], [-5, -5]),
            beziers.bez_joint([-6, 50], [0, 10], [0, -10]),
            beziers.bez_end([5, 0], [-5, 10]),
        ]
    )
    outer_curve = beziers.bezpath_curve(outer_bezpath, splinesteps=SPLINE_STEPS_DEBUG if debug else SPLINE_STEPS_PRINT)
    inner_curve = beziers.bezpath_curve(inner_bezpath, splinesteps=SPLINE_STEPS_DEBUG if debug else SPLINE_STEPS_PRINT)

    # ``flatten([outer, inner])`` plus ``move`` centers the full petal like mirroring the half.
    petal_shape = transforms.move(
        [-PETAL_X, 0], p=lists.flatten([outer_curve, inner_curve])
    )
    elliptic_arc = transforms.xscale(
        4, p=drawing.arc(n=RESOLUTION_DEBUG if debug else RESOLUTION_DETAILED, angle=[180, 0], r=1))
    # Reverse so profile winding matches the sweep; path_sweep2d needs a 2D path (shape Y → Z).
    sweep_path = lists.reverse(elliptic_arc)
    petal = skin.path_sweep2d(petal_shape, sweep_path)

    # Debug skips the base extension: it duplicates path_sweep2d and projection(cut) is very slow.
    extension = s.projection(cut=True)(petal)
    extension = s.linear_extrude(height=10, convexity=4)(extension)
    extension = s.mirror((0, 0, 1))(extension)
    petal = s.union()(petal, extension)

    # Rotate a bit and translate to match
    petal = s.translate((0, 0, 9))(s.rotate((-PETAL_ROTATE, 0, 0))(petal))
    return petal

def single_petal_geometry(debug: bool) -> s.OpenSCADObject:
    """One petal in canonical pose (same mesh exported to ``{petal_file_name()}.stl``)."""
    return generate_petal(debug)


def generate_flower_assembly_scad(file_name: str) -> str:
    """Union of ``import(petal.stl)`` with ring placement — fast preview/render vs full CSG."""
    stl_name = f"{file_name}.stl"
    header = (
        f"// Requires {stl_name} in this directory (export from {file_name}.scad).\n\n"
    )
    parts: List[str] = []
    for lay in iter_ring_layouts():
        stagger = lay.angle_per_petal / 2.0 if lay.ring % 2 == 0 else 0.0
        for i in range(lay.n_petals):
            angle_deg = lay.angle_per_petal * i + stagger
            parts.append(
                f"""  rotate([0, 0, {angle_deg:g}])
  translate([{lay.ring_radius:g}, 0, 0])
  rotate([0, 0, {FACE_CENTER_Z_DEG:g}])
  scale([{lay.scale:g}, {lay.scale:g}, {lay.scale:g}])
  import("{stl_name}");"""
            )
    return header + "union() {\n" + "\n".join(parts) + "\n}\n"


@dataclass(frozen=True)
class RingLayout:
    ring: int
    ring_radius: float
    scale: float
    n_petals: int
    angle_per_petal: float


def iter_ring_layouts() -> Iterator[RingLayout]:
    """Ring radius, scale, and petal count — single source for layout and assembly SCAD."""
    if NUM_RINGS <= 0:
        return
    scale_step = (1.0 - MIN_SCALE) / (NUM_RINGS - 1) if NUM_RINGS > 1 else 0.0
    for ring in range(NUM_RINGS):
        ring_radius = INNER_RING_RADIUS + ring * RING_SPACING
        scale = MIN_SCALE + ring * scale_step
        circumference = 2 * math.pi * ring_radius
        n_petals = max(3, int((circumference / PETAL_ARC_MM) * (1.0 / scale)))
        yield RingLayout(
            ring=ring,
            ring_radius=ring_radius,
            scale=scale,
            n_petals=n_petals,
            angle_per_petal=360.0 / n_petals,
        )


def _print_flower_layout() -> None:
    """Log ring radii, petals per ring, and totals (same math as ``generate_flower``)."""
    print("Flower layout:")
    print(
        f"  NUM_RINGS={NUM_RINGS}, INNER_RING_RADIUS={INNER_RING_RADIUS}, "
        f"RING_SPACING={RING_SPACING}, PETAL_ARC_MM={PETAL_ARC_MM}, MIN_SCALE={MIN_SCALE}"
    )
    total_petals = 0
    for lay in iter_ring_layouts():
        total_petals += lay.n_petals
        circumference = 2 * math.pi * lay.ring_radius
        print(
            f"  ring {lay.ring}: radius={lay.ring_radius:.2f} mm, circumference={circumference:.2f} mm, "
            f"scale={lay.scale:.4f}, petals={lay.n_petals}"
        )
    print(f"  total petals (all rings): {total_petals}")


def fix_import(scad: str) -> str:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    std = os.path.abspath(os.path.join(root, "BOSL2", "std.scad"))
    file_header = f'include <{std.replace(os.sep, "/")}>\n'

    scad = file_header + scad
    scad = re.sub(
        r"^\s*use <[^>]*BOSL2/(beziers|lists)\.scad>\s*\n",
        "",
        scad,
        flags=re.MULTILINE,
    )
    return scad

current_dir = os.path.dirname(os.path.abspath(__file__))
out_dir = os.path.join(current_dir, "out")

def write_to_file(filename: str, content: s.OpenSCADObject) -> None:
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    Path(os.path.join(out_dir, filename + ".scad")).write_text(fix_import(s.scad_render(content)))


def write_raw_scad(filename: str, body: str) -> None:
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    Path(os.path.join(out_dir, filename + ".scad")).write_text(body)


def to_stl(file_name: str) -> None:
    file_path = os.path.join(out_dir, f"{file_name}.scad")
    subprocess.run(
        [OPENSCAD_PATH, "-o", os.path.join(out_dir, f"{file_name}.stl"), file_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )


_print_flower_layout()

for debug in [True, False]:
    postfix = "-debug" if debug else ""
    single_petal_file_name = "single-petal" + postfix
    write_to_file(single_petal_file_name, single_petal_geometry(debug))
    print(f"Wrote cad/out/{single_petal_file_name}.scad")
    flower_assembly_file_name = "flower-assembly" + postfix
    write_raw_scad(flower_assembly_file_name, generate_flower_assembly_scad(single_petal_file_name))
    print(f"Wrote cad/out/{flower_assembly_file_name}.scad (imports {single_petal_file_name}.stl)")
    if "--3d" in sys.argv:
        to_stl(single_petal_file_name)
        print(f"Wrote cad/out/{single_petal_file_name}.stl")
        to_stl(flower_assembly_file_name)
        print(f"Wrote cad/out/{flower_assembly_file_name}.stl")
print("Done!")
