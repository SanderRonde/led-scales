"""RGBW color model implementation"""
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class RGBW:
    """Represents a color in RGBW format"""
    r: int
    g: int
    b: int
    w: int

    def to_dict(self) -> Dict[str, int]:
        """Convert RGBW to dictionary format"""
        return {'r': self.r, 'g': self.g, 'b': self.b, 'w': self.w}

    @classmethod
    def from_dict(cls, data: Dict[str, int]) -> 'RGBW':
        """Create RGBW from dictionary format"""
        return cls(
            r=data.get('r', 0),
            g=data.get('g', 0),
            b=data.get('b', 0),
            w=data.get('w', 0)
        )

    def to_list(self) -> List[int]:
        """Convert RGBW to list format [r, g, b, w]"""
        return [self.r, self.g, self.b, self.w]

    @classmethod
    def from_list(cls, data: List[int]) -> 'RGBW':
        """Create RGBW from list format [r, g, b, w]"""
        return cls(
            r=data[0] if len(data) > 0 else 0,
            g=data[1] if len(data) > 1 else 0,
            b=data[2] if len(data) > 2 else 0,
            w=data[3] if len(data) > 3 else 0
        )

def Color(red: int, green: int, blue: int, white: int = 0) -> RGBW:
    """Convert the provided red, green, blue color to a 24-bit color value.
    Each color component should be a value 0-255 where 0 is the lowest intensity
    and 255 is the highest intensity.
    """
    return RGBW(red, green, blue, white)
