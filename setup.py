#!/usr/bin/env python3
import os
import sys
import subprocess
import venv
import signal
import threading
from pathlib import Path
from typing import Union, List, TextIO
from setuptools import setup, find_packages

# Package configuration
PACKAGE_CONFIG = {
    'name': 'led-scales',
    'version': '0.1.0',
    'packages': find_packages(),
    'install_requires': [
        'rpi_ws281x; platform_system != "Windows"',  # Only install on non-Windows systems
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

def print_output(pipe: TextIO, prefix: str = "") -> None:
    for line in iter(pipe.readline, ''):
        if line.strip():  # Only print non-empty lines
            # Force immediate output
            print(f"{prefix}{line.strip()}", flush=True)


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
            target=print_output, args=(process.stderr, "ERROR: "))

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

if __name__ == "__main__":
    if len(sys.argv) < 2:
        help()
        sys.exit(1)

    command = sys.argv[1]
    
    # If it's a setuptools command, let setuptools handle it
    if command in SETUPTOOLS_COMMANDS:
        setup(**PACKAGE_CONFIG)
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
    setup(**PACKAGE_CONFIG)
