"""Base class for LED effects"""
import random
from abc import ABC, abstractmethod
from typing import Any, Literal
from leds.controllers.controller_base import ControllerBase
from leds.color import RGBW
from leds.effects.parameters import FloatParameter, EnumParameter


class SpeedParameters(ABC):
    def __init__(self):
        super().__init__()
        self.speed = FloatParameter(
            default=0.6,
            description="Speed of the effect (0-1)",
        )


class ColorInterpolationParameters(ABC):
    def __init__(self):
        super().__init__()
        self.interpolation = EnumParameter(
            default="linear",
            description="Color interpolation of the effect",
            enum_values=["linear", "hsv"]
        )
        


class SpeedWithDirectionParameters(SpeedParameters, ABC):
    def __init__(self):
        super().__init__()
        self.direction = EnumParameter(
            default="out",
            description="Direction of the effect",
            enum_values=["in", "out"]
        )


class ColorMigration:
    def __init__(self):
        self.to_color = RGBW.from_hsv(random.uniform(0, 360), 1, 1)
        self.re_init(0.0)

    def re_init(self, time_offset: float):
        self.from_color = self.to_color
        self.to_color = RGBW.from_hsv(random.uniform(0, 360), 1, 1)
        self.random_offset = random.uniform(0, 0.5)
        self.base_offset = time_offset

    def run_iteration(self, value: float, interpolation: Literal["linear", "hsv"]) -> RGBW:
        time_offset_base = self.base_offset + self.random_offset
        relative_time_offset = value - time_offset_base
        color = Effect.interpolate_color(
            self.from_color, self.to_color, relative_time_offset, interpolation)
        if relative_time_offset >= 1:
            self.re_init(value)
        return color


class Effect(ABC):
    """Base class for LED effects"""
    PARAMETERS: Any

    def __init__(self, controller: ControllerBase):
        self.controller = controller

    @abstractmethod
    def run(self, ms: int):
        pass

    @staticmethod
    def __interpolate_color_hsv(from_color: RGBW, to_color: RGBW, value: float) -> RGBW:
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

    @staticmethod
    def __interpolate_color_linear(from_color: RGBW, to_color: RGBW, value: float) -> RGBW:
        """
        Interpolate between two colors using linear RGB interpolation for pastel transitions
        Args:
            from_color (RGBW): Starting color
            to_color (RGBW): Ending color
            value (float): Interpolation value between 0 and 1
        Returns:
            RGBW: Interpolated color
        """
        # Linearly interpolate each RGB component
        r = int(from_color.r + (to_color.r - from_color.r) * value)
        g = int(from_color.g + (to_color.g - from_color.g) * value)
        b = int(from_color.b + (to_color.b - from_color.b) * value)
        w = int(from_color.w + (to_color.w - from_color.w) * value)

        # Ensure values are within valid range
        r = max(0, min(255, r))
        g = max(0, min(255, g))
        b = max(0, min(255, b))
        w = max(0, min(255, w))

        return RGBW(r, g, b, w)

    @staticmethod
    def interpolate_color(from_color: RGBW, to_color: RGBW, value: float, interpolation: Literal["linear", "hsv"]) -> RGBW:
        if interpolation == "hsv":
            return Effect.__interpolate_color_hsv(from_color, to_color, value)
        return Effect.__interpolate_color_linear(from_color, to_color, value)

    @staticmethod
    def time_offset(ms: int, speed: float, direction: str = 'in', mod: bool = True) -> float:
        min_sensitivity = 100  # Repeat every 100ms
        max_sensitivity = 1000 * 60 * 5  # Repeat every 5 minutes
        # Use exponential scaling to make sensitivity feel more natural
        actual_sensitivity = min_sensitivity * \
            pow(max_sensitivity/min_sensitivity, 1 - speed)
        if mod:
            offset = (ms % actual_sensitivity) / actual_sensitivity
        else:
            offset = ms / actual_sensitivity
        if direction == 'out':
            return -offset
        return offset

    @staticmethod
    def rainbow(value: float) -> RGBW:
        value = value % 1
        # Convert directly to HSV for smoother rainbow transitions
        return RGBW.from_hsv(value * 360, 1.0, 1.0)
