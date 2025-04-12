from typing import List
import json
from flask import Flask, render_template, jsonify, send_from_directory
import threading
import webbrowser
import os
from config import ScaleConfig

# Load configuration
config = ScaleConfig()

class Color:
    def __init__(self, red: int, green: int, blue: int, white: int = 0):
        self.red = red
        self.green = green
        self.blue = blue
        self.white = white

    def __repr__(self):
        return f"Color(red={self.red}, green={self.green}, blue={self.blue}, white={self.white})"

class PixelStrip:
    def __init__(self, num, pin, freq_hz=800000, dma=10, invert=False, brightness=255, channel=0, strip_type=None, gamma=None):
        self.num_pixels = num
        self._pixels: List[Color] = [Color(0, 0, 0) for _ in range(num)]
        self._brightness = brightness
        self._app = Flask(__name__)
        self._setup_routes()
        
    def _setup_routes(self):
        @self._app.route('/')
        def home():
            return render_template('visualizer.html')
            
        @self._app.route('/pixels')
        def get_pixels():
            return jsonify([{
                'red': p.red,
                'green': p.green,
                'blue': p.blue,
                'white': getattr(p, 'white', 0)
            } for p in self._pixels])

        @self._app.route('/config')
        def get_config():
            # Import here to avoid circular import
            from config import default_config
            return jsonify({
                'x_count': default_config.x_count,
                'y_count': default_config.y_count,
                'panel_count': default_config.panel_count,
                'spacing': default_config.spacing
            })

        @self._app.route('/static/<path:filename>')
        def static_files(filename):
            return send_from_directory(os.path.join(os.path.dirname(__file__), 'static'), filename)

    def begin(self):
        """Start the web server in a background thread"""
        def run_server():
            self._app.run(port=5000)
            
        self._server_thread = threading.Thread(target=run_server, daemon=True)
        self._server_thread.start()
        webbrowser.open('http://localhost:5000')

    def show(self):
        """In the mock implementation, this doesn't need to do anything as the web UI updates in real-time"""
        pass

    def setPixelColor(self, n: int, color: Color):
        if 0 <= n < self.num_pixels:
            self._pixels[n] = color

    def getPixels(self) -> List[Color]:
        return self._pixels

    def numPixels(self) -> int:
        return self.num_pixels

    def getBrightness(self) -> int:
        return self._brightness

    def setBrightness(self, brightness: int):
        self._brightness = brightness 