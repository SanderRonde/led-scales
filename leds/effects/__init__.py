from leds.effects.rainbow_radial import RainbowRadialEffect
from leds.effects.single_color_radial import SingleColorRadialEffect
from leds.effects.multi_color_radial import MultiColorRadialEffect
from leds.effects.rainbow import RainbowEffect
from leds.controller import LEDController
from leds.effects.effect import Effect
from typing import Dict


def get_effects(controller: LEDController) -> Dict[str, Effect]:
    return {
        RainbowRadialEffect.__name__: RainbowRadialEffect(controller),
        SingleColorRadialEffect.__name__: SingleColorRadialEffect(controller),
        MultiColorRadialEffect.__name__: MultiColorRadialEffect(controller),
        RainbowEffect.__name__: RainbowEffect(controller)
    }
