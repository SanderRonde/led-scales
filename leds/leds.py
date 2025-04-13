"""Main entry point for LED control"""
import os
import sys
import time
import threading
import logging
from typing import Callable
from flask import Flask, render_template, jsonify, send_from_directory
from flask_socketio import SocketIO
from leds.controller import LEDController
from leds.effects import MultiColorRadialEffect, Effect
from leds.color import Color
from config import ScaleConfig

# Load configuration
config = ScaleConfig()

# Add parent directory to Python path when running directly
if __name__ == '__main__':
    sys.path.append(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))

SLEEP_TIME_MOCK = 0.05
# Is sleeping even needed?
SLEEP_TIME_REAL = 0.01


class LEDs:
    def __init__(self, mock: bool):
        self._app = Flask(__name__)
        self._socketio = SocketIO(self._app, cors_allowed_origins="*")
        # Disable Flask request logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        self._controller = LEDController(config, mock)
        self._init_routes()
        self._running = False

    def _get_sleep_time(self) -> float:
        if self._controller.is_mock:
            return SLEEP_TIME_MOCK
        else:
            return SLEEP_TIME_REAL

    def _init_routes(self) -> None:
        @self._app.route('/')
        def home():  # type: ignore
            return render_template('visualizer.html')

        @self._app.route('/static/<path:filename>')
        def static_files(filename: str):  # type: ignore
            return send_from_directory(os.path.join(os.path.dirname(__file__), 'static'), filename)

        @self._app.route('/config')
        def get_config():  # type: ignore
            return jsonify({
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

    def listen(self) -> None:
        """Start the web server in the main thread"""
        print(f"LEDs web server running on http://localhost:{config.web_port}")
        self._socketio.run(self._app, port=config.web_port,  # type: ignore
                           debug=False, use_reloader=False)

    def set_effect(self, get_effect: Callable[[LEDController], Effect]):
        """Set the effect to run"""
        self._effect = get_effect(self._controller)
        self._running = True

    def start(self) -> None:
        """Start the LED effect in a background thread"""
        def run_effect() -> None:
            now = time.time()
            while self._running:
                elapsed_ms = int((time.time() - now) * 1000)
                self._effect.run(elapsed_ms)
                # Emit LED data through WebSocket
                self._socketio.emit(  # type: ignore
                    'led_update', self._controller.json(), namespace='/')
                time.sleep(self._get_sleep_time())

        self._effect_thread = threading.Thread(target=run_effect, daemon=True)
        self._effect_thread.start()


def main() -> None:
    mock = "--mock" in sys.argv

    leds = LEDs(mock)
    leds.set_effect(lambda controller: MultiColorRadialEffect(
        controller, [Color(255, 0, 0), Color(0, 255, 0), Color(0, 0, 255)], 0.6, 'out'))
    leds.start()  # Start effect thread
    leds.listen()  # Run Flask in main thread


if __name__ == '__main__':
    # When run directly, default to mock mode for safety
    main()
