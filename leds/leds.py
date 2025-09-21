"""Main entry point for LED control"""
import os
import sys
import time
import threading
import logging
import json
from typing import Dict, Any, Union, List
from pathlib import Path
from flask import Flask, render_template, jsonify, send_from_directory, request  # pylint: disable=import-error
from flask_socketio import SocketIO  # pylint: disable=import-error
from leds.effects import Effect, get_effects
from leds.effects.parameter_export import get_all_effects_parameters
from leds.effects.setup_mode import SetupModeEffect
from leds.effects.rainbow_radial import RainbowRadialEffect
from leds.controllers.controller_base import RGBW
from config import get_led_controller, BaseConfig, get_config, HexConfig
# Add parent directory to Python path when running directly
if __name__ == '__main__':
    sys.path.append(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__))))

SLEEP_TIME_MOCK = 0.05
# Is sleeping even needed?
SLEEP_TIME_REAL = 0.01


class LEDs:
    def __init__(self, mock: bool, config: BaseConfig):
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

        # Load all configuration from a single file
        self._config_data = self._load_config()
        self._power_state = self._config_data.get('power_state', True)
        self._brightness = self._config_data.get('brightness', 1.0)
        self._fade_start_time = 0
        self._fade_duration = 300  # ms
        self._target_power_state = self._power_state

        # Check if we're in setup mode and use setup effect
        if self.config.is_setup_mode():
            self._effect = self.set_effect(SetupModeEffect.__name__)
        else:
            # Try to load saved effect, fall back to RainbowRadialEffect if none exists
            saved_effect = self._config_data.get('effect_name')
            if saved_effect and saved_effect in self._effects:
                self._effect = self.set_effect(saved_effect)
            else:
                self._effect = self.set_effect(RainbowRadialEffect.__name__)

    def _get_sleep_time(self) -> float:
        if self._controller.is_mock:
            return SLEEP_TIME_MOCK
        return SLEEP_TIME_REAL

    def _get_config_path(self) -> Path:
        """Get the path where the configuration is saved"""
        return Path.home() / ".led_config.json"

    def _save_config(self) -> None:
        """Save the current configuration to disk"""
        save_path = self._get_config_path()
        config_data = {
            'power_state': self._power_state,
            'effect_name': self._effect.__class__.__name__,
            'brightness': self._brightness
        }
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(config_data, f)

    def _load_config(self) -> Dict[str, Any]:
        """Load the configuration from disk"""
        save_path = self._get_config_path()
        if not save_path.exists():
            return {'power_state': True}  # Default configuration
        try:
            with open(save_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, KeyError):
            return {'power_state': True}

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

        @self._app.route('/presets', methods=['GET'])
        def get_presets():  # type: ignore  # pylint: disable=unused-variable
            presets = self._config_data.get('presets', [])
            return jsonify(presets)

        @self._app.route('/presets', methods=['POST'])
        def save_preset():  # type: ignore  # pylint: disable=unused-variable
            data = request.get_json()
            if not data or 'name' not in data:
                return jsonify({'error': 'Invalid preset data'}), 400

            presets = self._config_data.get('presets', [])
            preset = {
                'id': data.get('id', int(time.time() * 1000)),
                'name': data['name'],
                'effect': data['effect'],
                'brightness': data['brightness'],
                'parameters': data['parameters']
            }

            # Update existing preset or add new one
            existing_index = next((i for i, p in enumerate(presets) if p['id'] == preset['id']), -1)
            if existing_index >= 0:
                presets[existing_index] = preset
            else:
                presets.append(preset)

            self._config_data['presets'] = presets
            self._save_config()
            return jsonify(preset)

        @self._app.route('/presets/<int:preset_id>', methods=['DELETE'])
        def delete_preset(preset_id: int):  # type: ignore  # pylint: disable=unused-variable
            presets = self._config_data.get('presets', [])
            self._config_data['presets'] = [p for p in presets if p['id'] != preset_id]
            self._save_config()
            return jsonify({'success': True})

        @self._app.route('/presets/apply', methods=['POST'])
        def apply_preset():  # type: ignore  # pylint: disable=unused-variable
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No preset data provided'}), 400

            # Set effect and parameters
            self._effect = self._effects[data['effect']]
            if 'parameters' in data:
                for param_name, param_value in data['parameters'].items():
                    if hasattr(self._effect.PARAMETERS, param_name):
                        getattr(self._effect.PARAMETERS, param_name).set_value(param_value)

            # Set brightness
            if 'brightness' in data:
                self._brightness = data['brightness']

            self._running = True
            self._save_config()
            return jsonify({'success': True})

        @self._app.route('/effects')
        def get_effects_route():  # type: ignore  # pylint: disable=unused-variable
            effect_parameters = get_all_effects_parameters(self._effects)
            return jsonify({
                'effect_parameters': effect_parameters,
                'effect_names': {effect_name: effect.get_name() for effect_name, effect in self._effects.items()},
                'current_effect': self._effect.__class__.__name__
            })

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
            self._save_config()  # Save the updated configuration
            return jsonify({
                'success': True
            })

        @self._app.route('/config')
        def get_visualizer_config():  # type: ignore  # pylint: disable=unused-variable
            return jsonify(self._controller.get_visualizer_config())

        @self._app.route('/state', methods=['POST'])
        def set_state():  # type: ignore  # pylint: disable=unused-variable
            data: Dict[str, Any] = request.get_json() or {}

            # Handle power state
            if 'power_state' in data:
                target_state: bool = data.get('power_state', False)
                self._target_power_state = target_state
                self._fade_start_time = time.time() * 1000  # Convert to ms

            # Handle brightness
            if 'brightness' in data:
                brightness: float = data.get('brightness', 1.0)
                self._brightness = max(0.0, min(1.0, brightness))

            self._save_config()
            return jsonify({
                'success': True,
                'power_state': self._power_state,
                'target_power_state': self._target_power_state,
                'brightness': self._brightness
            })

        @self._app.route('/state')
        def get_state():  # type: ignore  # pylint: disable=unused-variable
            return jsonify({
                'power_state': self._power_state,
                'target_power_state': self._target_power_state,
                'brightness': self._brightness
            })

        @self._app.route('/setup/hex/assign', methods=['POST'])
        def assign_led_to_hex():  # type: ignore  # pylint: disable=unused-variable
            """Assign an LED to a hexagon during setup mode"""
            if not isinstance(self.config, HexConfig) or not self.config.is_setup_mode():
                return jsonify({'error': 'Not in setup mode'}), 400

            data = request.get_json()
            if not data or 'hex_index' not in data or 'led_index' not in data:
                return jsonify({'error': 'Missing hex_index or led_index'}), 400

            hex_index = data['hex_index']
            led_index = data['led_index']

            if hex_index < 0 or hex_index >= len(self.config.hexagons):
                return jsonify({'error': 'Invalid hex_index'}), 400

            # Add LED to the hexagon's ordered_leds list
            self.config.hexagons[hex_index].setup_mode_leds.append(led_index)

            return jsonify({
                'success': True,
                'hex_index': hex_index,
                'led_index': led_index,
            })

        @self._app.route('/setup/hex/export', methods=['GET'])
        def export_config():  # type: ignore  # pylint: disable=unused-variable
            """Export the current hexagon configuration as copyable Python code"""
            if not isinstance(self.config, HexConfig):
                return jsonify({'error': 'Not using HexConfig'}), 400

            config_lines: List[str] = []
            config_lines.append("self.hexagons = [")
            for hexagon in self.config.hexagons:
                config_lines.append(
                    f"    Hexagon({hexagon.x}, {hexagon.y}, {hexagon.setup_mode_leds}),")
            config_lines.append("]")

            return jsonify({
                'config_code': '\n'.join(config_lines)
            })

        @self._app.route('/setup/hex/reset', methods=['POST'])
        def reset_setup():  # type: ignore  # pylint: disable=unused-variable
            """Reset all hexagon LED assignments"""
            if not isinstance(self.config, HexConfig):
                return jsonify({'error': 'Not using HexConfig'}), 400

            for hexagon in self.config.hexagons:
                hexagon.setup_mode_leds.clear()

            return jsonify({'success': True})

        @self._app.route('/setup/current-led', methods=['GET'])
        def get_current_led():  # type: ignore  # pylint: disable=unused-variable
            """Get the current LED index being assigned"""
            if not isinstance(self._effect, SetupModeEffect):
                return jsonify({'error': 'Not using SetupModeEffect'}), 400
            return jsonify({'current_led': self._effect.current_led})

        @self._app.route('/setup/next', methods=['POST'])
        def next_led():  # type: ignore  # pylint: disable=unused-variable
            """Get the current LED index being assigned"""
            if not isinstance(self._effect, SetupModeEffect):
                return jsonify({'error': 'Not using SetupModeEffect'}), 400
            self._effect.next()
            return jsonify({'success': True, 'current_led': self._effect.current_led})

    def listen(self) -> None:
        """Start the web server in the main thread"""
        print(
            f"LEDs web server running on http://0.0.0.0:{self.config.web_port}")
        self._socketio.run(self._app, host='0.0.0.0', port=self.config.web_port,  # type: ignore
                           debug=False, use_reloader=False)

    def set_effect(self, effect_name: str) -> Effect:
        """Set the effect to run"""
        self._effect = self._effects[effect_name]
        self._running = True
        self._save_config()  # Save the updated configuration
        return self._effect

    def start(self) -> None:
        """Start the LED effect in a background thread"""
        def run_effect() -> None:
            now = time.time()
            while self._running:
                elapsed_ms = int((time.time() - now) * 1000)

                # Calculate fade progress
                fade_progress = min(
                    1.0, (time.time() * 1000 - self._fade_start_time) / self._fade_duration)

                if fade_progress >= 1.0:
                    self._power_state = self._target_power_state

                if self._power_state or fade_progress < 1.0:
                    self._effect.run(elapsed_ms)
                    if fade_progress < 1.0:
                        # Apply fade effect
                        if self._target_power_state:
                            # Fading in
                            brightness = fade_progress
                        else:
                            # Fading out
                            brightness = 1.0 - fade_progress
                        self._controller.set_brightness(
                            brightness * self._brightness)
                    else:
                        self._controller.set_brightness(self._brightness)
                else:
                    self._controller.set_color(RGBW(0, 0, 0, 0))
                    self._controller.show()

                # Emit LED data through WebSocket
                self._socketio.emit(  # type: ignore
                    'led_update', self._controller.json(), namespace='/')
                time.sleep(self._get_sleep_time())

        effect_thread = threading.Thread(target=run_effect, daemon=True)
        effect_thread.start()


def main() -> None:
    mock = "--mock" in sys.argv

    leds = LEDs(mock, get_config())
    leds.start()  # Start effect thread
    leds.listen()  # Run Flask in main thread


if __name__ == '__main__':
    # When run directly, default to mock mode for safety
    main()
