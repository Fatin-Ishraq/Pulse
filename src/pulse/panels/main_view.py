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
        
        text.append(f"\n⏱ Up {hours}h {mins}m", style="dim")
        self.update(text)
    
    def get_detailed_view(self) -> Text:
        """This panel shows other panels' details, not its own."""
        return Text("System Overview - Tab to other panels for details")
