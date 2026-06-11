#!/usr/bin/env python3
"""One-shot installer for virtsudo.

Usage:
    python install.py [--user]
"""

import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path


def main():
    install_user = "--user" in sys.argv

    here = Path(__file__).resolve().parent
    virtsudo_pkg = here / "virtsudo"

    if not virtsudo_pkg.is_dir():
        print("Error: virtsudo/ package not found alongside installer.", file=sys.stderr)
        sys.exit(1)

    # Install the Python package
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "--upgrade"] +
        (["--user"] if install_user else []) +
        [str(here)]
    )

    # Write the activation script
    site_packages = Path(
        subprocess.run(
            [sys.executable, "-c",
             "import site; print(site.getsitepackages()[0] if not __import__('sys').argv[1:] else site.USER_SITE)"],
            capture_output=True, text=True,
        ).stdout.strip()
    )

    from virtsudo.utils.shell import write_activation_script, get_bin_dir, install_sudo_shim
    write_activation_script()
    install_sudo_shim()

    bindir = get_bin_dir()
    print(f"virtsudo installed.")
    print(f"Run 'virtsudo activate' to start the virtual sudo environment.")
    print(f"Make sure {bindir} is in your PATH.")


if __name__ == "__main__":
    main()
