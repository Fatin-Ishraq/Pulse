from collections import deque
import psutil
from rich.text import Text

from pulse.panels.base import Panel
from pulse.state import current_theme
from pulse.ui_utils import value_to_spark, value_to_heat_color, make_bar

class DiskIOPanel(Panel):
    """Disk I/O waveform showing read/write activity."""
    
    PANEL_NAME = "DISK I/O"
    
    def __init__(self):
        super().__init__("DISK I/O", "", id="disk-panel")
        self.read_history = deque(maxlen=80) 
        self.write_history = deque(maxlen=80)
        try:
            self.last_io = psutil.disk_io_counters()
        except:
            self.last_io = None
        self.current_read_lat = 0.0
        self.current_write_lat = 0.0
        
        # Transcendence Control States
        self.sampling_rate = 1.0
        self.view_mode = "developer" # cinematic / developer
        self.scaling_mode = "auto" # auto / absolute
    
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
        text.append("R ", style=current_theme["read"])
        text.append(f"{read_rate:4.1f}MB/s ", style="dim")
        for val in list(self.read_history)[-15:]:
            text.append(value_to_spark(val), style=current_theme["read"])
        
        # Latencies in summary
        lat_color_r = value_to_heat_color(self.current_read_lat * 2, current_theme["heat"])
        text.append(f"\n   {self.current_read_lat:4.1f}ms  ", style=lat_color_r)
        
        text.append("\nW ", style=current_theme["write"])
        text.append(f"{write_rate:4.1f}MB/s ", style="dim")
        for val in list(self.write_history)[-15:]:
            text.append(value_to_spark(val), style=current_theme["write"])
            
        lat_color_w = value_to_heat_color(self.current_write_lat * 2, current_theme["heat"])
        text.append(f"\n   {self.current_write_lat:4.1f}ms  ", style=lat_color_w)
        
        self.update(text)

    def get_transcendence_view(self) -> Text:
        """Immersive Disk console with throughput waves and per-drive telemetry."""
        text = Text()
        try:
            io = psutil.disk_io_counters()
            per_disk = psutil.disk_io_counters(perdisk=True)
        except:
            return Text("Disk Telemetry Offline")

        # --- HERO HEADER ---
        text.append(f"DISK FLOW ANALYTICS ", style="bold")
        text.append(f"[{self.view_mode.upper()} MODE]\n", style=current_theme["focus"])
        
        rlat_style = value_to_heat_color(self.current_read_lat * 2, current_theme["heat"])
        wlat_style = value_to_heat_color(self.current_write_lat * 2, current_theme["heat"])
        
        text.append(f"READ LATENCY:  {self.current_read_lat:6.2f} ms ", style=rlat_style)
        text.append(make_bar(min(self.current_read_lat, 50), 50, 20), style=rlat_style)
        text.append("\n")
        text.append(f"WRITE LATENCY: {self.current_write_lat:6.2f} ms ", style=wlat_style)
        text.append(make_bar(min(self.current_write_lat, 50), 50, 20), style=wlat_style)
        text.append("\n")

        if self.view_mode == "cinematic":
            # Massive Waveform Focus
            text.append("\nREAD THROUGHPUT (80s)\n", style=current_theme["read"])
            for val in self.read_history:
                text.append(value_to_spark(val), style=current_theme["read"])
            
            text.append("\n\nWRITE THROUGHPUT (80s)\n", style=current_theme["write"])
            for val in self.write_history:
                text.append(value_to_spark(val), style=current_theme["write"])
                
            text.append("\n\nI/O OPERATIONS (Total)\n", style=current_theme["accent"])
            text.append(f"  READS:  {io.read_count:,}    WRITES: {io.write_count:,}\n", style="dim")
        else:
            # Developer Focus: Per-Disk Matrix
            text.append("\n80s I/O PULSE: ", style="dim")
            for r, w in zip(list(self.read_history)[-30:], list(self.write_history)[-30:]):
                text.append("R" if r > w else "W", style=current_theme["read"] if r > w else current_theme["write"])
            
            text.append("\n\nDRIVE ACTIVITY MATRIX\n", style=current_theme["accent"])
            text.append(f"{'DISK':<12} {'READ':<10} {'WRITE':<10} {'BUSY%'}\n", style="dim")
            text.append("─" * 45 + "\n", style="dim")
            for disk, d_io in per_disk.items():
                text.append(f"  {disk:<10} ", style=current_theme["accent"])
                text.append(f"{d_io.read_bytes/(1024**2):>6.1f}MB ", style=current_theme["read"])
                text.append(f"{d_io.write_bytes/(1024**2):>6.1f}MB ", style=current_theme["write"])
                # Busy time is only on some systems
                if hasattr(d_io, 'busy_time'):
                    text.append(f" {d_io.busy_time/1000:>6.1f}s", style="dim")
                text.append("\n")

        return text

    def get_detailed_view(self) -> Text:
        """High-res disk telemetry and response heatmap."""
        text = Text()
        text.append("💿 DISK TELEMETRY\n\n", style="bold")
        
        try:
            io = psutil.disk_io_counters()
        except:
            return Text("Disk telemetry unavailable")
        
        # Waveforms
        text.append("Throughput Waves (Last 40s)\n", style=current_theme["accent"])
        text.append("  READ  ", style=current_theme["read"])
        for val in list(self.read_history)[-40:]:
            text.append(value_to_spark(val), style=current_theme["read"])
        text.append("\n  WRITE ", style=current_theme["write"])
        for val in list(self.write_history)[-40:]:
            text.append(value_to_spark(val), style=current_theme["write"])
        text.append("\n\n")

        # Response Latency Map
        text.append("Response Latency Map\n", style=current_theme["accent"])
        lat_r_style = value_to_heat_color(self.current_read_lat * 2, current_theme["heat"])
        lat_w_style = value_to_heat_color(self.current_write_lat * 2, current_theme["heat"])
        
        text.append(f"  READ  [", style="dim")
        text.append(f"{self.current_read_lat:6.2f} ms", style=lat_r_style)
        text.append("] " + make_bar(min(self.current_read_lat, 50), 50, 15) + "\n", style=lat_r_style)
        
        text.append(f"  WRITE [", style="dim")
        text.append(f"{self.current_write_lat:6.2f} ms", style=lat_w_style)
        text.append("] " + make_bar(min(self.current_write_lat, 50), 50, 15) + "\n", style=lat_w_style)

        text.append("\nSession Stats\n", style=current_theme["accent"])
        text.append(f"  Total Data: Read {io.read_bytes/(1024**3):.2f}GB / Write {io.write_bytes/(1024**3):.2f}GB\n", style="dim")
        
        return text
