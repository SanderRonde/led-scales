# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LED Scales is a Python project that generates 3D-printable dragon scales with embedded LEDs and provides a web interface to control lighting effects. The project consists of two main components:

1. **CAD Generation** (`cad/` directory) - Creates 3D printable scale STL files and 2D panel templates using OpenPySCAD
2. **LED Control** (`leds/` directory) - Web-based LED controller with real-time effects via Flask/SocketIO

## Architecture

### Dual Virtual Environment Setup
The project uses separate virtual environments for isolation:
- `venv-cad`: CAD generation dependencies (numpy, openpyscad, scipy, pylint)
- `venv-led`: LED control dependencies (Flask, SocketIO, watchdog, rpi_ws281x)

### Key Components

**Configuration System** (`config.py`):
- `BaseConfig`: Abstract base for all configurations
- `ScaleConfig`: Main configuration with scale dimensions, panel layout, LED specs
- Hardware pin configuration for Raspberry Pi GPIO

**LED Effects System** (`leds/effects/`):
- `Effect`: Abstract base class for all lighting effects
- Parameter system with `FloatParameter`, `EnumParameter` for web UI controls
- Mixin classes: `SpeedParameters`, `ColorInterpolationParameters`, `SpeedWithDirectionParameters`
- Built-in effects: rainbow, radial patterns, random colors, single colors

**Controller System** (`leds/controllers/`):
- `ControllerBase`: Abstract base with mock/real hardware abstraction
- `HexController`: Hexagonal grid layout controller
- `ScalePanelController`: Multi-panel scale arrangement controller
- Automatic fallback from real `rpi_ws281x` to mock implementation

**CAD Generation** (`cad/led-scales.py`):
- Generates 3D STL files for dragon scales
- Creates 2D SVG templates for panel drilling
- Configurable scale dimensions and panel layouts

## Common Development Commands

### Setup and Environment Management
```bash
python main.py setup          # Set up both virtual environments
python main.py clean          # Clean generated files and environments
```

### CAD Development
```bash
python main.py generate       # Generate CAD files (default mode)
python main.py 3d             # Generate 3D STL files only
python main.py 2d             # Generate 2D SVG templates only
python main.py all            # Generate all files (3D + 2D)
```

### LED Development
```bash
python main.py dev            # Development server with auto-reload (uses mock LEDs)
python main.py leds           # Run real LED controller
python main.py leds-mock      # Run with mock LED implementation
python main.py leds-debug     # Run with FPS debug output
```

### Code Quality
```bash
python main.py lint           # Run pylint (uses CAD environment)
python main.py format         # Format code with Black (uses CAD environment)
```

## Development Workflow

1. **Configuration**: Modify `config.py` for hardware setup and scale dimensions
2. **CAD Generation**: Use `python main.py all` to generate printable files
3. **LED Development**: Use `python main.py dev` for iterative development with auto-reload
4. **Hardware Testing**: Use `python main.py leds` on Raspberry Pi for real hardware

## Key File Locations
- Generated 3D files: `cad/out/tiles/`
- Generated 2D templates: `cad/out/panels/`
- LED effects: `leds/effects/`
- Hardware controllers: `leds/controllers/`
- Web interface: `leds/templates/` and `leds/static/`

## Testing Notes
- Mock LED implementation automatically provides web interface for testing
- Real hardware requires Raspberry Pi with `rpi_ws281x` library
- Development mode includes file watching for automatic server restarts
- Web interface runs on port 5001 by default (configurable in `config.py`)