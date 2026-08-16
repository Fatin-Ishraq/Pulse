from collections import deque
import psutil
from rich.text import Text

from pulse import core
from pulse.panels.base import Panel
from pulse.ui_utils import value_to_spark, value_to_heat_color

from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Button

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
        ("k", "kill_process", "Kill Top Process"),
        ("plus", "renice_up", "Lower Priority"),
        ("minus", "renice_down", "Higher Priority"),
    ]
    
    def __init__(self):
        super().__init__("MEMORY", "", id="memory-panel")
        self.history = deque(maxlen=80)

        # Transcendence Control States
        self.sampling_rate = 1.0
        self.view_mode = "developer" # cinematic / developer
        # The heaviest process currently on display. Actions name it explicitly
        # and confirm before touching it - see Panel.request_kill.
        self.top_pid = None

        core.init()

    def action_kill_process(self):
        """Terminate the displayed top process, after confirmation."""
        self.request_kill(self.top_pid)

    def action_renice_up(self):
        """Increase nice value (lower priority)."""
        self.request_renice(self.top_pid, 1)

    def action_renice_down(self):
        """Decrease nice value (higher priority)."""
        self.request_renice(self.top_pid, -1)

    def compose_transcendence(self):
        """Compose the interactive Memory Management Console."""
        with Container(id="mem-transcendence-layout"):
            # Top Section: Header & Stats
            with Horizontal(classes="header-section"):
                yield Static(id="mem-hero-header")
            
            # Middle: Memory Map
            with Container(classes="core-section"):
                yield Static("ALLOCATION MAP (PHYSICAL vs SWAP)", classes="section-title")
                yield Static(id="mem-allocation-map")
            
            # Bottom: Process Inspector
            with Container(classes="process-section"):
                yield Static("TOP MEMORY OFFENDER", classes="section-title")
                with Horizontal(id="process-control-box"):
                    yield Static(id="mem-top-process-info", classes="process-info")
                    with Vertical(id="process-actions"):
                        yield Button("KILL PID [K]", id="btn-kill", variant="error")
                        with Horizontal():
                            yield Button("NICE + [+] ", id="btn-renice-up", variant="warning")
                            yield Button("NICE - [-] ", id="btn-renice-down", variant="success")

    def on_button_pressed(self, event: Button.Pressed):
        """Handle process control buttons."""
        if event.button.id == "btn-kill":
            self.request_kill(self.top_pid)
        elif event.button.id == "btn-renice-up":
            self.request_renice(self.top_pid, 1)
        elif event.button.id == "btn-renice-down":
            self.request_renice(self.top_pid, -1)

    def update_transcendence(self, screen):
        """Update the interactive transcendence view."""
        self.update_data() # Ensure fresh data
        
        # 1. Update Header
        try:
            data = core.get_memory_info()
            mem = MemAdapter(data)
            swap = MemAdapter(data, prefix="swap_")
            
            header = Text()
            header.append(f"MEM PRESSURE: {mem.percent:3.0f}%  ", style="bold " + value_to_heat_color(mem.percent))
            from pulse.ui_utils import make_bar
            header.append(make_bar(mem.percent, 30, 20), style=value_to_heat_color(mem.percent))
            header.append(f"   SWAP: {swap.percent:.0f}%   ", style="yellow")
            header.append(f"TOTAL: {mem.total / (1024**3):.1f} GB", style="dim")
            screen.query_one("#mem-hero-header", Static).update(header)
            
            # 2. Update Allocation Map
            # Visual layout of physical vs swap
            # 100 blocks total
            total_vol = mem.total + swap.total
            phys_blocks = int((mem.used / total_vol) * 100) if total_vol else 0
            swap_blocks = int((swap.used / total_vol) * 100) if total_vol else 0
            
            amap = Text()
            # Physical
            amap.append("PHYSICAL RAM IN USE\n", style="cyan")
            amap.append("█" * phys_blocks, style="cyan")
            amap.append("░" * (50 - phys_blocks) if phys_blocks < 50 else "", style="dim cyan")
            
            amap.append("\n\nSWAP FILE COMMITTED\n", style="yellow")
            amap.append("▓" * swap_blocks, style="yellow")
            
            amap.append("\n\nSTATS:\n", style="bold")
            amap.append(f"  Available: {mem.available / (1024**3):.2f} GB\n", style="green")
            amap.append(f"  Used:      {mem.used / (1024**3):.2f} GB\n", style="cyan")
            amap.append(f"  Swap Used: {swap.used / (1024**3):.2f} GB", style="yellow")
            
            screen.query_one("#mem-allocation-map", Static).update(amap)
            
        except Exception:
            pass # Guard against race conditions
            
        # 3. Update Top Memory Offender
        try:
            procs = core.get_process_list(sort_by='mem', limit=1)
            if procs:
                top = procs[0]
                # Tracked for display; the action itself names this process in a
                # confirmation before doing anything to it.
                self.top_pid = top['pid']
                mem_mb = top['memory_info'] / (1024 * 1024)

                info = Text()
                info.append(f"PID: {top['pid']}\n", style="bold yellow")
                info.append(f"NAME: {top['name']}\n", style="bold white")
                info.append(f"MEM: {mem_mb:.1f} MB\n", style="cyan")
                info.append("Actions below apply to this process.", style="dim")

                screen.query_one("#mem-top-process-info", Static).update(info)
            else:
                self.top_pid = None
                screen.query_one("#mem-top-process-info", Static).update("No active processes identified.")
        except Exception:
            pass


    def update_data(self):
        try:
            # Get memory info from Direct OS engine
            data = core.get_memory_info()
            mem = MemAdapter(data)
            swap = MemAdapter(data, prefix="swap_")
            used_gb = mem.used / (1024**3)
            total_gb = mem.total / (1024**3)
            pct = mem.percent
        except Exception:
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
            # sin/sout are cumulative pages swapped in/out. Windows reports 0.
            if swap.sin or swap.sout:
                text.append(
                    f"  Swap In/Out:  {swap.sin/(1024**2):.1f} MB / {swap.sout/(1024**2):.1f} MB\n",
                    style="dim",
                )

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
