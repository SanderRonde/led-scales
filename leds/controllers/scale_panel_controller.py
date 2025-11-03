from typing import Type, Any, List, Tuple, Callable, Union, TYPE_CHECKING
from leds.color import RGBW
from leds.mock import MockPixelStrip
from leds.controllers.controller_base import ControllerBase

if TYPE_CHECKING:
    from config import ScaleConfig


class LEDPanel:
    def __init__(
        self,
        PixelStrip: Type[MockPixelStrip],
        config: "ScaleConfig",
        index: int,
        brightness: int = 255,
    ):
        self.num_pixels = config.scale_per_panel_count
        self.index = index
        self.config = config
        self._pixels: List[RGBW] = [RGBW(0, 0, 0, 0) for _ in range(self.num_pixels)]
        self._buffer: List[RGBW] = [RGBW(0, 0, 0, 0) for _ in range(self.num_pixels)]
        self._brightness = brightness
        pin, channel = config.pins[index]
        self.strip = ControllerBase.init_strip(
            PixelStrip, self.num_pixels, pin, channel
        )

    @property
    def distance_from_center(self) -> int:
        center_panel = int((self.config.panel_count - 1) / 2)
        if self.index == center_panel:
            return 0
        return self.index - center_panel

    def get_base_x(self) -> float:
        bottom_left_offset = -0.5 * self.config.x_count
        scales_offset = self.config.x_count * self.distance_from_center
        inter_panel_spacing_offset = (
            self.config.panel_spacing_scales * self.distance_from_center
        )
        return bottom_left_offset + scales_offset + inter_panel_spacing_offset + 0.5

    def set_color(self, color: RGBW) -> None:
        for i in range(self.num_pixels):
            self._buffer[i] = color


class ScalePanelLEDController(ControllerBase):
    def __init__(self, config: "ScaleConfig", mock: bool, **kwargs: Any):
        super().__init__(config, mock)
        self.config = config
        self.panels: List[LEDPanel] = [
            LEDPanel(self.PixelStrip, config, index, **kwargs)
            for index in range(config.panel_count)
        ]
        self.cached_coordinates: List[List[Tuple[float, float, Tuple[int, int]]]] = []
        for panel in self.panels:
            panel_cache: List[Tuple[float, float, Tuple[int, int]]] = []
            base_x = panel.get_base_x()
            center_y = self.config.y_count / 2
            led_index = 0
            y = 0
            for x in range(self.config.x_count):
                # First go up from the bottom left
                for y in range(self.config.y_count):
                    panel_cache.append(
                        (base_x + x, center_y - y - 1, (panel.index, led_index))
                    )
                    led_index += 1
                y += 1

                if x != self.config.x_count - 1:
                    # Then go down again
                    for y in range(self.config.y_count):
                        panel_cache.append(
                            (
                                base_x + x + 0.5,
                                center_y - (self.config.y_count - (y + 0.5)),
                                (panel.index, led_index),
                            )
                        )
                        led_index += 1
                    y += 1
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
        for absolute_x, absolute_y, indices in self.cached_coordinates[strip_index]:
            if indices == (strip_index, led_index):
                return absolute_x, absolute_y
        raise ValueError(
            f"Coordinates not found for panel {strip_index} and led {led_index}"
        )

    def get_strips(self) -> List["MockPixelStrip"]:
        return [panel.strip for panel in self.panels]

    def get_visualizer_config(self) -> Any:
        return {
            "type": "scale",
            "x_count": self.config.x_count,
            "y_count": self.config.y_count,
            "panel_count": self.config.panel_count,
            "spacing": self.config.spacing,
            "space_between_panels": self.config.space_between_panels,
            "total_width": self.config.total_width,
            "total_height": self.config.total_height,
            "scale_length": self.config.base_length,
            "scale_width": self.config.base_width,
        }
