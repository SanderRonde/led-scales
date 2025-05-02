from typing import Dict
from leds.effects.rainbow_radial import RainbowRadialEffect
from leds.effects.single_color_radial import SingleColorRadialEffect
from leds.effects.multi_color_radial import MultiColorRadialEffect
from leds.effects.rainbow import RainbowEffect
from leds.effects.rainbow_spin import RainbowSpinEffect
from leds.effects.random_color_single import RandomColorSingleEffect
from leds.effects.random_color_hex import RandomColorHexEffect
from leds.effects.random_color_dual import RandomColorDualEffect
from leds.controllers.controller_base import ControllerBase
from leds.effects.effect import Effect
from leds.controllers.scale_panel_controller import ScalePanelLEDController
from leds.controllers.hex_controller import HexPanelLEDController


def get_effects(controller: ControllerBase) -> Dict[str, Effect]:
    effects: Dict[str, Effect] = {
        RainbowRadialEffect.__name__: RainbowRadialEffect(controller),
        SingleColorRadialEffect.__name__: SingleColorRadialEffect(controller),
        MultiColorRadialEffect.__name__: MultiColorRadialEffect(controller),
        RandomColorSingleEffect.__name__: RandomColorSingleEffect(controller),
        RandomColorDualEffect.__name__: RandomColorDualEffect(controller),
    }
    if isinstance(controller, ScalePanelLEDController):
        effects[RainbowEffect.__name__] = RainbowEffect(controller)
    if isinstance(controller, HexPanelLEDController):
        effects[RainbowSpinEffect.__name__] = RainbowSpinEffect(controller)
        effects[RandomColorHexEffect.__name__] = RandomColorHexEffect(controller)
    return effects
