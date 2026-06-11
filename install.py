#!/usr/bin/env python3
"""One-shot installer for virtsudo.

Usage:
    python install.py [--user]
"""

import subprocess
import sys
from pathlib import Path


def _pip_install(here):
    base = [sys.executable, "-m", "pip", "install", "--upgrade"]
    strategies = [
        ["--user", "--break-system-packages"],
        ["--user"],
        [],
    ]
    for flags in strategies:
        cmd = base + flags + [str(here)]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode == 0:
            return
    print("error: all pip install strategies failed", file=sys.stderr)
    print(f"last attempt stderr: {result.stderr.decode()}", file=sys.stderr)
    sys.exit(1)


def main():
    here = Path(__file__).resolve().parent
    virtsudo_pkg = here / "virtsudo"

    if not virtsudo_pkg.is_dir():
        print("Error: virtsudo/ package not found alongside installer.", file=sys.stderr)
        sys.exit(1)

    _pip_install(here)

    from virtsudo.utils.shell import write_activation_script, get_bin_dir, install_sudo_shim
    write_activation_script()
    install_sudo_shim()

    bindir = get_bin_dir()
    print(f"virtsudo installed.")
    print(f"Run 'virtsudo activate' to start the virtual sudo environment.")
    print(f"Make sure {bindir} is in your PATH.")


if __name__ == "__main__":
    main()
