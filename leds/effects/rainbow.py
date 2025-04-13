from leds.led_library import Color, RGBW
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
        for i in range(len(self.strips)):
            for j in range(256):
                for k in range(self.strips[i].numPixels()):
                    pixel_index = int(((k + (offset * self.strips[i].numPixels())) * 256 // self.strips[i].numPixels()) + j)
                    self.strips[i].setPixelColor(
                        k, self.wheel(pixel_index & 255))
            self.strips[i].show()
