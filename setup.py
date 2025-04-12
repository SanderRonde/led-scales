#!/usr/bin/env python3
import os
import sys
import subprocess
import venv
import signal
import threading
from pathlib import Path
from typing import Union, List, TextIO

def print_output(pipe: TextIO, prefix: str = "") -> None:
    for line in iter(pipe.readline, ''):
        if line.strip():  # Only print non-empty lines
            print(f"{prefix}{line.strip()}", flush=True)  # Force immediate output

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
        stdout_thread = threading.Thread(target=print_output, args=(process.stdout,))
        stderr_thread = threading.Thread(target=print_output, args=(process.stderr, "ERROR: "))
        
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
                        print(f"Error: Command failed with exit code {return_code}", flush=True)
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

def setup() -> None:
    print("Setting up virtual environment...")
    venv_path = Path("venv")
    
    if not venv_path.exists():
        venv.create(venv_path, with_pip=True)
    
    # Activate virtual environment and install requirements
    if sys.platform == "win32":
        activate_script = venv_path / "Scripts" / "activate.bat"
        pip_command = f'"{activate_script}" && pip install -r requirements.txt'
    else:
        activate_script = venv_path / "bin" / "activate"
        pip_command = f'. "{activate_script}" && pip install -r requirements.txt'
    
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
    print("  python setup.py help     - Show this help message")
    print("\nOutput files will be generated in the cad/out directory")
    print("  - 3D files: cad/out/tiles/")
    print("  - 2D files: cad/out/panels/")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        help()
        sys.exit(1)
    
    command = sys.argv[1]
    if command == "setup":
        setup()
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
    else:
        print(f"Unknown command: {command}")
        help()
        sys.exit(1) 