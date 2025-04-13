from leds.controller import LEDController
from leds.effects.effect import Effect
from typing import Literal
class RainbowRadialEffect(Effect):
    def __init__(self, controller: LEDController, speed: float, direction: Literal['in', 'out']):
        super().__init__(controller)
        self._speed = speed
        self._direction: Literal['in', 'out'] = direction

    def run(self, ms: int):
        offset = self.time_offset(ms, self._speed, self._direction)
        self.controller.map_scaled_distance(lambda distance, index: self.rainbow(distance + offset))
        self.controller.show()
