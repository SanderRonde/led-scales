from functools import cache
from typing import TYPE_CHECKING, Type, Any, Tuple, Callable, Union, List, Dict
from abc import ABC, abstractmethod
import math
from leds.color import RGBW
from leds.mock import MockPixelStrip

if TYPE_CHECKING:
    from config import BaseConfig

# Try to import the real library first
try:
    from rpi_ws281x import PixelStrip as RealPixelStrip  # type: ignore

    real_library_available = True
except ImportError:
    real_library_available = False


def get_library(mock: bool) -> Tuple[Type[Any], bool]:
    if not mock and not real_library_available:
        print(
            "Real LED library was forced but rpi_ws281x is not available, falling back to mock library"
        )
        return (MockPixelStrip, False)

    if mock:
        return (MockPixelStrip, False)
    return (RealPixelStrip, True)  # type: ignore


class ControllerBase(ABC):
    def __init__(self, config: "BaseConfig", mock: bool):
        PixelStrip, is_real = get_library(mock)
        self.is_mock = not is_real
        self.PixelStrip: Type[MockPixelStrip] = PixelStrip
        self.config = config

    @staticmethod
    def init_strip(
        PixelStrip: Type[MockPixelStrip], led_count: int, pin: int, channel: int
    ):
        strip = PixelStrip(
            num=led_count,
            pin=pin,
            brightness=255,
            freq_hz=800000,
            dma=10,
            invert=False,
            channel=channel,
        )
        strip.begin()
        return strip

    @cache  # pylint: disable=method-cache-max-size-none
    def get_max_distance(self) -> float:
        highest = 0

        def distance_callback(
            distance: float, index: Tuple[int, int]  # pylint: disable=unused-argument
        ) -> None:
            nonlocal highest
            highest = max(highest, distance)

        self.map_distance(distance_callback)
        return highest

    @cache  # pylint: disable=method-cache-max-size-none
    def get_x_y_limits(self) -> Tuple[float, float, float, float]:
        highest_x = 0
        highest_y = 0
        lowest_x = 0
        lowest_y = 0

        def x_callback(
            x: float,
            y: float,
            index: Tuple[int, int],  # pylint: disable=unused-argument
        ) -> None:
            nonlocal highest_x
            nonlocal highest_y
            nonlocal lowest_x
            nonlocal lowest_y
            highest_x = max(highest_x, x)
            highest_y = max(highest_y, y)
            lowest_x = min(lowest_x, x)
            lowest_y = min(lowest_y, y)

        self.map_coordinates(x_callback)
        return highest_x, highest_y, lowest_x, lowest_y

    @abstractmethod
    def get_coordinates(self, strip_index: int, led_index: int) -> Tuple[float, float]:
        pass

    @abstractmethod
    def map_coordinates(
        self, callback: Callable[[float, float, Tuple[int, int]], Union[RGBW, None]]
    ) -> None:
        pass

    def map_distance(
        self, callback: Callable[[float, Tuple[int, int]], Union[RGBW, None]]
    ) -> None:
        def coordinate_callback(
            x: float, y: float, index: Tuple[int, int]
        ) -> Union[RGBW, None]:
            return callback(math.sqrt(x**2 + y**2), index)

        self.map_coordinates(coordinate_callback)

    def map_scaled_coordinates(
        self,
        callback: Callable[[float, float, Tuple[int, int]], Union[RGBW, None]],
        force_positive: bool,
    ) -> None:
        max_x, max_y, lowest_x, lowest_y = self.get_x_y_limits()
        self.map_coordinates(
            lambda x, y, index: callback(
                (x - lowest_x) / (max_x - lowest_x) if force_positive else x / max_x,
                (y - lowest_y) / (max_y - lowest_y) if force_positive else y / max_y,
                index,
            )
        )

    def map_scaled_distance(
        self, callback: Callable[[float, Tuple[int, int]], Union[RGBW, None]]
    ) -> None:
        max_distance = self.get_max_distance()
        self.map_distance(
            lambda distance, index: callback(distance / max_distance, index)
        )

    def map_angle(
        self, callback: Callable[[float, Tuple[int, int]], Union[RGBW, None]]
    ) -> None:
        """Maps LEDs based on their angle from center (0,0) in radians.
        Angle 0 points right (positive x-axis), increases counter-clockwise."""

        def coordinate_callback(
            x: float, y: float, index: Tuple[int, int]
        ) -> Union[RGBW, None]:
            angle = math.atan2(y, x)
            # Ensure angle is positive (0 to 2π instead of -π to π)
            if angle < 0:
                angle += 2 * math.pi
            return callback(angle, index)

        self.map_coordinates(coordinate_callback)

    @abstractmethod
    def get_strips(self) -> List[MockPixelStrip]:
        pass

    def set_brightness(self, brightness: float) -> None:
        for strip in self.get_strips():
            strip.setBrightness(int(brightness * 255))

    def show(self) -> None:
        for strip in self.get_strips():
            strip.show()

    def set_color(self, color: RGBW) -> None:
        for strip in self.get_strips():
            for i in range(strip.numPixels()):
                strip.setPixelColor(i, color)

    def json(self) -> List[List[Dict[str, Union[int, float]]]]:
        pixels: List[List[Dict[str, Union[int, float]]]] = []
        for strip_index, strip in enumerate(self.get_strips()):
            strip_pixels: List[Dict[str, Union[int, float]]] = []
            for i in range(strip.numPixels()):
                pixel = strip.getPixelColorRGBW(i)
                pixel_data: Dict[str, Union[int, float]] = {
                    "r": pixel.r,
                    "g": pixel.g,
                    "b": pixel.b,
                    "w": pixel.w,
                    "brightness": strip.getBrightness(),
                }
                if self.config.debug_positions:
                    x, y = self.get_coordinates(strip_index, i)
                    pixel_data["x"] = x
                    pixel_data["y"] = y
                strip_pixels.append(pixel_data)
            pixels.append(strip_pixels)
        return pixels

    @abstractmethod
    def get_visualizer_config(self) -> Any:
        pass
