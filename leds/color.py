"""RGBW color model implementation"""
from typing import Dict, List, Tuple, Optional


class RGBW(int):
    """Represents a color in RGBW format"""
    def __new__(cls, r: int, g: Optional[int]=None, b: Optional[int]=None, w: Optional[int]=None):
        if (g, b, w) == (None, None, None):
            return int.__new__(cls, r)
        else:
            if w is None:
                w = 0
            if g is None or b is None:
                raise ValueError("Either only the first arg or all three must be provided")
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

    @property
    def hsv(self) -> Tuple[float, float, float]:
        """Convert RGB to HSV (hue, saturation, value)
        Returns:
            Tuple[float, float, float]: HSV values where:
                - hue is in range [0, 360)
                - saturation is in range [0, 1]
                - value is in range [0, 1]
        """
        r = self.r / 255.0
        g = self.g / 255.0
        b = self.b / 255.0
        
        cmax = max(r, g, b)
        cmin = min(r, g, b)
        diff = cmax - cmin

        # Calculate hue
        if diff == 0:
            h = 0
        elif cmax == r:
            h = (60 * ((g - b) / diff) + 360) % 360
        elif cmax == g:
            h = (60 * ((b - r) / diff) + 120) % 360
        else:
            h = (60 * ((r - g) / diff) + 240) % 360

        # Calculate saturation
        s = 0 if cmax == 0 else (diff / cmax)

        # Calculate value
        v = cmax

        return (h, s, v)

    @classmethod
    def from_hsv(cls, h: float, s: float, v: float, w: int = 0) -> 'RGBW':
        """Create RGBW from HSV values
        Args:
            h (float): Hue in range [0, 360)
            s (float): Saturation in range [0, 1]
            v (float): Value in range [0, 1]
            w (int, optional): White value in range [0, 255]. Defaults to 0.
        Returns:
            RGBW: New RGBW color
        """
        h = h % 360
        s = max(0, min(1, s))
        v = max(0, min(1, v))

        c = v * s
        x = c * (1 - abs((h / 60) % 2 - 1))
        m = v - c

        if h < 60:
            r, g, b = c, x, 0
        elif h < 120:
            r, g, b = x, c, 0
        elif h < 180:
            r, g, b = 0, c, x
        elif h < 240:
            r, g, b = 0, x, c
        elif h < 300:
            r, g, b = x, 0, c
        else:
            r, g, b = c, 0, x

        return cls(
            int((r + m) * 255),
            int((g + m) * 255),
            int((b + m) * 255),
            w
        )

    def to_dict(self) -> Dict[str, int]:
        """Convert RGBW to dictionary format"""
        return {'r': self.r, 'g': self.g, 'b': self.b, 'w': self.w}

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> 'RGBW':
        """Create RGBW from dictionary format"""
        return cls(
            data.get('r', 0),
            data.get('g', 0),
            data.get('b', 0),
            data.get('w', 0)
        )

    def to_list(self) -> List[int]:
        """Convert RGBW to list format [r, g, b, w]"""
        return [self.r, self.g, self.b, self.w]

    @classmethod
    def from_list(cls, data: List[int]) -> 'RGBW':
        """Create RGBW from list format [r, g, b, w]"""
        return cls(
            data[0] if len(data) > 0 else 0,
            data[1] if len(data) > 1 else 0,
            data[2] if len(data) > 2 else 0,
            data[3] if len(data) > 3 else 0
        )

def Color(red: int, green: int, blue: int, white: int = 0) -> RGBW:
    """Convert the provided red, green, blue color to a 24-bit color value.
    Each color component should be a value 0-255 where 0 is the lowest intensity
    and 255 is the highest intensity.
    """
    return RGBW(red, green, blue, white)
