from rich.text import Text

from pulse.panels.base import Panel
from pulse.ui_utils import value_to_heat_color, make_bar

from textual.widgets import DataTable, Static, Button
from textual.containers import Container, Horizontal
from textual.binding import Binding

# How far the memory percentage is stretched before colouring it. A process at
# 20% of RAM is already notable, so the heat scale is compressed.
MEM_HEAT_SCALE = 5


class ProcessPanel(Panel):
    """Process list showing top consumers (CPU/MEM)."""

    PANEL_NAME = "PROCESSES"
    BINDINGS = [
        ("c", "sort('cpu')", "Sort CPU"),
        ("m", "sort('mem')", "Sort Mem"),
        Binding("k", "kill_process", "Kill", priority=True),
        Binding("plus", "renice_up", "Nice +", priority=True),
        Binding("minus", "renice_down", "Nice -", priority=True),
    ]

    def __init__(self):
        super().__init__("TOP PROCS", "", id="process-panel")
        self.sort_key = "cpu"  # or 'mem'
        self.sampling_rate = 2.0
        self.view_mode = "developer"

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_sort(self, mode: str):
        """Sort the process list."""
        self.sort_key = mode
        self.update_data()
        self.notify(f"Sorting by {mode.upper()}")

    def action_kill_process(self):
        """Terminate the process under the cursor, after confirmation."""
        pid = self._selected_pid()
        if pid is not None:
            self.request_kill(pid)

    def action_renice_up(self):
        self.request_renice(self._selected_pid(), 1)

    def action_renice_down(self):
        self.request_renice(self._selected_pid(), -1)

    def action_refresh_stats(self):
        self.app.refresh_data()

    def _selected_pid(self):
        """PID under the table cursor, or None with a message explaining why not."""
        try:
            table = self.app.screen.query_one("#proc_table", DataTable)
        except Exception:
            self.notify("Press X for the full process view to manage processes.",
                        severity="warning")
            return None

        if table.cursor_row is None:
            self.notify("No process selected.", severity="warning")
            return None

        try:
            row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
            return int(row_key.value)
        except (ValueError, TypeError, AttributeError):
            self.notify("Could not identify the selected process.", severity="error")
            return None

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_kill":
            self.action_kill_process()
        elif event.button.id == "btn_sort_cpu":
            self.action_sort("cpu")
        elif event.button.id == "btn_sort_mem":
            self.action_sort("mem")
        elif event.button.id == "btn_refresh":
            self.action_refresh_stats()

    # ------------------------------------------------------------------
    # Summary view
    # ------------------------------------------------------------------
    def update_data(self):
        snapshot = self.snapshot
        if snapshot is None:
            self.update(self.waiting_text())
            return

        text = Text()
        text.append(f"Sorted by {self.sort_key.upper()}\n", style="dim")

        total_memory = snapshot.memory.total
        for process in snapshot.top_processes(self.sort_key, limit=4):
            if self.sort_key == "cpu":
                value = process.cpu_percent
                color = value_to_heat_color(value)
                threshold = 10
            else:
                value = process.memory_percent(total_memory)
                color = value_to_heat_color(value * MEM_HEAT_SCALE)
                threshold = 5

            text.append("★ " if value > threshold else "· ", style=color)
            text.append(f"{process.name[:8]:<8} {value:4.1f}%\n", style="dim")

        self.update(text)

    # ------------------------------------------------------------------
    # Transcendence
    # ------------------------------------------------------------------
    def compose_transcendence(self):
        """Interactive Process Management Matrix."""
        with Container(id="proc-transcendence-layout"):
            with Horizontal(classes="header-section"):
                yield Static(id="proc-hero-header")

            yield DataTable(id="proc_table", cursor_type="row", zebra_stripes=True)

            with Horizontal(classes="footer-section", id="proc-actions"):
                yield Button("KILL [K]", id="btn_kill", variant="error")
                yield Button("SORT CPU [C]", id="btn_sort_cpu", variant="primary")
                yield Button("SORT MEM [M]", id="btn_sort_mem", variant="default")
                yield Button("REFRESH [R]", id="btn_refresh", variant="warning")

    def update_transcendence(self, screen):
        """Update the process table, preserving the user's cursor position."""
        snapshot = self.snapshot
        if snapshot is None:
            return

        table = screen.query_one("#proc_table", DataTable)
        header = screen.query_one("#proc-hero-header", Static)

        if not table.columns:
            table.add_columns("PID", "NAME", "CPU %", "MEM %", "USER", "STATUS")

        total_memory = snapshot.memory.total
        processes = snapshot.top_processes(self.sort_key, limit=100)

        head = Text()
        cpu = snapshot.cpu.percent
        head.append(f" ⚡ {cpu:5.1f}%   ", style="bold green")
        head.append(make_bar(cpu, 100, 15), style="green")
        memory = snapshot.memory.percent
        head.append(f"   💾 {memory:5.1f}%   ", style="bold blue")
        head.append(make_bar(memory, 100, 15), style="blue")
        head.append(f"   ACTIVE TASKS: {len(snapshot.processes)}", style="dim")
        header.update(head)

        # Rows are updated in place and only added or removed on change, so a
        # scrolled, selected row stays put instead of being rebuilt each tick.
        column_keys = list(table.columns.keys())
        current_rows = set(table.rows.keys())
        seen = set()

        for process in processes:
            key = str(process.pid)
            seen.add(key)

            memory_percent = process.memory_percent(total_memory)
            row = [
                key,
                process.name,
                Text(f"{process.cpu_percent:5.1f}",
                     style=value_to_heat_color(process.cpu_percent)),
                Text(f"{memory_percent:5.1f}",
                     style=value_to_heat_color(memory_percent * MEM_HEAT_SCALE)),
                Text(process.username[:10], style="dim"),
                Text(process.status[:10], style="dim"),
            ]

            if key in current_rows:
                for index, value in enumerate(row):
                    table.update_cell(key, column_keys[index], value)
            else:
                table.add_row(*row, key=key)

        for stale in current_rows - seen:
            table.remove_row(stale)

    def get_transcendence_view(self) -> Text:
        """Text fallback for the full-screen view."""
        snapshot = self.snapshot
        if snapshot is None:
            return self.waiting_text()

        total_memory = snapshot.memory.total

        text = Text()
        text.append("PROCESS INFUSION ", style="bold")
        text.append(f"SORT: {self.sort_key.upper()}\n", style="dim")

        text.append("\nHIGH-CONSUMPTION LANDSCAPE\n", style="cyan")
        for process in snapshot.top_processes(self.sort_key, limit=15):
            if self.sort_key == "cpu":
                value = process.cpu_percent
                scaled = value
            else:
                value = process.memory_percent(total_memory)
                scaled = value * MEM_HEAT_SCALE

            color = value_to_heat_color(scaled)
            text.append(f"{process.name[:15]:<15} ", style="cyan")
            text.append(make_bar(min(scaled, 100), 100, 30), style=color)
            text.append(f" {value:>4.1f}% ", style=color)
            text.append(f"PID: {process.pid}\n", style="dim")

        text.append("\nSTATE DISTRIBUTION\n", style="cyan")
        counts = {}
        for process in snapshot.processes:
            counts[process.status] = counts.get(process.status, 0) + 1
        for status, count in sorted(counts.items(), key=lambda item: -item[1]):
            text.append(f"  {status.upper():<10}: {count:>4}  ", style="dim")
            filled = min(10, count // 20)
            text.append("█" * filled + "░" * (10 - filled) + "\n", style="cyan")

        return text

    # ------------------------------------------------------------------
    # Detail view
    # ------------------------------------------------------------------
    def get_detailed_view(self) -> Text:
        """Detailed process table."""
        snapshot = self.snapshot
        if snapshot is None:
            return self.waiting_text()

        total_memory = snapshot.memory.total

        text = Text()
        text.append("⭐ TOP PROCESSES\n\n", style="bold")
        text.append(f"Sorted by: {self.sort_key.upper()}   ", style="cyan")
        text.append("[C] Sort CPU  [M] Sort Memory\n\n", style="dim")

        text.append("PID      CPU%   MEM%   NAME\n", style="yellow")
        text.append("─" * 40 + "\n", style="dim")

        for process in snapshot.top_processes(self.sort_key, limit=20):
            memory_percent = process.memory_percent(total_memory)
            text.append(f"{process.pid:<8}", style="dim")
            text.append(f"{process.cpu_percent:5.1f}%  ",
                        style=value_to_heat_color(process.cpu_percent))
            text.append(f"{memory_percent:5.1f}%  ",
                        style=value_to_heat_color(memory_percent * MEM_HEAT_SCALE))
            text.append(f"{process.name}\n")

        return text
