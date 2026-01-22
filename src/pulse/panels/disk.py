from collections import deque
import psutil
from rich.text import Text

from pulse.panels.base import Panel
from pulse.ui_utils import value_to_spark, value_to_heat_color, make_bar

from textual.widgets import DataTable, Static, Button
from textual.containers import Container, Horizontal
from textual.binding import Binding

class DiskIOPanel(Panel):
    """Disk I/O waveform showing read/write activity."""
    
    PANEL_NAME = "DISK I/O"
    BINDINGS = [
        Binding("r", "refresh_stats", "Refresh", priority=True)
    ]
    
    def __init__(self):
        super().__init__("DISK I/O", "", id="disk-panel")
        self.read_history = deque(maxlen=80) 
        self.write_history = deque(maxlen=80)
        try:
            self.last_io = psutil.disk_io_counters()
        except:
            self.last_io = None
        
        # Per-disk state for transcendence rate calc
        self.last_per_disk_io = {}

        self.current_read_lat = 0.0
        self.current_write_lat = 0.0
        
        # Transcendence Control States
        self.sampling_rate = 1.0
        self.view_mode = "developer" # cinematic / developer
        self.scaling_mode = "auto" # auto / absolute
    
    def action_refresh_stats(self):
        """Force refresh."""
        self.refresh_content(force=True)
        self.notify("Refreshing Disk Stats...")
    
    def refresh_content(self, force=False):
        if hasattr(self.app.screen, "query_one"):
             try:
                 self.update_transcendence(self.app.screen)
             except: pass
    
    def update_data(self):
        try:
            current = psutil.disk_io_counters()
        except:
            return

        if not self.last_io:
            self.last_io = current
            return
            
        # Throughput
        read_rate = (current.read_bytes - self.last_io.read_bytes) / (1024**2)
        write_rate = (current.write_bytes - self.last_io.write_bytes) / (1024**2)
        
        # Latency (read_time/write_time are in ms in psutil)
        delta_read_count = current.read_count - self.last_io.read_count
        delta_write_count = current.write_count - self.last_io.write_count
        delta_read_time = current.read_time - self.last_io.read_time
        delta_write_time = current.write_time - self.last_io.write_time
        
        self.current_read_lat = delta_read_time / delta_read_count if delta_read_count > 0 else 0
        self.current_write_lat = delta_write_time / delta_write_count if delta_write_count > 0 else 0
        
        self.last_io = current
        
        self.read_history.append(min(read_rate * 2, 100))
        self.write_history.append(min(write_rate * 2, 100))
        
        text = Text()
        # Summary with throughput + sparks
        text.append("R ", style="cyan")
        text.append(f"{read_rate:4.1f}MB/s ", style="dim")
        for val in list(self.read_history)[-15:]:
            text.append(value_to_spark(val), style="cyan")
        
        # Latencies in summary
        lat_color_r = value_to_heat_color(self.current_read_lat * 2)
        text.append(f"\n   {self.current_read_lat:4.1f}ms  ", style=lat_color_r)
        
        text.append("\nW ", style="yellow")
        text.append(f"{write_rate:4.1f}MB/s ", style="dim")
        for val in list(self.write_history)[-15:]:
            text.append(value_to_spark(val), style="yellow")
            
        lat_color_w = value_to_heat_color(self.current_write_lat * 2)
        text.append(f"\n   {self.current_write_lat:4.1f}ms  ", style=lat_color_w)
        
        self.update(text)

    def compose_transcendence(self):
        """Interactive Disk I/O Matrix."""
        with Container(id="disk-transcendence-layout"):
            with Horizontal(classes="header-section"):
                yield Static(id="disk-hero-header")
            
            yield DataTable(id="disk_table", cursor_type="row", zebra_stripes=True)
            
            with Horizontal(classes="footer-section", id="disk-actions"):
                yield Button("REFRESH [R]", id="btn_refresh", variant="primary")
                yield Static("  Monitoring Real-Time I/O Activity", classes="status-text")
    
    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn_refresh":
            self.update_transcendence(self.app.screen)
            self.notify("Refreshed I/O Stats")

    def update_transcendence(self, screen):
        """Update Disk I/O Table."""
        table = screen.query_one("#disk_table", DataTable)
        header = screen.query_one("#disk-hero-header", Static)
        
        # Init Cols
        if not table.columns:
            table.add_columns("DEVICE", "MOUNT", "READ/s", "WRITE/s", "ACTIVITY", "TOTAL DATA")
        
        try:
            io_counters = psutil.disk_io_counters(perdisk=True)
            parts = {p.device: p.mountpoint for p in psutil.disk_partitions()}
            
            current_rows = set(table.rows.keys())
            
            # Timestamp for rate calc
            import time
            now = time.time()
            
            for dev, io in io_counters.items():
                mount = parts.get(dev, parts.get(dev.replace('/dev/', ''), "?"))
                
                # Rate Calculation
                r_rate_mb = 0.0
                w_rate_mb = 0.0
                
                if dev in self.last_per_disk_io:
                    last_io, last_time = self.last_per_disk_io[dev]
                    dt = now - last_time
                    if dt > 0:
                        r_rate_mb = (io.read_bytes - last_io.read_bytes) / (1024**2) / dt
                        w_rate_mb = (io.write_bytes - last_io.write_bytes) / (1024**2) / dt
                
                # Update state
                self.last_per_disk_io[dev] = (io, now)
                
                # Format Data
                r_gb = io.read_bytes / (1024**3)
                w_gb = io.write_bytes / (1024**3)
                total_str = f"R:{r_gb:.1f}G W:{w_gb:.1f}G"
                
                # Activity Bar (Max 50 MB/s ref for visualization)
                max_speed = 50.0 
                activity_val = max(r_rate_mb, w_rate_mb)
                bar_color = "green" if w_rate_mb < r_rate_mb else "yellow"
                if activity_val > 100: bar_color = "red"
                
                bar = make_bar(min(activity_val, max_speed), max_speed, 20)
                activity_cell = Text(f"{bar}", style=bar_color)
                
                # Styles
                r_style = value_to_heat_color(min(r_rate_mb * 5, 100))
                w_style = value_to_heat_color(min(w_rate_mb * 5, 100))
                
                row = [
                    dev,
                    mount,
                    Text(f"{r_rate_mb:5.1f} MB/s", style=r_style),
                    Text(f"{w_rate_mb:5.1f} MB/s", style=w_style),
                    activity_cell,
                    Text(total_str, style="dim")
                ]
                
                if dev in current_rows:
                    for i, val in enumerate(row):
                        key = list(table.columns.keys())[i]
                        table.update_cell(dev, key, val)
                else:
                    table.add_row(*row, key=dev)
            
            # Update Header
            header.update(f"DISK I/O MATRIX   SCANNING {len(io_counters)} DEVICES")
            
        except Exception as e:
            header.update(f"Disk Telemetry Error: {e}")

    def get_transcendence_view(self) -> Text:
        """Fallback text view (should not be reached if compose_transcendence works)."""
        return Text("Interactive Mode Active")

    def get_detailed_view(self) -> Text:
        """High-res disk telemetry and response heatmap."""
        text = Text()
        text.append("💿 DISK TELEMETRY\n\n", style="bold")
        
        try:
            io = psutil.disk_io_counters()
        except:
            return Text("Disk telemetry unavailable")
        
        # Waveforms
        text.append("Throughput Waves (Last 40s)\n", style="cyan")
        text.append("  READ  ", style="cyan")
        for val in list(self.read_history)[-40:]:
            text.append(value_to_spark(val), style="cyan")
        text.append("\n  WRITE ", style="yellow")
        for val in list(self.write_history)[-40:]:
            text.append(value_to_spark(val), style="yellow")
        text.append("\n\n")

        # Response Latency Map
        text.append("Response Latency Map\n", style="cyan")
        lat_r_style = value_to_heat_color(self.current_read_lat * 2)
        lat_w_style = value_to_heat_color(self.current_write_lat * 2)
        
        text.append(f"  READ  [", style="dim")
        text.append(f"{self.current_read_lat:6.2f} ms", style=lat_r_style)
        text.append("] " + make_bar(min(self.current_read_lat, 50), 50, 15) + "\n", style=lat_r_style)
        
        text.append(f"  WRITE [", style="dim")
        text.append(f"{self.current_write_lat:6.2f} ms", style=lat_w_style)
        text.append("] " + make_bar(min(self.current_write_lat, 50), 50, 15) + "\n", style=lat_w_style)

        text.append("\nSession Stats\n", style="cyan")
        text.append(f"  Total Data: Read {io.read_bytes/(1024**3):.2f}GB / Write {io.write_bytes/(1024**3):.2f}GB\n", style="dim")
        
        return text
