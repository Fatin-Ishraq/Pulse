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

    def get_transcendence_view(self):
        """Ultimate System Dashboard using Grid Layout."""
        # Note: We return a rich.console.Group or Table, which Panel.update() can handle!
        from rich.table import Table
        from rich.columns import Columns
        from rich.panel import Panel as RichPanel
        from rich.console import Group
        
        try:
            # Gather Data
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            disk = psutil.disk_usage('/')
            
            import platform
            uname = platform.uname()
            
            # --- ROW 1: System Header & Session ---
            header_table = Table.grid(expand=True)
            header_table.add_column("Info", ratio=2)
            header_table.add_column("Session", ratio=1, justify="right")
            
            sys_info = f"[bold white]{uname.system} {uname.release}[/]\n[dim]{uname.version[:40]}...[/]"
            
            uptime_str = "Unknown"
            if self.boot_time:
                boot = datetime.fromtimestamp(self.boot_time)
                delta = datetime.now() - boot
                uptime_str = str(delta).split('.')[0]
            
            header_table.add_row(
                sys_info,
                f"[cyan]UPTIME[/]\n[green bold]{uptime_str}[/]"
            )
            
            # --- ROW 2: Resources Grid ---
            res_table = Table(title="RESOURCE UTILIZATION", expand=True, box=None, padding=(1,1))
            res_table.add_column("Component", style="bold")
            res_table.add_column("Usage %", justify="right")
            res_table.add_column("Visual", ratio=3)
            res_table.add_column("Details", style="dim")
            
            # CPU
            c_color = value_to_heat_color(cpu)
            res_table.add_row(
                "CPU", 
                f"[{c_color}]{cpu:.1f}%[/]", 
                f"[{c_color}]{make_bar(cpu, 100, 40)}[/]", 
                f"{psutil.cpu_count(logical=False)}C/{psutil.cpu_count()}T @ {getattr(psutil.cpu_freq(), 'current', 0):.0f}MHz"
            )
            
            # RAM
            m_color = value_to_heat_color(mem.percent)
            res_table.add_row(
                "RAM",
                f"[{m_color}]{mem.percent:.1f}%[/]",
                f"[{m_color}]{make_bar(mem.percent, 100, 40)}[/]",
                f"{mem.used/1024**3:.1f}/{mem.total/1024**3:.0f} GB"
            )
            
            # SWAP
            s_color = value_to_heat_color(swap.percent)
            res_table.add_row(
                "SWAP",
                f"[{s_color}]{swap.percent:.1f}%[/]",
                f"[{s_color}]{make_bar(swap.percent, 100, 40)}[/]",
                f"{swap.used/1024**3:.1f} GB"
            )
            
            # DISK
            d_color = value_to_heat_color(disk.percent)
            res_table.add_row(
                "DISK (/)",
                f"[{d_color}]{disk.percent:.1f}%[/]",
                f"[{d_color}]{make_bar(disk.percent, 100, 40)}[/]",
                f"{disk.used/1024**3:.0f}/{disk.total/1024**3:.0f} GB"
            )
            
            # --- BUILD LAYOUT ---
            layout = Group(
                RichPanel(header_table, title="[bold]SYSTEM IDENTITY[/]", border_style="blue"),
                Text("\n"),
                RichPanel(res_table, border_style="white")
            )
            return layout
            
        except Exception as e:
            return Text(f"Error rendering dashboard: {e}", style="red")

    def get_detailed_view(self) -> Text:
        return self.get_transcendence_view()
