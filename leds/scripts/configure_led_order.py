#!/usr/bin/env python3
"""
LED Order Configuration Script

This script helps configure the LED ordering for hexagonal layouts where:
- Each hexagon has multiple LEDs
- The first LED should be at the bottom
- LEDs should be ordered counter-clockwise from the bottom

Usage:
1. Run the script - it will show each hexagon's LEDs in different colors
2. Identify which LED is at the bottom position
3. The script will shift the array to make that LED first
4. Test the final configuration with rainbow patterns
"""

import sys
import time
from typing import List, Dict, Tuple
from pathlib import Path

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from config import HexConfig, get_config, BaseConfig
from leds.color import RGBW
from leds.controllers.controller_base import get_library


class LEDOrderConfigurator:
    def __init__(self):
        self.config = get_config()
        if not isinstance(self.config, HexConfig):
            raise ValueError("This script is designed for HexConfig only")

        PixelStrip, self.is_real = get_library(False)  # Always try real hardware first
        self.pin, self.channel = self.config.pins

        self.strip = PixelStrip(
            num=self.config.get_led_count(),
            pin=self.pin,
            brightness=100,  # Start with lower brightness
            freq_hz=800000,
            dma=10,
            channel=self.channel,
        )
        self.strip.begin()

        # Colors for identifying LEDs in each hexagon
        self.colors = [
            RGBW(255, 0, 0, 0),    # Red
            RGBW(0, 255, 0, 0),    # Green
            RGBW(0, 0, 255, 0),    # Blue
            RGBW(255, 255, 0, 0),  # Yellow
            RGBW(255, 0, 255, 0),  # Magenta
            RGBW(0, 255, 255, 0),  # Cyan
            RGBW(255, 128, 0, 0),  # Orange
            RGBW(128, 0, 255, 0),  # Purple
        ]

        self.color_codes = [
            "\033[91m",  # Red
            "\033[92m",  # Green
            "\033[94m",  # Blue
            "\033[93m",  # Yellow
            "\033[95m",  # Magenta
            "\033[96m",  # Cyan
            "\033[33m",  # Orange
            "\033[35m",  # Purple
        ]

        self.new_hexagons = []

    def clear_all(self):
        """Turn off all LEDs"""
        for i in range(self.config.get_led_count()):
            self.strip.setPixelColor(i, RGBW(0, 0, 0, 0))
        self.strip.show()

    def identify_led_by_subdivision(self, leds: List[int]) -> int:
        """Use binary subdivision to identify a specific LED"""
        if len(leds) == 1:
            # Light up the single LED
            self.clear_all()
            self.strip.setPixelColor(leds[0], RGBW(255, 255, 255, 0))
            self.strip.show()
            print(f"LED {leds[0]} should be lit (white)")
            return 0

        # Split LEDs into groups and light them up
        self.clear_all()

        # Calculate group size (aim for roughly equal groups)
        total_leds = len(leds)
        print(f"Total LEDs: {total_leds}", leds)
        if total_leds <= 8:
            # Small enough - use individual colors
            for i, led_id in enumerate(leds):
                color = self.colors[i % len(self.colors)]
                self.strip.setPixelColor(led_id, color)
                color_name = ['Red', 'Green', 'Blue', 'Yellow', 'Magenta', 'Cyan', 'Orange', 'Purple'][i % 8]
                print(f"  Position {i}: {self.color_codes[i % len(self.color_codes)]}{color_name}\033[0m")
            self.strip.show()
            
            group_input = input(f"Which color (1-{total_leds}) contains the bottom LED? ").strip()
            if not group_input.isdigit():
                print("Please enter a color number")
                return self.identify_led_by_subdivision(leds)
            color_num = int(group_input)
            return leds[color_num - 1]
        else:
            # Use groups
            group_size = max(1, total_leds // len(self.colors))
            if total_leds % len(self.colors) != 0:
                group_size += 1

            print(f"Showing {total_leds} LEDs in groups of ~{group_size}:")

            groups = []
            for i in range(0, total_leds, group_size):
                group = leds[i:i + group_size]
                groups.append(group)
                color = self.colors[len(groups) - 1]
                color_name = ['Red', 'Green', 'Blue', 'Yellow', 'Magenta', 'Cyan', 'Orange', 'Purple'][len(groups) - 1]

                print(f"  Group {len(groups)}: Positions {i}-{min(i + group_size - 1, total_leds - 1)} = {self.color_codes[len(groups) - 1]}{color_name}\033[0m")

                for led_id in group:
                    self.strip.setPixelColor(led_id, color)

            self.strip.show()

            group_input = input(f"Which group (1-{len(groups)}) contains the bottom LED? ").strip()
            if group_input.isdigit():
                group_num = int(group_input)
                if 1 <= group_num <= len(groups):
                    selected_group = groups[group_num - 1]

                    # Recursively subdivide the selected group
                    return self.identify_led_by_subdivision(selected_group)
                else:
                    print(f"Invalid group number. Must be 1-{len(groups)}")
            else:
                print("Please enter a group number")

    def show_hexagon_leds(self, hex_index: int) -> int:
        """Identify which LED is at the bottom using subdivision"""
        hexagon = self.config.hexagons[hex_index]
        leds = hexagon.ordered_leds

        print(f"\nHexagon {hex_index} at position ({hexagon.x}, {hexagon.y})")
        print(f"Has {len(leds)} LEDs")
        print("We'll identify the bottom LED using groups...")

        bottom_pos_led = self.identify_led_by_subdivision(leds)
        bottom_pos = leds.index(bottom_pos_led)

        if bottom_pos is None:
            # Small group - let user pick directly
            while True:
                try:
                    pos_input = input(f"Which position (0-{len(leds)-1}) is the bottom LED? ").strip()
                    if pos_input.isdigit():
                        pos = int(pos_input)
                        if 0 <= pos < len(leds):
                            return pos
                        else:
                            print(f"Invalid position. Must be 0-{len(leds)-1}")
                    else:
                        print("Please enter a position number")
                except KeyboardInterrupt:
                    raise

        return bottom_pos

    def configure_hexagon(self, hex_index: int) -> List[int]:
        """Configure LED ordering for a single hexagon"""
        hexagon = self.config.hexagons[hex_index]
        leds = hexagon.ordered_leds.copy()

        while True:
            print(f"\nConfiguring hexagon {hex_index} at ({hexagon.x}, {hexagon.y})")
            print("Options:")
            print("  'identify' - Identify the bottom LED using subdivision")
            print("  'test' - Test current ordering with rainbow")
            print("  'ok' - Accept current ordering")
            print("  'skip' - Keep original ordering")

            try:
                user_input = input("Choose action: ").strip().lower()
                print(f"User input: {user_input}")

                if user_input in ['ok', 'o']:
                    print("LED order confirmed!")
                    return leds
                elif user_input in ['skip', 's']:
                    print("Keeping original LED order")
                    return hexagon.ordered_leds
                elif user_input in ['test', 't']:
                    self.test_rainbow_hexagon(leds)
                    input("Press Enter to continue configuration...")
                    continue
                elif user_input in ['identify', 'i']:
                    bottom_pos = self.show_hexagon_leds(hex_index)
                    if 0 <= bottom_pos < len(leds):
                        # Shift the array so the bottom LED is first
                        leds = leds[bottom_pos:] + leds[:bottom_pos]
                        print(f"\nShifted array to put LED at position {bottom_pos} first")
                        print("New ordering: bottom LED is now at position 0")

                        # Show test
                        print("Showing test rainbow with new ordering, should following ordering starting from bottom and going counter-clockwise:")
                        print(f"  {self.color_codes[0]}Red\033[0m")
                        print(f"  {self.color_codes[6]}Orange\033[0m")
                        print(f"  {self.color_codes[3]}Yellow\033[0m")
                        print(f"  {self.color_codes[1]}Green\033[0m")
                        print(f"  {self.color_codes[2]}Blue\033[0m")
                        print(f"  {self.color_codes[5]}Cyan\033[0m")
                        print(f"  {self.color_codes[4]}Magenta\033[0m")
                        print(f"  {self.color_codes[7]}Purple\033[0m")
                        self.test_rainbow_hexagon(leds)
                        input("Press Enter to continue (or choose 'ok' to confirm)...")
                    else:
                        print(f"Invalid position: {bottom_pos}")
                else:
                    print("Invalid input. Choose 'identify', 'test', 'ok', or 'skip'")

            except KeyboardInterrupt:
                print("\nConfiguration cancelled")
                raise
            except Exception as e:
                print(f"Error: {e}")

    def test_rainbow_hexagon(self, leds: List[int]):
        """Show rainbow pattern on a single hexagon to verify ordering"""
        self.clear_all()

        # Create rainbow colors
        num_leds = len(leds)
        for i, led_id in enumerate(leds):
            # HSV rainbow: vary hue from 0 to 360
            hue = (i * 360) // num_leds
            r, g, b = self.hsv_to_rgb(hue, 1.0, 1.0)
            self.strip.setPixelColor(led_id, RGBW(int(r), int(g), int(b), 0))

        self.strip.show()

    def hsv_to_rgb(self, h: float, s: float, v: float) -> Tuple[float, float, float]:
        """Convert HSV to RGB"""
        import math

        h = h / 60.0
        i = int(h)
        f = h - i
        p = v * (1 - s)
        q = v * (1 - s * f)
        t = v * (1 - s * (1 - f))

        if i == 0:
            return (v * 255, t * 255, p * 255)
        elif i == 1:
            return (q * 255, v * 255, p * 255)
        elif i == 2:
            return (p * 255, v * 255, t * 255)
        elif i == 3:
            return (p * 255, q * 255, v * 255)
        elif i == 4:
            return (t * 255, p * 255, v * 255)
        else:
            return (v * 255, p * 255, q * 255)

    def test_all_rainbow(self):
        """Test mode: show static rainbow on all hexagons"""
        self.clear_all()

        print("Test mode: All hexagons showing rainbow patterns")
        print("Each hexagon should show a smooth rainbow counter-clockwise from bottom")

        for hex_index, hexagon in enumerate(self.new_hexagons):
            leds = hexagon.ordered_leds
            num_leds = len(leds)

            for i, led_id in enumerate(leds):
                hue = (i * 360) // num_leds
                r, g, b = self.hsv_to_rgb(hue, 1.0, 0.8)  # Slightly dimmer
                self.strip.setPixelColor(led_id, RGBW(int(r), int(g), int(b), 0))

        self.strip.show()

    def run_configuration(self):
        """Run the full configuration process"""
        print("LED Order Configuration Tool")
        print("=" * 40)
        print()
        print("This tool helps you configure LED ordering so that:")
        print("- The first LED in each hexagon is at the bottom")
        print("- LEDs are ordered counter-clockwise from the bottom")
        print()

        if not self.is_real:
            print("WARNING: Using mock LED implementation. Connect to real hardware for actual configuration.")
            print()

        try:
            for hex_index, hexagon in enumerate(self.config.hexagons):
                print(f"\n{'='*50}")
                print(f"Configuring Hexagon {hex_index + 1}/{len(self.config.hexagons)}")
                print(f"Position: ({hexagon.x}, {hexagon.y})")

                new_leds = self.configure_hexagon(hex_index)

                # Create new hexagon with updated LED order
                from config import Hexagon
                new_hex = Hexagon(hexagon.x, hexagon.y, new_leds)
                self.new_hexagons.append(new_hex)

            # Final test
            print(f"\n{'='*50}")
            print("Configuration complete! Running final test...")
            self.test_all_rainbow()

            input("\nPress Enter to see the new configuration code...")

            # Generate new configuration
            self.print_new_configuration()

        except KeyboardInterrupt:
            print("\n\nConfiguration cancelled by user")
            self.print_new_configuration()
        finally:
            self.clear_all()

    def print_new_configuration(self):
        """Print the new configuration code"""
        print(f"\n{'='*60}")
        print("NEW CONFIGURATION")
        print(f"{'='*60}")
        print()
        print("Replace the hexagons list in your HexConfig class with:")
        print()
        print("self.hexagons = [")

        for hexagon in self.new_hexagons:
            led_str = ", ".join(map(str, hexagon.ordered_leds))
            print(f"    Hexagon({hexagon.x}, {hexagon.y}, [{led_str}]),")

        print("]")
        print()
        print("Copy this code into your config.py file in the HexConfig.__init__() method")


def main():
    """Main entry point"""
    try:
        configurator = LEDOrderConfigurator()
        configurator.run_configuration()
    except KeyboardInterrupt:
        print("\n\nConfiguration cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()