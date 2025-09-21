from leds.effects.effect import (
    Effect,
    SpeedWithDirectionParameters,
    ColorMigration,
    ColorInterpolationParameters,
)
from leds.controllers.controller_base import ControllerBase


class RandomColorSingleParameters(
    SpeedWithDirectionParameters, ColorInterpolationParameters
):
    pass


class RandomColorSingleEffect(Effect):
    def __init__(self, controller: ControllerBase):
        super().__init__(controller)
        self.PARAMETERS = RandomColorSingleParameters()
        self.color_migrations = ColorMigration()

    def run(self, ms: int):
        offset = Effect.time_offset(ms, self.PARAMETERS.speed.get_value(), mod=False)

        color = self.color_migrations.run_iteration(
            abs(offset), self.PARAMETERS.interpolation.get_value()
        )
        self.controller.set_color(color)

        self.controller.show()
