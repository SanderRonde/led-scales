"""Main entry point for LED control"""
import os
import sys
import time
from typing import Optional

# Add parent directory to Python path when running directly
if __name__ == '__main__':
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # First try importing as installed package
    from leds.led_library import PixelStrip, Color
    from config import default_config  # config.py is in root directory
except ImportError:
    # Fallback for direct script execution
    from .led_library import PixelStrip, Color
    from ..config import default_config


def create_strip(mock: bool = False) -> PixelStrip:
    """Create and initialize LED strip"""
    # Calculate total number of LEDs
    led_count = (default_config.x_count * default_config.y_count *
                 default_config.panel_count)

    # Force mock mode if requested
    if mock:
        os.environ['FORCE_MOCK_LEDS'] = '1'

    # Create strip
    strip = PixelStrip(
        num=led_count,
        pin=18,  # GPIO pin
        freq_hz=800000,
        dma=10,
        invert=False,
        brightness=255,
        channel=0
    )

    # Initialize
    strip.begin()
    return strip


def rainbow_cycle(strip: PixelStrip, wait_ms: int = 20) -> None:
    """Draw rainbow that uniformly distributes itself across all pixels."""
    def wheel(pos: int) -> Color:
        """Generate rainbow colors across 0-255 positions."""
        if pos < 85:
            return Color(pos * 3, 255 - pos * 3, 0)
        elif pos < 170:
            pos -= 85
            return Color(255 - pos * 3, 0, pos * 3)
        else:
            pos -= 170
            return Color(0, pos * 3, 255 - pos * 3)

    for j in range(256):
        for i in range(strip.numPixels()):
            pixel_index = (i * 256 // strip.numPixels()) + j
            strip.setPixelColor(i, wheel(pixel_index & 255))
        strip.show()
        time.sleep(wait_ms / 1000.0)


def run_demo(strip: PixelStrip) -> None:
    """Run a demo animation"""
    try:
        while True:
            rainbow_cycle(strip)
    except KeyboardInterrupt:
        # Turn off all LEDs on Ctrl+C
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, Color(0, 0, 0))
        strip.show()


def main() -> None:
    """Entry point for real LED implementation"""
    strip = create_strip(mock=False)
    run_demo(strip)


def main_mock() -> None:
    """Entry point for mock implementation"""
    strip = create_strip(mock=True)
    run_demo(strip)


if __name__ == '__main__':
    # When run directly, default to mock mode for safety
    main_mock()
