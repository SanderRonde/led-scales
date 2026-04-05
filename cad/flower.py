# pyright: reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
# pyright: reportUnknownParameterType=false
# pyright: reportPrivateUsage=false
# pylint: disable=duplicate-code

import os
import re
import sys
from pathlib import Path

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
RESOLUTION_DETAILED = 360

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
    outer_curve = beziers.bezpath_curve(outer_bezpath, splinesteps=24)
    inner_curve = beziers.bezpath_curve(inner_bezpath, splinesteps=24)

    # ``flatten([outer, inner])`` plus ``move`` centers the full petal like mirroring the half.
    petal_shape = transforms.move(
        [-PETAL_X, 0], p=lists.flatten([outer_curve, inner_curve])
    )
    elliptic_arc = transforms.xscale(
        4, p=drawing.arc(n=RESOLUTION_DEBUG if debug else RESOLUTION_DETAILED, angle=[180, 0], r=1))
    # Reverse so profile winding matches the sweep; path_sweep2d needs a 2D path (shape Y → Z).
    sweep_path = lists.reverse(elliptic_arc)
    petal = skin.path_sweep2d(petal_shape, sweep_path)

    extension = s.projection(cut=True)(petal)
    extension = s.linear_extrude(height=10, convexity=4)(extension)
    extension = s.mirror((0, 0, 1))(extension)
    petal = s.union()(petal, extension)

    # Rotate a bit and translate to match
    petal = s.translate((0, 0, 9))(s.rotate((-45, 0, 0))(petal))
    return petal

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

def write_to_file(filename: str, content: s.OpenSCADObject) -> None:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(current_dir, "out")
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    Path(os.path.join(out_dir, filename)).write_text(fix_import(s.scad_render(content)))

write_to_file("flower-debug.scad", generate_petal(True))
write_to_file("flower-print.scad", generate_petal(False))


print("Done!")
