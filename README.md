# ⚡ P U L S E

> *"Not a dashboard. An instrument panel."*

**Pulse** is a terminal system monitor for people who want high-density telemetry with a bit of style. Built on [Textual](https://textual.textualize.io/) and [psutil](https://github.com/giampaolo/psutil).

---

## ✨ Features

- **Live telemetry** for CPU, memory, disk I/O, storage, network, and processes.
- **Transcendence mode** — press `X` on any focused panel for a full-screen, interactive view.
- **Process and container control** — terminate, renice, and manage Docker containers. Every destructive action confirms first and names its exact target.
- **Six themes** — Nord, Dracula, Monokai, Dark, Solarized, Gruvbox. Your choice is remembered.
- **Configurable refresh rate**, from 0.1s for micro-stutter hunting to 60s for a background glance.

### How metrics are collected

On Linux, Pulse reads `/proc` directly and computes its own CPU and per-process deltas. On Windows it uses `GlobalMemoryStatusEx` for memory and psutil elsewhere; on macOS and other platforms it uses psutil throughout. psutil is a dependency on every platform.

---

## 🚀 Installation

```bash
pip install pulse-monitor
```

Then launch from anywhere:

```bash
pulse
```

Docker container monitoring is optional, because access to the Docker socket is root-equivalent on the host:

```bash
pip install "pulse-monitor[docker]"
```

---

## 🎮 Controls

| Key | Action |
| --- | --- |
| `Q` | Quit |
| `T` | Cycle theme |
| `Tab` / `Shift+Tab` | Focus next / previous panel |
| `Arrow Keys` | Move focus around the grid |
| `X` | Enter / exit **Transcendence** view |
| `F` | Freeze updates |
| `?` / `H` | Help overlay |

### Inside Transcendence

| Key | Action |
| --- | --- |
| `P` | Toggle sampling precision |
| `S` | Cycle scaling mode |
| `Esc` | Back to the grid |

### Process and container actions

| Key | Action |
| --- | --- |
| `K` | Terminate the selected process (asks first) |
| `+` / `-` | Lower / raise priority |
| `C` / `M` | Sort processes by CPU / memory |
| `S` / `K` / `R` | Docker: start / stop / restart the selected container (asks first) |

Pulse will not act on processes where a mistake takes down your session: itself, its parent shell, PID 1 or the session leader on POSIX, and the reserved Windows system PIDs. It never escalates privileges on its own — if a kill is denied, it says so and offers a force kill as a separate, explicit choice.

---

## ⚙️ Configuration

Config lives at `%APPDATA%\pulse\config.toml` on Windows, `$XDG_CONFIG_HOME/pulse/config.toml` (usually `~/.config/pulse/`) elsewhere.

```toml
[ui]
theme = "nord"        # nord | dracula | monokai | textual-dark | solarized-dark | gruvbox

[core]
refresh_rate = 1.0    # seconds, clamped to 0.1 - 60.0
```

Unknown or out-of-range values fall back to the defaults rather than breaking startup.

---

## 🛠️ Development

```bash
git clone https://github.com/Fatin-Ishraq/Pulse.git
cd Pulse
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[test]"
pytest
```

Run it from the source tree with `pulse` or `python -m pulse`.

---

## 🚀 Release Process

Publishing to PyPI uses GitHub Actions with **Trusted Publishing** — no API tokens in secrets.

1. Bump `__version__` in `src/pulse/__init__.py` (the package version is read from there).
2. Update `CHANGELOG.md`.
3. Confirm CI is green on `main` — the Linux job is the one that matters.
4. Tag and push:
   ```bash
   git tag v0.5.0
   git push origin v0.5.0
   ```

The tag must match the version in `__init__.py`. PyPI will not accept a version
number twice, so a mismatched tag burns that version permanently.

---

## 📜 License
MIT © [Fatin Ishraq](https://github.com/Fatin-Ishraq)
