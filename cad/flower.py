# pyright: reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
# pyright: reportUnknownParameterType=false
# pyright: reportPrivateUsage=false
# pylint: disable=duplicate-code

import os
import re
import sys
from pathlib import Path
from typing import Any, List, Optional

import solid as s

# To auto watch and run:
# bun x nodemon --exec "python cad/flower.py" --watch "cad/flower.py"

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SHOW_BEZIER_DEBUG = True
PETAL_X = 12

beziers = s.import_scad("BOSL2/beziers.scad")
lists = s.import_scad("BOSL2/lists.scad")


def half_petal_outer_bezpath() -> List[Any]:
    """Closed-form cubic bezpath via BOSL2 ``bez_begin`` / ``bez_joint`` / ``bez_end``."""
    return lists.flatten(
        [
            beziers.bez_begin([0, 0], [0, 0]),
            beziers.bez_joint([-12, 50], [0, -20], [0, 20]),
            beziers.bez_joint([0, 80], [-4, -4], [4, 4]),
            beziers.bez_end([PETAL_X, 84], [0, 0]),
        ]
    )


def half_petal_inner_bezpath() -> List[Any]:
    return lists.flatten(
        [
            beziers.bez_begin([PETAL_X, 76], [5, 0]),
            beziers.bez_joint([2, 72], [5, 5], [-5, -5]),
            beziers.bez_joint([-6, 50], [0, 10], [0, -10]),
            beziers.bez_end([5, 0], [-5, 10]),
        ]
    )


def create_half_flower_petal(
    bezier_samples: int = 24,
    debug: Optional[bool] = None,
):
    """2D half-petal outline via BOSL2 ``bezpath_curve``; tune ``*_bezpath()`` helpers below."""
    show_handles = SHOW_BEZIER_DEBUG if debug is None else debug

    outer_bezpath = half_petal_outer_bezpath()
    inner_bezpath = half_petal_inner_bezpath()

    outer_curve = beziers.bezpath_curve(outer_bezpath, splinesteps=bezier_samples)
    inner_curve = beziers.bezpath_curve(inner_bezpath, splinesteps=bezier_samples)
    pts = lists.flatten([outer_curve, inner_curve])

    poly = s.polygon(pts)
    if not show_handles:
        return poly

    w = 0.5
    dbg = (
        beziers.debug_bezier(outer_bezpath, width=w, N=3)()
        + beziers.debug_bezier(inner_bezpath, width=w, N=3)()
    )
    return poly + dbg


def create_flower_petal(
    bezier_samples: int = 24,
    debug: Optional[bool] = None,
):
    """2D flower petal outline; mirrored half-petals."""
    return s.translate((-PETAL_X, 0, 0))(
        create_half_flower_petal(bezier_samples, debug=debug)
    ) + s.translate((PETAL_X, 0, 0))(
        s.mirror((1, 0, 0))(create_half_flower_petal(bezier_samples, debug=debug))
    )


def main():
    return create_flower_petal()


def _bosl2_std_include_line() -> str:
    """``use <beziers.scad>`` alone does not load ``paths.scad``; ``debug_bezier`` needs ``is_path()`` from the full library."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    std = os.path.abspath(os.path.join(root, "BOSL2", "std.scad"))
    return f'include <{std.replace(os.sep, "/")}>\n'


def _strip_redundant_bosl2_use(scad_text: str) -> str:
    """Drop ``use <.../beziers.scad>`` and ``lists.scad`` after ``include std.scad`` to avoid duplicate definitions."""
    return re.sub(
        r"^\s*use <[^>]*BOSL2/(beziers|lists)\.scad>\s*\n",
        "",
        scad_text,
        flags=re.MULTILINE,
    )


current_dir = os.path.dirname(os.path.abspath(__file__))
out_dir = os.path.join(current_dir, "out")
out_scad = os.path.join(out_dir, "flower.scad")
written = s.scad_render_to_file(
    main(),
    out_scad,
    file_header=_bosl2_std_include_line(),
)
path = Path(written)
path.write_text(
    _strip_redundant_bosl2_use(path.read_text(encoding="utf-8")), encoding="utf-8"
)

print("Done!")
