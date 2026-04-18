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
from typing import Dict, Iterator, List
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
    petal = petal - cube

    # Add a base
    base = s.translate((0, 0, -1))(s.cylinder(r=16, h=1, segments=100))
    pin = s.translate((14, 0, -10))(s.cylinder(r=2, h=10, segments=100))
    base = base + pin + s.rotate((0, 0, 120))(pin) + s.rotate((0, 0, 240))(pin)

    return (petal - cube) + base


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
    ring_radius = INNER_RING_RADIUS
    for ring in range(NUM_RINGS):
        scale = MIN_SCALE + ring * scale_step
        ring_radius += RING_SPACING_DELTA * scale
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
        f"RING_SPACING_MAX={RING_SPACING_DELTA}, PETAL_ARC_MM={PETAL_ARC_MM}, MIN_SCALE={MIN_SCALE}"
    )
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


def write_to_file(filename: str, content: s.OpenSCADObject, file_type: str) -> str:
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    scad_path = os.path.join(out_dir, filename + ".scad")
    Path(scad_path).write_text(fix_import(s.scad_render(content)))
    if "--3d" in sys.argv:
        return to_3d(scad_path, f"{filename}.{file_type}")
    return "2d-only"


def write_raw_scad(filename: str, body: str) -> None:
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    Path(os.path.join(out_dir, filename + ".scad")).write_text(body)


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


_print_flower_layout()

variants = [True]
if "--prod" in sys.argv:
    variants = [False]
for debug in variants:
    postfix = "-debug" if debug else ""
    single_petal_file_name = "single-petal" + postfix
    status = write_to_file(single_petal_file_name, generate_petal(debug), "stl")
    print(f"Wrote cad/out/{single_petal_file_name}.scad status: {status}")

    flower_assembly_file_name = "flower-assembly" + postfix
    write_raw_scad(
        flower_assembly_file_name, generate_flower_assembly_scad(single_petal_file_name)
    )
    print(
        f"Wrote cad/out/{flower_assembly_file_name}.scad (imports {single_petal_file_name}.stl)"
    )

    for lay in iter_ring_layouts():
        scaled_petal = s.scale((lay.scale, lay.scale, lay.scale))(generate_petal(debug))
        status = write_to_file(f"scaled-petal-{lay.ring}", scaled_petal, "3mf")
        print(
            f"Wrote cad/out/scaled-petal-{lay.ring}.scad status: {status}. Print {lay.n_petals} times"
        )
print("Done!")
