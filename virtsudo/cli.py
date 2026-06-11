#!/usr/bin/env python3
"""virtsudo — CLI entry point and subcommand dispatch."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

from virtsudo import VERSION, PROJECT_NAME
from virtsudo.container import (
    exec_in_container,
    exec_interactive,
    start_container,
    check_available,
    CONTAINER_NAME,
    CONTAINER_IMAGE,
)
from virtsudo.utils.shell import (
    write_activation_script,
    get_bin_dir,
    install_sudo_shim,
)

USAGE = f"""{PROJECT_NAME} v{VERSION} — Virtual sudo environment inside a container

Usage:
    sudo <command> [args...]           Run command in container (when activated)
    sudo --overwrite <command>          Run command with REAL host sudo
    virtsudo exec <command> [args...]   Explicitly run in container
    virtsudo activate                   Activate the sudo override for this shell
    virtsudo activate --system          Replace /usr/bin/sudo with virtsudo shim
    virtsudo deactivate                 Deactivate the sudo override
    virtsudo deactivate --system        Restore /usr/bin/sudo from backup
    virtsudo shell [shell]              Interactive container shell
    virtsudo status                     Show environment status
    virtsudo help-sudo                  Print sudo usage for virtsudo
    eval "$(virtsudo activate-source)"  Source activation script
"""

SUDO_REAL = "/usr/bin/sudo.real"


def _install_system_shim():
    if os.geteuid() != 0:
        print("error: --system requires root", file=sys.stderr)
        sys.exit(1)
    real = Path(SUDO_REAL)
    sudo_bin = Path("/usr/bin/sudo")
    if not real.exists() and sudo_bin.exists():
        shutil.copy2(str(sudo_bin), str(real))
    shim_content = r'''#!/bin/sh
# virtsudo system shim — replaces /usr/bin/sudo
_parse() {
    local overwrite=0
    local args=()
    for arg in "$@"; do
        if [ "$arg" = "--overwrite" ]; then
            overwrite=1
        elif [ "$arg" = "--help" ]; then
            exec virtsudo help-sudo
        else
            args+=("$arg")
        fi
    done
    if [ "$overwrite" -eq 1 ]; then
        exec /usr/bin/sudo.real "${args[@]}"
    else
        exec virtsudo exec "${args[@]}"
    fi
}
_parse "$@"
'''
    sudo_bin.write_text(shim_content)
    sudo_bin.chmod(0o4755)


def cmd_activate(args):
    rt = check_available()
    start_container()
    system = "--system" in args
    if system:
        _install_system_shim()
        print("virtsudo: system sudo replaced at /usr/bin/sudo (original at /usr/bin/sudo.real)")
        return
    write_activation_script()
    install_sudo_shim()
    bindir = get_bin_dir()
    print(f"To activate virtsudo in your shell, run:")
    print(f"  eval \"$(virtsudo activate-source)\"")
    print(f"Or add {bindir} to your PATH and use 'sudo' directly.")


def cmd_activate_source(args):
    from virtsudo.utils.shell import get_activation_script
    print(get_activation_script())


def cmd_deactivate(args):
    system = "--system" in args
    if system:
        if os.geteuid() != 0:
            print("error: --system requires root", file=sys.stderr)
            sys.exit(1)
        real = Path(SUDO_REAL)
        sudo_bin = Path("/usr/bin/sudo")
        if real.exists():
            shutil.move(str(real), str(sudo_bin))
            sudo_bin.chmod(0o4755)
            print("virtsudo: /usr/bin/sudo restored from backup")
        else:
            print("virtsudo: no backup found at /usr/bin/sudo.real")
        return
    bindir = get_bin_dir()
    shim = bindir / "sudo"
    if shim.exists():
        shim.unlink()
    print("virtsudo deactivated. sudo will use the host's /usr/bin/sudo again.")


def cmd_exec(args):
    if not args:
        print("Usage: virtsudo exec <command> [args...]", file=sys.stderr)
        sys.exit(1)
    result = exec_in_container(args)
    sys.exit(result.returncode)


def cmd_shell(args):
    rt = check_available()
    start_container()
    shell = args[0] if args else os.environ.get("SHELL", "/bin/bash")
    exec_interactive(["env", "-i", f"TERM={os.environ.get('TERM','xterm-256color')}", "HOME=/root", shell])


def cmd_status(args):
    rt = check_available()
    start_container()

    result = exec_in_container(["cat", "/etc/os-release"], capture_output=True)
    os_info = "unknown"
    if result.returncode == 0:
        for line in result.stdout.decode().splitlines():
            if line.startswith("PRETTY_NAME="):
                os_info = line.split("=", 1)[1].strip('"')
                break

    active = os.environ.get("VIRTSUDO_ACTIVE") == "1"
    system_active = Path("/usr/bin/sudo.real").exists() and not Path("/usr/bin/sudo").resolve().samefile("/usr/bin/sudo.real")
    image_status = subprocess.run(
        [rt, "image", "exists", CONTAINER_IMAGE], capture_output=True
    ).returncode == 0
    ctr_exists = subprocess.run(
        [rt, "ps", "-a", "--filter", f"name={CONTAINER_NAME}",
         "--format", "{{.Names}}"],
        capture_output=True, text=True,
    ).stdout.strip()

    print(f"{PROJECT_NAME} v{VERSION}")
    print(f"  Runtime:           {rt}")
    print(f"  Image:             {CONTAINER_IMAGE}")
    print(f"  Image pulled:      {'yes' if image_status else 'no'}")
    print(f"  Container:         {CONTAINER_NAME}")
    print(f"  Container exists:  {'yes' if CONTAINER_NAME in ctr_exists else 'no'}")
    print(f"  Container OS:      {os_info}")
    print(f"  User-mode active:  {'yes' if active else 'no'}")
    print(f"  System-mode:       {'yes' if system_active else 'no'}")
    print(f"  Activation script: {write_activation_script()}")


def cmd_help_sudo(args):
    print(f"""{PROJECT_NAME} — sudo passthrough

When virtsudo is active, 'sudo' runs commands inside the container.

Options:
    --overwrite             Bypass the container and use the REAL host sudo.
                            Example: sudo --overwrite pacman -Syu

    --help                  Show this help.
""")


_cmds = {
    "activate": cmd_activate,
    "activate-source": cmd_activate_source,
    "deactivate": cmd_deactivate,
    "exec": cmd_exec,
    "shell": cmd_shell,
    "status": cmd_status,
    "info": cmd_status,
    "help-sudo": cmd_help_sudo,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in _cmds:
        print(USAGE, file=sys.stderr)
        sys.exit(1)

    _cmds[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    main()
