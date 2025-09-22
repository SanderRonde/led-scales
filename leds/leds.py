"""Main entry point for LED control"""

import os
import sys
import time
import threading
import logging
import json
from typing import Dict, Any, Union
from pathlib import Path
from flask import (
    Flask,
    render_template,
    jsonify,
    send_from_directory,
    request,
)  # pylint: disable=import-error
from flask_socketio import SocketIO  # pylint: disable=import-error
from leds.effects import Effect, get_effects
from leds.effects.parameter_export import get_all_effects_parameters
from leds.effects.rainbow_radial import RainbowRadialEffect
from leds.controllers.controller_base import RGBW
from leds.performance import profile_function, profile_block, get_profiler, log_performance_summary
from config import get_led_controller, BaseConfig, get_config

# Add parent directory to Python path when running directly
if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Optimized sleep times for better performance
SLEEP_TIME_MOCK = 0.033  # ~30 FPS for mock mode
SLEEP_TIME_REAL = 0.016  # ~60 FPS for real hardware (if it can keep up)

# Performance monitoring
FRAME_TIME_WARNING_MS = 50  # Warn if frame takes longer than 50ms
PERF_LOG_INTERVAL = 1000  # Log performance stats every 1000 frames


class LEDs:
    @profile_function("LEDs.__init__")
    def __init__(self, mock: bool, config: BaseConfig):
        with profile_block("LEDs.init.flask_setup"):
            self._app = Flask(__name__, static_folder=None)
            self.config = config
            self._socketio = SocketIO(self._app, cors_allowed_origins="*")
            # Disable Flask request logging
            log = logging.getLogger("werkzeug")
            log.setLevel(logging.ERROR)
        
        with profile_block("LEDs.init.controller_setup"):
            self._controller = get_led_controller(mock)
        
        with profile_block("LEDs.init.routes_setup"):
            self._init_routes()
        
        with profile_block("LEDs.init.effects_setup"):
            self._effects = get_effects(self._controller)
        
        self._running = False
        
        # Performance tracking
        self._frame_count = 0
        self._last_perf_log = time.time()
        self._frame_times = []
        
        # WebSocket optimization
        self._active_clients = 0
        self._last_client_check = 0
        self._client_check_interval = 30  # Check every 30 frames
        
        with profile_block("LEDs.init.config_load"):
            # Load all configuration from a single file
            self._config_data = self._load_config()
            self._power_state = self._config_data.get("power_state", True)
            self._brightness = self._config_data.get("brightness", 1.0)
            self._fade_start_time = 0
            self._fade_duration = 300  # ms
            self._target_power_state = self._power_state

            # Try to load saved effect, fall back to RainbowRadialEffect if none exists
            saved_effect = self._config_data.get("effect_name")
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

    @profile_function("LEDs._save_config")
    def _save_config(self) -> None:
        """Save the current configuration to disk"""
        save_path = self._get_config_path()
        config_data = {
            "power_state": self._power_state,
            "effect_name": self._effect.__class__.__name__,
            "brightness": self._brightness,
        }
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f)

    @profile_function("LEDs._load_config")
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

    def _init_routes(self) -> None:
        @self._app.route("/")
        def home():  # type: ignore  # pylint: disable=unused-variable
            return render_template("visualizer.html")
        
        # WebSocket event handlers for client tracking
        @self._socketio.on('connect')
        def handle_connect():  # type: ignore  # pylint: disable=unused-variable
            self._active_clients += 1
            get_profiler().logger.debug(f"Client connected. Active clients: {self._active_clients}")
        
        @self._socketio.on('disconnect')
        def handle_disconnect():  # type: ignore  # pylint: disable=unused-variable
            self._active_clients = max(0, self._active_clients - 1)
            get_profiler().logger.debug(f"Client disconnected. Active clients: {self._active_clients}")

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
            return jsonify(preset)

        @self._app.route("/presets/<int:preset_id>", methods=["DELETE"])
        def delete_preset(preset_id: int):  # type: ignore  # pylint: disable=unused-variable
            presets = self._config_data.get("presets", [])
            self._config_data["presets"] = [p for p in presets if p["id"] != preset_id]
            self._save_config()
            return jsonify({"success": True})

        @self._app.route("/presets/apply", methods=["POST"])
        def apply_preset():  # type: ignore  # pylint: disable=unused-variable
            data = request.get_json()
            if not data:
                return jsonify({"error": "No preset data provided"}), 400

            # Set effect and parameters
            self._effect = self._effects[data["effect"]]
            if "parameters" in data:
                for param_name, param_value in data["parameters"].items():
                    if hasattr(self._effect.PARAMETERS, param_name):
                        getattr(self._effect.PARAMETERS, param_name).set_value(
                            param_value
                        )

            # Set brightness
            if "brightness" in data:
                self._brightness = data["brightness"]

            self._running = True
            self._save_config()
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

            self._running = True
            self._save_config()  # Save the updated configuration
            return jsonify({"success": True})

        @self._app.route("/config")
        def get_visualizer_config():  # type: ignore  # pylint: disable=unused-variable
            return jsonify(self._controller.get_visualizer_config())

        @self._app.route("/state", methods=["POST"])
        def set_state():  # type: ignore  # pylint: disable=unused-variable
            data: Dict[str, Any] = request.get_json() or {}

            # Handle power state
            if "power_state" in data:
                target_state: bool = data.get("power_state", False)
                self._target_power_state = target_state
                self._fade_start_time = time.time() * 1000  # Convert to ms

            # Handle brightness
            if "brightness" in data:
                brightness: float = data.get("brightness", 1.0)
                self._brightness = max(0.0, min(1.0, brightness))

            self._save_config()
            return jsonify(
                {
                    "success": True,
                    "power_state": self._power_state,
                    "target_power_state": self._target_power_state,
                    "brightness": self._brightness,
                }
            )

        @self._app.route("/state")
        def get_state():  # type: ignore  # pylint: disable=unused-variable
            return jsonify(
                {
                    "power_state": self._power_state,
                    "target_power_state": self._target_power_state,
                    "brightness": self._brightness,
                }
            )
        
        @self._app.route("/performance")
        def get_performance():  # type: ignore  # pylint: disable=unused-variable
            """Get performance and WebSocket statistics"""
            ws_stats = self.get_websocket_stats()
            perf_stats = get_profiler().get_all_stats()
            
            # Calculate WebSocket efficiency
            total_frames = ws_stats['frame_count']
            emissions_sent = ws_stats['emissions_sent']
            emissions_skipped = ws_stats['emissions_skipped']
            efficiency = (emissions_skipped / total_frames * 100) if total_frames > 0 else 0
            
            return jsonify({
                "websocket": {
                    "active_clients": ws_stats['active_clients'],
                    "total_frames": total_frames,
                    "emissions_sent": emissions_sent,
                    "emissions_skipped": emissions_skipped,
                    "efficiency_percent": round(efficiency, 1),
                    "led_count": self.config.get_led_count()
                },
                "performance": {
                    "tracked_operations": len(perf_stats),
                    "total_operations": sum(stat.get('count', 0) for stat in perf_stats.values()),
                    "total_time_ms": sum(stat.get('total_ms', 0) for stat in perf_stats.values())
                }
            })

    def listen(self) -> None:
        """Start the web server in the main thread"""
        print(f"LEDs web server running on http://0.0.0.0:{self.config.web_port}")
        self._socketio.run(
            self._app,
            host="0.0.0.0",
            port=self.config.web_port,  # type: ignore
            debug=False,
            use_reloader=False,
        )

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
            profiler = get_profiler()
            
            while self._running:
                frame_start = time.perf_counter()
                
                with profile_block("effect_frame"):
                    elapsed_ms = int((time.time() - now) * 1000)

                    # Calculate fade progress
                    with profile_block("fade_calculation"):
                        fade_progress = min(
                            1.0,
                            (time.time() * 1000 - self._fade_start_time) / self._fade_duration,
                        )

                        if fade_progress >= 1.0:
                            self._power_state = self._target_power_state

                    # Run effect or set to black
                    if self._power_state or fade_progress < 1.0:
                        with profile_block("effect_run"):
                            self._effect.run(elapsed_ms)
                        
                        with profile_block("brightness_control"):
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
                        with profile_block("power_off"):
                            self._controller.set_color(RGBW(0, 0, 0, 0))
                            self._controller.show()

                    # Emit LED data through WebSocket only when clients are listening
                    if self._should_emit_websocket_data():
                        with profile_block("websocket_emit"):
                            self._socketio.emit(  # type: ignore
                                "led_update", self._controller.json(), namespace="/"
                            )
                
                # Performance tracking
                frame_time = (time.perf_counter() - frame_start) * 1000
                self._frame_times.append(frame_time)
                self._frame_count += 1
                
                # Log performance warnings
                if frame_time > FRAME_TIME_WARNING_MS:
                    profiler.logger.warning(f"Slow frame: {frame_time:.2f}ms (frame #{self._frame_count})")
                
                # Periodic performance logging
                if self._frame_count % PERF_LOG_INTERVAL == 0:
                    self._log_performance_stats()
                
                time.sleep(self._get_sleep_time())

        effect_thread = threading.Thread(target=run_effect, daemon=True)
        effect_thread.start()
        
        # Log that LED system has started
        get_profiler().logger.info(f"LED effect system started with {self.config.get_led_count()} LEDs")
    
    def _log_performance_stats(self) -> None:
        """Log performance statistics"""
        if not self._frame_times:
            return
            
        profiler = get_profiler()
        avg_frame_time = sum(self._frame_times) / len(self._frame_times)
        max_frame_time = max(self._frame_times)
        fps = 1000 / avg_frame_time if avg_frame_time > 0 else 0
        
        profiler.logger.info(
            f"Performance: {self._frame_count} frames, "
            f"avg={avg_frame_time:.2f}ms, max={max_frame_time:.2f}ms, "
            f"fps={fps:.1f}, LEDs={self.config.get_led_count()}"
        )
        
        # Clear frame times to prevent memory growth
        self._frame_times.clear()
    
    def _should_emit_websocket_data(self) -> bool:
        """Determine if WebSocket data should be emitted based on active clients and frame rate"""
        # Always check if we have active clients
        if self._active_clients <= 0:
            return False
        
        # Emit every other frame when clients are connected (30 FPS instead of 60 FPS)
        if self._frame_count % 2 != 0:
            return False
        
        # Periodically verify client count using SocketIO's built-in method
        if self._frame_count % self._client_check_interval == 0:
            try:
                # Get actual connected clients from SocketIO
                room_clients = len(self._socketio.server.manager.get_participants('/', '/'))  # type: ignore
                if room_clients != self._active_clients:
                    get_profiler().logger.debug(
                        f"Client count mismatch detected. Tracked: {self._active_clients}, Actual: {room_clients}"
                    )
                    self._active_clients = room_clients
            except Exception as e:
                # Fallback: assume we have clients if we can't check
                get_profiler().logger.warning(f"Could not verify client count: {e}")
        
        return self._active_clients > 0
    
    def get_active_client_count(self) -> int:
        """Get the number of active WebSocket clients"""
        return self._active_clients
    
    def reset_websocket_stats(self):
        """Reset WebSocket performance statistics"""
        self._frame_count = 0
        get_profiler().logger.info("WebSocket statistics reset")
    
    def stop(self) -> None:
        """Stop the LED system and log final performance stats"""
        self._running = False
        self._log_performance_stats()
        log_performance_summary()
        get_profiler().logger.info(f"LED system stopped. Final client count: {self._active_clients}")
    
    def get_websocket_stats(self) -> dict:
        """Get WebSocket performance statistics"""
        return {
            "active_clients": self._active_clients,
            "frame_count": self._frame_count,
            "emissions_sent": self._frame_count // 2 if self._active_clients > 0 else 0,
            "emissions_skipped": self._frame_count - (self._frame_count // 2 if self._active_clients > 0 else 0)
        }


def main() -> None:
    mock = "--mock" in sys.argv

    leds = LEDs(mock, get_config())
    leds.start()  # Start effect thread
    leds.listen()  # Run Flask in main thread


if __name__ == "__main__":
    # When run directly, default to mock mode for safety
    main()
