import psutil
from datetime import datetime
from rich.text import Text
from pulse.panels.base import Panel
from pulse.ui_utils import value_to_heat_color, make_bar

class SystemPanel(Panel):
    """General System Info (CPU, MEM, DISK, UPTIME)."""
    
    PANEL_NAME = "SYSTEM"
    
    def __init__(self):
        super().__init__("SYSTEM", "", id="system-panel")
        self.sampling_rate = 1.0
        self.view_mode = "developer"
        try:
            self.boot_time = psutil.boot_time()
        except:
            self.boot_time = None
            
    def update_data(self):
        try:
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory()
            disk_usage = psutil.disk_usage('/')
        except:
            return

        uptime_str = "?"
        if self.boot_time:
            delta = datetime.now() - datetime.fromtimestamp(self.boot_time)
            days = delta.days
            hours, remainder = divmod(delta.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            uptime_str = f"{hours}h {minutes}m"
            if days > 0:
                uptime_str = f"{days}d {uptime_str}"

        text = Text()
        
        # CPU
        text.append("CPU  ", style="bold")
        text.append(f"{cpu:5.1f}% ", style=value_to_heat_color(cpu))
        text.append(make_bar(cpu, 100, 15) + "\n", style=value_to_heat_color(cpu))
        
        # RAM
        text.append("RAM  ", style="bold")
        text.append(f"{mem.percent:5.1f}% ", style=value_to_heat_color(mem.percent))
        text.append(make_bar(mem.percent, 100, 15) + "\n", style=value_to_heat_color(mem.percent))
        
        # DISK
        text.append("DISK ", style="bold")
        text.append(f"{disk_usage.percent:5.1f}% ", style=value_to_heat_color(disk_usage.percent))
        text.append(make_bar(disk_usage.percent, 100, 15) + "\n", style=value_to_heat_color(disk_usage.percent))
        
        # UPTIME
        text.append(f"\nUP: {uptime_str}", style="dim cyan")
        
        self.update(text)

    def get_transcendence_view(self) -> Text:
        """Ultimate System Dashboard."""
        text = Text()
        text.append("SYSTEM DASHBOARD\n", style="bold")
        text.append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n\n", style="dim")

        try:
            # OS Info
            import platform
            uname = platform.uname()
            text.append("PLATFORM DETAILS\n", style="cyan")
            text.append(f"  OS:      {uname.system} {uname.release} ({uname.version})\n", style="white")
            text.append(f"  Node:    {uname.node}\n", style="dim")
            text.append(f"  Arch:    {uname.machine}\n", style="dim")
            text.append(f"  Proc:    {uname.processor}\n\n", style="dim")

            # Uptime
            if self.boot_time:
                boot = datetime.fromtimestamp(self.boot_time)
                uptime = datetime.now() - boot
                text.append("SESSION STATUS\n", style="cyan")
                text.append(f"  Booted:  {boot.strftime('%Y-%m-%d %H:%M:%S')}\n", style="dim")
                text.append(f"  Uptime:  {str(uptime).split('.')[0]}\n\n", style="green")

            # Hardware Summary
            text.append("RESOURCE UTILIZATION\n", style="cyan")
            
            # CPU
            cpu = psutil.cpu_percent()
            text.append(f"  CPU:     {cpu:5.1f}% ", style=value_to_heat_color(cpu))
            text.append(make_bar(cpu, 100, 20) + "\n", style=value_to_heat_color(cpu))
            
            # MEM
            mem = psutil.virtual_memory()
            text.append(f"  RAM:     {mem.percent:5.1f}% ", style=value_to_heat_color(mem.percent))
            text.append(make_bar(mem.percent, 100, 20), style=value_to_heat_color(mem.percent))
            text.append(f" ({mem.used/1024**3:.1f}/{mem.total/1024**3:.1f} GB)\n", style="dim")
            
            # SWAP
            swap = psutil.swap_memory()
            text.append(f"  SWAP:    {swap.percent:5.1f}% ", style=value_to_heat_color(swap.percent))
            text.append(make_bar(swap.percent, 100, 20) + "\n", style=value_to_heat_color(swap.percent))

            # DISK (Root)
            disk = psutil.disk_usage('/')
            text.append(f"  DISK (/):{disk.percent:5.1f}% ", style=value_to_heat_color(disk.percent))
            text.append(make_bar(disk.percent, 100, 20) + "\n", style=value_to_heat_color(disk.percent))

        except Exception as e:
            text.append(f"\nError: {e}", style="red")

        return text

    def get_detailed_view(self) -> Text:
        return self.get_transcendence_view()
