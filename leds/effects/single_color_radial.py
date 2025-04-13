from leds.effects.parameters import ColorParameter, FloatParameter, EnumParameter
from leds.controller import LEDController
from leds.effects.effect import Effect
from leds.color import RGBW, Color
import math


class SingleColorRadialParameters:
    def __init__(self):
        self.color = ColorParameter(
            default=Color(255, 0, 0),
            description="Color of the effect",
        )
        self.speed = FloatParameter(
            default=0.6,
            description="Speed of the effect (0-1)",
        )
        self.lower_bound = FloatParameter(
            default=0.5,
            description="Lower bound of the effect (0-1)",
        )
        self.direction = EnumParameter(
            default="out",
            description="Direction of the effect",
            enum_values=["in", "out"]
        )


class SingleColorRadialEffect(Effect):
    PARAMETERS = SingleColorRadialParameters()

    def __init__(self, controller: LEDController):
        super().__init__(controller)

    def color_at_distance(self, distance: float) -> RGBW:
        lower_bound = self.PARAMETERS.lower_bound.get_value()
        color = self.PARAMETERS.color.get_value()
        diff = 1 - lower_bound
        abs_distance = (distance if distance < 0.5 else 1 - distance) * 2
        final_brightness = lower_bound + diff * abs_distance
        return Color(
            math.floor(color.r * final_brightness),
            math.floor(color.g * final_brightness),
            math.floor(color.b * final_brightness)
        )

    def run(self, ms: int):
        offset = self.time_offset(
            ms, self.PARAMETERS.speed.get_value(), self.PARAMETERS.direction.get_value())
        self.controller.map_scaled_distance(lambda distance, index: self.color_at_distance(
            ((distance) + offset) % 1))
        self.controller.show()
