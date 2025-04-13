from typing import Type, Any, List, Tuple, Dict, Callable
from leds.color import RGBW
from leds.mock import MockPixelStrip
from config import ScaleConfig

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
        )
        return scale_offset


class LEDController:
    def __init__(self, config: ScaleConfig, mock: bool, **kwargs: Any):
        PixelStrip, is_mock = get_library(mock)
        self.is_mock = is_mock
        self.config = config
        self.panels: List[LEDPanel] = [
            LEDPanel(PixelStrip, config, index, **kwargs) for index in range(config.panel_count)]

    def map_coordinates(self, callback: Callable[[float, float], RGBW]) -> None:
        for panel in self.panels:
            base_x = panel.get_base_x()
            for i in range(self.config.y_count):
                pass
            for pixel in panel.strip.getPixels():
                pixel.r = callback(pixel.r)
                pixel.g = callback(pixel.g)
                pixel.b = callback(pixel.b)
                pixel.w = callback(pixel.w)

    def map_distance(self, callback: Callable[[float], RGBW]) -> None:
        for panel in self.panels:
            base_x = panel.get_base_x()
            for i in range(self.config.y_count):
                pass
            for pixel in panel.strip.getPixels():
                pixel.r = callback(pixel.r)
                pixel.g = callback(pixel.g)
                pixel.b = callback(pixel.b)
                pixel.w = callback(pixel.w)

    def json(self):
        pixels: List[List[Dict[str, int]]] = []
        for panel in self.panels:
            strip_pixels: List[Dict[str, int]] = []
            for pixel in panel.strip.getPixels():
                strip_pixels.append(
                    {'r': pixel.r, 'g': pixel.g, 'b': pixel.b, 'w': pixel.w})
            pixels.append(strip_pixels)
        return pixels
