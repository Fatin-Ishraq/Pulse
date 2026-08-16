from rich.text import Text

from pulse.panels.base import Panel
from pulse.ui_utils import value_to_spark, value_to_heat_color, make_bar

from textual.widgets import DataTable, Static, Button
from textual.containers import Container, Horizontal
from textual.binding import Binding

GIB = 1024 ** 3
# Reference ceiling for the activity bars, in MB/s.
BAR_SCALE_MBPS = 50.0


class DiskIOPanel(Panel):
    """Disk I/O waveform showing read/write activity."""

    PANEL_NAME = "DISK I/O"
    BINDINGS = [
        Binding("r", "refresh_stats", "Refresh", priority=True)
    ]

    def __init__(self):
        super().__init__("DISK I/O", "", id="disk-panel")
        self.sampling_rate = 1.0
        self.view_mode = "developer"  # cinematic / developer
        self.scaling_mode = "auto"  # auto / absolute

    def action_refresh_stats(self):
        self.app.refresh_data()
        self.notify("Refreshing disk stats...")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn_refresh":
            self.action_refresh_stats()

    # ------------------------------------------------------------------
    # Summary view
    # ------------------------------------------------------------------
    def update_data(self):
        if self.snapshot is None:
            self.update(self.waiting_text())
            return

        rates = self.rates

        text = Text()
        text.append("R ", style="cyan")
        text.append(f"{rates.disk_read_mbps:4.1f}MB/s ", style="dim")
        for value in list(self.history.disk_read)[-15:]:
            text.append(value_to_spark(value, BAR_SCALE_MBPS), style="cyan")

        read_latency_color = value_to_heat_color(rates.disk_read_latency_ms * 2)
        text.append(f"\n   {rates.disk_read_latency_ms:4.1f}ms  ", style=read_latency_color)

        text.append("\nW ", style="yellow")
        text.append(f"{rates.disk_write_mbps:4.1f}MB/s ", style="dim")
        for value in list(self.history.disk_write)[-15:]:
            text.append(value_to_spark(value, BAR_SCALE_MBPS), style="yellow")

        write_latency_color = value_to_heat_color(rates.disk_write_latency_ms * 2)
        text.append(f"\n   {rates.disk_write_latency_ms:4.1f}ms  ", style=write_latency_color)

        self.update(text)

    # ------------------------------------------------------------------
    # Transcendence
    # ------------------------------------------------------------------
    def compose_transcendence(self):
        """Interactive Disk I/O Matrix."""
        with Container(id="disk-transcendence-layout"):
            with Horizontal(classes="header-section"):
                yield Static(id="disk-hero-header")

            yield DataTable(id="disk_table", cursor_type="row", zebra_stripes=True)

            with Horizontal(classes="footer-section", id="disk-actions"):
                yield Button("REFRESH [R]", id="btn_refresh", variant="primary")
                yield Static("  Monitoring Real-Time I/O Activity", classes="status-text")

    def update_transcendence(self, screen):
        """Update the per-device I/O table."""
        snapshot = self.snapshot
        if snapshot is None:
            return

        table = screen.query_one("#disk_table", DataTable)
        header = screen.query_one("#disk-hero-header", Static)

        if not table.columns:
            table.add_columns("DEVICE", "READ TOTAL", "WRITE TOTAL", "OPS (R/W)")

        per_disk = snapshot.disk_io.per_disk
        column_keys = list(table.columns.keys())
        current_rows = set(table.rows.keys())

        for device, counters in per_disk.items():
            row = [
                device,
                Text(f"{counters.read_bytes / GIB:.2f} GB", style="cyan"),
                Text(f"{counters.write_bytes / GIB:.2f} GB", style="yellow"),
                Text(f"{counters.read_count:,} / {counters.write_count:,}", style="dim"),
            ]
            if device in current_rows:
                # Updating in place keeps the cursor where the user put it.
                for index, value in enumerate(row):
                    table.update_cell(device, column_keys[index], value)
            else:
                table.add_row(*row, key=device)

        for stale in current_rows - set(per_disk):
            table.remove_row(stale)

        rates = self.rates
        header.update(
            f"DISK I/O MATRIX   "
            f"READ {rates.disk_read_mbps:5.1f} MB/s   "
            f"WRITE {rates.disk_write_mbps:5.1f} MB/s   "
            f"DEVICES {len(per_disk)}"
        )

    def get_transcendence_view(self) -> Text:
        """Text fallback for the full-screen view."""
        if self.snapshot is None:
            return self.waiting_text()
        return self.get_detailed_view()

    # ------------------------------------------------------------------
    # Detail view
    # ------------------------------------------------------------------
    def get_detailed_view(self) -> Text:
        """High-res disk telemetry and response heatmap."""
        snapshot = self.snapshot
        if snapshot is None:
            return self.waiting_text()

        disk = snapshot.disk_io
        rates = self.rates

        text = Text()
        text.append("💿 DISK TELEMETRY\n\n", style="bold")

        text.append("Throughput Waves\n", style="cyan")
        text.append("  READ  ", style="cyan")
        for value in list(self.history.disk_read)[-40:]:
            text.append(value_to_spark(value, BAR_SCALE_MBPS), style="cyan")
        text.append("\n  WRITE ", style="yellow")
        for value in list(self.history.disk_write)[-40:]:
            text.append(value_to_spark(value, BAR_SCALE_MBPS), style="yellow")
        text.append("\n\n")

        text.append("Current Throughput\n", style="cyan")
        text.append(f"  READ  {rates.disk_read_mbps:6.2f} MB/s ", style="cyan")
        text.append(make_bar(min(rates.disk_read_mbps, BAR_SCALE_MBPS),
                             BAR_SCALE_MBPS, 15) + "\n", style="cyan")
        text.append(f"  WRITE {rates.disk_write_mbps:6.2f} MB/s ", style="yellow")
        text.append(make_bar(min(rates.disk_write_mbps, BAR_SCALE_MBPS),
                             BAR_SCALE_MBPS, 15) + "\n", style="yellow")

        text.append("\nResponse Latency Map\n", style="cyan")
        read_color = value_to_heat_color(rates.disk_read_latency_ms * 2)
        write_color = value_to_heat_color(rates.disk_write_latency_ms * 2)

        text.append("  READ  [", style="dim")
        text.append(f"{rates.disk_read_latency_ms:6.2f} ms", style=read_color)
        text.append("] " + make_bar(min(rates.disk_read_latency_ms, 50), 50, 15) + "\n",
                    style=read_color)

        text.append("  WRITE [", style="dim")
        text.append(f"{rates.disk_write_latency_ms:6.2f} ms", style=write_color)
        text.append("] " + make_bar(min(rates.disk_write_latency_ms, 50), 50, 15) + "\n",
                    style=write_color)

        text.append("\nSession Stats\n", style="cyan")
        text.append(f"  Total Data: Read {disk.read_bytes / GIB:.2f}GB / "
                    f"Write {disk.write_bytes / GIB:.2f}GB\n", style="dim")
        text.append(f"  Operations: {disk.read_count:,} reads / "
                    f"{disk.write_count:,} writes\n", style="dim")

        return text
