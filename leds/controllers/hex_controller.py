# pylint: disable=duplicate-code

import math
from typing import Any, List, Tuple, Callable, Union, TYPE_CHECKING, Dict
from leds.color import RGBW
from leds.controllers.controller_base import ControllerBase

if TYPE_CHECKING:
    from config import HexConfig, Hexagon
    from leds.mock import MockPixelStrip  # pylint: disable=ungrouped-imports

# Arbitrary number. What this number is doesn't matter, as long as it's consistent
# Making it somewhat high does help making visualizer programming a lot easier since
# the pixel numbers are easier to work with.
HEX_SIZE = 100
HEX_X_SCALE = 0.8
HEX_Y_SCALE = 0.9


class HexPanel:
    def __init__(self, panel_config: "Hexagon", strip: "MockPixelStrip"):
        self.panel_config = panel_config
        self.strip = strip

    def get_edges(self) -> Tuple[float, float, float, float]:
        x_per_hex = HEX_SIZE * HEX_X_SCALE
        y_per_hex = HEX_SIZE * HEX_Y_SCALE
        hex_base_x = self.panel_config.x * x_per_hex
        hex_base_y = self.panel_config.y * y_per_hex
        return (
            hex_base_x,
            hex_base_x + x_per_hex,
            hex_base_y,
            hex_base_y + y_per_hex,
        )

    def get_center_x(self):
        base_x, end_x, _, _ = self.get_edges()
        return (base_x + end_x) / 2

    def get_center_y(self):
        _, _, base_y, end_y = self.get_edges()
        return (base_y + end_y) / 2

    def get_angle_at_index(self, index: int) -> float:
        """
        Calculate the angle for a specific LED index around the hexagon.
        """
        # Get the total number of LEDs in this hexagon
        total_leds = len(self.panel_config.ordered_leds)

        # Calculate what fraction of the circle this index represents
        fraction = index / total_leds

        # Convert to degrees
        return ((-fraction * 360) + 360 + 180 - 30) % 360

    def get_x_y_at_index(self, index: int) -> Tuple[float, float]:
        angle = self.get_angle_at_index(index)
        return round((HEX_SIZE * 0.9 * 0.5) * math.sin(math.radians(angle))), round(
            (HEX_SIZE * 0.9 * 0.5) * math.cos(math.radians(angle))
        )

    def set_color(self, color: RGBW):
        for index in self.panel_config.ordered_leds:
            self.strip.setPixelColor(index, color)


class HexPanelLEDController(ControllerBase):
    def __init__(self, config: "HexConfig", mock: bool):
        super().__init__(config, mock)

        (pin, channel) = config.pins
        self.strip = ControllerBase.init_strip(
            self.PixelStrip, config.get_led_count(), pin, channel
        )
        self.config = config
        self.panels: List[HexPanel] = [
            HexPanel(hexagon, self.strip) for hexagon in config.hexagons
        ]
        self.max_x = 0
        self.max_y = 0
        self.cached_coordinates: List[List[Tuple[float, float, Tuple[int, int]]]] = (
            []
        )  # Cache for pre-calculated coordinates
        for panel in self.panels:
            for panel in self.panels:
                self.max_x = max(self.max_x, panel.get_edges()[1])
                self.max_y = max(self.max_y, panel.get_edges()[3])

        # Pre-calculate and cache coordinates
        total_center_x = self.max_x / 2
        total_center_y = self.max_y / 2
        self.led_number_map: Dict[int, Tuple[int, int]] = {}

        for panel_index, panel in enumerate(self.panels):
            center_x = panel.get_center_x()
            center_y = panel.get_center_y()

            panel_cache: List[Tuple[float, float, Tuple[int, int]]] = []
            for led_index, led_number in enumerate(panel.panel_config.ordered_leds):
                self.led_number_map[led_number] = (panel_index, led_index)
                relative_x, relative_y = panel.get_x_y_at_index(led_index)
                absolute_x = center_x + relative_x - total_center_x
                absolute_y = center_y + relative_y - total_center_y
                panel_cache.append((absolute_x, absolute_y, (panel_index, led_number)))
            self.cached_coordinates.append(panel_cache)

    def map_coordinates(
        self, callback: Callable[[float, float, Tuple[int, int]], Union[RGBW, None]]
    ) -> None:
        for panel_cache in self.cached_coordinates:
            for absolute_x, absolute_y, indices in panel_cache:
                color = callback(absolute_x, absolute_y, indices)
                if color is not None:
                    panel_index, led_index = indices
                    self.panels[panel_index].strip.setPixelColor(led_index, color)

    def get_coordinates(self, strip_index: int, led_index: int) -> Tuple[float, float]:
        panel_index, _ = self.led_number_map[led_index]
        for absolute_x, absolute_y, indices in self.cached_coordinates[panel_index]:
            if indices == (panel_index, led_index):
                return absolute_x, absolute_y
        raise ValueError(
            f"Coordinates not found for panel {panel_index} and led {led_index}"
        )

    def get_strips(self) -> List["MockPixelStrip"]:
        return list({panel.strip for panel in self.panels})

    def get_visualizer_config(self) -> Any:
        return {
            "type": "hex",
            "hex_size": HEX_SIZE,
            "max_x": self.max_x,
            "max_y": self.max_y,
            "hexagons": [hexagon.to_dict() for hexagon in self.config.hexagons],
        }
