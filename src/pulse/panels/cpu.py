from collections import deque
import psutil
from rich.text import Text

from pulse import core
from pulse.panels.base import Panel
from pulse.ui_utils import value_to_spark, value_to_heat_color, make_bar

class CPUPanel(Panel):
    """Shows CPU core heat blocks with real data."""
    
    PANEL_NAME = "CPU"
    
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
        
        # Initialize Core
        core.init()
    
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
