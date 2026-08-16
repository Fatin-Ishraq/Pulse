from rich.text import Text

from pulse.panels.base import Panel
from pulse.ui_utils import value_to_spark, value_to_heat_color, make_bar

from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Button

GIB = 1024 ** 3


class MemoryPanel(Panel):
    """Shows memory usage as a live pressure bar."""

    PANEL_NAME = "MEMORY"
    BINDINGS = [
        ("k", "kill_process", "Kill Top Process"),
        ("plus", "renice_up", "Lower Priority"),
        ("minus", "renice_down", "Higher Priority"),
    ]

    def __init__(self):
        super().__init__("MEMORY", "", id="memory-panel")

        # Transcendence Control States
        self.sampling_rate = 1.0
        self.view_mode = "developer"  # cinematic / developer
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
        self.request_renice(self.top_pid, 1)

    def action_renice_down(self):
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

        memory = snapshot.memory
        percent = memory.percent
        color = value_to_heat_color(percent)

        text = Text()
        text.append("MEM ", style="cyan")
        bar_width = 12
        filled = int(percent / 100 * bar_width)
        text.append("█" * filled, style=color)
        text.append("░" * (bar_width - filled), style="dim")
        text.append(f"\n{memory.used / GIB:.1f}/{memory.total / GIB:.1f}GB", style=color)
        self.update(text)

        if percent > 95:
            self.add_class("alarm")
            self.border_title = "MEM CRITICAL"
        else:
            self.remove_class("alarm")
            self.border_title = "MEMORY"

    # ------------------------------------------------------------------
    # Transcendence
    # ------------------------------------------------------------------
    def compose_transcendence(self):
        """Compose the interactive Memory Management Console."""
        with Container(id="mem-transcendence-layout"):
            with Horizontal(classes="header-section"):
                yield Static(id="mem-hero-header")

            with Container(classes="core-section"):
                yield Static("ALLOCATION MAP (PHYSICAL vs SWAP)", classes="section-title")
                yield Static(id="mem-allocation-map")

            with Container(classes="process-section"):
                yield Static("TOP MEMORY OFFENDER", classes="section-title")
                with Horizontal(id="process-control-box"):
                    yield Static(id="mem-top-process-info", classes="process-info")
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

        memory = snapshot.memory
        color = value_to_heat_color(memory.percent)

        header = Text()
        header.append(f"MEM PRESSURE: {memory.percent:3.0f}%  ", style="bold " + color)
        header.append(make_bar(memory.percent, 100, 20), style=color)
        header.append(f"   SWAP: {memory.swap_percent:.0f}%   ", style="yellow")
        header.append(f"TOTAL: {memory.total / GIB:.1f} GB", style="dim")
        screen.query_one("#mem-hero-header", Static).update(header)

        # Allocation map: physical and swap drawn against the same total.
        total_volume = memory.total + memory.swap_total
        physical_blocks = int(memory.used / total_volume * 100) if total_volume else 0
        swap_blocks = int(memory.swap_used / total_volume * 100) if total_volume else 0

        allocation = Text()
        allocation.append("PHYSICAL RAM IN USE\n", style="cyan")
        allocation.append("█" * physical_blocks, style="cyan")
        allocation.append("░" * max(0, 50 - physical_blocks), style="dim cyan")

        allocation.append("\n\nSWAP FILE COMMITTED\n", style="yellow")
        allocation.append("▓" * swap_blocks, style="yellow")

        allocation.append("\n\nSTATS:\n", style="bold")
        allocation.append(f"  Available: {memory.available / GIB:.2f} GB\n", style="green")
        allocation.append(f"  Used:      {memory.used / GIB:.2f} GB\n", style="cyan")
        allocation.append(f"  Swap Used: {memory.swap_used / GIB:.2f} GB", style="yellow")
        screen.query_one("#mem-allocation-map", Static).update(allocation)

        top = snapshot.top_processes("mem", limit=1)
        info_widget = screen.query_one("#mem-top-process-info", Static)
        if top:
            process = top[0]
            self.top_pid = process.pid

            info = Text()
            info.append(f"PID: {process.pid}\n", style="bold yellow")
            info.append(f"NAME: {process.name}\n", style="bold white")
            info.append(f"MEM: {process.memory_bytes / (1024 * 1024):.1f} MB\n", style="cyan")
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

        memory = snapshot.memory
        color = value_to_heat_color(memory.percent)

        text = Text()
        text.append("MEMORY DEPTH ANALYTICS ", style="bold")
        text.append(f"[{self.view_mode.upper()} MODE]\n", style="cyan")
        text.append(f"PRESSURE: {memory.percent:3.0f}% ", style=color)
        text.append(make_bar(memory.percent, 100, 20), style=color)
        text.append(f"  SWAP: {memory.swap_percent:3.0f}%\n", style="dim")

        if self.view_mode == "cinematic":
            text.append("\nPRESSURE WAVEFORM\n", style="cyan")
            for value in self.history.memory:
                text.append(value_to_spark(value), style=value_to_heat_color(value))

            text.append("\n\nALLOCATION LANDSCAPE\n", style="cyan")
            total_volume = memory.total + memory.swap_total
            physical = int(memory.used / total_volume * 40) if total_volume else 0
            swap = int(memory.swap_used / total_volume * 40) if total_volume else 0
            free = max(0, 40 - physical - swap)

            text.append("PHYS [", style="dim")
            text.append("█" * physical, style="cyan")
            text.append("] SWAP [", style="dim")
            text.append("▓" * swap, style="yellow")
            text.append("] FREE [", style="dim")
            text.append("░" * free, style="dim")
            text.append("]\n", style="dim")
        else:
            text.append("\nPRESSURE: ", style="dim")
            for value in list(self.history.memory)[-30:]:
                text.append(value_to_spark(value), style=value_to_heat_color(value))

            text.append("\n\nSUBSYSTEM BREAKDOWN\n", style="cyan")
            rows = [
                ("Physical Total", memory.total),
                ("Available", memory.available),
                ("Used (Kernel+Apps)", memory.used),
            ]
            if memory.cached is not None:
                rows.append(("Cached", memory.cached))
            if memory.buffers is not None:
                rows.append(("Buffers", memory.buffers))

            for label, value in rows:
                text.append(f"  {label:<20} ", style="dim")
                text.append(f"{value / GIB:>9.2f} GB\n", style="cyan")

            text.append("\nSWAP & PAGING\n", style="cyan")
            text.append(f"  Swap Used:    {memory.swap_used / GIB:6.2f} GB / "
                        f"{memory.swap_total / GIB:.2f} GB\n", style="dim")

        return text

    # ------------------------------------------------------------------
    # Detail view
    # ------------------------------------------------------------------
    def get_detailed_view(self) -> Text:
        """Detailed memory breakdown with pressure waveform."""
        snapshot = self.snapshot
        if snapshot is None:
            return self.waiting_text()

        memory = snapshot.memory

        text = Text()
        text.append("💾 MEMORY ANALYTICS\n\n", style="bold")

        text.append("Pressure Waveform\n", style="cyan")
        for value in list(self.history.memory)[-40:]:
            text.append(value_to_spark(value), style=value_to_heat_color(value))
        text.append(f" {memory.percent:.0f}%\n\n", style=value_to_heat_color(memory.percent))

        text.append(f"{'TYPE':<12} {'TOTAL':<10} {'USED':<10} {'FREE':<10}\n", style="dim")
        text.append("─" * 45 + "\n", style="dim")
        text.append(f"{'Physical':<12} {memory.total / GIB:.1f}GB    "
                    f"{memory.used / GIB:.1f}GB    {memory.free / GIB:.1f}GB\n")
        text.append(f"{'Swap':<12} {memory.swap_total / GIB:.1f}GB    "
                    f"{memory.swap_used / GIB:.1f}GB    {memory.swap_free / GIB:.1f}GB\n\n")

        text.append("Allocation Map\n", style="cyan")
        used_blocks = int(memory.used / memory.total * 30) if memory.total else 0
        text.append("[" + "█" * used_blocks + "▒" * (30 - used_blocks) + "]\n", style="cyan")
        text.append(f"  {'Used':<8} {memory.used / GIB:.1f}GB\n", style="dim")
        text.append(f"  {'Avail':<8} {memory.available / GIB:.1f}GB\n", style="dim")

        return text
