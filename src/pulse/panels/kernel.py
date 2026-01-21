import psutil
from rich.text import Text

from pulse.panels.base import Panel
from pulse.state import current_theme
from pulse.ui_utils import value_to_heat_color, make_bar

class KernelThermalPanel(Panel):
    """Kernel vitals and thermal pulse."""
    
    PANEL_NAME = "KERNEL"
    
    def __init__(self):
        super().__init__("KERNEL", "", id="kernel-panel")
        try:
            self.last_stats = psutil.cpu_stats()
        except:
            self.last_stats = None
        # Transcendence Control States
        self.sampling_rate = 1.0
        self.view_mode = "developer" # cinematic / developer
        self.scaling_mode = "absolute" # absolute / relative
    
    def get_transcendence_view(self) -> Text:
        """Ultimate Kernel & Thermal Analytics."""
        text = Text()
        text.append(f"KERNEL PULSE ", style="bold")
        text.append(f"[{self.view_mode.upper()} MODE]\n", style=current_theme["focus"])
        
        try:
            boot_time = psutil.boot_time()
            import datetime
            uptime = datetime.datetime.now() - datetime.datetime.fromtimestamp(boot_time)
            text.append(f"UPTIME: {str(uptime).split('.')[0]}\n", style="dim")
            
            if self.view_mode == "cinematic":
                text.append("\nTHERMAL GRADIENT MAP\n", style=current_theme["accent"])
                try:
                    temps = psutil.sensors_temperatures()
                    if temps:
                        for name, entries in temps.items():
                            for e in entries:
                                color = value_to_heat_color(e.current, current_theme["heat"])
                                text.append(f"{name[:10]:<10} {e.label or 'Core'[:10]:<10} ", style="dim")
                                text.append(make_bar(e.current, 100, 30), style=color)
                                text.append(f" {e.current:.1f}°C\n", style=color)
                    else:
                        text.append("(Thermal data restricted or unavailable)\n", style="yellow")
                except:
                    text.append("(Thermal API Access Denied)\n", style="red")
            else:
                # Developer Mode: Raw Kernel Events & System Info
                text.append("\nKERNEL EVENT ANALYTICS\n", style=current_theme["accent"])
                try:
                    stats = psutil.cpu_stats()
                    text.append(f"{'METRIC':<20} {'RAW VALUE':<15}\n", style="dim")
                    text.append("─" * 40 + "\n", style="dim")
                    text.append(f"{'Context Switches':<20} {stats.ctx_switches:,}\n", style="cyan")
                    text.append(f"{'Interrupts':<20} {stats.interrupts:,}\n", style="cyan")
                    text.append(f"{'Soft Interrupts':<20} {stats.soft_interrupts:,}\n", style="cyan")
                    text.append(f"{'Syscalls':<20} {stats.syscalls:,}\n", style="cyan")
                except: pass
                
                text.append("\nFAN SPEED SENSORS\n", style=current_theme["accent"])
                try:
                    fans = psutil.sensors_fans()
                    if fans:
                        for name, entries in fans.items():
                            for e in entries:
                                text.append(f"  {name} {e.label or 'Fan'}: {e.current} RPM\n", style="green")
                    else:
                        text.append("  (No fan sensors detected)\n", style="dim")
                except:
                    text.append("  (Fan API Access Denied)\n", style="red")
                
                text.append("\nSYSTEM PLATFORM\n", style=current_theme["accent"])
                import platform
                text.append(f"  OS:      {platform.system()} {platform.release()}\n", style="dim")
                text.append(f"  VERSION: {platform.version()[:50]}...\n", style="dim")
                text.append(f"  ARCH:    {platform.machine()}\n", style="dim")

        except Exception as e:
            text.append(f"Kernel Telemetry Offline: {e}", style="red")
            
        return text
    
    def update_data(self):
        try:
            current_stats = psutil.cpu_stats()
        except:
            return

        if not self.last_stats:
            self.last_stats = current_stats
            return
            
        # Rates per second (assuming 1s update interval)
        ctx_switches = current_stats.ctx_switches - self.last_stats.ctx_switches
        interrupts = current_stats.interrupts - self.last_stats.interrupts
        self.last_stats = current_stats
        
        text = Text()
        # Thermal
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                key = next(iter(temps))
                t = temps[key][0].current
                color = value_to_heat_color(t, current_theme["heat"])
                text.append(f"THERM: {t:.1f}°C\n", style=color)
            else:
                text.append("THERM: [N/A]\n", style="dim")
        except:
            text.append("THERM: LOCKED\n", style="dim")
            
        # Kernel summary
        text.append(f"CTX:   {ctx_switches/1000:4.1f}k/s\n", style=current_theme["accent"])
        text.append(f"INTR:  {interrupts/1000:4.1f}k/s", style="dim")
        
        self.update(text)
        
    def get_detailed_view(self) -> Text:
        """Detailed kernel stats and thermal mapping."""
        text = Text()
        text.append("🌡️ KERNEL & THERMAL PULSE\n\n", style="bold")
        
        try:
            stats = psutil.cpu_stats()
        except:
            return Text("Kernel telemetry unavailable")
            
        text.append("Kernel Events\n", style=current_theme["accent"])
        text.append(f"  Context Switches: {stats.ctx_switches:,}\n", style="dim")
        text.append(f"  Interrupts:       {stats.interrupts:,}\n", style="dim")
        text.append(f"  Soft Interrupts:  {stats.soft_interrupts:,}\n", style="dim")
        text.append(f"  Syscalls:         {stats.syscalls:,}\n", style="dim")
        
        # Thermal Throttling / Freq details
        text.append("\nThermal Sensors\n", style=current_theme["accent"])
        try:
            temps = psutil.sensors_temperatures()
            if not temps:
                text.append("  (No sensors found or restricted on Windows)\n", style="dim")
            else:
                for name, entries in temps.items():
                    text.append(f"  {name}\n", style="dim")
                    for e in entries:
                        color = value_to_heat_color(e.current, current_theme["heat"])
                        text.append(f"    {e.label or 'Core'}: {e.current:.1f}°C ", style=color)
                        text.append(make_bar(e.current, 100, 10) + "\n", style=color)
        except:
            text.append("  Thermal API Access Denied\n", style="red")
            
        return text
