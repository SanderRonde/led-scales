"""Main entry point for LED control"""
import os
import sys
import time
import threading
import logging
from flask import Flask, render_template, jsonify, send_from_directory
from leds.controller import LEDController
from leds.effects.rainbow import RainbowEffect
from leds.effects.effect import Effect
from config import ScaleConfig

# Load configuration
config = ScaleConfig()

# Add parent directory to Python path when running directly
if __name__ == '__main__':
    sys.path.append(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))

SLEEP_TIME_MOCK = 0.25
# Is sleeping even needed?
SLEEP_TIME_REAL = 0.01


class LEDs:
    def __init__(self, mock: bool):
        self._app = Flask(__name__)
        # Disable Flask request logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        self._controller = LEDController(config, mock)
        self._init_routes()

    def _get_sleep_time(self):
        if self._controller.is_mock:
            return SLEEP_TIME_MOCK
        else:
            return SLEEP_TIME_REAL

    def _init_routes(self):
        @self._app.route('/')
        def home():  # type: ignore
            return render_template('visualizer.html')

        @self._app.route('/static/<path:filename>')
        def static_files(filename: str):  # type: ignore
            return send_from_directory(os.path.join(os.path.dirname(__file__), 'static'), filename)

        @self._app.route('/pixels')
        def get_pixels():  # type: ignore
            return self._controller.json()

        @self._app.route('/config')
        def get_config():  # type: ignore
            return jsonify({
                'delay': self._get_sleep_time(),
                'x_count': config.x_count,
                'y_count': config.y_count,
                'panel_count': config.panel_count,
                'spacing': config.spacing,
                'panel_spacing_scales': config.panel_spacing_scales,
                'total_width': config.total_width,
                'total_height': config.total_height,
                'scale_length': config.base_length,
                'scale_width': config.base_width,
            })

    def listen(self):
        """Start the web server in a background thread"""
        def run_server():
            self._app.run(port=config.web_port)

        self._server_thread = threading.Thread(target=run_server, daemon=True)
        self._server_thread.start()
        print(f"LEDs web server running on http://localhost:{config.web_port}")

    def set_effect(self, effect: type[Effect]):
        """Set the effect to run"""
        self._effect = effect(self._controller)

    def start(self):
        now = time.time()
        while True:
            elapsed_ms = int((time.time() - now) * 1000)
            self._effect.run(elapsed_ms)
            if self._controller.is_mock:
                time.sleep(1)
            else:
                time.sleep(self._get_sleep_time())


def main() -> None:
    mock = "--mock" in sys.argv

    leds = LEDs(mock)
    leds.listen()
    leds.set_effect(RainbowEffect)
    leds.start()


if __name__ == '__main__':
    # When run directly, default to mock mode for safety
    main()
