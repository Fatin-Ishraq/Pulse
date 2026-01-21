import platform
import psutil
from rich.text import Text

from pulse.panels.base import Panel
from pulse.ui_utils import value_to_heat_color, make_bar

class StoragePanel(Panel):
    """Storage Matrix showing all mounted drives and their health."""
    
    PANEL_NAME = "STORAGE"
    
    def __init__(self):
        super().__init__("STORAGE", "", id="storage-panel")
        # Transcendence Control States
        self.sampling_rate = 1.0
        self.view_mode = "developer" # cinematic / developer
        self.scaling_mode = "absolute" # absolute / relative
    
    def get_transcendence_view(self) -> Text:
        """Ultimate Storage Matrix with Mount Point Health & Detailed Inodes."""
        text = Text()
        text.append(f"STORAGE INFUSION ", style="bold")
        text.append(f"[{self.view_mode.upper()} MODE]\n", style="cyan")
        
        try:
            parts = psutil.disk_partitions()
            
            if self.view_mode == "cinematic":
                text.append("\nVOLUME HEALTH LANDSCAPE\n", style="cyan")
                for part in parts:
                    if 'cdrom' in part.opts or part.fstype == '': continue
                    try:
                        usage = psutil.disk_usage(part.mountpoint)
                        color = value_to_heat_color(usage.percent)
                        text.append(f"{part.mountpoint:<15}", style="cyan")
                        text.append(make_bar(usage.percent, 100, 30), style=color)
                        text.append(f" {usage.percent:>4.1f}% ", style=color)
                        text.append(f"[{usage.used/(1024**3):.1f}/{usage.total/(1024**3):.1f} GB]\n", style="dim")
                    except: continue
            else:
                # Developer Mode: Detailed Inodes & Mount Flags
                text.append("\nMOUNT POINT REGISTRY\n", style="cyan")
                text.append(f"{'MOUNT':<15} {'FSTYPE':<8} {'USAGE':<20} {'INODES':<15} {'FLAGS'}\n", style="dim")
                text.append("─" * 80 + "\n", style="dim")
                
                for part in parts:
                    if 'cdrom' in part.opts or part.fstype == '': continue
                    try:
                        usage = psutil.disk_usage(part.mountpoint)
                        color = value_to_heat_color(usage.percent)
                        
                        text.append(f"{part.mountpoint[:15]:<15}", style="cyan")
                        text.append(f"{part.fstype:<8}", style="dim")
                        text.append(make_bar(usage.percent, 100, 10) + f" {usage.percent:>4.1f}% ", style=color)
                        
                        # Inodes (posix only usually)
                        try:
                            # psutil usage object might have .inodes_percent
                            if hasattr(usage, 'inodes_percent') and usage.inodes_percent is not None:
                                i_color = value_to_heat_color(usage.inodes_percent)
                                text.append(f"{usage.inodes_percent:>5.1f}% inodes ", style=i_color)
                            else:
                                text.append("N/A inodes      ", style="dim")
                        except:
                            text.append("N/A inodes      ", style="dim")
                            
                        # Flags (shortened)
                        opts = part.opts[:20]
                        text.append(f"{opts}", style="dim")
                        text.append("\n")
                    except: continue
                
                text.append("\nI/O COUNTERS (SYSTEM-WIDE)\n", style="cyan")
                io = psutil.disk_io_counters()
                if io:
                    text.append(f"  READ:  {io.read_bytes/(1024**3):.2f} GB ({io.read_count:,} ops)\n", style="green")
                    text.append(f"  WRITE: {io.write_bytes/(1024**3):.2f} GB ({io.write_count:,} ops)\n", style="cyan")
                    text.append(f"  BUSY:  {io.busy_time/1000:.1f}s active time\n", style="yellow")

        except Exception as e:
            text.append(f"Storage Telemetry Offline: {e}", style="red")
            
        return text
    
    def update_data(self):
        text = Text()
        try:
            parts = psutil.disk_partitions()
            # Show top 3 disks in summary
            count = 0
            for part in parts:
                if 'cdrom' in part.opts or part.fstype == '':
                    continue
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    color = value_to_heat_color(usage.percent)
                    
                    drive = part.mountpoint[:2] if platform.system() == "Windows" else part.mountpoint[-8:]
                    text.append(f"{drive:<4} ", style="cyan")
                    text.append(make_bar(usage.percent, 100, 8), style=color)
                    text.append(f" {usage.percent:3.0f}%\n", style=color)
                    count += 1
                    if count >= 3: break
                except:
                    continue
        except:
            text.append("Storage info restricted", style="dim")
            
        self.update(text)
        
    def get_detailed_view(self) -> Text:
        """Full storage matrix with wide capacity bars."""
        text = Text()
        text.append("🗄️ STORAGE ANALYTICS\n\n", style="bold")
        
        try:
            parts = psutil.disk_partitions()
            text.append(f"{'VOLUME':<12} {'TYPE':<8} {'CAPACITY USAGE':<25} {'FREE':<10}\n", style="dim")
            text.append("─" * 60 + "\n", style="dim")
            
            for part in parts:
                if 'cdrom' in part.opts or part.fstype == '':
                    continue
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    color = value_to_heat_color(usage.percent)
                    
                    label = part.mountpoint[:12]
                    text.append(f"{label:<12}", style="cyan")
                    text.append(f"{part.fstype:<8}", style="dim")
                    # Wide bar
                    text.append(make_bar(usage.percent, 100, 20) + f" {usage.percent:>3.0f}% ", style=color)
                    text.append(f"{usage.free / (1024**3):>6.1f} GB\n", style="dim")
                except:
                    continue
        except:
            text.append("Access Denied to Storage API", style="red")
            
        return text
