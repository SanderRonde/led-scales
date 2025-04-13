from leds.controller import LEDController
from leds.color import RGBW
from abc import ABC, abstractmethod
from typing import Literal


class Effect(ABC):
    def __init__(self, controller: LEDController):
        self.controller = controller

    @abstractmethod
    def run(self, ms: int):
        pass

    def interpolate_color(self, from_color: RGBW, to_color: RGBW, value: float) -> RGBW:
        """Interpolate between two colors using HSV color space for smoother transitions
        Args:
            from_color (RGBW): Starting color
            to_color (RGBW): Ending color
            value (float): Interpolation value between 0 and 1
        Returns:
            RGBW: Interpolated color
        """
        # Get HSV values
        h1, s1, v1 = from_color.hsv
        h2, s2, v2 = to_color.hsv

        # Special case for hue interpolation to handle the circular nature of hue
        # Find the shortest path around the color wheel
        if abs(h2 - h1) > 180:
            if h1 < h2:
                h1 += 360
            else:
                h2 += 360

        # Interpolate HSV values
        h = (h1 + (h2 - h1) * value) % 360
        s = s1 + (s2 - s1) * value
        v = v1 + (v2 - v1) * value

        # Interpolate white separately in RGB space since it's not part of HSV
        w = int(from_color.w + (to_color.w - from_color.w) * value)

        # Convert back to RGBW
        return RGBW.from_hsv(h, s, v, w)

    def time_offset(self, ms: int, speed: float, direction: Literal['in', 'out']) -> float:
        min_sensitivity = 100  # Repeat every 100ms
        max_sensitivity = 1000 * 60 * 5  # Repeat every 5 minutes
        # Use exponential scaling to make sensitivity feel more natural
        actual_sensitivity = min_sensitivity * \
            pow(max_sensitivity/min_sensitivity, 1 - speed)
        offset = (ms % actual_sensitivity) / actual_sensitivity
        if direction == 'out':
            return -offset
        return offset

    def rainbow(self, value: float) -> RGBW:
        value = value % 1
        # Convert directly to HSV for smoother rainbow transitions
        return RGBW.from_hsv(value * 360, 1.0, 1.0)
