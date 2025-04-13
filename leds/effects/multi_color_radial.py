from leds.controller import LEDController
from typing import List, Literal
from leds.effects.effect import Effect
from leds.color import RGBW
import math
from leds.effects.parameters import Parameter, ParameterType


class MultiColorRadialEffect(Effect):
    # Define parameters for the effect
    PARAMETERS = [
        Parameter(
            name="colors",
            type=ParameterType.COLOR_LIST,
            description="List of colors to use in the radial effect",
        ),
        Parameter(
            name="speed",
            type=ParameterType.FLOAT,
            description="Speed of the effect (0-1)",
        ),
        Parameter(
            name="direction",
            type=ParameterType.ENUM,
            description="Direction of the effect",
            enum_values=["in", "out"]
        )
    ]

    def __init__(self, controller: LEDController, colors: List[RGBW], speed: float, direction: Literal['in', 'out']):
        super().__init__(controller)
        self._colors = colors
        self._speed = speed
        self._direction: Literal['in', 'out'] = direction

    def color_at_distance(self, distance: float) -> RGBW:
        distance = distance % 1
        if distance < 0:
            distance = 1 + distance

        index = (distance * (len(self._colors)))
        lower_bound = math.floor(index)
        upper_bound = 0 if index == len(
            self._colors) else math.ceil(index) % len(self._colors)
        return self.interpolate_color(self._colors[lower_bound], self._colors[upper_bound], (index - lower_bound) % 1)

    def run(self, ms: int):
        offset = self.time_offset(ms, self._speed, self._direction)
        self.controller.map_scaled_distance(
            lambda distance, index: self.color_at_distance(distance + offset))
        self.controller.show()
