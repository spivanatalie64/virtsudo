# virtsudo

**Virtual sudo — run `sudo` commands inside an isolated container.**

virtsudo is a transparent `sudo` replacement that executes privileged commands inside a
container (podman or docker) instead of on your host. Think of it like `venv` for `sudo` —
your CWD is bind-mounted into the container so file output lands on your host, but system
packages install into the container's own filesystem, isolated from the host.

No password prompts. No host contamination.

---

## How it works

1. virtsudo detects whether **podman** or **docker** is available, and detects your host OS
   from `/etc/os-release` to pull a matching container image (Arch, Ubuntu, Debian, Fedora).
2. It starts a persistent container named `virtsudo-env` mounting only your **current working
   directory** at the same path with `rslave`.
3. Commands run as **root** inside the container. System packages (via `apt`, `pacman`, etc.)
   install into the container's own layer — NOT the host. File writes to the CWD appear on
   the host immediately.
4. If you change directories between invocations, the container is automatically recreated
   with the new CWD mount.
5. Signals (Ctrl+C) are proxied into the container process via `--sig-proxy`.

---

## Installation

Requirements: **Python 3.10+**, **podman** or **docker** installed and running.

```bash
git clone https://github.com/spivanatalie64/virtsudo.git
cd virtsudo
pip install --user -e .
```

Or with the bundled installer (handles `--break-system-packages` automatically):

```bash
python install.py
```

Make sure `~/.local/bin` is in your `PATH`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

---

## Usage

### Activate (user mode — PATH shim)

```bash
eval "$(virtsudo activate-source)"
```

Add that to `~/.bashrc` for persistence. Then every `sudo` runs via the container:

```bash
sudo apt update
sudo make install
```

### Activate (system mode — replaces /usr/bin/sudo)

For full interposition (catches `command sudo` and `/usr/bin/sudo`), use `--system` as root:

```bash
sudo virtsudo activate --system
```

This renames `/usr/bin/sudo` to `/usr/bin/sudo.real` and installs the virtsudo shim in its
place. Deactivate with:

```bash
sudo virtsudo deactivate --system
```

### Use real sudo (bypass the container)

```bash
sudo --overwrite pacman -Syu
sudo --overwrite systemctl reboot
```

### Explicit container execution

```bash
virtsudo exec apt install htop
virtsudo exec make install
```

### Interactive container shell

```bash
virtsudo shell
```

### Status

```bash
virtsudo status
```

---

## Commands reference

| Command | Description |
|---|---|
| `sudo <cmd>` | Run in container (when activated) |
| `sudo --overwrite <cmd>` | Run with real host sudo |
| `virtsudo exec <cmd>` | Explicit container exec |
| `virtsudo activate` | User-mode activation (prints instructions) |
| `virtsudo activate --system` | System-mode: replaces `/usr/bin/sudo` (requires root) |
| `virtsudo deactivate` | User-mode deactivation |
| `virtsudo deactivate --system` | Restores `/usr/bin/sudo` from backup (requires root) |
| `virtsudo shell [shell]` | Interactive container shell |
| `virtsudo status` | Environment status |

---

## Container image

virtsudo uses **Arch Linux** (`archlinux:latest`) as the container image for all hosts.

---



## btrfs compatibility

If your root filesystem is btrfs, podman's `overlay` storage driver won't work. virtsudo
detects this and falls back to the **VFS** driver, which is slower but compatible. For
better performance on btrfs, install `fuse-overlayfs`.

---

## Development

```
virtsudo/
├── install.py                   # One-shot installer with pip fallback
├── pyproject.toml               # Build configuration
├── setup.py                     # (legacy)
├── README.md
└── virtsudo/
    ├── __init__.py
    ├── __main__.py              # python -m virtsudo
    ├── cli.py                   # CLI dispatch
    ├── container.py             # Runtime detection, lifecycle, exec
    └── utils/
        ├── __init__.py
        └── shell.py             # Activation scripts and sudo shim
```

---

## License

MIT
