# pyright: reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
# pyright: reportUnknownParameterType=false
# pyright: reportPrivateUsage=false
# pylint: disable=duplicate-code

import hashlib
import json
import math
import os
import re
from dataclasses import dataclass
import sys
from pathlib import Path
from typing import Dict, List, Optional
import subprocess
import solid as s

# To auto watch and run:
# bun x nodemon --exec "python cad/flower.py" --watch "cad/flower.py"

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

RESOLUTION_DEBUG = 24
RESOLUTION_DETAILED = 100
# Sweep profile density: path_sweep2d cost scales with this × sweep segments; keep debug low.
SPLINE_STEPS_DEBUG = 8
SPLINE_STEPS_PRINT = 24

# Flower layout (tune): concentric rings around origin in XY, petals face the center.
NUM_RINGS = 6
MIN_SCALE = 0.35
INNER_RING_RADIUS = 35.0
RING_SPACING_DELTA = 40.0
# Target arc length along each ring per petal — smaller ⇒ more petals on that ring.
PETAL_ARC_MM = 45.0
# Extra Z rotation so petal local “forward” points radially inward after placement.
FACE_CENTER_Z_DEG = 300.0
PETAL_ROTATE = 50.0
EST_WEIGHT_G = 21
PETAL_BASE_RADIUS = 7

OPENSCAD_PATH = (
    "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"
    if sys.platform == "darwin"
    else "B:\\programs\\Program Files\\OpenSCAD\\openscad.exe"
)

beziers = s.import_scad("BOSL2/beziers.scad")
lists = s.import_scad("BOSL2/lists.scad")
skin = s.import_scad("BOSL2/skin.scad")
transforms = s.import_scad("BOSL2/transforms.scad")
drawing = s.import_scad("BOSL2/drawing.scad")


def generate_petal_base_pins() -> s.OpenSCADObject:
    pin = s.translate((6, 0, -10))(s.cylinder(r=1, h=10, segments=100))
    return pin + s.rotate((0, 0, 120))(pin) + s.rotate((0, 0, 240))(pin)


def generate_petal_base() -> s.OpenSCADObject:
    return (
        s.translate((0, 0, -1))(s.cylinder(r=PETAL_BASE_RADIUS, h=1, segments=100))
        + generate_petal_base_pins()
    )


def generate_petal(debug: bool) -> s.OpenSCADObject:
    petal_x = 12
    outer_bezpath = lists.flatten(
        [
            beziers.bez_begin([0, 0], [0, 0]),
            beziers.bez_joint([-9, 50], [0, -20], [0, 20]),
            beziers.bez_joint([0, 95], [-4, -4], [4, 4]),
            beziers.bez_end([petal_x, 100], [0, 0]),
        ]
    )
    inner_bezpath = lists.flatten(
        [
            beziers.bez_begin([petal_x, 96], [5, 0]),
            beziers.bez_joint([2, 92], [5, 5], [-5, -5]),
            beziers.bez_joint([-6, 50], [0, 10], [0, -10]),
            beziers.bez_end([4, 0], [-5, 10]),
        ]
    )
    outer_curve = beziers.bezpath_curve(
        outer_bezpath, splinesteps=SPLINE_STEPS_DEBUG if debug else SPLINE_STEPS_PRINT
    )
    inner_curve = beziers.bezpath_curve(
        inner_bezpath, splinesteps=SPLINE_STEPS_DEBUG if debug else SPLINE_STEPS_PRINT
    )

    # ``flatten([outer, inner])`` plus ``move`` centers the full petal like mirroring the half.
    petal_shape = transforms.move(
        [-petal_x, 0], p=lists.flatten([outer_curve, inner_curve])
    )
    elliptic_arc = transforms.xscale(
        3,
        p=drawing.arc(
            n=RESOLUTION_DEBUG if debug else RESOLUTION_DETAILED, angle=[180, 0], r=1
        ),
    )
    # Reverse so profile winding matches the sweep; path_sweep2d needs a 2D path (shape Y → Z).
    sweep_path = lists.reverse(elliptic_arc)
    petal = skin.path_sweep2d(petal_shape, sweep_path)

    # Debug skips the base extension: it duplicates path_sweep2d and projection(cut) is very slow.
    extension = s.projection(cut=True)(petal)
    extension = s.linear_extrude(height=15, convexity=4)(extension)
    extension = s.mirror((0, 0, 1))(extension)
    petal = petal + extension

    # Rotate a bit and translate to match
    petal = s.translate((0, 0, 9))(s.rotate((-PETAL_ROTATE, 0, 0))(petal))

    # Remove the XZ plane
    cube = s.translate((0, 0, -50))(s.cube([100, 100, 100], center=True))

    return petal - cube


def get_center_radius() -> float:
    center_layer = iter_ring_layouts()[0]
    return center_layer.ring_radius - PETAL_BASE_RADIUS - 1


def generate_flower_assembly(
    flower: Optional[s.OpenSCADObject], base: s.OpenSCADObject
) -> s.OpenSCADObject:
    obj = s.union()
    for lay in iter_ring_layouts():
        stagger = lay.angle_per_petal / 2.0 if lay.ring % 2 == 0 else 0.0
        for i in range(lay.n_petals):
            angle_deg = lay.angle_per_petal * i + stagger
            scaled_obj = base
            if flower:
                scaled_obj = scaled_obj + s.scale((lay.scale, lay.scale, lay.scale))(
                    flower
                )
            obj = obj + (
                s.rotate((0, 0, angle_deg))(
                    s.translate((lay.ring_radius, 0, 0))(
                        s.rotate((0, 0, FACE_CENTER_Z_DEG))(scaled_obj)
                    )
                )
            )

    return obj


def generate_center() -> s.OpenSCADObject:
    return s.cylinder(get_center_radius(), 1)


@dataclass(frozen=True)
class RingLayout:
    ring: int
    ring_radius: float
    scale: float
    n_petals: int
    angle_per_petal: float


def iter_ring_layouts() -> List[RingLayout]:
    """Ring radius, scale, and petal count — single source for layout and assembly SCAD."""
    scale_step = (1.0 - MIN_SCALE) / (NUM_RINGS - 1) if NUM_RINGS > 1 else 0.0
    ring_radius = INNER_RING_RADIUS
    ring_layouts = []
    for ring in range(NUM_RINGS):
        scale = MIN_SCALE + ring * scale_step
        ring_radius += RING_SPACING_DELTA * scale
        circumference = 2 * math.pi * ring_radius
        n_petals = max(3, int((circumference / PETAL_ARC_MM) * (1.0 / scale)))
        ring_layouts.append(
            RingLayout(
                ring=ring,
                ring_radius=ring_radius,
                scale=scale,
                n_petals=n_petals,
                angle_per_petal=360.0 / n_petals,
            )
        )
    return ring_layouts


def print_flower_layout() -> None:
    """Log ring radii, petals per ring, and totals (same math as ``generate_flower``)."""
    print("Flower layout:")
    print(f"  num rings:{NUM_RINGS}\n  center radius:{get_center_radius()}")
    total_petals = 0
    total_weight_g = 0
    for lay in iter_ring_layouts():
        total_petals += lay.n_petals
        circumference = 2 * math.pi * lay.ring_radius
        total_weight_g += lay.n_petals * EST_WEIGHT_G * lay.scale**2
        print(
            f"  ring {lay.ring}: radius={lay.ring_radius:.2f} mm, circumference={circumference:.2f} mm, "
            f"scale={lay.scale:.4f}, petals={lay.n_petals}"
        )
    print(f"  total petals (all rings): {total_petals}")
    print(f"  total weight (all rings): {total_weight_g:.2f} g")


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


def write_to_file(
    folder: str,
    file_name: str,
    content: s.OpenSCADObject,
    three_d_file_type: Optional[str],
) -> None:
    folder_path = os.path.join(out_dir, folder)
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    scad_path = os.path.join(folder_path, file_name + ".scad")
    Path(scad_path).write_text(fix_import(s.scad_render(content)), encoding="utf-8")
    print(f"Wrote {scad_path}")
    if "--3d" in sys.argv and three_d_file_type:
        three_d_path = os.path.join(folder_path, file_name + "." + three_d_file_type)
        three_d_status = to_3d(scad_path, three_d_path)
        print(f"Write {three_d_path} status: {three_d_status}")


THREE_D_CACHE_NAME = ".3d-cache.json"


def _scad_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_3d_cache() -> Dict[str, str]:
    cache_path = os.path.join(out_dir, THREE_D_CACHE_NAME)
    if not os.path.isfile(cache_path):
        return {}
    try:
        raw = json.loads(Path(cache_path).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, str] = {}
    for k, v in raw.items():
        if isinstance(k, str) and isinstance(v, str) and len(v) == 64:
            out[k] = v
    return out


def _save_3d_cache(cache: Dict[str, str]) -> None:
    cache_path = os.path.join(out_dir, THREE_D_CACHE_NAME)
    Path(cache_path).write_text(
        json.dumps(dict(sorted(cache.items())), indent=2) + "\n", encoding="utf-8"
    )


def to_3d(scad_path: str, three_d_path: str) -> str:
    if not os.path.isfile(scad_path):
        return "missing_scad"

    scad_hash = _scad_sha256(scad_path)
    cache = _load_3d_cache()
    if os.path.isfile(three_d_path) and cache.get(three_d_path) == scad_hash:
        return "skipped"

    result = subprocess.run(
        [OPENSCAD_PATH, "-o", three_d_path, scad_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode == 0 and os.path.isfile(three_d_path):
        cache[three_d_path] = scad_hash
        _save_3d_cache(cache)
        return "wrote"
    return "failed"


def main():
    variants = [True]
    if "--prod" in sys.argv:
        variants = [False]
    for debug in variants:
        folder = "petals/debug/" if debug else "petals/"

        # Single petal
        single_petal_file_name = "single-petal"
        write_to_file(folder, single_petal_file_name, generate_petal(debug), "stl")

        # Full assembly
        write_to_file(
            folder,
            "flower-assembly",
            generate_flower_assembly(
                s.import_(single_petal_file_name + ".stl"), generate_petal_base()
            )
            + generate_center(),
            None,
        )

        # Ring petals
        for lay in iter_ring_layouts():
            write_to_file(
                folder,
                f"scaled-petal-{lay.ring}",
                s.scale((lay.scale, lay.scale, lay.scale))(generate_petal(debug)),
                "3mf",
            )

        # Flower bases
        write_to_file(
            folder,
            "flower-bases",
            generate_flower_assembly(None, generate_petal_base()),
            None,
        )

        # Bases projection
        write_to_file(
            folder,
            "flower-bases-projection",
            generate_flower_assembly(
                None, s.projection(True)(generate_petal_base_pins())
            ),
            None,
        )

    print_flower_layout()
    print("Done!")


main()
