#!/usr/bin/env python3
import os
import sys
import subprocess
import venv
import platform
import signal
import threading
import time
from pathlib import Path
from typing import Union, List, TextIO, Literal
from config import ConfigMode


def print_output(pipe: TextIO) -> None:
    for line in iter(pipe.readline, ""):
        if line.strip():  # Only print non-empty lines
            # Force immediate output
            print(line.strip(), flush=True)


def run_command(cmd: Union[str, List[str]], shell: bool = True) -> None:
    print(f"Running: {cmd}", flush=True)
    try:
        # Use Popen instead of run to have more control over the process
        with subprocess.Popen(
            cmd,
            shell=shell,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line buffered
            universal_newlines=True,
        ) as process:
            # Start threads to read stdout and stderr
            stdout_thread = threading.Thread(
                target=print_output, args=(process.stdout,)
            )
            stderr_thread = threading.Thread(
                target=print_output, args=(process.stderr,)
            )

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
                                f"Error: Command failed with exit code {return_code}",
                                flush=True,
                            )
                            sys.exit(1)
                        break
                except KeyboardInterrupt:
                    # Send SIGINT to the process group
                    if sys.platform == "win32":
                        process.terminate()
                    else:
                        if hasattr(os, "killpg"):
                            os.killpg(os.getpgid(process.pid), signal.SIGINT)
                        else:
                            process.terminate()
                    raise
    except KeyboardInterrupt:
        print("\nProcess interrupted by user", flush=True)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}", flush=True)
        sys.exit(1)


def get_venv_path(venv_type: Literal["cad", "led"]) -> Path:
    """Get the path for a specific virtual environment"""
    return Path(f"venv-{venv_type}")


def get_venv_python(venv_type: Literal["cad", "led"]) -> str:
    """Get the Python executable path for a specific virtual environment"""
    venv_path = get_venv_path(venv_type)
    if sys.platform == "win32":
        return str(venv_path / "Scripts" / "python.exe")
    return str(venv_path / "bin" / "python")


def get_venv_activate(venv_type: Literal["cad", "led"]) -> Path:
    """Get the activation script path for a specific virtual environment"""
    venv_path = get_venv_path(venv_type)
    if sys.platform == "win32":
        return venv_path / "Scripts" / "activate.bat"
    return venv_path / "bin" / "activate"


def setup_venv(venv_type: Literal["cad", "led"]) -> None:
    """Set up a specific virtual environment"""
    print(f"Setting up {venv_type} virtual environment...")
    venv_path = get_venv_path(venv_type)

    if not venv_path.exists():
        venv.create(venv_path, with_pip=True)

    # Install base package in editable mode with appropriate extras
    activate_script = get_venv_activate(venv_type)
    if sys.platform == "win32":
        pip_command = f'"{activate_script}" && pip install -e ".[{venv_type}]"'
    else:
        pip_command = f'. "{activate_script}" && pip install -e ".[{venv_type}]"'

    run_command(pip_command)
    print(f"{venv_type.upper()} environment setup complete!")


def generate_cad(mode: str = "") -> None:
    print("Setting up CAD environment...")
    setup_venv("cad")

    print("Generating CAD files...")
    activate_script = get_venv_activate("cad")
    if sys.platform == "win32":
        cmd = f'"{activate_script}" && python cad/led-scales.py {mode}'
    else:
        cmd = f'. "{activate_script}" && python cad/led-scales.py {mode}'

    run_command(cmd)
    print("CAD generation complete! Files can be found in the cad/out directory")


def run_leds(mode: ConfigMode, mock: bool = False, debug: bool = False) -> None:
    print("Setting up LED environment...")
    setup_venv("led")

    print("Running LED implementation...")
    activate_script = get_venv_activate("led")
    flags: List[str] = [mode.value]
    if mock:
        flags.append("--mock")
    if debug:
        flags.append("--debug")
    flags_str = " ".join(flags)

    if sys.platform == "win32":
        cmd = f'"{activate_script}" && python -m leds.leds {flags_str}'
    else:
        cmd = f'. "{activate_script}" && python -m leds.leds {flags_str}'
    run_command(cmd)

def install_leds(mode: ConfigMode) -> None:
    print("Installing LEDs service")

    if platform.system() != "Linux":
        print("Only supported on linux")
        sys.exit(1)

    if os.geteuid() != 0: # type: ignore pylint: disable=no-member
        print("Run this as root")
        sys.exit(1)

    service_name = "leds"
    service_dir = Path("/etc/systemd/system")
    target_path = service_dir / (service_name + ".service")

    # Read source file
    source_path = Path("./leds/scripts/leds.service")
    try:
        content = source_path.read_text("utf-8")
    except FileNotFoundError:
        print(f"Source file {source_path} does not exist.")
        return

    # Replace {mode} placeholder
    cwd = str(Path(__file__).parent.resolve())
    content = content.replace("{mode}", mode)
    content = content.replace("{cwd}", cwd)

    # Ensure /etc/systemd/system exists
    service_dir.mkdir(parents=True, exist_ok=True)

    # Write modified service file
    try:
        target_path.write_text(content)
        print(f"Installed service file to {target_path}")
    except PermissionError:
        print(f"Permission denied: run with sudo to write to {target_path}")
        return

    # Print instructions for the user
    print("\nYou can now manage the service using systemctl:")
    print("  sudo systemctl daemon-reload")
    print(f"  sudo systemctl enable {service_name}")
    print(f"  sudo systemctl start {service_name}")
    print(f"  sudo systemctl status {service_name}")
    print(f"  sudo systemctl stop {service_name}")
    print(f"  sudo systemctl disable {service_name}")

def clean() -> None:
    print("Cleaning up...")
    paths_to_clean = [
        "__pycache__",
        "cad/__pycache__",
        "venv-cad",
        "venv-led",
        "cad/out",
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


def lint() -> None:
    """Run pylint on the codebase"""
    print("Setting up CAD environment for linting...")
    setup_venv("cad")  # CAD environment has pylint

    print("Running pylint...")
    python_exe = get_venv_python("cad")
    cmd = f'"{python_exe}" -m pylint --rcfile=.pylintrc leds/ cad/ main.py config.py'
    run_command(cmd)


def format_code() -> None:
    """Format the codebase using Black"""
    print("Setting up CAD environment for formatting...")
    setup_venv("cad")  # CAD environment has black

    print("Running Black formatter...")
    python_exe = get_venv_python("cad")
    cmd = f'"{python_exe}" -m black leds/ cad/ main.py config.py setup.py'
    run_command(cmd)


def configure_led_order() -> None:
    """Run the LED order configuration tool"""
    print("Setting up LED environment...")
    setup_venv("led")

    print("Running LED order configuration tool...")
    python_exe = get_venv_python("led")
    cmd = f'"{python_exe}" leds/scripts/configure_led_order.py'
    run_command(cmd)


def print_help() -> None:
    print("LED Scales CAD Generator:")
    print(
        "  python main.py setup                   - Set up both development environments"
    )
    print(
        "  python main.py generate                - Generate CAD files (default mode)"
    )
    print(
        "  python main.py 3d                      - Generate 3D printable STL files for the scales"
    )
    print(
        "  python main.py 2d                      - Generate 2D SVG files for laser cutting/CNC"
    )
    print(
        "  python main.py clean                   - Clean up generated files and environments"
    )
    print("  python main.py all                     - Generate all needed files")
    print("  python main.py help                    - Show this help message")
    print("  python main.py install-leds <mode>     - Install LEDs as systemd service")
    print("  python main.py leds <mode>             - Run the LED implementation")
    print(
        "  python main.py leds-mock <mode>        - Run the LED implementation in mock mode"
    )
    print(
        "  python main.py leds-debug <mode>       - Run the LED implementation with debug output (FPS)"
    )
    print(
        "  python main.py leds-mock-debug <mode>  - Run the LED implementation in mock mode with debug output"
    )
    print(
        "  python main.py dev                     - Run the server in development mode with auto-reload"
    )
    print("  python main.py lint                    - Run pylint on the codebase")
    print("  python main.py format                  - Format the codebase using Black")
    print(
        "  python main.py configure-leds          - Configure LED ordering for hexagon layout"
    )
    print("\nOutput files will be generated in the cad/out directory")
    print("  - 3D files: cad/out/tiles/")
    print("  - 2D files: cad/out/panels/")


def dev() -> None:
    """Run the server in development mode with auto-reload"""
    print("Setting up LED environment...")
    setup_venv("led")

    print("Starting development server with auto-reload...")

    try:
        # Only import watchdog when needed
        from watchdog.observers import (  # pylint: disable=import-outside-toplevel
            Observer,
        )
        from watchdog.events import (  # pylint: disable=import-outside-toplevel
            FileSystemEventHandler,
            FileSystemEvent,
        )

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

                # Use python from venv
                python_executable = get_venv_python("led")

                cmd = [python_executable, "-m", "leds.leds", "--mock"]
                self.process = subprocess.Popen(  # pylint: disable=consider-using-with
                    cmd, start_new_session=sys.platform != "win32"
                )

            def stop_process(self):
                if self.process:
                    try:
                        if sys.platform == "win32":
                            subprocess.run(
                                ["taskkill", "/F", "/T", "/PID", str(self.process.pid)],
                                check=False,
                            )
                        else:
                            if hasattr(os, "killpg"):
                                pgid = os.getpgid(self.process.pid)
                                os.killpg(pgid, signal.SIGTERM)
                            else:
                                self.process.terminate()
                    except (ProcessLookupError, subprocess.TimeoutExpired):
                        # Process already terminated or timeout waiting for it
                        pass
                    except Exception as e:
                        print(f"Warning: Failed to stop process: {e}")
                    finally:
                        self.process = None

            def on_modified(self, event: FileSystemEvent) -> None:
                if not event.is_directory and (
                    str(event.src_path).endswith(".py")
                    or str(event.src_path).endswith(".js")
                ):
                    current_time = time.time()
                    if current_time - self.last_restart > self.cooldown:
                        self.last_restart = current_time
                        print("\nRestarting server due to file change...")
                        self.start_process()

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

    except ImportError:
        print("Error: watchdog package is not installed.")
        print(
            "Please run 'python main.py setup' first to set up the virtual environment and source it."
        )
        print("This will install all required dependencies including watchdog.")
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_help()
        sys.exit(1)

    command = sys.argv[1]

    def get_mode() -> ConfigMode:
        mode = sys.argv[2] if len(sys.argv) > 2 else None
        if not mode or mode not in list(ConfigMode):
            print(
                "Please pass a valid config mode. Should be one of",
                list(map(lambda x: x.value, list(ConfigMode))),
            )
            sys.exit(1)
        return ConfigMode(mode)

    if command == "setup":
        setup_venv("cad")
        setup_venv("led")
    elif command == "generate":
        generate_cad()
    elif command == "2d":
        generate_cad("--2d")
    elif command == "3d":
        generate_cad("--3d")
    elif command == "clean":
        clean()
    elif command == "help":
        print_help()
    elif command == "install-leds":
        install_leds(get_mode())
    elif command == "leds":
        run_leds(get_mode())
    elif command == "leds-mock":
        run_leds(get_mode(), True)
    elif command == "leds-debug":
        run_leds(get_mode(), debug=True)
    elif command == "leds-mock-debug":
        run_leds(get_mode(), True, True)
    elif command == "dev":
        dev()  # New development mode with auto-reload
    elif command == "lint":
        lint()  # New lint command
    elif command == "format":
        format_code()  # New format command
    elif command == "configure-leds":
        configure_led_order()  # New LED configuration command
    elif command == "all":
        print("Generating 3D print files...")
        generate_cad("--3d")
        print("Generating 2D files...")
        generate_cad("--2d")
        print(
            "STL files can be found in cad/out/tiles/. Slice and print these with your 3D printer."
        )
        print(
            "SVG files can be found in cad/out/panels. Have these printed out on paper."
        )
        print(
            "Order the panels based on the provided panel count and dimensions. Put the paper over it. Drill marked holes for the LEDs and put the printed scales on the marked positions. Use cad/out/led-scales-py.positioning.scad to map printed scales to the panels."
        )
        print("Done!")
    else:
        print(f"Unknown command: {command}")
        print_help()
        sys.exit(1)
