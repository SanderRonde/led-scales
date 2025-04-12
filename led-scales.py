# pyright: reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false
# pyright: reportUnknownParameterType=false
# pyright: reportPrivateUsage=false

# To auto watch and run:
# bun x nodemon --exec "python led-scales.py" --watch "led-scales.py"

import math
import subprocess
import sys
import os
from enum import Enum
from typing import Dict, Tuple, List, Union

import openpyscad as ops

# Scale
base_length = 25
base_width = 2
base_height = 110
spike_size = 50

# Scale lean
lean_base = 5
lean_factor = 0.05

# Panel
spacing = 55
x_count = 6
y_count = 12

# Panel counts
panel_count = 3

# LED - not really but easier to drill
led_diameter = 3

# Weight and price
estimated_weight_g = 23 / 2
price_per_kilo = 20

# Printing
print_bed_spacing = 400
x_print_bed = 200
y_print_bed = 200
x_print_spacing = 15
y_print_additional_spacing = 6
print_outside_padding = 20
scad_path = "B:/programs/Program Files/OpenSCAD/openscad.exe"
x_per_build_plate_override = None
y_per_build_plate_override: Union[int, None] = 1

x_print_bed = x_print_bed - print_outside_padding
y_print_bed = y_print_bed - print_outside_padding

# Debug
is_fast = False

spike_height = base_height - spike_size


class Mode(Enum):
    PRINT = 1
    POSITIONING = 2
    TWO_D = 3
    THREE_D = 4


def scale_half():
    sub_y_cube = ops.Cube([base_length, base_width, spike_height]
                          ).translate([0, 0, -spike_height])
    base = ops.Cube([base_length, base_width, spike_height])
    spike = ops.Polygon(points=[[0, 0], [base_length, 0], [base_width, spike_height]], paths=[
        [0, 1, 2]]).linear_extrude(height=base_width).rotate([90, 0, 0]).translate([0, base_width, spike_height])
    tip = ops.Cube([base_width, base_width, spike_height]
                   ).translate([0, 0, spike_height])
    return sub_y_cube + base + spike + tip


def lean_angle(distance: float):
    return lean_base + (distance * lean_factor)


def scale_3d(distance: float):
    size_of_scale = base_length + base_width

    scale = ops.Union()
    scale_mirror = scale_half().rotate([0, 0, -45])
    scale.append(scale_mirror)
    scale.append(scale_mirror.mirror([0, 1, 0]))
    return scale.rotate([0, -lean_angle(distance), 0]).translate([-math.sqrt(size_of_scale * size_of_scale / 2), 0, 0])


def scale(mode: Mode, distance: float):
    if mode == Mode.TWO_D or mode == Mode.POSITIONING:
        result = Projection(cut=True).append(scale_3d(distance))
        if mode != Mode.POSITIONING:
            result = result + ops.Circle(d=led_diameter)
        return result
    else:
        return scale_3d(distance)


def draw_panel(mode: Mode, scale_x_offset: int):
    coordinate_map: Dict[Tuple[int, int], float] = {}

    panel = ops.Union()
    x_half = math.floor(x_count / 2)
    y_half = math.floor(y_count / 2)
    for _i in range(-x_half, x_half):
        i = _i + scale_x_offset
        for j in range(-y_half, y_half):
            distance: float = math.sqrt(i*i + j*j) * spacing

            coordinate_map[(i, j)] = distance
            panel.append(scale(mode, distance).rotate([0, 0, 0 if mode == Mode.PRINT else math.degrees(math.atan2(
                j, i))]).translate([-(i * spacing) - (spacing / 2), -(j * spacing), 0]))
            if _i != -x_half:
                panel.append(scale(mode, distance).rotate([0, 0, 0 if mode == Mode.PRINT else math.degrees(math.atan2(
                    j + 0.5, i))]).translate([-(i * spacing), -(j * spacing) - (spacing / 2), 0]))
    return (panel, coordinate_map)


panel_width = (x_count) * spacing
panel_height = (y_count + 0.5) * spacing
total_width = panel_width * panel_count + \
    (spacing * (panel_count - 1))
total_height = panel_height


def draw(mode: Mode):
    joined_coordinate_map: Dict[Tuple[int, int], float] = {}

    result = ops.Union()
    panels: List[ops.Union] = []
    (center_panel, center_coordinate_map) = draw_panel(mode, 0)
    joined_coordinate_map.update(center_coordinate_map)
    panels.append(center_panel)
    result.append(center_panel)

    for i in range(1, math.floor((panel_count - 1) / 2) + 1):
        left_offset = i * x_count + 1
        (left_panel, left_coordinate_map) = draw_panel(mode, left_offset)
        panels.append(left_panel.translate([left_offset * spacing, 0, 0]))
        result.append(left_panel)
        joined_coordinate_map.update(left_coordinate_map)

        right_offset = -(i * x_count) - 1
        (right_panel, right_coordinate_map) = draw_panel(mode, right_offset)
        panels.append(right_panel.translate([right_offset * spacing, 0, 0]))
        result.append(right_panel)
        joined_coordinate_map.update(right_coordinate_map)

    return (result, joined_coordinate_map, panels)


def x_offset_for_lean(lean: float):
    c = base_height
    alpha = 90 - lean
    a = c * math.sin(math.radians(alpha))
    b = math.sqrt(c**2 - a**2)
    return b


def get_optimal_tile_x(distance_values: List[float], y_per_build_plate: int, total_max_lean: float):
    max_lean = 0
    for d in distance_values:
        max_lean = max(max_lean, lean_angle(d))

    x_lower_bound = math.floor(
        (x_print_bed - x_offset_for_lean(total_max_lean)) / x_print_spacing)
    x_upper_bound = math.floor(
        (x_print_bed) / x_print_spacing)

    for x in range(x_upper_bound, x_lower_bound, -1):
        included_distance_values = distance_values[:x * y_per_build_plate]
        max_lean_for_included = 0
        for d in included_distance_values:
            max_lean_for_included = max(max_lean_for_included, lean_angle(d))

        x_per_build_plate = math.floor(
            (x_print_bed - x_offset_for_lean(max_lean_for_included)) / x_print_spacing
        )
        if x == x_per_build_plate:
            # This means that given this x, we can indeed fit all the scales
            # given the actual max lean we get
            return (max_lean_for_included, x)
    return (x_offset_for_lean(max_lean), x_lower_bound)


def printable(coordinate_map: Dict[Tuple[int, int], float], mode: Mode, preview: bool):
    distance_items = sorted(coordinate_map.items(), key=lambda item: item[1])
    result = ops.Union()

    scale_small_side_length = math.sqrt(
        ((base_length - (base_width / 2)) * (base_length - (base_width / 2))) / 2)
    y_print_spacing = (scale_small_side_length * 2) + 6
    y_per_build_plate = math.floor(
        (y_print_bed) / y_print_spacing)
    if y_per_build_plate_override is not None:
        y_per_build_plate = y_per_build_plate_override

    total_count = 0
    tile_count = 0
    tiles: List[ops.Union] = list()
    while True:
        tile = ops.Union()
        tiles.append(tile)
        result.append(tile)

        max_lean = 0
        for _, d in distance_items:
            max_lean = max(max_lean, lean_angle(d))

        tile_offset = tile_count * print_bed_spacing
        (max_x_offset, x_per_build_plate) = get_optimal_tile_x(
            [d for _, d in distance_items[total_count:]], y_per_build_plate, max_lean)
        if x_per_build_plate_override is not None:
            x_per_build_plate = x_per_build_plate_override

        if preview and mode != Mode.POSITIONING:
            result.append(ops.Cube([x_print_bed, y_print_bed, 1]).translate(
                [tile_offset, 0, 0]).translate([
                    -scale_small_side_length,
                    -scale_small_side_length,
                    0
                ]))

        for x in range(x_per_build_plate):
            for y in range(y_per_build_plate):
                if total_count >= len(distance_items):
                    return (result, tiles)

                key, d = distance_items[total_count]
                translate_x = max_x_offset + \
                    tile_offset + (x * x_print_spacing)
                translate_y = y * y_print_spacing
                tile.append(scale(mode, d).translate(
                    [translate_x, translate_y, 0]))

                if mode == Mode.POSITIONING:
                    text = ops.Text('"{}"'.format(key), size=3, halign='"center"', valign='"center"').translate([translate_x, translate_y]).translate([
                        -x_print_spacing / 2, 0, 0])
                    text.turn_on_debug()
                    result.append(text)

                total_count += 1
        tile_count += 1


def main(mode: Mode, preview: bool = False):
    (result, coordinate_map, _) = draw(mode)
    if mode != Mode.PRINT and mode != Mode.POSITIONING:
        return result
    (printable_result, tiles) = printable(coordinate_map, mode, preview)
    if not preview:
        printable_result = printable_result - ops.Cube([
            (print_bed_spacing * len(tiles)) * 1.5,
            total_height * 1.5,
            base_height * 1.5
        ]).translate([(-total_width / 2) * 1.5, (-total_height / 2) * 1.5, -base_height * 1.5])
    return printable_result


def to_stls(file_name: str):
    (_result, coordinate_map, _) = draw(Mode.PRINT)
    (_result, tiles) = printable(coordinate_map, Mode.PRINT, False)
    for i in range(len(tiles)):
        negative = ops.Cube([
            (print_bed_spacing * len(tiles)) * 3,
            total_height * 1.5,
            base_height * 1.5
        ]).translate([(-total_width / 2) * 1.5, (-total_height / 2) * 1.5, -base_height * 1.5])
        tile_out_path = "{}-{}.scad".format(file_name, i)
        (tiles[i] - negative).write(tile_out_path)
        if "--stl" in sys.argv:
            subprocess.run([scad_path, "-o", "{}-{}.stl".format(file_name,
                                                                i), tile_out_path])


def to_panel_svgs(file_name: str):
    (_result, _coordinate_map, panels) = draw(Mode.TWO_D)
    for i in range(len(panels)):
        panel_out_path = "{}-{}.scad".format(file_name, i)
        panels[i].write(panel_out_path)
        if "--svg" in sys.argv:
            subprocess.run([scad_path, "-o", "{}-{}.svg".format(file_name,
                                                                i), panel_out_path])


ops.base.MetaObject.object_definition['projection'] = (
    'projection', ('cut', ), True)


class Projection(ops.transformations._Transformation):
    pass


print("Panel dimensions are ", panel_width, "x", panel_height)
print("Panel count is ", panel_count)
print("Total dimensions are ", total_width, "x", total_height)
print("Square meters are ", (panel_width * panel_height * panel_count) / 1000000)
print("Scale count is ", (x_count + x_count - 1) * y_count * panel_count)
print("Estimated weight is ", estimated_weight_g *
      (x_count + x_count - 1) * y_count * panel_count / 1000, "kg")
print("Estimated price is €", estimated_weight_g *
      (x_count + x_count - 1) * y_count * panel_count / 1000 * price_per_kilo)


((scale(Mode.THREE_D, 0) - ops.Cube([100, 100, 100]).translate(
    [-50, -50, -100])) + ops.Cylinder(d=led_diameter, h=1)).write("out/led-scales-py.single.scad")
main(Mode.THREE_D, preview=True).write("out/led-scales-py.scad")
main(Mode.TWO_D, preview=True).write("out/led-scales-py.2d.scad")
main(Mode.PRINT, preview=False).write("out/led-scales-py.print.scad")
main(Mode.POSITIONING, preview=False).write(
    "out/led-scales-py.positioning.scad")

# Create output directories if they don't exist
if not os.path.exists("out/tiles"):
    os.makedirs("out/tiles")
    print("Created directory: out/tiles/")
if not os.path.exists("out/panels"):
    os.makedirs("out/panels")
    print("Created directory: out/panels/")
to_stls("out/tiles/Led Scales Tile")
to_panel_svgs("out/panels/Led Scales Panel")
