"""Shell activation helpers and sudo shim."""

import os
import shutil
import stat
from pathlib import Path


def get_activation_script():
    return r'''VIRTSUDO_ACTIVE=1
export VIRTSUDO_ACTIVE

_virtsudo_sudo() {
    local overwrite=0
    local passthru_args=()

    for arg in "$@"; do
        if [ "$arg" = "--overwrite" ]; then
            overwrite=1
        elif [ "$arg" = "--help" ]; then
            command virtsudo help-sudo
            return 0
        else
            passthru_args+=("$arg")
        fi
    done

    if [ "$overwrite" -eq 1 ]; then
        exec /usr/bin/sudo "${passthru_args[@]}"
    else
        exec virtsudo exec "${passthru_args[@]}"
    fi
}

alias sudo='_virtsudo_sudo'
'''


_DEACTIVATE = r'''if [ -n "${VIRTSUDO_ACTIVE}" ]; then
    unalias sudo 2>/dev/null
    unset VIRTSUDO_ACTIVE
fi
'''


def activate_hook_path():
    return Path.home() / ".local" / "share" / "virtsudo" / "activate"


def write_activation_script():
    p = activate_hook_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(get_activation_script())
    p.chmod(p.stat().st_mode | stat.S_IXUSR)
    return p


def get_bin_dir():
    return Path.home() / ".local" / "bin"


def install_sudo_shim():
    bindir = get_bin_dir()
    bindir.mkdir(parents=True, exist_ok=True)
    shim = bindir / "sudo"

    content = r'''#!/bin/sh
# virtsudo shim — routes sudo to virtsudo exec
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
        exec /usr/bin/sudo "${args[@]}"
    else
        exec virtsudo exec "${args[@]}"
    fi
}
_parse "$@"
'''
    shim.write_text(content)
    shim.chmod(stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
