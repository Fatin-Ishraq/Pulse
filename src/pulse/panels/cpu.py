from collections import deque
import psutil
from rich.text import Text

from pulse import core
from pulse.panels.base import Panel
from pulse.ui_utils import value_to_spark, value_to_heat_color, make_bar

from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Button, Label
from textual.message import Message

class CPUPanel(Panel):
    """Shows CPU core heat blocks with real data."""
    
    PANEL_NAME = "CPU"
    
    BINDINGS = [
        ("k", "kill_process", "Kill Process"),
        ("plus", "renice_up", "Lower Priority"),
        ("minus", "renice_down", "Higher Priority"),
    ]

    def __init__(self):
        super().__init__("CPU CORES", "", id="cpu-panel")
        self.core_count = psutil.cpu_count()
        # Track history for every core
        self.per_core_history = [deque(maxlen=30) for _ in range(self.core_count)]
        self.aggregate_history = deque(maxlen=80) 
        
        # Transcendence Control States
        self.sampling_rate = 1.0
        self.view_mode = "developer" # cinematic / developer
        self.scaling_mode = "absolute" # absolute / relative
        self.selected_pid = None # For process control
        
        # Initialize Core
        core.init()
    
    def action_kill_process(self):
        """Kill selected process via keyboard."""
        if self.selected_pid:
            core.kill_process(self.selected_pid)
            self.notify(f"Terminated PID {self.selected_pid}")
            self.selected_pid = None

    def action_renice_up(self):
        """Increase nice value (lower priority)."""
        self._adjust_nice(1)

    def action_renice_down(self):
        """Decrease nice value (higher priority)."""
        self._adjust_nice(-1)

    def _adjust_nice(self, delta):
        if not self.selected_pid: return
        try:
            p = psutil.Process(self.selected_pid)
            new_nice = max(-20, min(19, p.nice() + delta))
            core.renice_process(self.selected_pid, new_nice)
            self.notify(f"PID {self.selected_pid} Nice: {new_nice}")
        except:
            self.notify("Failed to renice", severity="error")

    def compose_transcendence(self):
        """Compose the interactive Core Management Console."""
        with Container(id="cpu-transcendence-layout"):
            # Top Section: Header & Stats
            with Horizontal(classes="header-section"):
                yield Static(id="cpu-hero-header")
            
            # Middle: Core Grid
            with Container(classes="core-section"):
                yield Static("CORE ARCHITECTURE", classes="section-title")
                yield Static(id="cpu-core-grid")
            
            # Bottom: Process Inspector
            with Container(classes="process-section"):
                yield Static("TOP OFFENDER ANALYSIS", classes="section-title")
                with Horizontal(id="process-control-box"):
                    yield Static(id="top-process-info", classes="process-info")
                    with Vertical(id="process-actions"):
                        yield Button("KILL PID [K]", id="btn-kill", variant="error")
                        with Horizontal():
                            yield Button("NICE + [+] ", id="btn-renice-up", variant="warning")
                            yield Button("NICE - [-] ", id="btn-renice-down", variant="success")
    
    def on_button_pressed(self, event: Button.Pressed):
        """Handle process control buttons."""
        if not self.selected_pid:
            return
            
        if event.button.id == "btn-kill":
            res = core.kill_process(self.selected_pid)
            self.notify(res)
            self.selected_pid = None
        elif event.button.id.startswith("btn-renice"):
            try:
                p = psutil.Process(self.selected_pid)
                nice = p.nice()
                if "up" in event.button.id: # Increase nice value (lower priority)
                    new_nice = min(19, nice + 1)
                else: # Decrease nice value (higher priority)
                    new_nice = max(-20, nice - 1)
                
                core.renice_process(self.selected_pid, new_nice)
                self.notify(f"Reniced PID {self.selected_pid} to {new_nice}")
            except:
                self.notify("Failed to renice process", severity="error")

    def update_transcendence(self, screen):
        """Update the interactive transcendence view."""
        # 1. Update Header
        try:
            avg = self.aggregate_history[-1] if self.aggregate_history else 0
            freq = psutil.cpu_freq()
            freq_str = f"{freq.current:.0f} MHz" if freq else "?"
            
            # Get Model Name (best effort)
            import platform
            model = platform.processor() or "Unknown CPU"

            header = Text()
            header.append(f"CPU LOAD: {avg:3.0f}%  ", style="bold " + value_to_heat_color(avg))
            header.append(make_bar(avg, 30, 20), style=value_to_heat_color(avg))
            header.append(f"   FREQ: {freq_str}   ", style="cyan")
            header.append(f"MODEL: {model[:20]}...", style="dim")
            screen.query_one("#cpu-hero-header", Static).update(header)
        except:
            pass # Widget might not be ready
        
        # 2. Update Core Grid (Visual) PLUS Kernel Stats
        try:
            # We'll use a dense block view
            grid = Text()
            percentages = core.get_cpu_percents() # This calls direct_os.get_cpu_percents which handles delta logic
            
            # Add Kernel Stats at top of grid
            stats = psutil.cpu_stats()
            grid.append(f"CTX SWITCH: {stats.ctx_switches:,} | INTERRUPTS: {stats.interrupts:,} | SYSCALLS: {stats.syscalls:,}\n\n", style="dim green")
            
            # Split into rows of 8
            row_len = 8
            for i, pct in enumerate(percentages):
                color = value_to_heat_color(pct)
                # Use a larger block for visual impact
                block = "███" if pct > 80 else "███" if pct > 40 else "███"
                val_str = f"{pct:3.0f}%"
                
                grid.append(f" CORE {i:02} ", style="dim white")
                grid.append(f"{val_str} ", style=color)
                grid.append(block, style=color)
                grid.append("   ")
                
                if (i + 1) % 4 == 0:
                    grid.append("\n\n")
            
            screen.query_one("#cpu-core-grid", Static).update(grid)
        except:
            pass

        # 3. Update Top Process (Heuristic: Max CPU)
        try:
            procs = core.get_process_list(sort_by='cpu', limit=1)
            if procs:
                top = procs[0]
                self.selected_pid = top['pid']
                
                info = Text()
                info.append(f"PID: {top['pid']}\n", style="bold yellow")
                info.append(f"NAME: {top['name']}\n", style="bold white")
                info.append(f"CPU: {top['cpu_percent']}%\n", style="red")
                # info.append(f"MEM: {top['memory_info'] / 1024 / 1024:.1f} MB", style="cyan")
                
                screen.query_one("#top-process-info", Static).update(info)
            else:
                screen.query_one("#top-process-info", Static).update("No active processes identified.")
        except:
            pass
    
    def update_data(self):
        # Use Direct OS engine for CPU data
        percentages = core.get_cpu_percents()
        
        # Store history
        for i, pct in enumerate(percentages):
            if i < len(self.per_core_history):
                self.per_core_history[i].append(pct)
        
        # Summary View: Heat Map Blocks
        text = Text()
        text.append("CPU ", style="cyan")
        for i, pct in enumerate(percentages):
            color = value_to_heat_color(pct)
            block = "█" if pct > 50 else "▓" if pct > 25 else "░"
            text.append(block, style=color)
            # Wrap every 8 cores for cleaner sidebar fit
            if (i + 1) % 8 == 0:
                text.append("\n    ")
            elif (i + 1) % 4 == 0:
                text.append(" ")
        
        avg = sum(percentages) / len(percentages) if percentages else 0
        self.aggregate_history.append(avg)
        text.append(f"\n{avg:.0f}% avg", style=value_to_heat_color(avg))
        self.update(text)
        
        # Critical Alert
        if avg > 90:
            self.add_class("alarm")
            self.border_title = "CPU CRITICAL"
        else:
            self.remove_class("alarm")
            # Don't reset styles.border/color here, let apply_theme handle standard state
            self.border_title = "CPU CORES"
    
    def get_transcendence_view(self) -> Text:
        """Ultimate Telemetry Console with switchable modes."""
        text = Text()
        avg = self.aggregate_history[-1] if self.aggregate_history else 0
        color = value_to_heat_color(avg)
        
        # --- HERO HEADER ---
        text.append(f"CPU CORE INFUSION ", style="bold")
        text.append(f"[{self.view_mode.upper()} MODE] ", style="cyan")
        text.append(f"{'⚡ HIGH-RES' if self.sampling_rate < 0.5 else ''}\n", style="yellow")
        
        text.append(f"LOAD: {avg:3.0f}% ", style=color)
        text.append(make_bar(avg, 100, 20), style=color)
        text.append("\n")

        if self.view_mode == "cinematic":
            # Massive Waveform Focus
            text.append("\nPERFORMANCE WAVEFORM (80s)\n", style="cyan")
            for val in self.aggregate_history:
                text.append(value_to_spark(val), style=value_to_heat_color(val))
            text.append("\n\nCORE HEAT MAP\n", style="cyan")
            cols = 4
            rows = (self.core_count + cols - 1) // cols
            for r in range(rows):
                for c in range(cols):
                    idx = r + c * rows
                    if idx < self.core_count:
                        pct = self.per_core_history[idx][-1] if self.per_core_history[idx] else 0
                        c_color = value_to_heat_color(pct)
                        text.append(f"C{idx:02} ", style="dim")
                        text.append("█" if pct > 50 else "▓" if pct > 20 else "░", style=c_color)
                        text.append(" ")
                text.append("\n")
        else:
            # Developer Focus (The raw telemetry we added before)
            text.append("\n80s PULSE: ", style="dim")
            for val in list(self.aggregate_history)[-30:]:
                text.append(value_to_spark(val), style=value_to_heat_color(val))
            
            text.append("\n\nSTATE BREAKDOWN\n", style="cyan")
            try:
                core_times = psutil.cpu_times_percent(percpu=True)
                core_pcts = psutil.cpu_percent(percpu=True)
                half = (self.core_count + 1) // 2
                for i in range(half):
                    for col in [i, i + half]:
                        if col < self.core_count:
                            t, p = core_times[col], core_pcts[col]
                            c = value_to_heat_color(p)
                            text.append(f"C{col:02} {p:3.0f}% ", style=c)
                            u, s = int(t.user/10), int(t.system/10)
                            text.append("[" + "█"*u + "▒"*s + "░"*(10-u-s) + "]  ", style=c)
                    text.append("\n")
            except:
                text.append("Developer mode restricted\n", style="red")

            text.append("\nKERNEL TELEMETRY\n", style="cyan")
            try:
                stats = psutil.cpu_stats()
                text.append(f"  Switches: {stats.ctx_switches:,}  Interrupts: {stats.interrupts:,}  Syscalls: {stats.syscalls:,}\n", style="dim")
                load = psutil.getloadavg()
                text.append(f"  Load Avg: {load[0]:.2f} / {load[1]:.2f} / {load[2]:.2f}\n", style="cyan")
            except:
                pass

        return text

    def get_detailed_view(self) -> Text:
        """Detailed CPU view with 2-column performance matrix."""
        text = Text()
        text.append("🔥 CORE PERFORMANCE MATRIX\n\n", style="bold")
        
        try:
            freq = psutil.cpu_freq()
            freq_str = f"{freq.current:.0f} MHz" if freq else "?"
            load_avg = psutil.getloadavg()
        except:
            freq_str = "?"
            load_avg = (0.0, 0.0, 0.0)
            
        text.append(f"THREADS: {self.core_count}  ", style="dim")
        text.append(f"CLOCK: {freq_str}  ", style="cyan")
        text.append(f"LOAD: {load_avg}\n\n", style="dim")

        # Render in 2 columns for high density
        half = (self.core_count + 1) // 2
        for i in range(half):
            # Left Column
            latest_l = self.per_core_history[i][-1] if self.per_core_history[i] else 0
            color_l = value_to_heat_color(latest_l)
            text.append(f"C{i:02} {latest_l:3.0f}% ", style=color_l)
            text.append(value_to_spark(latest_l), style=color_l)
            
            # Right Column
            idx_r = i + half
            if idx_r < self.core_count:
                latest_r = self.per_core_history[idx_r][-1] if self.per_core_history[idx_r] else 0
                color_r = value_to_heat_color(latest_r)
                text.append(f"   C{idx_r:02} {latest_r:3.0f}% ", style=color_r)
                text.append(value_to_spark(latest_r), style=color_r)
            
            text.append("\n")

        return text
