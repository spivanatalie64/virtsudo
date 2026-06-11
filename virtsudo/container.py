"""Container runtime detection, lifecycle, and command execution."""

import os
import shutil
import subprocess
from pathlib import Path

_RUNTIME = None
_PREBUILT = False

CONTAINER_IMAGE = "docker.io/library/ubuntu:24.04"
CONTAINER_NAME = "virtsudo-env"


def detect_runtime():
    global _RUNTIME
    if _RUNTIME:
        return _RUNTIME
    for exe in ("podman", "docker"):
        if shutil.which(exe):
            _RUNTIME = exe
            return exe
    raise RuntimeError(
        "No container runtime found. Install podman or docker."
    )


def check_available():
    rt = detect_runtime()
    try:
        subprocess.run([rt, "info"], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        raise RuntimeError(f"{rt} is installed but not running.")
    return rt


def ensure_image():
    global _PREBUILT
    if _PREBUILT:
        return
    rt = check_available()
    result = subprocess.run(
        [rt, "image", "exists", CONTAINER_IMAGE], capture_output=True
    )
    if result.returncode != 0:
        print(f"Pulling {CONTAINER_IMAGE} ...")
        subprocess.run([rt, "pull", CONTAINER_IMAGE], check=True)
    _PREBUILT = True


def container_exists(rt):
    result = subprocess.run(
        [rt, "ps", "-a", "--filter", f"name={CONTAINER_NAME}",
         "--format", "{{.Names}}"],
        capture_output=True, text=True,
    )
    return CONTAINER_NAME in result.stdout.strip().splitlines()


def start_container():
    rt = check_available()
    ensure_image()
    if container_exists(rt):
        result = subprocess.run(
            [rt, "inspect", CONTAINER_NAME, "--format", "{{.State.Status}}"],
            capture_output=True, text=True,
        )
        status = result.stdout.strip()
        if status == "running":
            return
        subprocess.run([rt, "start", CONTAINER_NAME], check=True)
        return
    host_root = Path("/")
    subprocess.run(
        [
            rt, "run", "-d", "--name", CONTAINER_NAME,
            "--userns=keep-id",
            "-v", f"{host_root}:{host_root}:rslave",
            "-w", os.getcwd(),
            CONTAINER_IMAGE,
            "sleep", "infinity",
        ],
        check=True,
    )


def exec_in_container(cmd):
    rt = check_available()
    start_container()
    return subprocess.run([rt, "exec", "-i", CONTAINER_NAME] + cmd)


def exec_interactive(cmd):
    rt = check_available()
    start_container()
    return subprocess.run([rt, "exec", "-it", CONTAINER_NAME] + cmd)
