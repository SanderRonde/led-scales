import math
from leds.controllers.controller_base import ControllerBase
from leds.effects.parameters import ColorListParameter
from leds.effects.effect import Effect, SpeedWithDirectionParameters, ColorInterpolationParameters
from leds.color import RGBW, Color


class MultiColorRadialParameters(SpeedWithDirectionParameters, ColorInterpolationParameters):
    def __init__(self):
        super().__init__()
        self.colors = ColorListParameter(
            default=[Color(255, 0, 0), Color(0, 255, 0), Color(0, 0, 255)],
            description="List of colors to use in the radial effect",
        )


class MultiColorRadialEffect(Effect):
    def __init__(self, controller: ControllerBase):
        super().__init__(controller)
        self.PARAMETERS = MultiColorRadialParameters()

    def color_at_distance(self, distance: float) -> RGBW:
        distance = distance % 1
        if distance < 0:
            distance = 1 + distance

        colors = self.PARAMETERS.colors.get_value()
        index = (distance * (len(colors)))
        lower_bound = math.floor(index)
        upper_bound = 0 if index == len(
            colors) else math.ceil(index) % len(colors)
        return Effect.interpolate_color(colors[lower_bound], colors[upper_bound], (index - lower_bound) % 1, self.PARAMETERS.interpolation.get_value())

    def run(self, ms: int):
        offset = Effect.time_offset(
            ms, self.PARAMETERS.speed.get_value(), self.PARAMETERS.direction.get_value())
        self.controller.map_scaled_distance(
            lambda distance, index: self.color_at_distance(distance + offset))
        self.controller.show()
