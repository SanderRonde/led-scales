"""Main entry point for LED control"""

import os
import sys
import time
import threading
import logging
import json
from typing import Any, Dict, Optional, Union
from pathlib import Path
from flask import (  # pylint: disable=import-error
    Flask,
    render_template,
    jsonify,
    send_from_directory,
    request,
)
from flask.json.provider import JSONProvider  # pylint: disable=import-error
from flask_socketio import SocketIO  # pylint: disable=import-error
from leds.effects import Effect, get_effects
from leds.effects.parameter_export import get_all_effects_parameters
from leds.effects.rainbow_radial import RainbowRadialEffect
from leds.controllers.controller_base import RGBW
from config import get_led_controller, BaseConfig, get_config, ConfigMode

# Add parent directory to Python path when running directly
if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SLEEP_TIME_MOCK = 0.05
# Is sleeping even needed?
SLEEP_TIME_REAL = 0.005


class CustomJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that ensures RGBW objects are serialized using to_dict()"""

    def default(self, o: Any) -> Any:
        if isinstance(o, RGBW):
            return o.to_dict()
        return super().default(o)


class CustomJSONProvider(JSONProvider):
    """Custom JSON provider that uses our custom encoder for RGBW serialization"""

    def dumps(self, obj: Any, **kwargs: Any) -> str:
        """Serialize data as JSON using our custom encoder"""
        kwargs.setdefault("cls", CustomJSONEncoder)
        return json.dumps(obj, **kwargs)

    def loads(self, s: Any, **kwargs: Any) -> Any:
        """Deserialize JSON data"""
        return json.loads(s, **kwargs)


class LEDs:
    def __init__(self, mock: bool, config: BaseConfig, debug: bool = False):
        self._app = Flask(__name__, static_folder=None)
        self._app.json = CustomJSONProvider(self._app)
        self.config = config
        self._debug = debug
        self._socketio = SocketIO(self._app, cors_allowed_origins="*")
        # Disable Flask request logging
        log = logging.getLogger("werkzeug")
        log.setLevel(logging.ERROR)
        self._controller = get_led_controller(config, mock)
        self._init_routes()
        self._effects = get_effects(self._controller)
        self._running = False
        self._ws_client_lock = threading.Lock()
        self._ws_client_count = 0

        # FPS tracking variables
        self._frame_count = 0
        self._last_fps_time = time.time()
        self._fps = 0.0

        # Load all configuration from a single file
        self._config_data = self._load_config()
        startup_power = self._effective_power_on_at_startup()
        self._power_state = startup_power
        self._brightness = self._config_data.get("brightness", 1.0)
        self._active_preset_id = self._config_data.get("active_preset_id", None)
        self._fade_start_time = 0
        self._fade_duration = 300  # ms
        self._target_power_state = startup_power

        # Try to load saved effect, fall back to RainbowRadialEffect if none exists
        saved_effect = self._config_data.get("effect_name")
        if saved_effect and saved_effect in self._effects:
            self._effect = self.set_effect(saved_effect)
        else:
            self._effect = self.set_effect(RainbowRadialEffect.__name__)

        self._apply_default_preset_on_startup()

    def _effective_power_on_at_startup(self) -> bool:
        """Whether LEDs should start on after a server restart."""
        if "power_on_at_startup" in self._config_data:
            return bool(self._config_data["power_on_at_startup"])
        return bool(self._config_data.get("power_state", True))

    def _apply_preset_payload(self, data: Dict[str, Any]) -> bool:
        """Apply effect, brightness, and parameters from a preset-style dict."""
        effect_name = data.get("effect")
        if not effect_name or effect_name not in self._effects:
            return False

        self._effect = self._effects[effect_name]
        if "parameters" in data and data["parameters"] is not None:
            for param_name, param_value in data["parameters"].items():
                if hasattr(self._effect.PARAMETERS, param_name):
                    getattr(self._effect.PARAMETERS, param_name).set_value(param_value)

        if "brightness" in data and data["brightness"] is not None:
            self._brightness = float(data["brightness"])

        self._active_preset_id = data.get("id", None)

        self._running = True
        self._save_config()
        self._emit_effects_update()
        self._emit_state_update()
        return True

    def _apply_default_preset_on_startup(self) -> None:
        """If a default preset id is configured and valid, apply it (overrides last effect)."""
        default_id: Optional[int] = self._config_data.get("default_preset_id")
        if default_id is None:
            return
        presets = self._config_data.get("presets", [])
        preset = next((p for p in presets if p["id"] == default_id), None)
        if preset is None:
            self._config_data["default_preset_id"] = None
            self._save_config()
            return
        ok = self._apply_preset_payload(
            {
                "id": preset["id"],
                "effect": preset["effect"],
                "brightness": preset.get("brightness", self._brightness),
                "parameters": preset.get("parameters", {}),
            }
        )
        if not ok:
            self._config_data["default_preset_id"] = None
            self._save_config()

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
        # Update the config data with current state
        self._config_data["power_state"] = self._power_state
        self._config_data["effect_name"] = self._effect.__class__.__name__
        self._config_data["brightness"] = self._brightness
        self._config_data["active_preset_id"] = self._active_preset_id
        # Save entire config including presets
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(self._config_data, f, indent=2)

    def _load_config(self) -> Dict[str, Any]:
        """Load the configuration from disk"""
        save_path = self._get_config_path()
        if not save_path.exists():
            return {"power_state": True}  # Default configuration
        try:
            with open(save_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, KeyError):
            return {"power_state": True}

    def _has_ws_clients(self) -> bool:
        with self._ws_client_lock:
            return self._ws_client_count > 0

    def _safe_emit(self, event: str, data: Any) -> None:
        """Emit to WebSocket clients, skipping when none are connected."""
        if not self._has_ws_clients():
            return
        try:
            self._socketio.emit(event, data, namespace="/")  # type: ignore
        except Exception:  # pylint: disable=broad-exception-caught
            # Stale/disconnecting clients can race engineio ping handling.
            logging.getLogger(__name__).debug(
                "WebSocket emit failed for %s", event, exc_info=True
            )

    def _emit_state_update(self) -> None:
        """Emit current state through WebSocket"""
        self._safe_emit(
            "state_update",
            {
                "power_state": self._power_state,
                "target_power_state": self._target_power_state,
                "brightness": self._brightness,
                "active_preset_id": self._active_preset_id,
                "default_preset_id": self._config_data.get("default_preset_id"),
                "power_on_at_startup": self._effective_power_on_at_startup(),
            },
        )

    def _emit_effects_update(self) -> None:
        """Emit current effects through WebSocket"""
        effect_parameters = get_all_effects_parameters(self._effects)
        self._safe_emit(
            "effects_update",
            {
                "effect_parameters": effect_parameters,
                "effect_names": {
                    effect_name: effect.get_name()
                    for effect_name, effect in self._effects.items()
                },
                "current_effect": self._effect.__class__.__name__,
            },
        )

    def _emit_presets_update(self) -> None:
        """Emit current presets through WebSocket"""
        presets = self._config_data.get("presets", [])
        self._safe_emit("presets_update", presets)

    def _init_routes(self) -> None:
        @self._app.route("/")
        def home():  # type: ignore  # pylint: disable=unused-variable
            return render_template("visualizer.html")

        @self._app.route("/static/<path:filename>")
        def static_files(filename: str):  # type: ignore  # pylint: disable=unused-variable
            static_dir = os.path.join(os.path.dirname(__file__), "static")
            response = send_from_directory(static_dir, filename)

            # Set correct MIME types for common web files
            if filename.endswith(".js"):
                response.headers["Content-Type"] = "application/javascript"
            elif filename.endswith(".css"):
                response.headers["Content-Type"] = "text/css"
            elif filename.endswith(".html"):
                response.headers["Content-Type"] = "text/html"
            elif filename.endswith(".json"):
                response.headers["Content-Type"] = "application/json"
            elif filename.endswith(".svg"):
                response.headers["Content-Type"] = "image/svg+xml"
            # For other file types, the default MIME type from send_from_directory is used

            return response

        @self._app.route("/presets", methods=["GET"])
        def get_presets():  # type: ignore  # pylint: disable=unused-variable
            presets = self._config_data.get("presets", [])
            return jsonify(presets)

        @self._app.route("/presets", methods=["POST"])
        def save_preset():  # type: ignore  # pylint: disable=unused-variable
            data = request.get_json()
            if not data or "name" not in data:
                return jsonify({"error": "Invalid preset data"}), 400

            presets = self._config_data.get("presets", [])
            preset = {
                "id": data.get("id", int(time.time() * 1000)),
                "name": data["name"],
                "effect": data["effect"],
                "brightness": data["brightness"],
                "parameters": data["parameters"],
            }

            # Update existing preset or add new one
            existing_index = next(
                (i for i, p in enumerate(presets) if p["id"] == preset["id"]), -1
            )
            if existing_index >= 0:
                presets[existing_index] = preset
            else:
                presets.append(preset)

            self._config_data["presets"] = presets
            self._save_config()
            self._emit_presets_update()
            return jsonify(preset)

        @self._app.route("/presets/<int:preset_id>", methods=["DELETE"])
        def delete_preset(preset_id: int):  # type: ignore  # pylint: disable=unused-variable
            presets = self._config_data.get("presets", [])
            self._config_data["presets"] = [p for p in presets if p["id"] != preset_id]
            if self._config_data.get("default_preset_id") == preset_id:
                self._config_data["default_preset_id"] = None
            self._save_config()
            self._emit_presets_update()
            self._emit_state_update()
            return jsonify({"success": True})

        @self._app.route("/presets/default", methods=["POST"])
        def set_default_preset():  # type: ignore  # pylint: disable=unused-variable
            data = request.get_json()
            if data is None or "id" not in data:
                return (
                    jsonify(
                        {
                            "error": 'JSON body must include "id" (preset id or null to clear)',
                        }
                    ),
                    400,
                )

            preset_id = data["id"]
            if preset_id is None:
                self._config_data["default_preset_id"] = None
                self._save_config()
                self._emit_state_update()
                return jsonify({"success": True, "default_preset_id": None})

            presets = self._config_data.get("presets", [])
            if not any(p["id"] == preset_id for p in presets):
                return jsonify({"error": "Preset not found"}), 404

            self._config_data["default_preset_id"] = preset_id
            self._save_config()
            self._emit_state_update()
            return jsonify({"success": True, "default_preset_id": preset_id})

        @self._app.route("/presets/apply", methods=["POST"])
        def apply_preset():  # type: ignore  # pylint: disable=unused-variable
            data = request.get_json()
            if not data:
                return jsonify({"error": "No preset data provided"}), 400

            if not self._apply_preset_payload(data):
                return jsonify({"error": "Invalid preset data"}), 400
            return jsonify({"success": True})

        @self._app.route("/effects")
        def get_effects_route():  # type: ignore  # pylint: disable=unused-variable
            effect_parameters = get_all_effects_parameters(self._effects)
            return jsonify(
                {
                    "effect_parameters": effect_parameters,
                    "effect_names": {
                        effect_name: effect.get_name()
                        for effect_name, effect in self._effects.items()
                    },
                    "current_effect": self._effect.__class__.__name__,
                }
            )

        @self._app.route("/effects", methods=["POST"])
        def set_effect():  # type: ignore  # pylint: disable=unused-variable
            data: Dict[str, Any] = request.get_json() or {}
            effect_name: Union[str, None] = data.get("effect_name")
            if not effect_name:
                return (
                    jsonify({"success": False, "error": "No effect name provided"}),
                    400,
                )

            if effect_name not in self._effects:
                return (
                    jsonify(
                        {"success": False, "error": f'Effect "{effect_name}" not found'}
                    ),
                    404,
                )

            self._effect = self._effects[effect_name]
            # Set parameters if provided
            if "parameters" in data:
                for param_name, param_value in data["parameters"].items():
                    if hasattr(self._effect.PARAMETERS, param_name):
                        getattr(self._effect.PARAMETERS, param_name).set_value(
                            param_value
                        )

            # Clear active preset since values were modified
            self._active_preset_id = None

            self._running = True
            self._save_config()  # Save the updated configuration
            self._emit_effects_update()
            self._emit_state_update()
            return jsonify({"success": True})

        @self._app.route("/config")
        def get_visualizer_config():  # type: ignore  # pylint: disable=unused-variable
            return jsonify(self._controller.get_visualizer_config())

        @self._app.route("/state", methods=["POST"])
        def set_state():  # type: ignore  # pylint: disable=unused-variable
            data: Dict[str, Any] = request.get_json() or {}

            if "power_on_at_startup" in data:
                val = data["power_on_at_startup"]
                if not isinstance(val, bool):
                    return (
                        jsonify(
                            {"error": '"power_on_at_startup" must be a boolean'},
                        ),
                        400,
                    )
                self._config_data["power_on_at_startup"] = val

            # Handle power state
            if "power_state" in data:
                target_state: bool = data.get("power_state", False)
                self._target_power_state = target_state
                self._fade_start_time = time.time() * 1000  # Convert to ms

            # Handle brightness
            if "brightness" in data:
                brightness: float = data.get("brightness", 1.0)
                self._brightness = max(0.0, min(1.0, brightness))
                # Clear active preset since brightness was modified
                self._active_preset_id = None

            self._save_config()
            self._emit_state_update()
            return jsonify(
                {
                    "success": True,
                    "power_state": self._power_state,
                    "target_power_state": self._target_power_state,
                    "brightness": self._brightness,
                    "active_preset_id": self._active_preset_id,
                    "default_preset_id": self._config_data.get("default_preset_id"),
                    "power_on_at_startup": self._effective_power_on_at_startup(),
                }
            )

        @self._app.route("/state")
        def get_state():  # type: ignore  # pylint: disable=unused-variable
            return jsonify(
                {
                    "power_state": self._power_state,
                    "target_power_state": self._target_power_state,
                    "brightness": self._brightness,
                    "active_preset_id": self._active_preset_id,
                    "default_preset_id": self._config_data.get("default_preset_id"),
                    "power_on_at_startup": self._effective_power_on_at_startup(),
                }
            )

        @self._socketio.on("connect")
        def handle_connect():  # type: ignore  # pylint: disable=unused-variable
            """Emit full state when a client connects"""
            with self._ws_client_lock:
                self._ws_client_count += 1
            self._emit_state_update()
            self._emit_effects_update()
            self._emit_presets_update()

        @self._socketio.on("disconnect")
        def handle_disconnect():  # type: ignore  # pylint: disable=unused-variable
            with self._ws_client_lock:
                self._ws_client_count = max(0, self._ws_client_count - 1)

    def listen(self) -> None:
        """Start the web server in the main thread"""
        print(
            f"LEDs web server running, visit http://localhost:{self.config.web_port} to view the visualizer"
        )
        self._socketio.run(
            self._app,
            host="0.0.0.0",
            port=self.config.web_port,  # type: ignore
            debug=False,
            use_reloader=False,
            allow_unsafe_werkzeug=True,
        )

    def set_effect(self, effect_name: str) -> Effect:
        """Set the effect to run"""
        self._effect = self._effects[effect_name]
        self._running = True
        self._save_config()  # Save the updated configuration
        self._emit_effects_update()
        return self._effect

    def start(self) -> None:
        """Start the LED effect in a background thread"""

        def run_effect() -> None:
            now = time.time()
            while self._running:
                elapsed_ms = int((time.time() - now) * 1000)

                # Calculate fade progress
                fade_progress = min(
                    1.0,
                    (time.time() * 1000 - self._fade_start_time) / self._fade_duration,
                )

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
                        self._controller.set_brightness(brightness * self._brightness)
                    else:
                        self._controller.set_brightness(self._brightness)
                else:
                    self._controller.set_color(RGBW(0, 0, 0, 0))
                    self._controller.show()

                # Emit LED data through WebSocket (skip when no visualizer is open)
                if self._has_ws_clients():
                    self._safe_emit("led_update", self._controller.json())

                # FPS tracking and debug output
                if self._debug:
                    self._frame_count += 1
                    current_time = time.time()
                    time_diff = current_time - self._last_fps_time

                    # Print FPS every 1 second
                    if time_diff >= 1.0:
                        self._fps = self._frame_count / time_diff
                        print(f"FPS: {self._fps:.2f}", flush=True)
                        self._frame_count = 0
                        self._last_fps_time = current_time

                time.sleep(self._get_sleep_time())

        effect_thread = threading.Thread(target=run_effect, daemon=True)
        effect_thread.start()


def main() -> None:

    mock = False
    debug = False
    mode: Union[None, ConfigMode] = None
    for arg in sys.argv[1:]:
        if arg == "--mock":
            mock = True
        elif arg == "--debug":
            debug = True
        else:
            if arg not in list(ConfigMode):
                print(
                    "Please pass a valid config mode. Should be one of",
                    list(map(lambda x: x.value, list(ConfigMode))),
                )
                sys.exit(1)
            mode = ConfigMode(arg)
    if not mode:
        print(
            "Please pass a valid config mode. Should be one of",
            list(map(lambda x: x.value, list(ConfigMode))),
        )
        sys.exit(1)

    leds = LEDs(mock, get_config(mode), debug)
    leds.start()  # Start effect thread
    leds.listen()  # Run Flask in main thread


if __name__ == "__main__":
    # When run directly, default to mock mode for safety
    main()
