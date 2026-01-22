# Pulse - Cinematic Terminal System Monitor

## Project Overview
**Pulse** is a high-fidelity, cinematic system monitor for the terminal, designed with a "sci-fi" aesthetic. It provides real-time telemetry for CPU, Memory, Disk, Network, and Processes using a smooth, animated TUI (Terminal User Interface).

**Key Features:**
- **Direct OS Engine:** Optimized for performance using native APIs via `psutil`.
- **Cinematic UI:** Built with [Textual](https://textual.textualize.io/), featuring animations and glassmorphism.
- **Transcendence Mode:** Deep-dive views into specific subsystems.
- **Theming:** Multiple built-in color palettes.

## Technology Stack
- **Language:** Python 3.10+
- **UI Framework:** [Textual](https://textual.textualize.io/) (>=2.0.0)
- **Formatting:** [Rich](https://github.com/Textualize/rich) (>=13.0.0)
- **System Metrics:** [Psutil](https://github.com/giampaolo/psutil) (>=5.9.0)
- **Build System:** Hatchling

## Development Setup

### Installation
1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Fatin-Ishraq/Pulse.git
    cd Pulse
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    python -m venv .venv
    # Windows:
    .venv\Scripts\activate
    # macOS/Linux:
    source .venv/bin/activate
    ```

3.  **Install dependencies in editable mode:**
    ```bash
    pip install -e .
    ```

### Running the Application
*   **Via Command Line:**
    ```bash
    pulse
    ```
*   **Via Python Module:**
    ```bash
    python -m pulse
    ```

## Architecture & Directory Structure

- **`src/pulse/`**: Main application package.
    - **`app.py`**: The entry point and main `App` class definition. Sets up the UI layout and screens.
    - **`core.py`**: Core application logic and utilities.
    - **`themes.py` & `themes.tcss`**: Theme definitions and Textual CSS styles.
    - **`panels/`**: Contains individual widgets for system monitoring.
        - **`base.py`**: Base `Panel` class that all other panels inherit from.
        - **`cpu.py`, `memory.py`, `network.py`, etc.**: Specific implementations for each metric.
    - **`screens/`**: Defines different application views.
        - **`boot.py`**: Initial loading sequence.
        - **`main_view.py`**: The primary dashboard layout.
        - **`immersive.py`**: Detailed "Transcendence" view.

## Coding Conventions
- **UI Components:** All dashboard widgets should inherit from `pulse.panels.base.Panel`.
- **Styling:** Use `src/pulse/themes.tcss` for defining styles. Keep logic separate from presentation where possible.
- **Type Hinting:** Use standard Python type hints strictly.
- **Async:** Textual is async-first; ensure UI updates and heavy IO are handled appropriately (e.g., using `work` decorators or async methods).
