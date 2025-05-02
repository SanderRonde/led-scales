from leds.effects.effect import Effect, SpeedParameters
from leds.controllers.controller_base import ControllerBase


class RainbowRadialParameters(SpeedParameters):
    pass


class RainbowRadialEffect(Effect):
    def __init__(self, controller: ControllerBase):
        super().__init__(controller)
        self.PARAMETERS = RainbowRadialParameters()

    def run(self, ms: int):
        offset = Effect.time_offset(
            ms, self.PARAMETERS.speed.get_value(), self.PARAMETERS.direction.get_value())
        self.controller.map_scaled_distance(
            lambda distance, index: Effect.rainbow(distance + offset))
        self.controller.show()
