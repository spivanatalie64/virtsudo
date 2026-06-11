#!/usr/bin/env python3
"""virtsudo — CLI entry point and subcommand dispatch."""

import os
import subprocess
import sys

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
    virtsudo deactivate                 Deactivate the sudo override
    virtsudo shell [shell]              Interactive container shell
    virtsudo status                     Show environment status
    virtsudo help-sudo                  Print sudo usage for virtsudo
    eval "$(virtsudo activate-source)"  Source activation script
"""


def cmd_activate(args):
    rt = check_available()
    start_container()
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

    result = exec_in_container(["cat", "/etc/os-release"])
    os_info = "unknown"
    if result.returncode == 0:
        for line in result.stdout.decode().splitlines():
            if line.startswith("PRETTY_NAME="):
                os_info = line.split("=", 1)[1].strip('"')
                break

    active = os.environ.get("VIRTSUDO_ACTIVE") == "1"
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
    if image_status:
        print(f"  Image pulled:      yes")
    else:
        print(f"  Image pulled:      no")
    print(f"  Container:         {CONTAINER_NAME}")
    print(f"  Container exists:  {'yes' if CONTAINER_NAME in ctr_exists else 'no'}")
    print(f"  Container OS:      {os_info}")
    print(f"  Virtual sudo:      {'ACTIVE' if active else 'inactive'}")
    print(f"  Activation script: {write_activation_script()}")


def cmd_help_sudo(args):
    print(f"""{PROJECT_NAME} — sudo passthrough

When virtsudo is active, 'sudo' runs commands inside the container.

Options:
    --overwrite             Bypass the container and use the REAL host sudo.
                            Example: sudo --overwrite pacman -Syu

    --help                  Show this help.

Note: All other flags and arguments are forwarded to the container.
      The container has the host filesystem mounted, so file output
      appears on your host immediately.
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
