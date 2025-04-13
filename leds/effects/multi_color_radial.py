from leds.effects.parameters import ColorListParameter, EnumParameter, FloatParameter
from leds.effects.effect import Effect
from leds.color import RGBW, Color
import math


class MultiColorRadialParameters:
    def __init__(self):
        self.colors = ColorListParameter(
            default=[Color(255, 0, 0), Color(0, 255, 0), Color(0, 0, 255)],
            description="List of colors to use in the radial effect",
        )
        self.speed = FloatParameter(
            default=0.6,
            description="Speed of the effect (0-1)",
        )
        self.direction = EnumParameter(
            default="out",
            description="Direction of the effect",
            enum_values=["in", "out"]
        )


class MultiColorRadialEffect(Effect):
    PARAMETERS = MultiColorRadialParameters()

    def color_at_distance(self, distance: float) -> RGBW:
        distance = distance % 1
        if distance < 0:
            distance = 1 + distance

        colors = self.PARAMETERS.colors.get_value()
        index = (distance * (len(colors)))
        lower_bound = math.floor(index)
        upper_bound = 0 if index == len(
            colors) else math.ceil(index) % len(colors)
        return self.interpolate_color(colors[lower_bound], colors[upper_bound], (index - lower_bound) % 1)

    def run(self, ms: int):
        offset = self.time_offset(
            ms, self.PARAMETERS.speed.get_value(), self.PARAMETERS.direction.get_value())
        self.controller.map_scaled_distance(
            lambda distance, index: self.color_at_distance(distance + offset))
        self.controller.show()
