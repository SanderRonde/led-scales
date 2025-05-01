from leds.effects.parameters import FloatParameter, EnumParameter
from leds.controllers.controller_base import ControllerBase
from leds.effects.effect import Effect


class RainbowRadialParameters:
    def __init__(self):
        self.speed = FloatParameter(
            default=0.6,
            description="Speed of the effect (0-1)",
        )
        self.direction = EnumParameter(
            default="out",
            description="Direction of the effect",
            enum_values=["in", "out"]
        )


class RainbowRadialEffect(Effect):
    PARAMETERS = RainbowRadialParameters()

    def __init__(self, controller: ControllerBase):
        super().__init__(controller)

    def run(self, ms: int):
        offset = self.time_offset(
            ms, self.PARAMETERS.speed.get_value(), self.PARAMETERS.direction.get_value())
        self.controller.map_scaled_distance(
            lambda distance, index: self.rainbow(distance + offset))
        self.controller.show()
