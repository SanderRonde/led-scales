from leds.color import RGBW, Color
from leds.effects.effect import Effect


class RainbowEffect(Effect):
    def wheel(self, pos: int) -> RGBW:
        """Generate rainbow colors across 0-255 positions."""
        if pos < 85:
            return Color(pos * 3, 255 - pos * 3, 0)
        elif pos < 170:
            pos -= 85
            return Color(255 - pos * 3, 0, pos * 3)
        else:
            pos -= 170
            return Color(0, pos * 3, 255 - pos * 3)

    def run(self, ms: int):
        offset = (ms % 5000) / 5000
        for i in range(len(self.controller.panels)):
            for j in range(256):
                for k in range(self.controller.panels[i].strip.numPixels()):
                    pixel_index = int(((k + (offset * self.controller.panels[i].strip.numPixels(
                    ))) * 256 // self.controller.panels[i].strip.numPixels()) + j)
                    self.controller.panels[i].strip.setPixelColor(
                        k, self.wheel(pixel_index & 255))
            self.controller.panels[i].strip.show()
