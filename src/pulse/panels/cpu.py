from rich.text import Text

from pulse.panels.base import Panel
from pulse.ui_utils import value_to_spark, value_to_heat_color, make_bar

from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Button


class CPUPanel(Panel):
    """Shows CPU core heat blocks with real data."""

    PANEL_NAME = "CPU"

    BINDINGS = [
        ("k", "kill_process", "Kill Top Process"),
        ("plus", "renice_up", "Lower Priority"),
        ("minus", "renice_down", "Higher Priority"),
    ]

    def __init__(self):
        super().__init__("CPU CORES", "", id="cpu-panel")

        # Transcendence Control States
        self.sampling_rate = 1.0
        self.view_mode = "developer"  # cinematic / developer
        self.scaling_mode = "absolute"  # absolute / relative
        # The heaviest process currently on display. Actions name it explicitly
        # and confirm before touching it - see Panel.request_kill.
        self.top_pid = None

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_kill_process(self):
        """Terminate the displayed top process, after confirmation."""
        self.request_kill(self.top_pid)

    def action_renice_up(self):
        """Increase nice value (lower priority)."""
        self.request_renice(self.top_pid, 1)

    def action_renice_down(self):
        """Decrease nice value (higher priority)."""
        self.request_renice(self.top_pid, -1)

    def on_button_pressed(self, event: Button.Pressed):
        """Handle process control buttons."""
        if event.button.id == "btn-kill":
            self.request_kill(self.top_pid)
        elif event.button.id == "btn-renice-up":
            self.request_renice(self.top_pid, 1)
        elif event.button.id == "btn-renice-down":
            self.request_renice(self.top_pid, -1)

    # ------------------------------------------------------------------
    # Summary view
    # ------------------------------------------------------------------
    def update_data(self):
        snapshot = self.snapshot
        if snapshot is None:
            self.update(self.waiting_text())
            return

        cpu = snapshot.cpu

        text = Text()
        text.append("CPU ", style="cyan")
        for index, percent in enumerate(cpu.per_core):
            color = value_to_heat_color(percent)
            block = "█" if percent > 50 else "▓" if percent > 25 else "░"
            text.append(block, style=color)
            # Wrap every 8 cores for cleaner sidebar fit
            if (index + 1) % 8 == 0:
                text.append("\n    ")
            elif (index + 1) % 4 == 0:
                text.append(" ")

        average = cpu.percent
        text.append(f"\n{average:.0f}% avg", style=value_to_heat_color(average))
        self.update(text)

        # Critical Alert
        if average > 90:
            self.add_class("alarm")
            self.border_title = "CPU CRITICAL"
        else:
            self.remove_class("alarm")
            self.border_title = "CPU CORES"

    # ------------------------------------------------------------------
    # Transcendence
    # ------------------------------------------------------------------
    def compose_transcendence(self):
        """Compose the interactive Core Management Console."""
        with Container(id="cpu-transcendence-layout"):
            with Horizontal(classes="header-section"):
                yield Static(id="cpu-hero-header")

            with Container(classes="core-section"):
                yield Static("CORE ARCHITECTURE", classes="section-title")
                yield Static(id="cpu-core-grid")

            with Container(classes="process-section"):
                yield Static("TOP OFFENDER ANALYSIS", classes="section-title")
                with Horizontal(id="process-control-box"):
                    yield Static(id="top-process-info", classes="process-info")
                    with Vertical(id="process-actions"):
                        yield Button("KILL PID [K]", id="btn-kill", variant="error")
                        with Horizontal():
                            yield Button("NICE + [+] ", id="btn-renice-up", variant="warning")
                            yield Button("NICE - [-] ", id="btn-renice-down", variant="success")

    def update_transcendence(self, screen):
        """Update the interactive transcendence view."""
        snapshot = self.snapshot
        if snapshot is None:
            return

        cpu = snapshot.cpu

        # 1. Header
        header = Text()
        average = cpu.percent
        header.append(f"CPU LOAD: {average:3.0f}%  ",
                      style="bold " + value_to_heat_color(average))
        header.append(make_bar(average, 100, 20), style=value_to_heat_color(average))
        frequency = f"{cpu.frequency_mhz:.0f} MHz" if cpu.frequency_mhz else "?"
        header.append(f"   FREQ: {frequency}   ", style="cyan")
        header.append(f"CORES: {cpu.core_count}", style="dim")
        screen.query_one("#cpu-hero-header", Static).update(header)

        # 2. Core grid, with kernel counters above it
        grid = Text()
        if cpu.context_switches is not None:
            syscalls = f" | SYSCALLS: {cpu.syscalls:,}" if cpu.syscalls else ""
            grid.append(
                f"CTX SWITCH: {cpu.context_switches:,} | "
                f"INTERRUPTS: {cpu.interrupts:,}{syscalls}\n\n",
                style="dim green",
            )

        for index, percent in enumerate(cpu.per_core):
            color = value_to_heat_color(percent)
            grid.append(f" CORE {index:02} ", style="dim white")
            grid.append(f"{percent:3.0f}% ", style=color)
            grid.append("███", style=color)
            grid.append("   ")
            if (index + 1) % 4 == 0:
                grid.append("\n\n")

        screen.query_one("#cpu-core-grid", Static).update(grid)

        # 3. Top offender
        top = snapshot.top_processes("cpu", limit=1)
        info_widget = screen.query_one("#top-process-info", Static)
        if top:
            process = top[0]
            self.top_pid = process.pid

            info = Text()
            info.append(f"PID: {process.pid}\n", style="bold yellow")
            info.append(f"NAME: {process.name}\n", style="bold white")
            info.append(f"CPU: {process.cpu_percent:.1f}%\n", style="red")
            info.append("Actions below apply to this process.", style="dim")
            info_widget.update(info)
        else:
            self.top_pid = None
            info_widget.update(Text("No active processes identified.", style="dim"))

    def get_transcendence_view(self) -> Text:
        """Text fallback for the full-screen view."""
        snapshot = self.snapshot
        if snapshot is None:
            return self.waiting_text()

        cpu = snapshot.cpu
        average = cpu.percent
        color = value_to_heat_color(average)

        text = Text()
        text.append("CPU CORE INFUSION ", style="bold")
        text.append(f"[{self.view_mode.upper()} MODE]\n", style="cyan")
        text.append(f"LOAD: {average:3.0f}% ", style=color)
        text.append(make_bar(average, 100, 20), style=color)
        text.append("\n")

        if self.view_mode == "cinematic":
            text.append("\nPERFORMANCE WAVEFORM\n", style="cyan")
            for value in self.history.cpu:
                text.append(value_to_spark(value), style=value_to_heat_color(value))

            text.append("\n\nCORE HEAT MAP\n", style="cyan")
            columns = 4
            rows = (cpu.core_count + columns - 1) // columns
            for row in range(rows):
                for column in range(columns):
                    index = row + column * rows
                    if index < cpu.core_count:
                        percent = cpu.per_core[index]
                        text.append(f"C{index:02} ", style="dim")
                        text.append(
                            "█" if percent > 50 else "▓" if percent > 20 else "░",
                            style=value_to_heat_color(percent),
                        )
                        text.append(" ")
                text.append("\n")
        else:
            text.append("\nPULSE: ", style="dim")
            for value in list(self.history.cpu)[-30:]:
                text.append(value_to_spark(value), style=value_to_heat_color(value))

            text.append("\n\nPER-CORE LOAD\n", style="cyan")
            half = (cpu.core_count + 1) // 2
            for i in range(half):
                for index in (i, i + half):
                    if index < cpu.core_count:
                        percent = cpu.per_core[index]
                        color = value_to_heat_color(percent)
                        text.append(f"C{index:02} {percent:3.0f}% ", style=color)
                        filled = int(percent / 10)
                        text.append("[" + "█" * filled + "░" * (10 - filled) + "]  ",
                                    style=color)
                text.append("\n")

            text.append("\nKERNEL TELEMETRY\n", style="cyan")
            if cpu.context_switches is not None:
                text.append(f"  Switches: {cpu.context_switches:,}  "
                            f"Interrupts: {cpu.interrupts:,}\n", style="dim")
            if cpu.load_average:
                one, five, fifteen = cpu.load_average
                text.append(f"  Load Avg: {one:.2f} / {five:.2f} / {fifteen:.2f}\n",
                            style="cyan")

        return text

    # ------------------------------------------------------------------
    # Detail view (shown in the centre panel when focused)
    # ------------------------------------------------------------------
    def get_detailed_view(self) -> Text:
        """Detailed CPU view with 2-column performance matrix."""
        snapshot = self.snapshot
        if snapshot is None:
            return self.waiting_text()

        cpu = snapshot.cpu

        text = Text()
        text.append("🔥 CORE PERFORMANCE MATRIX\n\n", style="bold")

        frequency = f"{cpu.frequency_mhz:.0f} MHz" if cpu.frequency_mhz else "?"
        text.append(f"THREADS: {cpu.core_count}  ", style="dim")
        text.append(f"CLOCK: {frequency}  ", style="cyan")
        if cpu.load_average:
            one, five, fifteen = cpu.load_average
            text.append(f"LOAD: {one:.2f} {five:.2f} {fifteen:.2f}\n\n", style="dim")
        else:
            text.append("\n\n", style="dim")

        half = (cpu.core_count + 1) // 2
        for i in range(half):
            left = cpu.per_core[i]
            color = value_to_heat_color(left)
            text.append(f"C{i:02} {left:3.0f}% ", style=color)
            text.append(value_to_spark(left), style=color)

            right_index = i + half
            if right_index < cpu.core_count:
                right = cpu.per_core[right_index]
                color = value_to_heat_color(right)
                text.append(f"   C{right_index:02} {right:3.0f}% ", style=color)
                text.append(value_to_spark(right), style=color)

            text.append("\n")

        return text
