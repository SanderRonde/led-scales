from typing import List, Dict
from config import HexConfig
from leds.color import RGBW
from leds.controllers.controller_base import get_library


def main():
    config = HexConfig()
    PixelStrip, _ = get_library(False)
    (pin, channel) = config.pins

    strip = PixelStrip(
        num=10000,
        pin=pin,
        brightness=255,
        freq_hz=800000,
        dma=10,
        channel=channel,
    )
    strip.begin()

    led_indices: Dict[int, List[int]] = {}
    current_led = 0
    last_user_index = 0

    try:
        while True:
            # Turn off all LEDs
            for i in range(10000):
                strip.setPixelColor(i, RGBW(0, 0, 0, 0))

            # Blink the current LED
            strip.setPixelColor(current_led, RGBW(255, 255, 255, 0))
            strip.show()

            # Get user input
            user_input = input(f"Hex for pixel {current_led}: ")
            if user_input.isdigit():
                user_num = int(user_input)
            else:
                user_num = last_user_index
            last_user_index = user_num
            if user_num not in led_indices:
                led_indices[user_num] = []
            led_indices[user_num].append(current_led)
            current_led += 1

    except KeyboardInterrupt:
        # Dump the array in the format of HexConfig
        result = "self.hexagons = [\n"
        for index, hexagon in enumerate(config.hexagons):
            result += f"\tHexagon({hexagon.x}, {hexagon.y}, [{', '.join(map(str, led_indices.get(index, [])))}]),\n"
        result += "]"
        print(result)


if __name__ == "__main__":
    main()
