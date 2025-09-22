import math
from typing import Any, List, Tuple, Callable, Union, TYPE_CHECKING
from leds.color import RGBW
from leds.controllers.controller_base import ControllerBase

if TYPE_CHECKING:
    from config import HexConfig, Hexagon
    from leds.mock import MockPixelStrip  # pylint: disable=ungrouped-imports

# Arbitrary number. What this number is doesn't matter, as long as it's consistent.
HEX_SIZE = 100


class HexPanel:
    def __init__(self, panel_config: "Hexagon", strip: "MockPixelStrip"):
        self.panel_config = panel_config
        self.strip = strip

    def get_center_x(self):
        return (self.panel_config.x + 0.5) * HEX_SIZE

    def get_center_y(self):
        return (self.panel_config.y + 0.5) * HEX_SIZE

    def get_angle_at_index(self, index: int) -> float:
        """
        Calculate the angle for a specific LED index around the hexagon.
        """
        # Get the total number of LEDs in this hexagon
        total_leds = len(self.panel_config.ordered_leds)

        # Calculate what fraction of the circle this index represents
        fraction = index / total_leds

        # Convert to degrees
        return ((-fraction * 360) + 360 + 180) % 360

    def get_x_y_at_index(self, index: int) -> Tuple[float, float]:
        angle = self.get_angle_at_index(index)
        return round((HEX_SIZE * 0.9) * math.sin(math.radians(angle))), round(
            (HEX_SIZE * 0.9) * math.cos(math.radians(angle))
        )

    def set_color(self, color: RGBW):
        for index in self.panel_config.ordered_leds:
            self.strip.setPixelColor(index, color)

class HexPanelLEDController(ControllerBase):
    def __init__(self, config: "HexConfig", mock: bool):
        super().__init__(mock)

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
        self.cached_coordinates = []  # Cache for pre-calculated coordinates
        for panel in self.panels:
            self.max_x = max(self.max_x, (panel.panel_config.x + 1) * HEX_SIZE)
            self.max_y = max(self.max_y, (panel.panel_config.y + 1) * HEX_SIZE)

        # Pre-calculate and cache coordinates
        total_center_x = self.max_x / 2
        total_center_y = self.max_y / 2

        for panel_index, panel in enumerate(self.panels):
            center_x = panel.get_center_x()
            center_y = panel.get_center_y()

            panel_cache = []
            for led_index in range(len(panel.panel_config.ordered_leds)):
                relative_x, relative_y = panel.get_x_y_at_index(led_index)
                absolute_x = center_x + relative_x - total_center_x
                absolute_y = center_y + relative_y - total_center_y
                panel_cache.append((absolute_x, absolute_y, (panel_index, panel.panel_config.ordered_leds[led_index])))
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
