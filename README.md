# virtsudo

**Virtual sudo — run `sudo` commands inside an isolated container.**

virtsudo is a transparent `sudo` replacement that executes privileged commands inside a
container (podman or docker) instead of on your host. Think of it like `venv` for `sudo` —
all file output lands on your host filesystem (the container mounts `/` with `rslave`), but
the process itself runs in an isolated environment with no authentication required.

No more worrying about `sudo` commands messing with your main system. No more password prompts.

---

## How it works

1. virtsudo detects whether **podman** or **docker** is available on your system.
2. It starts a persistent Ubuntu 24.04 container named `virtsudo-env`.
3. The container mounts your entire host root filesystem (`/`) at `/` with `rslave`.
4. Commands run inside the container as **real root**, but are confined to the container's
   namespaces — your host kernel, services, and init system are untouched.
5. File output (installed packages, compiled binaries, config files) appears on the host
   immediately because the filesystem is shared.

The container runs `sleep infinity` in the background and reuses the same container across
commands, making repeated invocations fast.

---

## Installation

Requirements: **Python 3.10+**, **podman** or **docker** installed and running.

```bash
# Install from source
git clone https://github.com/spivanatalie64/virtsudo.git
cd virtsudo
pip install --user -e .
```

Or with the bundled installer:

```bash
python install.py --user
```

Make sure `~/.local/bin` is in your `PATH`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

---

## Usage

### Activate the virtual sudo

```bash
virtsudo activate
```

This prints instructions. The recommended way to activate for your current shell:

```bash
eval "$(virtsudo activate-source)"
```

Or, for a persistent activation, add that line to your `~/.bashrc` or `~/.zshrc`.

### Use sudo (containerized)

Once activated, every `sudo` command runs inside the container:

```bash
sudo apt update                   # runs in the container
sudo pacman -S neovim             # runs in the container
sudo make install                 # runs in the container
```

### Use real sudo (bypass the container)

If you ever need to run a command with the **real** host `sudo`, pass `--overwrite`:

```bash
sudo --overwrite pacman -Syu      # runs on the HOST with real sudo
sudo --overwrite systemctl reboot # runs on the HOST with real sudo
```

### Explicit container execution

You don't need to be in an activated shell to use the container:

```bash
virtsudo exec apt install htop
virtsudo exec make install
```

### Interactive container shell

```bash
virtsudo shell          # default shell (/bin/bash inside the container)
virtsudo shell zsh      # custom shell
```

### Check status

```bash
virtsudo status
```

### Deactivate

```bash
virtsudo deactivate
```

---

## Commands reference

| Command | Description |
|---|---|
| `sudo <cmd>` | Run command in the container (when activated) |
| `sudo --overwrite <cmd>` | Run with real host sudo (bypass container) |
| `virtsudo exec <cmd>` | Run command in container explicitly |
| `virtsudo activate` | Print activation instructions |
| `virtsudo activate-source` | Print shell source-able activation script |
| `virtsudo deactivate` | Remove the sudo shim |
| `virtsudo shell [shell]` | Interactive container shell |
| `virtsudo status` | Show environment status |
| `virtsudo help-sudo` | Show sudo-specific help |

---

## Development

### Setup

```bash
git clone https://github.com/spivanatalie64/virtsudo.git
cd virtsudo
pip install --user -e .
```

### Project structure

```
virtsudo/
├── install.py                   # One-shot installer
├── pyproject.toml               # Build configuration
├── setup.py                     # Setuptools config (legacy)
├── README.md                    # This file
└── virtsudo/
    ├── __init__.py              # Package metadata
    ├── __main__.py              # python -m virtsudo
    ├── cli.py                   # CLI dispatch and subcommands
    ├── container.py             # Container lifecycle (podman/docker)
    └── utils/
        ├── __init__.py
        └── shell.py             # Activation scripts and sudo shim
```

### Implementation details

- **`container.py`** — Auto-detects podman or docker, pulls the Ubuntu 24.04 image,
  manages the persistent `virtsudo-env` container, and provides `exec_in_container()`.
- **`cli.py`** — Dispatches subcommands (`exec`, `activate`, `deactivate`, `shell`, `status`).
  The `--overwrite` flag is stripped before passing commands to the container or to real sudo.
- **`utils/shell.py`** — Generates the shell activation script (aliases `sudo` to a wrapper)
  and installs a `sudo` shim binary in `~/.local/bin/` for non-interactive use.

### Testing

```bash
# After installation, ensure podman/docker is running
virtsudo status
virtsudo exec echo "hello from container"
virtsudo shell
```

---

## License

MIT
