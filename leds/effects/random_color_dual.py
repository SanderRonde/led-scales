from leds.effects.effect import (
    Effect,
    SpeedWithDirectionParameters,
    ColorMigration,
    ColorInterpolationParameters,
)
from leds.effects.parameters import EnumParameter
from leds.controllers.controller_base import ControllerBase


class RandomColorDualParameters(
    SpeedWithDirectionParameters, ColorInterpolationParameters
):
    def __init__(self):
        super().__init__()
        self.orientation = EnumParameter(
            default="horizontal",
            description="Orientation of the effect",
            enum_values=["horizontal", "vertical", "radial"],
        )


class RandomColorDualEffect(Effect):
    def __init__(self, controller: ControllerBase):
        super().__init__(controller)
        self.PARAMETERS = RandomColorDualParameters()
        self.first_color_migrations = ColorMigration()
        self.second_color_migrations = ColorMigration()

    def run(self, ms: int):
        offset = Effect.time_offset(ms, self.PARAMETERS.speed.get_value(), mod=False)

        first_color = self.first_color_migrations.run_iteration(
            abs(offset), self.PARAMETERS.interpolation.get_value()
        )
        second_color = self.second_color_migrations.run_iteration(
            abs(offset), self.PARAMETERS.interpolation.get_value()
        )

        orientation = self.PARAMETERS.orientation.get_value()
        if orientation in ["horizontal", "vertical"]:
            self.controller.map_scaled_coordinates(
                lambda x, y, index: Effect.interpolate_color(
                    first_color,
                    second_color,
                    x if orientation == "horizontal" else y,
                    self.PARAMETERS.interpolation.get_value(),
                ),
                force_positive=True,
            )
        elif orientation == "radial":
            self.controller.map_scaled_distance(
                lambda distance, index: Effect.interpolate_color(
                    first_color,
                    second_color,
                    distance,
                    self.PARAMETERS.interpolation.get_value(),
                )
            )

        self.controller.show()
