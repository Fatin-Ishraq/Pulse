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

### From Source (Hybrid Core)
The core engine leverages **Rust** for maximum performance. To build from source, you need the [Rust Toolchain](https://rustup.rs/) and [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) installed.

```bash
git clone https://github.com/Fatin-Ishraq/Pulse.git
cd Pulse
pip install .
```

### via PyPI (Stable)
```bash
pip install pulse-monitor
```

> [!NOTE]
> If Rust or Build Tools are missing, Pulse will automatically fallback to the pure-Python engine (`psutil`). It will remain fully functional, just slightly less optimized.

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
