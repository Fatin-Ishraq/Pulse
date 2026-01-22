from datetime import datetime
import psutil
from rich.text import Text

from pulse.panels.base import Panel
from pulse.ui_utils import value_to_heat_color, make_bar

class MainViewPanel(Panel):
    """The large central panel showing system overview or focused panel details."""
    
    PANEL_NAME = "SYSTEM"
    
    def __init__(self):
        super().__init__("SYSTEM", "", id="main-panel")
        self.focused_panel = None  # Will be set by app when another panel is focused
    
    def update_data(self):
        # If another panel is focused, show its detailed view
        if self.focused_panel and hasattr(self.focused_panel, 'get_detailed_view'):
            self.update(self.focused_panel.get_detailed_view())
            self.border_title = f"◆ {self.focused_panel.PANEL_NAME}"
            return
        
        # Default: system overview
        self.border_title = "SYSTEM"
        try:
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            boot = datetime.fromtimestamp(psutil.boot_time())
        except:
            return
            
        uptime = datetime.now() - boot
        hours = int(uptime.total_seconds() // 3600)
        mins = int((uptime.total_seconds() % 3600) // 60)
        
        text = Text()
        text.append("CPU  ", style="bold")
        text.append(f"{cpu:5.1f}%  ", style=value_to_heat_color(cpu))
        text.append(make_bar(cpu, 100, 10) + "\n", style=value_to_heat_color(cpu))
        
        text.append("RAM  ", style="bold")
        text.append(f"{mem.percent:5.1f}%  ", style=value_to_heat_color(mem.percent))
        text.append(make_bar(mem.percent, 100, 10) + "\n", style=value_to_heat_color(mem.percent))
        
        text.append("DISK ", style="bold")
        text.append(f"{disk.percent:5.1f}%  ", style=value_to_heat_color(disk.percent))
        text.append(make_bar(disk.percent, 100, 10) + "\n", style=value_to_heat_color(disk.percent))
        
        text.append(f"\n⏱ Up {hours}h {mins}m\n", style="dim")
        
        # Add Platform Hint if space
        import platform
        sys_name = platform.system()
        text.append(f"{sys_name}", style="dim")
        
        self.update(text)
    
    def get_transcendence_view(self) -> Text:
        """Ultimate System Dashboard."""
        text = Text()
        text.append("SYSTEM OVERVIEW\n", style="bold")
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
            boot = datetime.fromtimestamp(psutil.boot_time())
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

            # Battery (Laptop only)
            if hasattr(psutil, "sensors_battery"):
                batt = psutil.sensors_battery()
                if batt:
                    text.append("\nPOWER STATUS\n", style="cyan")
                    plugged = "⚡ Plugged In" if batt.power_plugged else "🔋 On Battery"
                    color = "green" if batt.percent > 20 else "red"
                    text.append(f"  Level:   {batt.percent}% ({plugged})\n", style=color)
                    if not batt.power_plugged:
                         secs = batt.secsleft
                         if secs != psutil.POWER_TIME_UNLIMITED:
                             mins = secs // 60
                             text.append(f"  Est. Time: {mins//60}h {mins%60}m remaining\n", style="dim")

        except Exception as e:
            text.append(f"\nError fetching system details: {e}", style="red")

        return text
    
    def get_detailed_view(self) -> Text:
        """This panel shows other panels' details, not its own."""
        return Text("System Overview - Tab to other panels for details")
