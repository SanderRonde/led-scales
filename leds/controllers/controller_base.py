from typing import Type, Any, Tuple, Callable, Union
from abc import ABC, abstractmethod
import math
from leds.color import RGBW
from leds.mock import MockPixelStrip
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
    return (RealPixelStrip, True)  # type: ignore


class ControllerBase(ABC):
    def __init__(self, mock: bool):
        PixelStrip, is_real = get_library(mock)
        self.is_mock = not is_real
        self.PixelStrip: Type[MockPixelStrip] = PixelStrip

    @staticmethod
    def init_strip(PixelStrip: Type[MockPixelStrip], led_count: int, pin: int, channel: int):
        return PixelStrip(
            num=led_count,
            pin=pin,
            brightness=255,
            freq_hz=800000,
            dma=10,
            invert=False,
            channel=channel
        )

    def get_max_distance(self) -> float:
        highest = 0

        def distance_callback(distance: float, index: Tuple[int, int]) -> None:  # pylint: disable=unused-argument
            nonlocal highest
            highest = max(highest, distance)

        self.map_distance(distance_callback)
        return highest

    @abstractmethod
    def map_coordinates(self, callback: Callable[[float, float, Tuple[int, int]], Union[RGBW, None]]) -> None:
        pass

    def map_distance(self, callback: Callable[[float, Tuple[int, int]], Union[RGBW, None]]) -> None:
        def coordinate_callback(x: float, y: float, index: Tuple[int, int]) -> Union[RGBW, None]:
            return callback(math.sqrt(x**2 + y**2), index)

        self.map_coordinates(coordinate_callback)

    def map_scaled_distance(self, callback: Callable[[float, Tuple[int, int]], Union[RGBW, None]]) -> None:
        max_distance = self.get_max_distance()
        self.map_distance(lambda distance, index: callback(
            distance / max_distance, index))

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

    @abstractmethod
    def show(self) -> None:
        pass

    @abstractmethod
    def json(self) -> Any:
        pass

    @abstractmethod
    def get_visualizer_config(self) -> Any:
        pass
