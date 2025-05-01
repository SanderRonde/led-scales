from typing import Type, Any, Tuple, Callable, Union
from leds.color import RGBW
from leds.mock import MockPixelStrip
from abc import ABC, abstractmethod
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


class ControllerBase(ABC):
    def __init__(self, mock: bool):
        PixelStrip, is_real = get_library(mock)
        self.is_mock = not is_real
        self.PixelStrip: Type[MockPixelStrip] = PixelStrip

    @abstractmethod
    def get_pixel_count(self) -> int:
        pass

    @abstractmethod
    def map_distance(self, callback: Callable[[float, Tuple[int, int]], Union[RGBW, None]]) -> None:
        pass

    @abstractmethod
    def map_scaled_distance(self, callback: Callable[[float, Tuple[int, int]], Union[RGBW, None]]) -> None:
        pass

    @abstractmethod
    def map_angle(self, callback: Callable[[float, Tuple[int, int]], Union[RGBW, None]]) -> None:
        """Maps LEDs based on their angle from center (0,0) in radians.
        Angle 0 points right (positive x-axis), increases counter-clockwise."""
        pass

    @abstractmethod
    def show(self) -> None:
        pass

    @abstractmethod
    def json(self) -> Any:
        pass

    @abstractmethod
    def get_config(self) -> Any:
        pass
