import time
from config import HexConfig
from leds.color import RGBW
from leds.controllers.controller_base import get_library


def main():
    config = HexConfig()
    PixelStrip, _ = get_library(False)
    (pin, channel) = config.pins

    strip = PixelStrip(
        num=config.get_led_count(),
        pin=pin,
        brightness=255,
        freq_hz=800000,
        dma=10,
        channel=channel,
    )
    strip.begin()

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
        """Draw rainbow that uniformly distributes itself across all pixels."""
        frame_count = 0
        start_time = time.time()
        while True:
            for j in range(256):
                for i in range(config.get_led_count()):
                    pixel_index = (i * 256 // config.get_led_count()) + j
                    strip.setPixelColor(i, wheel(pixel_index & 255))
                strip.show()
                time.sleep(wait)
                frame_count += 1
                current_time = time.time()
                if current_time - start_time >= 1.0:
                    print(f"FPS: {frame_count}")
                    frame_count = 0
                    start_time = current_time

    try:
        rainbow_cycle(0.001)  # Adjust the speed of the animation here
    except KeyboardInterrupt:
        # Turn off all LEDs on exit
        for i in range(config.get_led_count()):
            strip.setPixelColor(i, RGBW(0, 0, 0, 0))
        strip.show()


if __name__ == "__main__":
    main()
