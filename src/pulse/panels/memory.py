from collections import deque
import psutil
from rich.text import Text

from pulse import core
from pulse.panels.base import Panel
from pulse.ui_utils import value_to_spark, value_to_heat_color

# Adapter for Rust dict to psutil-like object
class MemAdapter:
    def __init__(self, d, prefix=""):
        self.total = d.get(f"{prefix}total", 0)
        self.used = d.get(f"{prefix}used", 0)
        self.free = d.get(f"{prefix}free", 0)
        self.available = d.get("available", 0)
        self.percent = (self.used / self.total * 100) if self.total > 0 else 0

class MemoryPanel(Panel):
    """Shows memory usage as a live pressure bar."""
    
    PANEL_NAME = "MEMORY"
    BINDINGS = [
        ("f", "optimize", "Flush/Optimize"),
    ]
    
    def __init__(self):
        super().__init__("MEMORY", "", id="memory-panel")
        self.history = deque(maxlen=80) 
        self.optimizing = False
        
        # Transcendence Control States
        self.sampling_rate = 1.0
        self.view_mode = "developer" # cinematic / developer
        self.scaling_mode = "absolute" # absolute / relative
        
        core.init()

    def action_optimize(self):
        """Simulate memory optimization/cache flush."""
        self.optimizing = True
        self.notify("Initiating Memory Pulse Optimization...", severity="information")
        
        def reset_opt():
            self.optimizing = False
            self.refresh()
            
        import threading
        threading.Timer(1.5, reset_opt).start()
        self.refresh()
    
    def update_data(self):
        try:
            data = core.get_memory_info(lambda: None)
            if data and isinstance(data, dict):
                mem = MemAdapter(data)
                swap = MemAdapter(data, prefix="swap_")
            else:
                mem = psutil.virtual_memory()
                swap = psutil.swap_memory()
            used_gb = mem.used / (1024**3)
            total_gb = mem.total / (1024**3)
            pct = mem.percent
        except:
            return
        
        text = Text()
        text.append("MEM ", style="cyan")
        bar_width = 12
        filled = int(pct / 100 * bar_width)
        color = value_to_heat_color(pct)
        
        self.history.append(pct)
        
        text.append("█" * filled, style=color)
        text.append("░" * (bar_width - filled), style="dim")
        text.append(f"\n{used_gb:.1f}/{total_gb:.1f}GB", style=color)
        self.update(text)
        
        # Critical Alert
        if pct > 95:
            self.add_class("alarm")
            self.styles.border = ("heavy", "red")
            self.styles.color = "red"
            self.border_title = "MEM CRITICAL"
        else:
            self.remove_class("alarm")
            self.border_title = "MEMORY"

    def get_transcendence_view(self) -> Text:
        """Immersive Memory console with pressure waves and allocation mapping."""
        if self.optimizing:
            msg = Text("\n\n  ⚡ INITIATING MEMORY PURGE...\n", style="bold cyan")
            msg.append("  " + "█" * 20, style="cyan")
            return msg
            
        text = Text()
        try:
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
        except:
            return Text("Memory Telemetry Offline")

        color = value_to_heat_color(mem.percent)
        from pulse.ui_utils import make_bar

        # --- HERO HEADER ---
        text.append(f"MEMORY DEPTH ANALYTICS ", style="bold")
        text.append(f"[{self.view_mode.upper()} MODE]\n", style="cyan")
        
        text.append(f"PRESSURE: {mem.percent:3.0f}% ", style=color)
        text.append(make_bar(mem.percent, 100, 20), style=color)
        text.append(f"  SWAP: {swap.percent:3.0f}%\n", style="dim")
        
        if self.view_mode == "cinematic":
            # Massive Waveform Focus
            text.append("\nPRESSURE WAVEFORM (80s)\n", style="cyan")
            for val in self.history:
                text.append(value_to_spark(val), style=value_to_heat_color(val))
            
            text.append("\n\nALLOCATION LANDSCAPE\n", style="cyan")
            # Visual layout of physical vs swap
            total_vol = mem.total + swap.total
            phys_ratio = int((mem.used / total_vol) * 40)
            swap_ratio = int((swap.used / total_vol) * 40)
            free_ratio = 40 - phys_ratio - swap_ratio
            
            text.append("PHYS [", style="dim")
            text.append("█" * phys_ratio, style="cyan")
            text.append("] SWAP [", style="dim")
            text.append("▓" * swap_ratio, style="yellow")
            text.append("] FREE [", style="dim")
            text.append("░" * max(0, free_ratio), style="dim")
            text.append("]\n", style="dim")
        else:
            # Developer Focus: Detailed Subsystems
            text.append("\n80s PRESSURE: ", style="dim")
            for val in list(self.history)[-30:]:
                text.append(value_to_spark(val), style=value_to_heat_color(val))
            
            text.append("\n\nSUBSYSTEM BREAKDOWN\n", style="cyan")
            
            # Cross-platform safe breakdown
            data = [
                ("Physical Total", f"{mem.total/(1024**3):.2f} GB"),
                ("Available", f"{mem.available/(1024**3):.2f} GB"),
                ("Used (Kernel+Apps)", f"{mem.used/(1024**3):.2f} GB"),
            ]
            
            # Platform specifics
            if hasattr(mem, 'cached'):
                data.append(("Cached", f"{mem.cached/(1024**3):.2f} GB"))
            if hasattr(mem, 'buffers'):
                data.append(("Buffers", f"{mem.buffers/(1024**3):.2f} GB"))
            
            for label, val in data:
                text.append(f"  {label:<20} ", style="dim")
                text.append(f"{val:>12}\n", style="cyan")
                
            text.append("\nSWAP & PAGING\n", style="cyan")
            text.append(f"  Swap Used:    {swap.used/(1024**3):6.2f} GB / {swap.total/(1024**3):.2f} GB\n", style="dim")
            
            try:
                # Some platforms provide paging stats
                vm = psutil.swap_memory()
                text.append(f"  Total Faults: {getattr(psutil, 'wait_procs', lambda:[])[0] if hasattr(psutil, 'cpu_stats') else 'N/A'}\n", style="dim dim")
                # text.append(f"  Swap In/Out:  {vm.sin/(1024**2):.1f}MB / {vm.sout/(1024**2):.1f}MB\n", style="dim") # Often 0 on Windows
            except:
                pass

        return text

    def get_detailed_view(self) -> Text:
        """Detailed memory breakdown with pressure waveform."""
        text = Text()
        text.append("💾 MEMORY ANALYTICS\n\n", style="bold")
        
        try:
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
        except:
            return Text("Memory telemetry unavailable")
        
        # Pressure Waveform
        text.append("Pressure Waveform (Last 40s)\n", style="cyan")
        for val in list(self.history)[-40:]:
            text.append(value_to_spark(val), style=value_to_heat_color(val))
        text.append(f" {mem.percent:.0f}%\n\n", style=value_to_heat_color(mem.percent))

        # Status Table
        text.append(f"{'TYPE':<12} {'TOTAL':<10} {'USED':<10} {'FREE':<10}\n", style="dim")
        text.append("─" * 45 + "\n", style="dim")
        text.append(f"{'Physical':<12} {mem.total/(1024**3):.1f}GB    {mem.used/(1024**3):.1f}GB    {mem.free/(1024**3):.1f}GB\n")
        text.append(f"{'Swap':<12} {swap.total/(1024**3):.1f}GB    {swap.used/(1024**3):.1f}GB    {swap.free/(1024**3):.1f}GB\n\n")

        # Allocation Map
        text.append("Allocation Map\n", style="cyan")
        total = mem.total
        # Segments: Used, Available
        used_p = int((mem.used / total) * 30)
        avail_p = 30 - used_p
        text.append("[" + "█"*used_p + "▒"*avail_p + "]\n", style="cyan")
        text.append(f"  {'Used':<8} {mem.used/(1024**3):.1f}GB\n", style="dim")
        text.append(f"  {'Avail':<8} {mem.available/(1024**3):.1f}GB\n", style="dim")

        return text
