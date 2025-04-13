from leds.controller import LEDController
from leds.effects.effect import Effect

class RainbowRadialEffect(Effect):
    def __init__(self, controller: LEDController, speed: float):
        super().__init__(controller)
        self._max_distance = controller.get_max_distance()
        self._speed = speed

    def run(self, ms: int):
        offset = self.time_offset(ms, self._speed)
        self.controller.map_distance(lambda distance: self.rainbow(distance / self._max_distance - offset))
        self.controller.show()
