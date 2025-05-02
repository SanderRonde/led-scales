from leds.effects.effect import Effect, SpeedParameters
from leds.controllers.scale_panel_controller import ScalePanelLEDController


class RainbowParameters(SpeedParameters):
    pass


class RainbowEffect(Effect):
    def __init__(self, controller: ScalePanelLEDController):
        super().__init__(controller)
        self.controller = controller
        self.PARAMETERS = RainbowParameters()

    def run(self, ms: int):
        offset = Effect.time_offset(
            ms, self.PARAMETERS.speed.get_value(), self.PARAMETERS.direction.get_value())
        total_pixels = self.controller.config.get_led_count()
        for i, panel in enumerate(self.controller.panels):
            for j in range(panel.strip.numPixels()):
                pixel_index = i * \
                    panel.strip.numPixels() + j
                panel.strip.setPixelColor(
                    j, Effect.rainbow(pixel_index / total_pixels + offset))
        self.controller.show()
