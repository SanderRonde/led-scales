#!/usr/bin/env python3
from typing import Dict, Any
from setuptools import setup, find_packages

# Package configuration
PACKAGE_CONFIG: Dict[str, Any] = {
    'name': 'leds',
    'version': '0.1.0',
    'packages': find_packages(),
    'install_requires': [
        'rpi_ws281x; platform_system == "Linux"',  # Only install on Linux systems
    ],
    'entry_points': {
        'console_scripts': [
            'leds=leds.leds:main',  # Real LED implementation
            'leds-mock=leds.leds:main_mock',  # Mock implementation
        ],
    },
    'python_requires': '>=3.7',
    'package_data': {
        'leds.mock': ['templates/*.html', 'static/**/*'],  # Include HTML templates and static files
    },
    'extras_require': {
        'led': [
            'pylint',
            'flask',  # Required for mock implementation
            'watchdog',  # Required for development mode
            'Flask-SocketIO',  # Required for real-time updates
            'python-socketio',  # Required for real-time updates
        ],
        'cad': [
            'pylint',
            'numpy',  # Required for CAD generation
            'openpyscad',  # Required for CAD generation
            'scipy',  # Required for CAD generation
        ],
    }
}

# When imported as a module, run setup
setup(**PACKAGE_CONFIG)