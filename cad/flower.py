from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import struct
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import subprocess
import ezdxf
from ezdxf.enums import InsertUnits, Measurement
import numpy as np
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
# Extra space between copies on the exported ``all-petals`` plate (Python merge).
ALL_PETALS_PLATE_GAP_MM = 2.0

# -----------------------------------------------------------------------------
# Petal color: ring 0 (innermost) uses PETAL_GRADIENT_CENTER, ring NUM_RINGS-1
# uses PETAL_GRADIENT_OUTER, with linear RGB interpolation between. Values are
# "#RRGGBB" hex strings (also accepted: "RRGGBB" without #).
# -----------------------------------------------------------------------------
# --- Default: yellow (center) → red (outer) ---
PETAL_GRADIENT_CENTER = "#fcea81"
PETAL_GRADIENT_OUTER = "#fc3d4f"

# Target arc length along each ring per petal — smaller ⇒ more petals on that ring.
PETAL_ARC_MM = 45.0
# Extra Z rotation so petal local “forward” points radially inward after placement.
FACE_CENTER_Z_DEG = 300.0
PETAL_ROTATE = 50.0
EST_WEIGHT_G = 21
PETAL_BASE_RADIUS = 7
# Petal base pins (2D projection for backplate must match these)
PETAL_PIN_OFFSET_MM = 6.0
PETAL_PIN_BASE_R = 1.0
# Backplate 2D — single source for OpenSCAD ``generate_backplate`` and primitive DXF
BACKPLATE_OUTER_EXTRA_MM = 1.0
BACKPLATE_CENTER_HOLE_R = 2.5
BACKPLATE_MOUNT_OFFSET_MM = 15.0
BACKPLATE_MOUNT_HOLE_R = 2.0

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
TOLERANCE = 0.1

PLATE_THICKNESS = 3.0

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


def _parse_hex_rgb01(hex_color: str) -> Tuple[float, float, float]:
    h = hex_color.strip().lstrip("#")
    if len(h) != 6 or any(c not in "0123456789abcdefABCDEF" for c in h):
        raise ValueError(f"PETAL gradient color must be #RRGGBB (got {hex_color!r})")
    r = int(h[0:2], 16) / 255.0
    g = int(h[2:4], 16) / 255.0
    b = int(h[4:6], 16) / 255.0
    return (r, g, b)


def petal_rgb_for_ring(ring: int) -> Tuple[float, float, float]:
    """RGB in 0..1 for ``ring`` (0 = inner, NUM_RINGS-1 = outer)."""
    t = 0.0 if NUM_RINGS <= 1 else ring / float(NUM_RINGS - 1)
    t = max(0.0, min(1.0, t))
    c0 = _parse_hex_rgb01(PETAL_GRADIENT_CENTER)
    c1 = _parse_hex_rgb01(PETAL_GRADIENT_OUTER)
    return (
        c0[0] + (c1[0] - c0[0]) * t,
        c0[1] + (c1[1] - c0[1]) * t,
        c0[2] + (c1[2] - c0[2]) * t,
    )


def with_petal_ring_color(ring: int, obj: s.OpenSCADObject) -> s.OpenSCADObject:
    r, g, b = petal_rgb_for_ring(ring)
    return s.color((r, g, b))(obj)


def generate_petal_base_pins(
    tolerance: float = 0.0, extra_height: float = 0
) -> s.OpenSCADObject:
    height = 3 + extra_height
    pin = s.translate((PETAL_PIN_OFFSET_MM, 0, -(height - 1)))(
        s.cylinder(r=PETAL_PIN_BASE_R + tolerance, h=height, segments=100)
    )
    return pin + s.rotate((0, 0, 120))(pin) + s.rotate((0, 0, 240))(pin)


def generate_petal_base() -> s.OpenSCADObject:
    return s.cylinder(r=PETAL_BASE_RADIUS, h=2, segments=100)


def generate_petal_aligner() -> s.OpenSCADObject:
    return s.cylinder(r=PETAL_BASE_RADIUS, h=2, segments=100) + s.translate((0, 0, -1))(
        generate_petal_base_pins(-0.2, PLATE_THICKNESS - 0.25)
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

    # Cap the petal opening
    cap = s.linear_extrude(height=2, convexity=4)(
        s.hull()(s.projection(cut=True)(petal))
    )
    petal = petal + cap

    # Remove everything below Z=0 (the XZ plane)
    cube = s.translate((0, 0, -50))(s.cube([100, 100, 100], center=True))

    return petal - cube


def generate_flower_assembly(
    flower: Optional[s.OpenSCADObject], base: s.OpenSCADObject
) -> s.OpenSCADObject:
    obj = s.union()
    for lay in get_ring_layouts():
        stagger = lay.angle_per_petal / 2.0 if lay.ring % 2 == 0 else 0.0
        for i in range(lay.n_petals):
            angle_deg = lay.angle_per_petal * i + stagger
            scaled_obj = base
            if flower:
                scaled_obj = scaled_obj + s.scale((lay.scale, lay.scale, lay.scale))(
                    flower
                )
                scaled_obj = with_petal_ring_color(lay.ring, scaled_obj)
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
    center_layer = get_ring_layouts()[0]
    center_radius_base = center_layer.ring_radius - PETAL_BASE_RADIUS - 1
    center_radius = center_layer.ring_radius + (PETAL_BASE_RADIUS / 2) - 1
    base = _generate_center_base(center_radius_base, center_radius, debug)
    # Add center hole
    base = base + s.translate((0, 0, -3))(
        s.cylinder(r=BACKPLATE_CENTER_HOLE_R - 0.2, h=3, segments=100)
    )
    # Cut out mount ring
    mount_ring = s.difference()(
        s.cylinder(r=(BACKPLATE_MOUNT_OFFSET_MM * 2) + 2, h=4, segments=200),
        s.cylinder(r=(BACKPLATE_MOUNT_OFFSET_MM * 2) - 2, h=4, segments=200),
    )
    base = base - s.translate((0, 0, -1))(mount_ring)

    florets = _generate_phyllotaxis_florets(center_radius, debug)
    stamens = _generate_stamen_ring(center_radius, debug)
    # Florets/stamens are authored with z=0 at the dome surface; lift them by
    # CENTER_BASE_HEIGHT so they sit on top of the cap.
    return base + s.translate((0, 0, CENTER_BASE_HEIGHT))(florets + stamens)


def backplate_outer_radius_mm() -> float:
    """Outside radius of the backplate disc (mm)."""
    last_ring = get_ring_layouts()[-1]
    return last_ring.ring_radius + PETAL_BASE_RADIUS + BACKPLATE_OUTER_EXTRA_MM


def _rot_z_xy(angle_deg: float, x: float, y: float) -> Tuple[float, float]:
    a = math.radians(angle_deg)
    c, si = math.cos(a), math.sin(a)
    return (c * x - si * y, si * x + c * y)


def petal_pin_local_xy_offsets() -> List[Tuple[float, float]]:
    """XY offsets of the three pin centers in petal-base local coordinates."""
    return [_rot_z_xy(k * 120.0, PETAL_PIN_OFFSET_MM, 0.0) for k in range(3)]


def backplate_pin_center_xy(
    lay: RingLayout, petal_index: int, local_x: float, local_y: float
) -> Tuple[float, float]:
    """World XY of one pin after the same transforms as ``generate_flower_assembly``."""
    stagger = lay.angle_per_petal / 2.0 if lay.ring % 2 == 0 else 0.0
    angle_deg = lay.angle_per_petal * petal_index + stagger
    x0, y0 = _rot_z_xy(FACE_CENTER_Z_DEG, local_x, local_y)
    x1 = x0 + lay.ring_radius
    y1 = y0
    return _rot_z_xy(angle_deg, x1, y1)


def get_backplate_dxf_circles() -> List[Tuple[float, float, float]]:
    """All backplate circles as ``(cx, cy, radius)`` mm for primitive DXF.

    First circle is the outer outline; remaining are holes (center, mounting, pins).
    """
    r_out = backplate_outer_radius_mm()
    circles: List[Tuple[float, float, float]] = [(0.0, 0.0, r_out)]
    circles.append((0.0, 0.0, BACKPLATE_CENTER_HOLE_R))
    o = BACKPLATE_MOUNT_OFFSET_MM
    for dx, dy in ((-o, -o), (o, -o), (-o, o), (o, o)):
        circles.append((dx, dy, BACKPLATE_MOUNT_HOLE_R))
    r_pin = PETAL_PIN_BASE_R + TOLERANCE
    for lx, ly in petal_pin_local_xy_offsets():
        for lay in get_ring_layouts():
            for i in range(lay.n_petals):
                cx, cy = backplate_pin_center_xy(lay, i, lx, ly)
                circles.append((cx, cy, r_pin))
    return circles


def _backplate_dxf_geometry_hash() -> str:
    payload = json.dumps(
        [
            (round(cx, 9), round(cy, 9), round(r, 9))
            for cx, cy, r in get_backplate_dxf_circles()
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def write_backplate_dxf_primitive(dxf_path: str) -> None:
    """Write backplate as DXF ``CIRCLE`` entities (true primitives, not tessellated)."""
    parent = os.path.dirname(dxf_path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent)

    doc = ezdxf.new("R2010")  # type: ignore[attr-defined]
    # Geometry in ``flower.py`` is authored in millimeters; declare DXF units to match.
    doc.units = InsertUnits.Millimeters
    doc.header["$MEASUREMENT"] = Measurement.Metric
    msp = doc.modelspace()
    for cx, cy, r in get_backplate_dxf_circles():
        msp.add_circle((float(cx), float(cy)), float(r))  # type: ignore[attr-defined]
    doc.saveas(dxf_path)  # type: ignore[attr-defined]


def generate_backplate() -> s.OpenSCADObject:
    r_out = backplate_outer_radius_mm()
    plate = s.circle(r=r_out, segments=1000)

    # Holes for petals
    plate = plate - generate_flower_assembly(
        None, s.projection(True)(generate_petal_base_pins(TOLERANCE))
    )

    # Center hole
    plate = plate - s.circle(r=BACKPLATE_CENTER_HOLE_R, segments=100)

    # Holes for mounting
    mounting_hole = s.circle(r=BACKPLATE_MOUNT_HOLE_R, segments=100)
    o = BACKPLATE_MOUNT_OFFSET_MM
    plate = plate - s.translate((-o, -o, 0))(mounting_hole)
    plate = plate - s.translate((o, -o, 0))(mounting_hole)
    plate = plate - s.translate((-o, o, 0))(mounting_hole)
    plate = plate - s.translate((o, o, 0))(mounting_hole)

    return plate


@dataclass(frozen=True)
class RingLayout:
    ring: int
    ring_radius: float
    scale: float
    n_petals: int
    angle_per_petal: float


def get_ring_layouts() -> List[RingLayout]:
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
    for lay in get_ring_layouts():
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
        status = to_export(scad_path, three_d_path)
        print(f"Wrote {three_d_path} ({status})")
    return three_d_path


def write_dxf(scad_path: str) -> str:
    dxf_path = scad_path.replace(".scad", ".dxf")
    if "--3d" not in sys.argv:
        return dxf_path
    geom_hash = _backplate_dxf_geometry_hash()
    cache = _load_export_cache()
    if os.path.isfile(dxf_path) and cache.get(dxf_path) == geom_hash:
        print(f"Wrote {dxf_path} (cached)")
        return dxf_path
    write_backplate_dxf_primitive(dxf_path)
    cache[dxf_path] = geom_hash
    _save_export_cache(cache)
    print(f"Wrote {dxf_path} (new)")
    return dxf_path


EXPORT_CACHE_NAME = ".export-cache.json"


def _scad_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_export_cache() -> Dict[str, str]:
    cache_path = os.path.join(out_dir, EXPORT_CACHE_NAME)
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


def _save_export_cache(cache: Dict[str, str]) -> None:
    cache_path = os.path.join(out_dir, EXPORT_CACHE_NAME)
    Path(cache_path).write_text(
        json.dumps(dict(sorted(cache.items())), indent=2) + "\n", encoding="utf-8"
    )


_THREEMF_CORE_NS = "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"


def _threemf_tag(local: str) -> str:
    return f"{{{_THREEMF_CORE_NS}}}{local}"


def read_3mf_triangle_mesh(path: str) -> Tuple[np.ndarray, np.ndarray]:
    """Load the first mesh from a 3MF as ``(vertices, faces)`` (N×3, M×3)."""
    with zipfile.ZipFile(path, "r") as zf:
        model_xml = zf.read("3D/3dmodel.model")
    root = ET.fromstring(model_xml)
    mesh = root.find(f".//{_threemf_tag('mesh')}")
    if mesh is None:
        raise ValueError(f"No mesh in 3MF: {path}")

    verts_el = mesh.find(_threemf_tag("vertices"))
    if verts_el is None:
        raise ValueError(f"No vertices in 3MF: {path}")
    n = len(verts_el)
    vertices = np.empty((n, 3), dtype=np.float64)
    for i, ve in enumerate(verts_el):
        vertices[i, 0] = float(ve.attrib["x"])
        vertices[i, 1] = float(ve.attrib["y"])
        vertices[i, 2] = float(ve.attrib["z"])

    tris_el = mesh.find(_threemf_tag("triangles"))
    if tris_el is None:
        raise ValueError(f"No triangles in 3MF: {path}")
    m = len(tris_el)
    faces = np.empty((m, 3), dtype=np.int64)
    for i, te in enumerate(tris_el):
        faces[i, 0] = int(te.attrib["v1"])
        faces[i, 1] = int(te.attrib["v2"])
        faces[i, 2] = int(te.attrib["v3"])

    return vertices, faces


def write_binary_stl(path: str, vertices: np.ndarray, faces: np.ndarray) -> None:
    """Write a binary STL (single solid, possibly disjoint shells)."""
    v = np.ascontiguousarray(vertices, dtype=np.float64)
    f = np.ascontiguousarray(faces, dtype=np.int64)
    tris = v[f]
    e1 = tris[:, 1] - tris[:, 0]
    e2 = tris[:, 2] - tris[:, 0]
    ns = np.cross(e1, e2)
    ln = np.linalg.norm(ns, axis=1, keepdims=True)
    ln = np.maximum(ln, 1e-30)
    normals = (ns / ln).astype(np.float32)
    pts = tris.astype(np.float32)
    n_tri = int(pts.shape[0])
    header = b"all-petals plate (merged in Python)\0"
    header = (header + b"\0" * 80)[:80]
    rec = np.empty(
        n_tri,
        dtype=np.dtype(
            [("n", "<f4", (3,)), ("v", "<f4", (9,)), ("a", "<u2")], align=False
        ),
    )
    rec["n"] = normals
    rec["v"] = pts.reshape(n_tri, 9)
    rec["a"] = 0
    with open(path, "wb") as fp:
        fp.write(header)
        fp.write(struct.pack("<I", n_tri))
        rec.tofile(fp)


def combine_scaled_petals_plate_stl(
    out_folder: str, ring_layouts: List[RingLayout]
) -> Optional[str]:
    """Place ``n_petals`` copies of each ring mesh on a flat plate and write one STL.

    Avoids OpenSCAD ``import()`` + ``union()`` for ``all-petals``, which is very slow
    when there are hundreds of instances.
    """
    if "--3d" not in sys.argv:
        return None

    meshes: Dict[int, Tuple[np.ndarray, np.ndarray]] = {}
    for lay in ring_layouts:
        mf = os.path.join(out_dir, out_folder, f"parts/scaled-petal-{lay.ring}.3mf")
        if not os.path.isfile(mf):
            print(f"combine_scaled_petals_plate_stl: missing {mf}, skip plate")
            return None
        meshes[lay.ring] = read_3mf_triangle_mesh(mf)

    out_blocks_v: List[np.ndarray] = []
    out_blocks_f: List[np.ndarray] = []
    v_offset = 0
    y_cursor = 0.0

    for lay in ring_layouts:
        vertices, faces = meshes[lay.ring]
        vmin = vertices.min(axis=0)
        vmax = vertices.max(axis=0)
        size = vmax - vmin
        pitch_x = float(size[0]) + ALL_PETALS_PLATE_GAP_MM
        x_cursor = 0.0
        for _ in range(lay.n_petals):
            delta = np.array(
                [x_cursor - vmin[0], y_cursor - vmin[1], -vmin[2]], dtype=np.float64
            )
            out_blocks_v.append(vertices + delta)
            out_blocks_f.append(faces + v_offset)
            v_offset += vertices.shape[0]
            x_cursor += pitch_x
        y_cursor += float(size[1]) + ALL_PETALS_PLATE_GAP_MM

    v_all = np.vstack(out_blocks_v)
    f_all = np.vstack(out_blocks_f)
    stl_path = os.path.join(out_dir, out_folder, "all-petals.stl")
    parent = os.path.dirname(stl_path)
    if not os.path.exists(parent):
        os.makedirs(parent)
    write_binary_stl(stl_path, v_all, f_all)
    print(f"Wrote {stl_path} ({v_all.shape[0]} vertices, {f_all.shape[0]} triangles)")
    return stl_path


def to_export(scad_path: str, export_path: str) -> str:
    if not os.path.isfile(scad_path):
        raise FileNotFoundError(f"SCAD file not found: {scad_path}")

    scad_hash = _scad_sha256(scad_path)
    cache = _load_export_cache()
    if os.path.isfile(export_path) and cache.get(export_path) == scad_hash:
        return "cached"

    result = subprocess.run(
        [OPENSCAD_PATH, "-o", export_path, scad_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode != 0 or not os.path.isfile(export_path):
        raise RuntimeError(f"Failed to write 3MF file: {export_path}")
    cache[export_path] = scad_hash
    _save_export_cache(cache)
    return "new"


def _reexec_with_pythonhashseed_zero_if_needed() -> None:
    """SolidPython output can vary across runs unless PYTHONHASHSEED is fixed (set/dict iteration).

    Re-exec once so the interpreter and solid see a stable seed; export cache keys on SCAD SHA-256 then match.
    """
    if os.environ.get("PYTHONHASHSEED") == "0":
        return
    if os.environ.get("CAD_FLOWER_SKIP_HASHSEED_REEXEC") == "1":
        return
    env = os.environ.copy()
    env["PYTHONHASHSEED"] = "0"
    script = os.path.normpath(os.path.abspath(__file__))
    argv = [sys.executable, script, *sys.argv[1:]]
    os.execve(sys.executable, argv, env)


def main():
    _reexec_with_pythonhashseed_zero_if_needed()
    variants = [True]
    if "--prod" in sys.argv:
        variants = [False]
    for debug in variants:
        out_folder = "petals/debug/" if debug else "petals/"

        # Single petal (inner-ring hue)
        single_petal_3d_path = write_3d(
            write_scad(
                with_petal_ring_color(0, generate_petal(debug)),
                out_folder,
                "single-petal",
            )
        )

        # Full assembly
        write_scad(
            (
                generate_flower_assembly(
                    s.import_(single_petal_3d_path), generate_petal_base()
                )
                + generate_center(debug)
            )
            - generate_petal_base_pins(0),
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

        # Individual petals; one plate STL merged in Python (no OpenSCAD all-petals union).
        ring_layouts = get_ring_layouts()
        for lay in ring_layouts:
            write_3d(
                write_scad(
                    with_petal_ring_color(
                        lay.ring,
                        (
                            s.scale((lay.scale, lay.scale, lay.scale))(
                                generate_petal(debug)
                            )
                            + generate_petal_base()
                        )
                        - generate_petal_base_pins(0),
                    ),
                    out_folder,
                    f"parts/scaled-petal-{lay.ring}",
                )
            )
        combine_scaled_petals_plate_stl(out_folder, ring_layouts)

        # Flower bases
        write_scad(
            (
                generate_flower_assembly(None, generate_petal_base())
                - generate_petal_base_pins(0)
            ),
            out_folder,
            "flower-bases",
        )

        write_3d(
            write_scad(
                generate_petal_aligner(),
                out_folder,
                "petal-aligner",
            )
        )

        # Backplate
        write_dxf(
            write_scad(
                generate_backplate(),
                out_folder,
                "backplate",
            )
        )

    print_flower_layout()
    print("Done!")


if __name__ == "__main__":
    main()
