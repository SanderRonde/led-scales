from leds.controller import LEDController


class Effect:
    def __init__(self, controller: LEDController):
        self.controller = controller

    def run(self, ms: int):
        pass
