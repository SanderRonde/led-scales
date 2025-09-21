from typing import List, Any
from leds.color import RGBW


class MockPixelStrip:
    def __init__(
        self, num: int, brightness: int = 255, **kwargs: Any
    ):  # pylint: disable=unused-argument
        self.num_pixels = num
        self._pixels: List[RGBW] = [RGBW(0, 0, 0, 0) for _ in range(num)]
        self._buffer: List[RGBW] = [RGBW(0, 0, 0, 0) for _ in range(num)]
        self._brightness = brightness

    def __getitem__(self, pos: int) -> RGBW:
        return self._pixels[pos]

    def __setitem__(self, pos: int, value: RGBW):
        self._buffer[pos] = value

    def __len__(self):
        return self.num_pixels

    def _cleanup(self):
        pass

    def setGamma(self, gamma: float):
        pass

    def begin(self):
        pass

    def show(self):
        # Swap buffer with pixels
        self._pixels = self._buffer.copy()

    def setPixelColor(self, n: int, color: RGBW):
        self._buffer[n] = color

    def setPixelColorRGB(
        self, n: int, red: int, green: int, blue: int, white: int = 0
    ):  # pylint: disable=too-many-positional-arguments
        self.setPixelColor(n, RGBW(red, green, blue, white))

    def getBrightness(self):
        return self._brightness

    def setBrightness(self, brightness: int):
        self._brightness = brightness

    def getPixels(self):
        return self._pixels

    def numPixels(self):
        return len(self)

    def getPixelColor(self, n: int) -> int:
        return self._pixels[n]

    def getPixelColorRGB(self, n: int) -> RGBW:
        pixel = self._pixels[n]
        return RGBW(pixel.r, pixel.g, pixel.b, pixel.w)

    def getPixelColorRGBW(self, n: int) -> RGBW:
        pixel = self._pixels[n]
        return RGBW(pixel.r, pixel.g, pixel.b, pixel.w)
