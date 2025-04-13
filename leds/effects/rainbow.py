from leds.effects.effect import Effect


class RainbowEffect(Effect):
    PARAMETERS = []

    def run(self, ms: int):
        offset = (ms % 5000) / 5000
        for i in range(len(self.controller.panels)):
            for j in range(256):
                for k in range(self.controller.panels[i].strip.numPixels()):
                    pixel_index = int(((k + (offset * self.controller.panels[i].strip.numPixels(
                    ))) * 256 // self.controller.panels[i].strip.numPixels()) + j)
                    self.controller.panels[i].strip.setPixelColor(
                        k, self.rainbow(pixel_index & 255))
            self.controller.panels[i].strip.show()
