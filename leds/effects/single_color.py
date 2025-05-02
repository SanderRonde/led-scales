from leds.controllers.controller_base import ControllerBase
from leds.effects.parameters import ColorParameter
from leds.effects.effect import Effect
from leds.color import Color


class SingleColorParameters:
    def __init__(self):
        self.color = ColorParameter(
            default=Color(255, 0, 0),
            description="Color of the effect",
        )


class SingleColorEffect(Effect):
    def __init__(self, controller: ControllerBase):
        super().__init__(controller)
        self.PARAMETERS = SingleColorParameters()

    def run(self, ms: int):
        self.controller.set_color(self.PARAMETERS.color.get_value())
        self.controller.show()
