from leds.controller import LEDController
from leds.effects.rainbow import RainbowEffect

class RainbowRadialEffect(RainbowEffect):
    def __init__(self, controller: LEDController):
        super().__init__(controller)
        self._max_distance = controller.get_max_distance()

    def run(self, ms: int):
        offset = (ms % 5000) / 5000
        self.controller.map_distance(lambda distance: self.wheel(int(((distance / self._max_distance) - offset) * 255) % 255))
        self.controller.show()
