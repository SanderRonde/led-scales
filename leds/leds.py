"""Main entry point for LED control"""
import os
import sys
import time
import threading
import logging
from typing import Dict, Any, Union
from flask import Flask, render_template, jsonify, send_from_directory, request  # pylint: disable=import-error
from flask_socketio import SocketIO  # pylint: disable=import-error
from leds.effects import Effect, SingleColorRadialEffect, get_effects
from leds.effects.parameter_export import get_all_effects_parameters
from config import get_led_controller, BaseConfig, get_config

# Add parent directory to Python path when running directly
if __name__ == '__main__':
    sys.path.append(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))

SLEEP_TIME_MOCK = 0.05
# Is sleeping even needed?
SLEEP_TIME_REAL = 0.01


class LEDs:
    def __init__(self, mock: bool, config: BaseConfig, effect_name: str):
        self._app = Flask(__name__, static_folder=None)
        self.config = config
        self._socketio = SocketIO(self._app, cors_allowed_origins="*")
        # Disable Flask request logging
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        self._controller = get_led_controller(mock)
        self._init_routes()
        self._effects = get_effects(self._controller)
        self._running = False

        self._effect = self.set_effect(effect_name)

    def _get_sleep_time(self) -> float:
        if self._controller.is_mock:
            return SLEEP_TIME_MOCK
        return SLEEP_TIME_REAL

    def _init_routes(self) -> None:
        @self._app.route('/')
        def home():  # type: ignore  # pylint: disable=unused-variable
            return render_template('visualizer.html')

        @self._app.route('/static/<path:filename>')
        def static_files(filename: str):  # type: ignore  # pylint: disable=unused-variable
            static_dir = os.path.join(os.path.dirname(__file__), 'static')
            response = send_from_directory(static_dir, filename)

            # Set correct MIME types for common web files
            if filename.endswith('.js'):
                response.headers['Content-Type'] = 'application/javascript'
            elif filename.endswith('.css'):
                response.headers['Content-Type'] = 'text/css'
            elif filename.endswith('.html'):
                response.headers['Content-Type'] = 'text/html'
            elif filename.endswith('.json'):
                response.headers['Content-Type'] = 'application/json'
            elif filename.endswith('.svg'):
                response.headers['Content-Type'] = 'image/svg+xml'
            # For other file types, the default MIME type from send_from_directory is used

            return response

        @self._app.route('/effects')
        def get_effects_route():  # type: ignore  # pylint: disable=unused-variable
            return jsonify(get_all_effects_parameters(self._effects))

        @self._app.route('/effects', methods=['POST'])
        def set_effect():  # type: ignore  # pylint: disable=unused-variable
            data: Dict[str, Any] = request.get_json() or {}
            effect_name: Union[str, None] = data.get('effect_name')
            if not effect_name:
                return jsonify({
                    'success': False,
                    'error': 'No effect name provided'
                }), 400

            if effect_name not in self._effects:
                return jsonify({
                    'success': False,
                    'error': f'Effect "{effect_name}" not found'
                }), 404

            self._effect = self._effects[effect_name]
            # Set parameters if provided
            if 'parameters' in data:
                for param_name, param_value in data['parameters'].items():
                    if hasattr(self._effect.PARAMETERS, param_name):
                        getattr(self._effect.PARAMETERS,
                                param_name).set_value(param_value)

            self._running = True
            return jsonify({
                'success': True
            })

        @self._app.route('/config')
        def get_visualizer_config():  # type: ignore  # pylint: disable=unused-variable
            return jsonify(self._controller.get_visualizer_config())

    def listen(self) -> None:
        """Start the web server in the main thread"""
        print(
            f"LEDs web server running on http://localhost:{self.config.web_port}")
        self._socketio.run(self._app, port=self.config.web_port,  # type: ignore
                           debug=False, use_reloader=False)

    def set_effect(self, effect_name: str) -> Effect:
        """Set the effect to run"""
        self._effect = self._effects[effect_name]
        self._running = True
        return self._effect

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

        effect_thread = threading.Thread(target=run_effect, daemon=True)
        effect_thread.start()


def main() -> None:
    mock = "--mock" in sys.argv

    leds = LEDs(mock, get_config(), SingleColorRadialEffect.__name__)
    leds.start()  # Start effect thread
    leds.listen()  # Run Flask in main thread


if __name__ == '__main__':
    # When run directly, default to mock mode for safety
    main()
