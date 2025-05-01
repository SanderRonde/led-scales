from leds.effects.rainbow_radial import RainbowRadialEffect
from leds.effects.single_color_radial import SingleColorRadialEffect
from leds.effects.multi_color_radial import MultiColorRadialEffect
from leds.effects.rainbow import RainbowEffect
from leds.controllers.controller_base import ControllerBase
from leds.effects.effect import Effect
from typing import Dict
from leds.controllers.scale_panel_controller import ScalePanelLEDController


def get_effects(controller: ControllerBase) -> Dict[str, Effect]:
    effects: Dict[str, Effect] = {
        RainbowRadialEffect.__name__: RainbowRadialEffect(controller),
        SingleColorRadialEffect.__name__: SingleColorRadialEffect(controller),
        MultiColorRadialEffect.__name__: MultiColorRadialEffect(controller),
    }
    if isinstance(controller, ScalePanelLEDController):
        effects[RainbowEffect.__name__] = RainbowEffect(controller)
    return effects
