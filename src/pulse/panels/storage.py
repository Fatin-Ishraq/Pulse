import platform
import psutil
from rich.text import Text

from pulse import core
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
        
        disks = core.get_disk_info(lambda: None)
        
        if disks:
            # RUST PATH
            if self.view_mode == "cinematic":
                text.append("\nVOLUME HEALTH LANDSCAPE\n", style="cyan")
                for d in disks:
                    if d['total_space'] == 0: continue
                    mount = d['mount_point']
                    total = d['total_space']
                    used = total - d['available_space']
                    pct = (used / total) * 100
                    
                    color = value_to_heat_color(pct)
                    text.append(f"{mount:<15}", style="cyan")
                    text.append(make_bar(pct, 100, 30), style=color)
                    text.append(f" {pct:>4.1f}% ", style=color)
                    text.append(f"[{used/(1024**3):.1f}/{total/(1024**3):.1f} GB]\n", style="dim")
            else:
                # Developer Mode
                text.append("\nMOUNT POINT REGISTRY\n", style="cyan")
                text.append(f"{'MOUNT':<15} {'FSTYPE':<8} {'USAGE':<20} {'FREE':<15} {'FLAGS'}\n", style="dim")
                text.append("─" * 80 + "\n", style="dim")
                
                for d in disks:
                    if d['total_space'] == 0: continue
                    mount = d['mount_point']
                    fstype = d['file_system']
                    total = d['total_space']
                    free = d['available_space']
                    used = total - free
                    pct = (used / total) * 100
                    color = value_to_heat_color(pct)
                    
                    text.append(f"{mount[:15]:<15}", style="cyan")
                    text.append(f"{fstype:<8}", style="dim")
                    text.append(make_bar(pct, 100, 10) + f" {pct:>4.1f}% ", style=color)
                    text.append(f"{free/(1024**3):>6.1f} GB free  ", style="dim")
                    
                    # Flags not available in sysinfo basic
                    text.append(f"{'rw' if not d['is_removable'] else 'removable'}", style="dim")
                    text.append("\n")

        else:
            # FALLBACK PATH (Original psutil logic)
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
                            text.append("N/A inodes      ", style="dim")
                            text.append(f"{part.opts[:20]}", style="dim")
                            text.append("\n")
                        except: continue
            except Exception as e:
                text.append(f"Storage Telemetry Offline: {e}", style="red")

        # Global I/O (Keep psutil for now as sysinfo didn't reliably cover it across platforms in simple refresh)
        try:
            text.append("\nI/O COUNTERS (SYSTEM-WIDE)\n", style="cyan")
            io = psutil.disk_io_counters()
            if io:
                text.append(f"  READ:  {io.read_bytes/(1024**3):.2f} GB ({io.read_count:,} ops)\n", style="green")
                text.append(f"  WRITE: {io.write_bytes/(1024**3):.2f} GB ({io.write_count:,} ops)\n", style="cyan")
                text.append(f"  BUSY:  {io.busy_time/1000:.1f}s active time\n", style="yellow")
        except: pass
            
        return text
    
    def update_data(self):
        text = Text()
        
        # Try Rust Core
        disks = core.get_disk_info(lambda: None)
        
        if disks:
            # Rust Path
            count = 0
            for d in disks:
                if d.get('total_space', 0) == 0: continue
                
                mount = d['mount_point']
                total = d['total_space']
                used = total - d['available_space']
                percent = (used / total) * 100
                
                drive = mount[:2] if platform.system() == "Windows" else mount[-8:]
                color = value_to_heat_color(percent)
                
                text.append(f"{drive:<4} ", style="cyan")
                text.append(make_bar(percent, 100, 8), style=color)
                text.append(f" {percent:3.0f}%\n", style=color)
                
                count += 1
                if count >= 3: break
        else:
            # Fallback Path
            try:
                parts = psutil.disk_partitions()
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
