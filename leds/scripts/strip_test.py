import sys
import time
import argparse
from pathlib import Path
from typing import List, Tuple

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from leds.color import RGBW
from leds.controllers.controller_base import get_library
from leds.mock import MockPixelStrip


def main():
    parser = argparse.ArgumentParser(
        description="LED performance test for multiple strips"
    )
    parser.add_argument(
        "--config",
        action="append",
        help="Strip configuration as 'pin,channel,pin_count' (can be specified multiple times)",
    )
    args = parser.parse_args()

    if not args.config:
        print("Error: At least one --config must be specified")
        print("Example: --config '18,0,300' --config '19,1,150'")
        sys.exit(1)

    # Parse configurations
    strips: List[Tuple[MockPixelStrip, int]] = []
    PixelStrip, _ = get_library(False)

    for config_str in args.config:
        try:
            pin, channel, pin_count = map(int, config_str.split(","))
            strip = PixelStrip(
                num=pin_count,
                pin=pin,
                brightness=25,
                freq_hz=800000,
                dma=10,
                channel=channel,
            )
            strip.begin()
            strips.append((strip, pin_count))
            print(f"Initialized strip: pin={pin}, channel={channel}, LEDs={pin_count}")
        except ValueError as e:
            print(f"Error parsing config '{config_str}': {e}")
            sys.exit(1)

    def wheel(pos: int) -> RGBW:
        """Generate rainbow colors across 0-255 positions."""
        if pos < 85:
            return RGBW(pos * 3, 255 - pos * 3, 0, 0)
        elif pos < 170:
            pos -= 85
            return RGBW(255 - pos * 3, 0, pos * 3, 0)
        else:
            pos -= 170
            return RGBW(0, pos * 3, 255 - pos * 3, 0)

    def rainbow_cycle(wait: float) -> None:
        """Draw rainbow that uniformly distributes itself across all strips."""
        frame_count = 0
        start_time = time.time()

        while True:
            for j in range(256):
                # Update all strips in parallel
                for strip, pin_count in strips:
                    for i in range(pin_count):
                        pixel_index = (i * 256 // pin_count) + j
                        strip.setPixelColor(i, wheel(pixel_index & 255))

                # Show all strips
                for strip, _ in strips:
                    strip.show()

                time.sleep(wait)
                frame_count += 1

                # Log FPS every second
                current_time = time.time()
                if current_time - start_time >= 1.0:
                    print(f"FPS: {frame_count}")
                    frame_count = 0
                    start_time = current_time

    try:
        rainbow_cycle(0.001)
    except KeyboardInterrupt:
        # Turn off all LEDs on exit
        for strip, pin_count in strips:
            for i in range(pin_count):
                strip.setPixelColor(i, RGBW(0, 0, 0, 0))
            strip.show()


if __name__ == "__main__":
    main()
