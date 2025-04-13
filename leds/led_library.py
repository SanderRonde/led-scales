from typing import Type, Any, List, Tuple


# Try to import the real library first
try:
    from rpi_ws281x import PixelStrip as RealPixelStrip # type: ignore
    real_library_available = True
except ImportError:
    real_library_available = False


class RGBW(int):
    def __new__(cls, r: int, g: int, b: int, w: int) -> 'RGBW':
        return int.__new__(cls, (w << 24) | (r << 16) | (g << 8) | b)

    @property
    def r(self):
        return (self >> 16) & 0xff

    @property
    def g(self):
        return (self >> 8) & 0xff

    @property
    def b(self):
        return (self) & 0xff

    @property
    def w(self):
        return (self >> 24) & 0xff

    def __repr__(self):
        return f"RGBW(red={self.r}, green={self.g}, blue={self.b}, white={self.w})"


def Color(red: int, green: int, blue: int, white: int = 0) -> RGBW:
    """Convert the provided red, green, blue color to a 24-bit color value.
    Each color component should be a value 0-255 where 0 is the lowest intensity
    and 255 is the highest intensity.
    """
    return RGBW(red, green, blue, white)


class MockPixelStrip:
    def __init__(self, num: int, pin: int, brightness: int = 255, **kwargs: Any):
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

    def setPixelColorRGB(self, n: int, red: int, green: int, blue: int, white: int = 0):
        self.setPixelColor(n, RGBW(red, green, blue, white))

    def getBrightness(self):
        return self._brightness

    def setBrightness(self, brightness: int):
        self._brightness = brightness

    def getPixels(self):
        return self._pixels

    def numPixels(self):
        return len(self)

    def getPixelColor(self, n: int):
        return self._pixels[n]

    def getPixelColorRGB(self, n: int):
        pixel = self._pixels[n]
        return RGBW(pixel.r, pixel.g, pixel.b, pixel.w)

    def getPixelColorRGBW(self, n: int):
        pixel = self._pixels[n]
        return RGBW(pixel.r, pixel.g, pixel.b, pixel.w)


def get_library(mock: bool) -> Tuple[Type[Any], bool]:
    if not mock and not real_library_available:
        print("Real LED library was forced but rpi_ws281x is not available, falling back to mock library")
        return (MockPixelStrip, False)

    if mock:
        return (MockPixelStrip, False)
    else:
        return (RealPixelStrip, True) # type: ignore


# Export the mock classes as the main classes for easier imports
PixelStripType = MockPixelStrip
