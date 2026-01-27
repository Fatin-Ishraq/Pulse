# ⚡ P U L S E

> *"Not a dashboard. An instrument panel."*

**Pulse** is a cinematic, terminal-based system monitor built for enthusiasts who crave high-density telemetry with a premium aesthetic. Every panel animates; nothing is static. 

Built with the **Direct OS Engine**, Pulse communicates directly with your kernel for high-performance metrics with near-zero overhead.

---

## ✨ Features

- **Direct OS Engine**: High-performance architecture using native OS APIs. No Rust, no complex build tools—just pure, optimized Python.
- **Transcendence mode**: Hit `X` on any focused subsystem to enter an immersive, high-detail view.
- **Neural Insight Engine**: Real-time heuristic analysis of system bottlenecks and resource leaks.
- **Cinematic UI**: Smooth animations, glassmorphism-inspired transparency, and curated color palettes.
- **High-Precision Pulse**: Configurable sampling rates down to 0.2s for micro-stutter detection.

---

## 🚀 Installation

Install directly from PyPI:

```bash
pip install pulse-monitor
```

Then launch from anywhere:

```bash
pulse
```

---

## 🎮 Navigation & Tactical Controls

| Key | Tactical Action |
| --- | --- |
| `Q` | Kill Application Interlock |
| `T` | Cycle UI Theme Palettes |
| `Tab` | Shift Tactical Focus (Forward) |
| `Shift+Tab`| Shift Tactical Focus (Backward) |
| `Arrow Keys`| Spatial Navigation Grid |
| `X` | Enter/Exit **Transcendence View** |
| `F` | Toggle **Data Freeze** (Cryo-lock) |
| `?` / `H` | Toggle Tactical Overlay (Help) |

### 🌀 Transcendence Interaction
When inside a full-screen panel:
- `M` — Toggle **View Mode** (Cinematic vs. Developer)
- `R` — Toggle **Sampling Rate** (Precision Pulse)
- `S` — Cycle **Scaling Mode** (Absolute vs. Auto)
- `Esc` — Return to Master View

---

## 💎 Theming
Pulse comes with 6 curated high-contrast themes to match your terminal's vibe:
`Nord` • `Dracula` • `Monokai` • `Dark` • `Solarized` • `Gruvbox`

---

## 🚀 Release Process

This project uses automated PyPI publishing via GitHub Actions:

1. **Generate PyPI Token**: Create an API token on PyPI (Account Settings → API Tokens)
2. **Add to GitHub**: Add the token as `PYPI_API_TOKEN` to your repository secrets
3. **Release**: Tag and push to trigger publishing:
   ```bash
   git tag v0.3.3
   git push origin v0.3.3
   ```

The workflow automatically builds and publishes when a tag starting with `v` is pushed.

---

## 📜 License
MIT © [Fatin Ishraq](https://github.com/Fatin-Ishraq)
