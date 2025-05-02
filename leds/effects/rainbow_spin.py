from leds.effects.effect import Effect, SpeedWithDirectionParameters
from leds.controllers.hex_controller import HexPanelLEDController


class RainbowSpinParameters(SpeedWithDirectionParameters):
    pass


class RainbowSpinEffect(Effect):
    def __init__(self, controller: HexPanelLEDController):
        super().__init__(controller)
        self.controller = controller
        self.PARAMETERS = RainbowSpinParameters()

    def run(self, ms: int):
        offset = Effect.time_offset(
            ms, self.PARAMETERS.speed.get_value(), self.PARAMETERS.direction.get_value())

        for panel in self.controller.panels:
            for led_index in panel.panel_config.ordered_leds:
                angle = panel.get_angle_at_index(led_index)
                panel.strip.setPixelColor(
                    led_index, Effect.rainbow((angle / 360) + offset))
        self.controller.show()
