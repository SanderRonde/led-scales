from typing import Type, Any, List, Tuple, Dict, Callable, Union, TYPE_CHECKING
from leds.color import RGBW
from leds.mock import MockPixelStrip
from leds.controllers.controller_base import ControllerBase
import math

if TYPE_CHECKING:
    from config import ScaleConfig


class LEDPanel:
    def __init__(self, PixelStrip: Type[MockPixelStrip], config: "ScaleConfig", index: int, brightness: int = 255, **kwargs: Any):
        self.num_pixels = config.scale_per_panel_count
        self.index = index
        self.config = config
        self._pixels: List[RGBW] = [RGBW(0, 0, 0, 0)
                                    for _ in range(self.num_pixels)]
        self._buffer: List[RGBW] = [RGBW(0, 0, 0, 0)
                                    for _ in range(self.num_pixels)]
        self._brightness = brightness
        pin, channel = config.pins[index]
        self.strip = PixelStrip(
            num=self.num_pixels,
            pin=pin,
            brightness=255,
            freq_hz=800000,
            dma=10,
            invert=False,
            channel=channel
        )

    @property
    def distance_from_center(self) -> int:
        center_panel = int((self.config.panel_count - 1) / 2)
        if self.index == center_panel:
            return 0
        else:
            return self.index - center_panel

    def get_base_x(self) -> float:
        distance_from_center = self.distance_from_center
        scale_offset = (distance_from_center - 0.5) * self.config.x_count + (
            self.config.panel_spacing_scales * abs(distance_from_center)
        ) + 0.5
        return scale_offset


class ScalePanelLEDController(ControllerBase):
    def __init__(self, config: "ScaleConfig", mock: bool, **kwargs: Any):
        super().__init__(mock)
        self.config = config
        self.panels: List[LEDPanel] = [
            LEDPanel(self.PixelStrip, config, index, **kwargs) for index in range(config.panel_count)]
        self._max_distance = self._get_max_distance()

    def _get_max_distance(self) -> float:
        highest = 0

        def distance_callback(distance: float, index: Tuple[int, int]) -> None:
            nonlocal highest
            if distance > highest:
                highest = distance

        self.map_distance(distance_callback)
        return highest

    def map_coordinates(self, callback: Callable[[float, float, Tuple[int, int]], Union[RGBW, None]]) -> None:
        for panel in self.panels:
            base_x = panel.get_base_x()
            center_y = self.config.y_count / 2
            led_index = 0
            y = 0
            for x in range(self.config.x_count):
                # First go up from the bottom left
                for y in range(self.config.y_count):
                    color = callback(base_x + x, center_y -
                                     y - 1, (panel.index, led_index))
                    if color is not None:
                        panel.strip.setPixelColor(led_index, color)
                    led_index += 1
                y += 1

                if x != self.config.x_count - 1:
                    # Then go down again
                    for y in range(self.config.y_count):
                        color = callback(
                            base_x + x + 0.5, center_y - (self.config.y_count - (y + 0.5)), (panel.index, led_index))
                        if color is not None:
                            panel.strip.setPixelColor(led_index, color)
                        led_index += 1
                    y += 1

    def map_distance(self, callback: Callable[[float, Tuple[int, int]], Union[RGBW, None]]) -> None:
        def coordinate_callback(x: float, y: float, index: Tuple[int, int]) -> Union[RGBW, None]:
            return callback(math.sqrt(x**2 + y**2), index)

        self.map_coordinates(coordinate_callback)

    def map_scaled_distance(self, callback: Callable[[float, Tuple[int, int]], Union[RGBW, None]]) -> None:
        self.map_distance(lambda distance, index: callback(
            distance / self._max_distance, index))

    def map_angle(self, callback: Callable[[float, Tuple[int, int]], Union[RGBW, None]]) -> None:
        """Maps LEDs based on their angle from center (0,0) in radians.
        Angle 0 points right (positive x-axis), increases counter-clockwise."""
        def coordinate_callback(x: float, y: float, index: Tuple[int, int]) -> Union[RGBW, None]:
            angle = math.atan2(y, x)
            # Ensure angle is positive (0 to 2π instead of -π to π)
            if angle < 0:
                angle += 2 * math.pi
            return callback(angle, index)

        self.map_coordinates(coordinate_callback)

    def show(self):
        for panel in self.panels:
            panel.strip.show()

    def json(self):
        pixels: List[List[Dict[str, int]]] = []
        for panel in self.panels:
            strip_pixels: List[Dict[str, int]] = []
            for pixel in panel.strip.getPixels():
                strip_pixels.append(
                    {'r': pixel.r, 'g': pixel.g, 'b': pixel.b, 'w': pixel.w})
            pixels.append(strip_pixels)
        return pixels

    def get_config(self) -> Any:
        return {
            'x_count': self.config.x_count,
            'y_count': self.config.y_count,
            'panel_count': self.config.panel_count,
            'spacing': self.config.spacing,
            'panel_spacing_scales': self.config.panel_spacing_scales,
            'total_width': self.config.total_width,
            'total_height': self.config.total_height,
            'scale_length': self.config.base_length,
            'scale_width': self.config.base_width,
        }

    def get_pixel_count(self) -> int:
        return self.config.scale_count
