from leds.effects.effect import Effect
from leds.effects.parameters import FloatParameter, EnumParameter
from leds.controllers.scale_panel_controller import ScalePanelLEDController


class RainbowParameters:
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


class RainbowEffect(Effect):
    PARAMETERS = RainbowParameters()

    def __init__(self, controller: ScalePanelLEDController):
        super().__init__(controller)
        self.controller = controller

    def run(self, ms: int):
        offset = self.time_offset(
            ms, self.PARAMETERS.speed.get_value(), self.PARAMETERS.direction.get_value())
        total_pixels = self.controller.config.get_led_count()
        for i in range(len(self.controller.panels)):
            for j in range(self.controller.panels[i].strip.numPixels()):
                pixel_index = i * \
                    self.controller.panels[i].strip.numPixels() + j
                self.controller.panels[i].strip.setPixelColor(
                    j, self.rainbow(pixel_index / total_pixels + offset))
        self.controller.show()
