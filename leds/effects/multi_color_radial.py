from leds.controller import LEDController
from leds.effects.effect import Effect
from leds.color import RGBW
from typing import List
import math

class MultiColorRadialEffect(Effect):
    def __init__(self, controller: LEDController, colors: List[RGBW], speed: float):
        super().__init__(controller)
        self._max_distance = controller.get_max_distance()
        self._colors = colors
        self._speed = speed

    def color_at_distance(self, distance: float) -> RGBW:
        index = (distance / self._max_distance * len(self._colors))
        lower_bound = math.floor(index)
        upper_bound = math.ceil(index)
        return self.interpolate_color(self._colors[lower_bound], self._colors[upper_bound], index - lower_bound)

    def run(self, ms: int):
        offset = self.time_offset(ms, self._speed)
        self.controller.map_distance(lambda distance: self.color_at_distance(distance - offset))
        self.controller.show()
