"""Container runtime detection, lifecycle, and command execution."""

import os
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path

_RUNTIME = None
_PREBUILT = False
_LAST_CWD = None

CONTAINER_NAME = "virtsudo-env"

_VIRTSUDO_STORAGE = None

CONTAINER_IMAGE = "docker.io/library/archlinux:latest"


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


def _probe_btrfs_overlay(rt):
    result = subprocess.run([rt, "info"], capture_output=True, text=True)
    if result.returncode == 0:
        return True
    if "backing file system is unsupported for this graph driver" not in result.stderr:
        return False

    global _VIRTSUDO_STORAGE
    storage_dir = Path(tempfile.mkdtemp(prefix="virtsudo-storage-"))
    storage_dir.chmod(storage_dir.stat().st_mode | stat.S_IRWXU)
    conf_dir = Path.home() / ".config" / "containers"
    conf_dir.mkdir(parents=True, exist_ok=True)
    storage_conf = conf_dir / "storage.conf"
    if not storage_conf.exists():
        storage_conf.write_text(
            f"[storage]\n"
            f"driver = \"vfs\"\n"
            f"graphroot = \"{storage_dir}\"\n"
            f"runroot = \"{storage_dir}/run\"\n"
        )
        _VIRTSUDO_STORAGE = storage_dir
        db_file = Path.home() / ".local" / "share" / "containers" / "storage" / "db.sql"
        if db_file.exists():
            db_file.unlink()
    result2 = subprocess.run([rt, "info"], capture_output=True, text=True)
    if result2.returncode == 0:
        return True
    raise RuntimeError(
        f"btrfs filesystem detected — podman overlay is unsupported. "
        f"Set up a non-btrfs graphroot or install fuse-overlayfs.\n"
        f"VFS fallback also failed at {storage_dir}."
    )


def check_available():
    rt = detect_runtime()
    if _probe_btrfs_overlay(rt):
        return rt
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


def _get_mounted_cwd(rt):
    result = subprocess.run(
        [rt, "inspect", CONTAINER_NAME, "--format", "{{range .Mounts}}{{.Source}}{{end}}"],
        capture_output=True, text=True,
    )
    return result.stdout.strip()


def start_container():
    global _LAST_CWD
    rt = check_available()
    ensure_image()
    cwd = os.getcwd()
    _LAST_CWD = cwd

    if container_exists(rt):
        mounted = _get_mounted_cwd(rt)
        if mounted != cwd:
            subprocess.run([rt, "rm", "-f", CONTAINER_NAME],
                           capture_output=True, check=False)
            _PREBUILT = False
        else:
            result = subprocess.run(
                [rt, "inspect", CONTAINER_NAME, "--format", "{{.State.Status}}"],
                capture_output=True, text=True,
            )
            status = result.stdout.strip()
            if status == "running":
                return
            subprocess.run([rt, "start", CONTAINER_NAME], check=True)
            return

    subprocess.run(
        [
            rt, "run", "-d", "--name", CONTAINER_NAME,
            "--network=host",
            "-v", f"{cwd}:{cwd}:rslave",
            CONTAINER_IMAGE,
            "sleep", "infinity",
        ],
        check=True,
    )


def exec_in_container(cmd, capture_output=False):
    rt = check_available()
    start_container()
    cwd = os.getcwd()
    kwargs = {}
    if capture_output:
        kwargs["capture_output"] = True
    return subprocess.run(
        [rt, "exec", "-i", "-u", "0", "-w", cwd, CONTAINER_NAME] + cmd,
        **kwargs,
    )


def exec_interactive(cmd):
    rt = check_available()
    start_container()
    cwd = os.getcwd()
    return subprocess.run(
        [rt, "exec", "-it", "-u", "0", "-w", cwd, CONTAINER_NAME] + cmd,
    )
