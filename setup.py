#!/usr/bin/env python3
import os
import sys
import subprocess
import venv
import signal
import threading
import time
from pathlib import Path
from typing import Union, List, TextIO
from setuptools import setup, find_packages
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

# Package configuration
PACKAGE_CONFIG = {
    'name': 'leds',
    'version': '0.1.0',
    'packages': find_packages(),
    'install_requires': [
        'rpi_ws281x; platform_system == "Linux"',  # Only install on Linux systems
        'flask',  # Required for mock implementation
    ],
    'entry_points': {
        'console_scripts': [
            'leds=leds.leds:main',  # Real LED implementation
            'leds-mock=leds.leds:main_mock',  # Mock implementation
        ],
    },
    'python_requires': '>=3.7',
    'package_data': {
        'leds.mock': ['templates/*.html'],  # Include HTML templates
    },
}

def print_output(pipe: TextIO) -> None:
    for line in iter(pipe.readline, ''):
        if line.strip():  # Only print non-empty lines
            # Force immediate output
            print(line.strip(), flush=True)


def run_command(command: Union[str, List[str]], shell: bool = True) -> None:
    print(f"Running: {command}", flush=True)
    try:
        # Use Popen instead of run to have more control over the process
        process = subprocess.Popen(
            command,
            shell=shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line buffered
            universal_newlines=True
        )

        # Start threads to read stdout and stderr
        stdout_thread = threading.Thread(
            target=print_output, args=(process.stdout,))
        stderr_thread = threading.Thread(
            target=print_output, args=(process.stderr,))

        stdout_thread.start()
        stderr_thread.start()

        # Wait for the process to complete, but allow keyboard interrupts
        while True:
            try:
                return_code = process.poll()
                if return_code is not None:
                    # Wait for output threads to finish
                    stdout_thread.join()
                    stderr_thread.join()

                    if return_code != 0:
                        print(
                            f"Error: Command failed with exit code {return_code}", flush=True)
                        sys.exit(1)
                    break
            except KeyboardInterrupt:
                # Send SIGINT to the process group
                if sys.platform == "win32":
                    process.terminate()
                else:
                    os.killpg(os.getpgid(process.pid), signal.SIGINT)
                raise
    except KeyboardInterrupt:
        print("\nProcess interrupted by user", flush=True)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}", flush=True)
        sys.exit(1)


def setup_venv() -> None:
    print("Setting up virtual environment...")
    venv_path = Path("venv")

    if not venv_path.exists():
        venv.create(venv_path, with_pip=True)

    # Activate virtual environment and install requirements
    if sys.platform == "win32":
        activate_script = venv_path / "Scripts" / "activate.bat"
        pip_command = f'"{activate_script}" && pip install -r requirements.txt && pip install -e .'
    else:
        activate_script = venv_path / "bin" / "activate"
        pip_command = f'. "{activate_script}" && pip install -r requirements.txt && pip install -e .'

    run_command(pip_command)
    print("Setup complete!")


def generate_cad(mode: str = "") -> None:
    print("Generating CAD files...")
    if sys.platform == "win32":
        activate_script = "venv\\Scripts\\activate.bat"
        cmd = f'"{activate_script}" && python cad/led-scales.py {mode}'
    else:
        activate_script = "venv/bin/activate"
        cmd = f'. "{activate_script}" && python cad/led-scales.py {mode}'

    run_command(cmd)
    print("CAD generation complete! Files can be found in the cad/out directory")

def run_leds(mock: bool = False) -> None:
    print("Running LED implementation...")
    if sys.platform == "win32":
        activate_script = "venv\\Scripts\\activate.bat"
        cmd = f'"{activate_script}" && leds {"--mock" if mock else ""}'
    else:
        activate_script = "venv/bin/activate"
        cmd = f'. "{activate_script}" && leds {"--mock" if mock else ""}'
    run_command(cmd)

def clean() -> None:
    print("Cleaning up...")
    paths_to_clean = [
        "__pycache__",
        "cad/__pycache__",
        "venv",
        "cad/out"
    ]

    for path in paths_to_clean:
        if os.path.exists(path):
            if os.path.isdir(path):
                if sys.platform == "win32":
                    run_command(f'rmdir /s /q "{path}"')
                else:
                    run_command(f'rm -rf "{path}"')
            else:
                os.remove(path)

    print("Cleanup complete!")


def help() -> None:
    print("LED Scales CAD Generator:")
    print("  python setup.py setup    - Set up the development environment")
    print("  python setup.py generate - Generate CAD files (default mode)")
    print("  python setup.py 3d       - Generate 3D printable STL files for the scales")
    print("  python setup.py 2d       - Generate 2D SVG files for laser cutting/CNC")
    print("  python setup.py clean    - Clean up generated files and environment")
    print("  python setup.py all      - Generate all needed files")
    print("  python setup.py help     - Show this help message")
    print("  python setup.py leds     - Run the LED implementation")
    print("  python setup.py leds-mock - Run the LED implementation in mock mode")
    print("  python setup.py dev      - Run the server in development mode with auto-reload")
    print("\nOutput files will be generated in the cad/out directory")
    print("  - 3D files: cad/out/tiles/")
    print("  - 2D files: cad/out/panels/")


# List of setuptools commands that should bypass our custom command handling
SETUPTOOLS_COMMANDS = {
    'build', 'install', 'develop', 'bdist_wheel', 'sdist', 'egg_info',
    'easy_install', 'upload', 'register', 'check', 'test', 'build_ext',
    'build_py', 'build_scripts', 'build_clib', 'clean', 'install_lib',
    'install_headers', 'install_scripts', 'install_data', 'install_egg_info'
}

class RestartHandler(FileSystemEventHandler):
    def __init__(self):
        self.process = None
        self.last_restart = 0
        self.cooldown = 1.0  # Minimum time between restarts

    def start_process(self):
        # Kill existing process if any
        self.stop_process()

        # Start new process
        print("\nStarting server...")
        cmd = ['python', '-m', 'leds.leds', '--mock']
        self.process = subprocess.Popen(
            cmd,
            preexec_fn=None if sys.platform == "win32" else os.setsid
        )

    def stop_process(self):
        if self.process:
            try:
                if sys.platform == "win32":
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(self.process.pid)])
                else:
                    pgid = os.getpgid(self.process.pid)
                    os.killpg(pgid, signal.SIGTERM)
                    # Give it a moment to terminate gracefully
                    self.process.wait(timeout=1)
            except (ProcessLookupError, subprocess.TimeoutExpired):
                # Process already terminated or timeout waiting for it
                pass
            except Exception as e:
                print(f"Warning: Failed to stop process: {e}")
            finally:
                self.process = None

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory and (event.src_path.endswith('.py') or event.src_path.endswith('.js')):
            current_time = time.time()
            if current_time - self.last_restart > self.cooldown:
                self.last_restart = current_time
                print("\nRestarting server due to file change...")
                self.start_process()

def dev() -> None:
    """Run the server in development mode with auto-reload"""
    print("Starting development server with auto-reload...")
    
    # Set up file watching
    event_handler = RestartHandler()
    observer = Observer()
    
    # Watch Python files
    observer.schedule(event_handler, ".", recursive=True)
    observer.start()

    # Start initial process
    event_handler.start_process()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        observer.stop()
        event_handler.stop_process()
        observer.join()
        print("Server stopped")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        help()
        sys.exit(1)

    command = sys.argv[1]
    
    # If it's a setuptools command, let setuptools handle it
    if command in SETUPTOOLS_COMMANDS:
        setup(**PACKAGE_CONFIG)  # type: ignore
    # Otherwise handle our custom commands
    elif command == "setup":
        setup_venv()
    elif command == "generate":
        generate_cad()
    elif command == "2d":
        generate_cad("--2d")
    elif command == "3d":
        generate_cad("--3d")
    elif command == "clean":
        clean()
    elif command == "help":
        help()
    elif command == "leds":
        run_leds()
    elif command == "leds-mock":
        run_leds(True)
    elif command == "dev":
        dev()  # New development mode with auto-reload
    elif command == "all":
        print("Generating 3D print files...")
        generate_cad("--3d")
        print("Generating 2D files...")
        generate_cad("--2d")
        print("STL files can be found in cad/out/tiles/. Slice and print these with your 3D printer.")
        print("SVG files can be found in cad/out/panels. Have these printed out on paper.")
        print("Order the panels based on the provided panel count and dimensions. Put the paper over it. Drill marked holes for the LEDs and put the printed scales on the marked positions. Use cad/out/led-scales-py.positioning.scad to map printed scales to the panels.")
        print("Done!")
    else:
        print(f"Unknown command: {command}")
        help()
        sys.exit(1)
else:
    # When imported as a module, always run setup
    setup(**PACKAGE_CONFIG)  # type: ignore
