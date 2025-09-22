from typing import Type, Any, List, Tuple, Callable, Union, TYPE_CHECKING
from functools import lru_cache
from leds.color import RGBW
from leds.mock import MockPixelStrip
from leds.controllers.controller_base import ControllerBase
from leds.performance import profile_function, profile_block

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
        
        # Cache frequently used values
        self._base_x = None
        self._center_y = config.y_count / 2

    @property
    def distance_from_center(self) -> int:
        center_panel = int((self.config.panel_count - 1) / 2)
        if self.index == center_panel:
            return 0
        return self.index - center_panel

    @lru_cache(maxsize=1)
    def get_base_x(self) -> float:
        if self._base_x is None:
            distance_from_center = self.distance_from_center
            self._base_x = (
                (distance_from_center - 0.5) * self.config.x_count
                + (self.config.panel_spacing_scales * abs(distance_from_center))
                + 0.5
            )
        return self._base_x

    def set_color(self, color: RGBW) -> None:
        for i in range(self.num_pixels):
            self._buffer[i] = color


class ScalePanelLEDController(ControllerBase):
    @profile_function("ScalePanelLEDController.__init__")
    def __init__(self, config: "ScaleConfig", mock: bool, **kwargs: Any):
        super().__init__(mock)
        self.config = config
        
        with profile_block("ScalePanelLEDController.panels_creation"):
            self.panels: List[LEDPanel] = [
                LEDPanel(self.PixelStrip, config, index, **kwargs)
                for index in range(config.panel_count)
            ]

    @profile_function("ScalePanelLEDController.map_coordinates")
    def map_coordinates(
        self, callback: Callable[[float, float, Tuple[int, int]], Union[RGBW, None]]
    ) -> None:
        # Pre-calculate values to avoid repeated computation
        x_count = self.config.x_count
        y_count = self.config.y_count
        
        for panel in self.panels:
            base_x = panel.get_base_x()
            center_y = panel._center_y  # Use cached value
            led_index = 0
            
            for x in range(x_count):
                # First go up from the bottom left
                for y in range(y_count):
                    color = callback(
                        base_x + x, center_y - y - 1, (panel.index, led_index)
                    )
                    if color is not None:
                        panel.strip.setPixelColor(led_index, color)
                    led_index += 1

                if x != x_count - 1:
                    # Then go down again
                    for y in range(y_count):
                        color = callback(
                            base_x + x + 0.5,
                            center_y - (y_count - (y + 0.5)),
                            (panel.index, led_index),
                        )
                        if color is not None:
                            panel.strip.setPixelColor(led_index, color)
                        led_index += 1

    def get_strips(self) -> List["MockPixelStrip"]:
        return [panel.strip for panel in self.panels]

    def get_visualizer_config(self) -> Any:
        return {
            "type": "scale",
            "x_count": self.config.x_count,
            "y_count": self.config.y_count,
            "panel_count": self.config.panel_count,
            "spacing": self.config.spacing,
            "panel_spacing_scales": self.config.panel_spacing_scales,
            "total_width": self.config.total_width,
            "total_height": self.config.total_height,
            "scale_length": self.config.base_length,
            "scale_width": self.config.base_width,
        }
