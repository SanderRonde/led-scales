# pyright: reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
# pyright: reportUnknownParameterType=false
# pyright: reportPrivateUsage=false
# pylint: disable=duplicate-code

# To auto watch and run:
# bun x nodemon --exec "python cad/led-scales.py" --watch "cad/led-scales.py"

import math
import subprocess
import sys
import os
import shutil
from enum import Enum
from typing import Dict, Tuple, List, Callable
import openpyscad as ops
from config import ScaleConfig

# Add parent directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Load configuration
config = ScaleConfig()


class Mode(Enum):
    PRINT = 1
    POSITIONING = 2
    TWO_D = 3
    THREE_D = 4


def scale_half():
    sub_y_cube = ops.Cube(
        [config.base_length, config.base_width, config.spike_height]
    ).translate([0, 0, -config.spike_height])
    base = ops.Cube([config.base_length, config.base_width, config.spike_height])
    spike = (
        ops.Polygon(
            points=[
                [0, 0],
                [config.base_length, 0],
                [config.base_width, config.spike_height],
            ],
            paths=[[0, 1, 2]],
        )
        .linear_extrude(height=config.base_width)
        .rotate([90, 0, 0])
        .translate([0, config.base_width, config.spike_height])
    )
    tip = ops.Cube(
        [config.base_width, config.base_width, config.spike_height]
    ).translate([0, 0, config.spike_height])
    return sub_y_cube + base + spike + tip


def lean_angle(distance: float):
    return config.lean_base + (distance * config.lean_factor)


def hsv_to_rgb(h: float, s: float = 1.0, v: float = 1.0) -> str:
    """Convert HSV color to RGB hex string. H is in degrees (0-360), S and V are 0-1."""
    h = h % 360
    s = max(0, min(1, s))
    v = max(0, min(1, v))

    c = v * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = v - c

    if h < 60:
        r, g, b = c, x, 0
    elif h < 120:
        r, g, b = x, c, 0
    elif h < 180:
        r, g, b = 0, c, x
    elif h < 240:
        r, g, b = 0, x, c
    elif h < 300:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x

    r = int(round((r + m) * 255))
    g = int(round((g + m) * 255))
    b = int(round((b + m) * 255))
    return f"#{r:02X}{g:02X}{b:02X}"


def draw_scale_3d(distance: float):
    size_of_scale = config.base_length + config.base_width

    scale = ops.Union()
    scale_mirror = scale_half().rotate([0, 0, -45])
    scale.append(scale_mirror)
    scale.append(scale_mirror.mirror([0, 1, 0]))
    return scale.rotate([0, -lean_angle(distance), 0]).translate(
        [-math.sqrt(size_of_scale * size_of_scale / 2), 0, 0]
    )


def draw_scale(mode: Mode, distance: float):
    if mode in [Mode.TWO_D, Mode.POSITIONING]:
        result = Projection(cut=True).append(draw_scale_3d(distance))
        if mode == Mode.TWO_D:
            result = result + ops.Circle(d=config.led_template_diameter)
        return result
    return draw_scale_3d(distance)


def get_coordinate_map(panel_index: int, scale_x_offset: int):
    coordinate_map: Dict[Tuple[int, float, float], float] = {}

    x_half = math.floor(config.x_count / 2)
    y_half = math.floor(config.y_count / 2)
    for _i in range(-x_half, x_half):
        i = _i + scale_x_offset
        for j in range(-y_half, y_half):
            distance: float = math.sqrt(i * i + j * j) * config.spacing
            coordinate_map[(panel_index, i + 0.5, j)] = distance
            if i != -x_half:
                coordinate_map[(panel_index, i, j + 0.5)] = distance

    return coordinate_map


def draw_panel(
    mode: Mode,
    panel_index: int,
    coordinate_map: Dict[Tuple[int, float, float], float],
    sorted_coordinates: List[Tuple[Tuple[int, float, float], float]],
    scale_x_offset: int,
):
    x_half = math.floor(config.x_count / 2)
    y_half = math.floor(config.y_count / 2)

    get_text: Callable[[int], ops.Text] = lambda coordinate_map_index: (
        ops.Text(
            f'"{coordinate_map_index}"',
            size=6,
            halign='"center"',
            valign='"center"',
        ).color(hsv_to_rgb(coordinate_map_index % 360))
        if mode != Mode.PRINT
        else None
    )

    panel = ops.Union()
    for _i in range(-x_half, x_half):
        i = _i + scale_x_offset
        for j in range(-y_half, y_half):
            coordinate_map_key = (panel_index, i + 0.5, j)
            distance = coordinate_map[coordinate_map_key]
            coordinate_map_index = sorted_coordinates.index(
                (coordinate_map_key, distance)
            )

            panel.append(
                (
                    (
                        (draw_scale(mode, distance)).rotate(
                            [
                                0,
                                0,
                                (
                                    0
                                    if mode == Mode.PRINT
                                    else math.degrees(math.atan2(j, i))
                                ),
                            ]
                        )
                    )
                    + get_text(coordinate_map_index)
                ).translate(
                    [
                        -(i * config.spacing) - (config.spacing / 2),
                        -(j * config.spacing),
                        0,
                    ]
                )
            )
            if i != -x_half:
                coordinate_map_key = (panel_index, i, j + 0.5)
                coordinate_map_index = sorted_coordinates.index(
                    (coordinate_map_key, distance)
                )
                panel.append(
                    (
                        (
                            draw_scale(mode, distance).rotate(
                                [
                                    0,
                                    0,
                                    (
                                        0
                                        if mode == Mode.PRINT
                                        else math.degrees(math.atan2(j + 0.5, i))
                                    ),
                                ]
                            )
                        )
                        + get_text(coordinate_map_index)
                    ).translate(
                        [
                            -(i * config.spacing),
                            -(j * config.spacing) - (config.spacing / 2),
                            0,
                        ]
                    )
                )
    return panel


def draw(mode: Mode):
    joined_coordinate_map: Dict[Tuple[int, float, float], float] = {}
    center_coordinate_map = get_coordinate_map(0, 0)
    joined_coordinate_map.update(center_coordinate_map)

    for i in range(1, math.floor((config.panel_count - 1) / 2) + 1):
        left_offset = i * config.x_count + config.panel_spacing_scales
        left_coordinate_map = get_coordinate_map(-i, left_offset)
        joined_coordinate_map.update(left_coordinate_map)

        right_offset = -(i * config.x_count) - config.panel_spacing_scales
        right_coordinate_map = get_coordinate_map(i, right_offset)
        joined_coordinate_map.update(right_coordinate_map)

    sorted_coordinates = sorted(joined_coordinate_map.items(), key=lambda x: x[1])

    result = ops.Union()
    panels: List[ops.Union] = []
    center_panel = draw_panel(mode, 0, joined_coordinate_map, sorted_coordinates, 0)
    panels.append(center_panel)
    result.append(center_panel)

    for i in range(1, math.floor((config.panel_count - 1) / 2) + 1):
        left_offset = i * config.x_count + config.panel_spacing_scales
        left_panel = draw_panel(
            mode, -i, joined_coordinate_map, sorted_coordinates, left_offset
        )
        panels.append(left_panel.translate([left_offset * config.spacing, 0, 0]))
        result.append(left_panel)

        right_offset = -(i * config.x_count) - config.panel_spacing_scales
        right_panel = draw_panel(
            mode, i, joined_coordinate_map, sorted_coordinates, right_offset
        )
        panels.append(right_panel.translate([right_offset * config.spacing, 0, 0]))
        result.append(right_panel)

    return (result, joined_coordinate_map, panels)


def x_offset_for_lean(lean: float):
    c = config.base_height
    alpha = 90 - lean
    a = c * math.sin(math.radians(alpha))
    b = math.sqrt(c**2 - a**2)
    return b


def get_optimal_tile_x(
    distance_values: List[float], y_per_build_plate: int, total_max_lean: float
):
    max_lean = 0
    for d in distance_values:
        max_lean = max(max_lean, lean_angle(d))

    x_lower_bound = math.floor(
        (config.print_bed_x - x_offset_for_lean(total_max_lean))
        / config.x_print_spacing
    )
    x_upper_bound = math.floor((config.print_bed_x) / config.x_print_spacing)

    for x in range(x_upper_bound, x_lower_bound, -1):
        included_distance_values = distance_values[: x * y_per_build_plate]
        max_lean_for_included = 0
        for d in included_distance_values:
            max_lean_for_included = max(max_lean_for_included, lean_angle(d))

        x_per_build_plate = math.floor(
            (config.print_bed_x - x_offset_for_lean(max_lean_for_included))
            / config.x_print_spacing
        )
        if x == x_per_build_plate:
            # This means that given this x, we can indeed fit all the scales
            # given the actual max lean we get
            return (max_lean_for_included, x)
    return (x_offset_for_lean(max_lean), x_lower_bound)


def printable(
    coordinate_map: Dict[Tuple[int, float, float], float], mode: Mode, preview: bool
):
    distance_items = sorted(coordinate_map.items(), key=lambda item: item[1])
    result = ops.Union()

    scale_small_side_length = math.sqrt(
        (
            (config.base_length - (config.base_width / 2))
            * (config.base_length - (config.base_width / 2))
        )
        / 2
    )
    y_print_spacing = (scale_small_side_length * 2) + 6
    y_per_build_plate = math.floor((config.print_bed_y) / y_print_spacing)
    if config.y_per_build_plate_override is not None:
        y_per_build_plate = config.y_per_build_plate_override

    total_count = 0
    tile_count = 0
    tiles: List[ops.Union] = []
    while True:
        tile = ops.Union()
        tiles.append(tile)
        result.append(tile)

        max_lean = 0
        for _, d in distance_items:
            max_lean = max(max_lean, lean_angle(d))

        tile_offset = tile_count * config.print_bed_spacing
        (max_x_offset, x_per_build_plate) = get_optimal_tile_x(
            [d for _, d in distance_items[total_count:]], y_per_build_plate, max_lean
        )
        if config.x_per_build_plate_override is not None:
            x_per_build_plate = config.x_per_build_plate_override

        if preview:
            result.append(
                ops.Cube([config.print_bed_x, config.print_bed_y, 1])
                .translate([tile_offset, 0, 0])
                .translate([-scale_small_side_length, -scale_small_side_length, 0])
            )

        for x in range(x_per_build_plate):
            for y in range(y_per_build_plate):
                _, d = distance_items[total_count]
                translate_x = max_x_offset + tile_offset + (x * config.x_print_spacing)
                translate_y = y * y_print_spacing
                tile.append(
                    draw_scale(mode, d).translate([translate_x, translate_y, 0])
                )

                total_count += 1
                if total_count >= len(distance_items):
                    return (result, tiles)
        tile_count += 1


def main(mode: Mode, preview: bool = False):
    (result, coordinate_map, _) = draw(mode)
    if mode != Mode.PRINT:
        return result
    (printable_result, tiles) = printable(coordinate_map, mode, preview)
    if not preview:
        printable_result = printable_result - ops.Cube(
            [
                (config.print_bed_spacing * len(tiles)) * 1.5,
                config.total_height * 1.5,
                config.base_height * 1.5,
            ]
        ).translate(
            [
                (-config.total_width / 2) * 1.5,
                (-config.total_height / 2) * 1.5,
                -config.base_height * 1.5,
            ]
        )
    return printable_result


def to_stls(file_name: str):
    (_result, coordinate_map, _) = draw(Mode.PRINT)
    (_result, tiles) = printable(coordinate_map, Mode.PRINT, False)
    for i, tile in enumerate(tiles):
        negative = ops.Cube(
            [
                (config.print_bed_spacing * len(tiles)) * 3,
                config.total_height * 1.5,
                config.base_height * 1.5,
            ]
        ).translate(
            [
                (-config.total_width / 2) * 1.5,
                (-config.total_height / 2) * 1.5,
                -config.base_height * 1.5,
            ]
        )
        tile_out_path = f"{file_name}-{i}.scad"
        (tile - negative).write(tile_out_path)
        if "--3d" in sys.argv:
            print(
                f"Converting SCAD file to STL for tile {i + 1}/{len(tiles)} ({(i+1)/len(tiles)*100:.1f}%)...",
                flush=True,
            )
            subprocess.run(
                [config.scad_path, "-o", f"{file_name}-{i}.stl", tile_out_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )


def to_panel_svgs(file_name: str):
    (_result, _coordinate_map, panels) = draw(Mode.TWO_D)
    for i, panel in enumerate(panels):
        panel_out_path = f"{file_name}-{i}.scad"
        panel.write(panel_out_path)
        if "--2d" in sys.argv:
            print(
                f"Converting SCAD file to SVG for panel {i+1}/{len(panels)} ({(i+1)/len(panels)*100:.1f}%)...",
                flush=True,
            )
            subprocess.run(
                [config.scad_path, "-o", f"{file_name}-{i}.svg", panel_out_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )


def diffusers(file_name: str):
    # Create the diffuser shape
    diffuser = ops.Union()

    base = ops.Cylinder(
        h=1, d1=config.led_diameter - 1, d2=config.led_diameter, _fn=100
    )
    diffuser.append(base)

    top = ops.Cylinder(
        h=config.led_diffuser_thickness - 1.5, d=config.led_diameter + 2, _fn=100
    )
    diffuser.append(top.translate([0, 0, 1]))

    fillet = ops.Cylinder(
        h=0.5, d1=config.led_diameter + 2, d2=config.led_diameter + 1, _fn=100
    )
    diffuser.append(fillet.translate([0, 0, config.led_diffuser_thickness - 0.5]))

    # Write to file
    diffuser_path = os.path.join(out_dir, f"{file_name}.scad")
    diffuser.write(diffuser_path)

    if "--3d" in sys.argv:
        print("Converting SCAD file to STL for diffuser...", flush=True)
        subprocess.run(
            [config.scad_path, "-o", f"{file_name}.stl", diffuser_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )


# This is not in the openpyscad library so we fix it here
ops.base.MetaObject.object_definition["projection"] = ("projection", ("cut",), True)


class Projection(
    ops.transformations._Transformation
):  # pylint: disable=protected-access
    pass


# Get the directory of the current file
current_dir = os.path.dirname(os.path.abspath(__file__))
out_dir = os.path.join(current_dir, "out")
tiles_dir = os.path.join(out_dir, "tiles")
panels_dir = os.path.join(out_dir, "panels")
diffuser_dir = os.path.join(out_dir, "diffuser")
# Create output directories if they don't exist
if not os.path.exists(out_dir):
    os.makedirs(out_dir)
    print(f"Created directory: {out_dir}", flush=True)
for directory in [tiles_dir, panels_dir, diffuser_dir]:
    if os.path.exists(directory):
        for file in os.listdir(directory):
            file_path = os.path.join(directory, file)
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
    else:
        os.makedirs(directory)
        print(f"Created directory: {directory}", flush=True)

(
    (
        draw_scale(Mode.THREE_D, 0)
        - ops.Cube([100, 100, 100]).translate([-50, -50, -100])
    )
    + ops.Cylinder(d=config.led_template_diameter, h=1)
).write(os.path.join(out_dir, "led-scales-py.single.scad"))
main(Mode.THREE_D, preview=True).write(os.path.join(out_dir, "led-scales-py.scad"))
main(Mode.TWO_D, preview=True).write(os.path.join(out_dir, "led-scales-py.2d.scad"))
main(Mode.PRINT, preview=False).write(os.path.join(out_dir, "led-scales-py.print.scad"))
main(Mode.POSITIONING, preview=True).write(
    os.path.join(out_dir, "led-scales-py.positioning.scad")
)

to_stls(os.path.join(tiles_dir, "Led Scales Tile"))
to_panel_svgs(os.path.join(panels_dir, "Led Scales Panel"))
diffusers(os.path.join(diffuser_dir, "diffuser"))

print("Panel dimensions are ", config.panel_width, "x", config.panel_height, flush=True)
print("Panel count is ", config.panel_count, flush=True)
print("Total dimensions are ", config.total_width, "x", config.total_height, flush=True)
print("Space between panels is ", config.space_between_panels, flush=True)
print("Square meters are ", config.total_area_m2, flush=True)
print("Scale count is ", config.get_led_count(), flush=True)
print("Estimated weight is ", config.total_weight_kg, "kg", flush=True)
print("Estimated filament price is €", config.total_price_eur, flush=True)
