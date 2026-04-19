import hashlib
import json
import math
import os
import random
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

# Sunflower-center tuning: phyllotaxis field + stamen rim around the flat disc.
GOLDEN_ANGLE_DEG = 137.50776405003785
CENTER_BASE_HEIGHT = 8.0
# Controls phyllotaxis radial spacing: r_n = CENTER_FLORET_SPACING * sqrt(n).
CENTER_FLORET_SPACING = 2.0
# Inner fraction of the center radius that gets cones (rest gets stars).
CENTER_CONE_FRACTION = 0.45
CENTER_CONE_R1 = 1.1
CENTER_CONE_R2 = 0.15
CENTER_CONE_H = 1.8
# Outer-band florets: low-poly tapered pyramid (triangle/cube look, not flat star).
CENTER_STAR_BASE_R = 1.1
CENTER_STAR_TIP_R = 0.3
CENTER_STAR_H = 2.2
CENTER_STAR_SIDES = 4
# Random extra z-rotation range applied to each floret so orientations don't align.
CENTER_FLORET_JITTER_DEG = 45.0
# Dome rise from rim to center — the disc is a shallow spherical cap.
CENTER_DOME_HEIGHT_RATIO = 15 / 40
# Width of rim annulus reserved for stamens (excluded from floret field).
CENTER_ANTENNA_BAND = 6.0
# Target arc spacing between stamens around the rim.
CENTER_STAMEN_ARC_MM = 1.8
CENTER_STAMEN_R = 0.45
# Short stems print reliably and read less “spiky” than tall wavy ones.
CENTER_STAMEN_H = 3.4
CENTER_STAMEN_CAP_R = 0.48
# Concentric rows of stamens filling CENTER_ANTENNA_BAND, innermost rows are shorter.
CENTER_STAMEN_ROWS = 3
CENTER_STAMEN_ROW_SPACING = 1.4
# 1 = straight shaft + cap (best for FDM). >1 adds mild bends between segments.
CENTER_STAMEN_SEGMENTS = 1
CENTER_STAMEN_BEND_DEG = 5.0
# Small random tilt only — keeps a hint of variation without extreme angles.
CENTER_STAMEN_TILT_DEG = 4.0
CENTER_STAMEN_INWARD_BIAS_DEG = 4.0
CENTER_STAMEN_RNG_SEED = 1337
# Per-unit segment counts: keep low since we place hundreds of primitives.
CENTER_UNIT_SEGS_DEBUG = 6
CENTER_UNIT_SEGS_PRINT = 16

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


def _dome_sphere_radius(center_radius: float) -> float:
    """Radius of the sphere whose cap, with rise ``CENTER_DOME_HEIGHT`` over
    ``center_radius``, forms the sunflower disc's dome."""
    center_dome_height = CENTER_DOME_HEIGHT_RATIO * center_radius
    return (center_radius**2 + center_dome_height**2) / (2.0 * center_dome_height)


def _dome_z(r: float, center_radius: float) -> float:
    """Z-height of the dome surface at radial distance ``r`` from the axis,
    measured from the flat underside of the cap (rim sits at z=0, center at
    z=CENTER_DOME_HEIGHT)."""
    center_dome_height = CENTER_DOME_HEIGHT_RATIO * center_radius
    sphere_r = _dome_sphere_radius(center_radius)
    # Clamp to avoid tiny negatives from float error at r≈center_radius.
    inside = max(0.0, sphere_r**2 - r**2)
    return center_dome_height - sphere_r + math.sqrt(inside)


def _generate_cone_unit(debug: bool) -> s.OpenSCADObject:
    segs = CENTER_UNIT_SEGS_DEBUG if debug else CENTER_UNIT_SEGS_PRINT
    return s.cylinder(
        r1=CENTER_CONE_R1, r2=CENTER_CONE_R2, h=CENTER_CONE_H, segments=segs
    )


def _generate_star_unit(debug: bool) -> s.OpenSCADObject:
    """Outer-band floret: a low-poly tapered prism (cube-into-pyramid shape)
    instead of a flat 2D star. ``CENTER_STAR_SIDES`` controls the polygon
    (3=triangle, 4=cube-like)."""
    _ = debug
    return s.cylinder(
        r1=CENTER_STAR_BASE_R,
        r2=CENTER_STAR_TIP_R,
        h=CENTER_STAR_H,
        segments=CENTER_STAR_SIDES,
    )


def _generate_wavy_stamen(
    rng: random.Random, height: float, debug: bool
) -> s.OpenSCADObject:
    """Stamen: stacked cylinders with optional small random bends between segments,
    capped with a sphere, then a mild random overall tilt (inward bias on Y). With
    ``CENTER_STAMEN_SEGMENTS == 1`` this is a straight printable post + cap."""
    segs_n = CENTER_UNIT_SEGS_DEBUG if debug else CENTER_UNIT_SEGS_PRINT
    seg_h = height / CENTER_STAMEN_SEGMENTS

    # Start at the top: capped segment
    chain = s.cylinder(r=CENTER_STAMEN_R, h=seg_h, segments=segs_n) + s.translate(
        (0, 0, seg_h)
    )(s.sphere(r=CENTER_STAMEN_CAP_R, segments=segs_n))

    # Prepend further segments, each rotating the existing chain at the joint.
    for _ in range(CENTER_STAMEN_SEGMENTS - 1):
        bx = rng.uniform(-CENTER_STAMEN_BEND_DEG, CENTER_STAMEN_BEND_DEG)
        by = rng.uniform(-CENTER_STAMEN_BEND_DEG, CENTER_STAMEN_BEND_DEG)
        chain = s.cylinder(r=CENTER_STAMEN_R, h=seg_h, segments=segs_n) + s.translate(
            (0, 0, seg_h)
        )(s.rotate((bx, by, 0))(chain))

    tilt_x = rng.uniform(-CENTER_STAMEN_TILT_DEG, CENTER_STAMEN_TILT_DEG)
    # Positive rot_y tilts the top toward -x, which is toward the center after
    # the caller translates the stamen out to +x on the ring.
    tilt_y = CENTER_STAMEN_INWARD_BIAS_DEG + rng.uniform(
        -CENTER_STAMEN_TILT_DEG, CENTER_STAMEN_TILT_DEG
    )
    return s.rotate((tilt_x, tilt_y, 0))(chain)


def _generate_phyllotaxis_florets(
    center_radius: float, debug: bool
) -> s.OpenSCADObject:
    cone_unit = _generate_cone_unit(debug)
    star_unit = _generate_star_unit(debug)
    cone_cutoff_r = CENTER_CONE_FRACTION * center_radius
    # Leave a small margin between the outermost floret and the stamen band.
    max_r = center_radius - CENTER_ANTENNA_BAND - 0.5
    rng = random.Random(CENTER_STAMEN_RNG_SEED ^ 0xA5)

    obj = s.union()
    n = 1
    while True:
        r_n = CENTER_FLORET_SPACING * math.sqrt(n)
        if r_n > max_r:
            break
        theta_deg = n * GOLDEN_ANGLE_DEG
        unit = cone_unit if r_n < cone_cutoff_r else star_unit
        # Small per-floret z-rotation so adjacent pyramids don't all share an edge.
        jitter = rng.uniform(-CENTER_FLORET_JITTER_DEG, CENTER_FLORET_JITTER_DEG)
        z_surf = _dome_z(r_n, center_radius)
        obj = obj + s.rotate((0, 0, theta_deg))(
            s.translate((r_n, 0, z_surf))(s.rotate((0, 0, jitter))(unit))
        )
        n += 1
    return obj


def _generate_stamen_ring(center_radius: float, debug: bool) -> s.OpenSCADObject:
    """Concentric rings filling ``CENTER_ANTENNA_BAND``. Each stamen gets a
    seeded-random mild tilt (and optional waviness if ``CENTER_STAMEN_SEGMENTS`` > 1).
    """
    rng = random.Random(CENTER_STAMEN_RNG_SEED)
    # Outermost row sits near the edge; subsequent rows step inward.
    outer_ring_r = (
        center_radius
        - CENTER_ANTENNA_BAND * 0.5
        + ((CENTER_STAMEN_ROWS - 1) * CENTER_STAMEN_ROW_SPACING * 0.5)
    )

    obj = s.union()
    for row in range(CENTER_STAMEN_ROWS):
        r_ring = outer_ring_r - row * CENTER_STAMEN_ROW_SPACING
        n_stamens = max(12, int((2 * math.pi * r_ring) / CENTER_STAMEN_ARC_MM))
        # Stagger alternating rows by half the angular pitch.
        row_offset_deg = (row % 2) * (180.0 / n_stamens)
        # Inner rows slightly shorter — mimics real sunflower stamen gradient.
        row_height = CENTER_STAMEN_H * (1.0 - 0.12 * row)
        z_surf = _dome_z(r_ring, center_radius)
        for i in range(n_stamens):
            theta_deg = 360.0 * i / n_stamens + row_offset_deg
            stamen = _generate_wavy_stamen(rng, row_height, debug)
            obj = obj + s.rotate((0, 0, theta_deg))(
                s.translate((r_ring, 0, z_surf))(stamen)
            )
    return obj


def _generate_center_base(
    bottom_radius: float, top_radius: float, debug: bool
) -> s.OpenSCADObject:
    """Tapered base: a frustum skirt from ``bottom_radius`` at z=0 up to
    ``top_radius`` at z=CENTER_BASE_HEIGHT, topped by a shallow spherical dome
    of radius ``top_radius``. The skirt lets the center sit between the first
    ring's petal bases while still capping them once it rises above the floor."""
    base_segs = RESOLUTION_DEBUG if debug else RESOLUTION_DETAILED
    sphere_r = _dome_sphere_radius(top_radius)
    center_dome_height = CENTER_DOME_HEIGHT_RATIO * top_radius

    skirt = s.cylinder(
        r1=bottom_radius,
        r2=top_radius,
        h=CENTER_BASE_HEIGHT,
        segments=base_segs,
    )
    dome_cyl = s.translate((0, 0, CENTER_BASE_HEIGHT))(
        s.cylinder(r=top_radius, h=center_dome_height, segments=base_segs)
    )
    sphere_z = CENTER_BASE_HEIGHT + center_dome_height - sphere_r
    dome = s.translate((0, 0, sphere_z))(
        s.sphere(r=sphere_r, segments=max(base_segs * 2, 48))
    )
    return skirt + s.intersection()(dome_cyl, dome)


def generate_center(debug: bool) -> s.OpenSCADObject:
    center_layer = iter_ring_layouts()[0]
    center_radius_base = center_layer.ring_radius - PETAL_BASE_RADIUS - 1
    center_radius = center_layer.ring_radius + (PETAL_BASE_RADIUS / 2) - 1
    base = _generate_center_base(center_radius_base, center_radius, debug)
    florets = _generate_phyllotaxis_florets(center_radius, debug)
    stamens = _generate_stamen_ring(center_radius, debug)
    # Florets/stamens are authored with z=0 at the dome surface; lift them by
    # CENTER_BASE_HEIGHT so they sit on top of the cap.
    return base + s.translate((0, 0, CENTER_BASE_HEIGHT))(florets + stamens)


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
    ring_layouts: List[RingLayout] = []
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
    print(f"  num rings:{NUM_RINGS}")
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


def write_scad(content: s.OpenSCADObject, folder: str, file_name: str) -> str:
    scad_path = os.path.join(out_dir, folder, file_name + ".scad")
    parent_dir = os.path.dirname(scad_path)
    if not os.path.exists(parent_dir):
        os.makedirs(parent_dir)
    Path(scad_path).write_text(fix_import(s.scad_render(content)), encoding="utf-8")
    print(f"Wrote {scad_path}")
    return scad_path


def write_3d(scad_path: str) -> str:
    three_d_path = scad_path.replace(".scad", ".3mf")
    if "--3d" in sys.argv:
        three_d_status = to_3d(scad_path, three_d_path)
        print(f"Write {three_d_path} status: {three_d_status}")
    return three_d_path


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
        raw: Dict[str, str] = json.loads(Path(cache_path).read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    out: Dict[str, str] = {}
    for k, v in raw.items():
        if len(v) == 64:
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
        out_folder = "petals/debug/" if debug else "petals/"

        # Single petal
        single_petal_3d_path = write_3d(
            write_scad(generate_petal(debug), out_folder, "single-petal")
        )

        # Full assembly
        write_scad(
            generate_flower_assembly(
                s.import_(single_petal_3d_path), generate_petal_base()
            )
            + generate_center(debug),
            out_folder,
            "flower-assembly",
        )

        # Just the center
        write_3d(
            write_scad(
                generate_center(debug),
                out_folder,
                "flower-center",
            )
        )

        # Individual petals & all petals
        all_petals = s.union()
        for lay in iter_ring_layouts():
            scaled_petal_3d_path = write_3d(
                write_scad(
                    s.scale((lay.scale, lay.scale, lay.scale))(generate_petal(debug))
                    + generate_petal_base(),
                    out_folder,
                    f"parts/scaled-petal-{lay.ring}",
                )
            )
            for i in range(lay.n_petals):
                all_petals = all_petals + s.translate(
                    (lay.ring * RING_SPACING_DELTA, i * RING_SPACING_DELTA, 0)
                )(s.import_(scaled_petal_3d_path))
        write_3d(write_scad(all_petals, out_folder, "all-petals"))

        # Flower bases
        write_scad(
            generate_flower_assembly(None, generate_petal_base()),
            out_folder,
            "flower-bases",
        )

        # Bases projection
        write_scad(
            generate_flower_assembly(
                None, s.projection(True)(generate_petal_base_pins())
            ),
            out_folder,
            "flower-bases-projection",
        )

    print_flower_layout()
    print("Done!")


main()
