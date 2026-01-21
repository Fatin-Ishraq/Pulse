# ⚡ Pulse

> *"Not a dashboard. An instrument panel."*

**Pulse** is a cinematic, terminal-based system monitor built for enthusiasts who crave high-density telemetry with a premium aesthetic. Every panel animates; nothing is static. 

## ✨ Key Features

- **Transcendence Modes**: Fullscreen immersive views for every subsystem.
- **Neural Insight Engine**: Heuristic analysis of system bottlenecks.
- **Dynamic Theming**: Cycle through high-contrast palettes (Key: `T`).
- **High-Precision Pulse**: Up to 0.2s sampling rate for micro-stutter detection.
- **Modular Core**: High-performance architecture leveraging `psutil` and `Textual`.

## 🚀 Installation

### Full Potential (Recommended)
Get the **maximum performance** Rust engine automatically, no build tools required:

```bash
git clone https://github.com/Fatin-Ishraq/Pulse.git
cd Pulse

# Linux/Mac
chmod +x install.sh && ./install.sh

# Windows (PowerShell or CMD)
install.bat
```

Then run:
```bash
python -m pulse
```

### From Source (For Contributors)
If you have Rust installed and want to compile locally:
```bash
pip install .
python -m pulse
```

> [!NOTE]
> The bootstrap script automatically downloads pre-compiled binaries from GitHub Releases. If none are available for your system, it falls back to compiling from source.

## 🎮 Navigation & Controls

| Key | Action |
| --- | --- |
| `Q` | Kill Application |
| `T` | Cycle UI Theme |
| `H` | Toggle Help Overlay |
| `X` | Enter/Exit **Transcendence Mode** |
| `Tab` | Cycle Focused Subsystem |

### 🌀 Transcendence Interaction
When inside a full-screen panel:
- `M` — Toggle **View Mode** (Cinematic vs. Developer)
- `R` — Toggle **Sampling Rate** (Precision Pulse)
- `F` — Trigger **Optimization/Reset** (Panel-specific)
- `S` — Cycle **Scaling Mode** (Absolute vs. Auto)
