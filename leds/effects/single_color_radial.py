from leds.controller import LEDController
from leds.effects.effect import Effect
from leds.color import RGBW, Color
from typing import Literal
import math


class SingleColorRadialEffect(Effect):
    def __init__(self, controller: LEDController, color: RGBW, speed: float, lower_bound: float, direction: Literal['in', 'out']):
        super().__init__(controller)
        self._speed = speed
        self._color = color
        self._lower_bound = lower_bound
        self._direction: Literal['in', 'out'] = direction

    def color_at_distance(self, distance: float) -> RGBW:
        diff = 1 - self._lower_bound
        abs_distance = (distance if distance < 0.5 else 1 - distance) * 2
        final_brightness = self._lower_bound + diff * abs_distance
        return Color(
            math.floor(self._color.r * final_brightness),
            math.floor(self._color.g * final_brightness),
            math.floor(self._color.b * final_brightness)
        )

    def run(self, ms: int):
        offset = self.time_offset(ms, self._speed, self._direction)
        self.controller.map_scaled_distance(lambda distance, index: self.color_at_distance(
            ((distance) + offset) % 1))
        self.controller.show()
