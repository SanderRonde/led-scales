from typing import Type, Any, List, Tuple, Dict, Callable, Union
from leds.color import RGBW
from leds.mock import MockPixelStrip
from config import ScaleConfig
import math
# Try to import the real library first
try:
    from rpi_ws281x import PixelStrip as RealPixelStrip  # type: ignore
    real_library_available = True
except ImportError:
    real_library_available = False


def get_library(mock: bool) -> Tuple[Type[Any], bool]:
    if not mock and not real_library_available:
        print("Real LED library was forced but rpi_ws281x is not available, falling back to mock library")
        return (MockPixelStrip, False)

    if mock:
        return (MockPixelStrip, False)
    else:
        return (RealPixelStrip, True)  # type: ignore


class LEDPanel:
    def __init__(self, PixelStrip: Type[MockPixelStrip], config: ScaleConfig, index: int, brightness: int = 255, **kwargs: Any):
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


class LEDController:
    def __init__(self, config: ScaleConfig, mock: bool, **kwargs: Any):
        PixelStrip, is_mock = get_library(mock)
        self.is_mock = is_mock
        self.config = config
        self.panels: List[LEDPanel] = [
            LEDPanel(PixelStrip, config, index, **kwargs) for index in range(config.panel_count)]
        
    def get_max_distance(self) -> float:
        highest = 0

        def distance_callback(distance: float) -> None:
            nonlocal highest
            if distance > highest:
                highest = distance

        self.map_distance(distance_callback)
        return highest

    def map_coordinates(self, callback: Callable[[float, float], Union[RGBW, None]]) -> None:
        for panel in self.panels:
            base_x = panel.get_base_x()
            center_y = self.config.y_count - 1
            led_index = 0
            y = 0
            for _ in range(self.config.y_count):
                for x in range(self.config.x_count - 1):
                    color = callback(base_x + x + 0.5, center_y - y)
                    if color is not None:
                        panel.strip.setPixelColor(led_index, color)
                    led_index += 1
                y += 1
                for x in range(self.config.x_count):
                    color = callback(base_x + x, center_y - y + 0.5)
                    if color is not None:
                        panel.strip.setPixelColor(led_index, color)
                    led_index += 1
                y += 1

    def map_distance(self, callback: Callable[[float], Union[RGBW, None]]) -> None:
        def coordinate_callback(x: float, y: float) -> Union[RGBW, None]:
            return callback(math.sqrt(x**2 + y**2))

        self.map_coordinates(coordinate_callback)

    def map_angle(self, callback: Callable[[float], Union[RGBW, None]]) -> None:
        """Maps LEDs based on their angle from center (0,0) in radians.
        Angle 0 points right (positive x-axis), increases counter-clockwise."""
        def coordinate_callback(x: float, y: float) -> Union[RGBW, None]:
            angle = math.atan2(y, x)
            # Ensure angle is positive (0 to 2π instead of -π to π)
            if angle < 0:
                angle += 2 * math.pi
            return callback(angle)

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
