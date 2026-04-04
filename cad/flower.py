# pyright: reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
# pyright: reportUnknownParameterType=false
# pyright: reportPrivateUsage=false
# pylint: disable=duplicate-code

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

import solid as s

# To auto watch and run:
# bun x nodemon --exec "python cad/flower.py" --watch "cad/flower.py"

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SHOW_BEZIER_DEBUG = True
PETAL_X = 12

BOSL2 = s.import_scad("BOSL2")


@dataclass(frozen=True)
class BezierKnot:
    """One vertex on a cubic Bézier chain (Inkscape-style handles).

    Segment from knot i to i+1 uses:
      P0 = knot[i].xy, P1 = knot[i].xy + knot[i].out_tangent,
      P2 = knot[i+1].xy + knot[i+1].in_tangent, P3 = knot[i+1].xy

    First knot: ``in_tangent`` is ignored. Last knot: ``out_tangent`` is ignored.
    """

    xy: Tuple[float, float]
    out_tangent: Tuple[float, float] = (0.0, 0.0)
    in_tangent: Tuple[float, float] = (0.0, 0.0)


def knots_to_bezpath(knots: Sequence[BezierKnot]) -> List[List[float]]:
    """Flatten knots to a BOSL2 cubic (N=3) bezier path: len % 3 == 1."""
    if len(knots) < 2:
        return []

    flat: List[List[float]] = []
    for i in range(len(knots) - 1):
        p0 = knots[i].xy
        p1 = (p0[0] + knots[i].out_tangent[0], p0[1] + knots[i].out_tangent[1])
        p3 = knots[i + 1].xy
        p2 = (
            p3[0] + knots[i + 1].in_tangent[0],
            p3[1] + knots[i + 1].in_tangent[1],
        )
        if i == 0:
            flat.extend(
                [
                    [p0[0], p0[1]],
                    [p1[0], p1[1]],
                    [p2[0], p2[1]],
                    [p3[0], p3[1]],
                ]
            )
        else:
            flat.extend(
                [
                    [p1[0], p1[1]],
                    [p2[0], p2[1]],
                    [p3[0], p3[1]],
                ]
            )
    return flat


def create_half_flower_petal(
    bezier_samples: int = 24,
    debug: Optional[bool] = None,
):
    """2D half-petal outline via BOSL2 ``bezpath_curve``; tune knot tuples below."""
    show_handles = SHOW_BEZIER_DEBUG if debug is None else debug

    outer_knots: Tuple[BezierKnot, ...] = (
        BezierKnot((0, 0), out_tangent=(0, 0), in_tangent=(0, 0)),
        BezierKnot((-12, 50), out_tangent=(0, 20), in_tangent=(0, -20)),
        BezierKnot((0, 80), out_tangent=(4, 4), in_tangent=(-4, -4)),
        BezierKnot((PETAL_X, 84), out_tangent=(0, 0), in_tangent=(0, 0)),
    )

    inner_knots: Tuple[BezierKnot, ...] = (
        BezierKnot((PETAL_X, 76), out_tangent=(5, 0), in_tangent=(-5, 0)),
        BezierKnot((2, 72), out_tangent=(-5, -5), in_tangent=(5, 5)),
        BezierKnot((-6, 50), out_tangent=(0, -10), in_tangent=(0, 10)),
        BezierKnot((5, 0), out_tangent=(0, 0), in_tangent=(-5, 10)),
    )

    outer_bezpath = knots_to_bezpath(outer_knots)
    inner_bezpath = knots_to_bezpath(inner_knots)

    outer_curve = BOSL2.beziers.bezpath_curve(outer_bezpath, splinesteps=bezier_samples)
    inner_curve = BOSL2.beziers.bezpath_curve(inner_bezpath, splinesteps=bezier_samples)
    pts = BOSL2.lists.flatten([outer_curve, inner_curve])

    poly = s.polygon(pts)
    if not show_handles:
        return poly

    w = 0.5
    dbg = (
        BOSL2.beziers.debug_bezier(outer_bezpath, width=w, N=3)()
        + BOSL2.beziers.debug_bezier(inner_bezpath, width=w, N=3)()
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
