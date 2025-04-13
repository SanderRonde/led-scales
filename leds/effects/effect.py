from typing import List
from leds.led_library import PixelStripType


class Effect:
    def __init__(self, strips: List[PixelStripType]):
        self.strips = strips

    def run(self, ms: int):
        pass
