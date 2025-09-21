"""Setup mode effect that blinks one LED at a time"""

from typing import TYPE_CHECKING
from leds.effects.effect import Effect
from leds.color import RGBW

if TYPE_CHECKING:
    from leds.controllers.controller_base import ControllerBase


class SetupModeParameters:
    pass


class SetupModeEffect(Effect):
    """Effect that blinks one LED at a time for setup mode"""

    def __init__(self, controller: "ControllerBase"):
        super().__init__(controller)
        self.PARAMETERS = SetupModeParameters()
        self.current_led = 0
        self.last_update = 0
        self.blink_state = False  # Track the blink state

    def next(self) -> None:
        self.current_led = self.current_led + 1

    def run(self, ms: int) -> None:
        # Turn off all LEDs
        self.controller.set_color(RGBW(0, 0, 0, 0))

        # Blink the current LED
        if ms - self.last_update >= 50:  # Toggle every 50ms
            self.blink_state = not self.blink_state
            self.last_update = ms

        if self.blink_state:
            self.controller.set_pixel_color(
                # For the time being only support 1 strip
                0,
                self.current_led,
                RGBW(255, 255, 255, 0),
            )

        self.controller.show()
