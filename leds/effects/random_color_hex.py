from leds.effects.effect import Effect, SpeedParameters, ColorInterpolationParameters, ColorMigration
from leds.controllers.hex_controller import HexPanelLEDController


class RandomColorHexParameters(SpeedParameters, ColorInterpolationParameters):
    pass


class RandomColorHexEffect(Effect):
    def __init__(self, controller: HexPanelLEDController):
        super().__init__(controller)
        self.PARAMETERS = RandomColorHexParameters()
        self.controller = controller
        self.color_migrations = [ColorMigration()
                                 for _ in range(len(self.controller.panels))]

    def run(self, ms: int):
        offset = Effect.time_offset(
            ms, self.PARAMETERS.speed.get_value(), mod=False)

        for i, panel in enumerate(self.controller.panels):
            color = self.color_migrations[i].run_iteration(
                abs(offset), self.PARAMETERS.interpolation.get_value())
            panel.set_color(color)

        self.controller.show()
