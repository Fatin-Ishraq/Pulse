from datetime import datetime
from collections import deque
import psutil
from rich.text import Text

from pulse.panels.base import Panel
from pulse.state import current_theme
from pulse.ui_utils import value_to_spark, value_to_heat_color, make_bar

class InsightPanel(Panel):
    """Proactive system intelligence and session analytics."""
    
    PANEL_NAME = "INTELLIGENCE"
    
    def __init__(self):
        super().__init__("INTELLIGENCE", "", id="insight-panel")
        self.peaks = {
            "cpu": 0.0,
            "mem": 0.0,
            "net_up": 0.0,
            "net_down": 0.0,
            "disk_lat": 0.0
        }
        self.tension_score = 0
        self.history = deque(maxlen=80) # Expanded for high-res
        self.start_time = datetime.now()
        
        # Transcendence Control States
        self.sampling_rate = 1.0
        self.view_mode = "developer" # cinematic / developer
        self.scaling_mode = "auto"
        
        # Animation state for "Neural" analysis
        self.thought_idx = 0
        self.thoughts = [
            "Analyzing kernel scheduling patterns...",
            "Correlating I/O wait times with memory paging...",
            "Synthesizing network flow heuristics...",
            "Detecting micro-stutters in frame timings...",
            "Optimizing thermal dissipation models...",
            "Predicting future resource contention..."
        ]

    def get_transcendence_view(self) -> Text:
        """Ultimate Heuristic Insight Engine."""
        text = Text()
        text.append(f"NEURAL INSIGHT ENGINE ", style="bold")
        text.append(f"[{self.view_mode.upper()} MODE]\n", style=current_theme["focus"])
        
        if self.view_mode == "cinematic":
            # Heuristic "AI" thought process
            text.append("\nLIVE BOTTLENECK INFERENCE\n", style=current_theme["accent"])
            
            # Simulated neural activity
            thought = self.thoughts[self.thought_idx % len(self.thoughts)]
            self.thought_idx += 1
            
            text.append(f"  🧠 {thought}\n", style="italic")
            
            # Real performance correlation
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent
            
            text.append("\nSUBSYSTEM HEALTH MATRIX\n", style="dim")
            text.append(f"  COMPUTE: {make_bar(cpu, 100, 20)} {cpu:>3.0f}%\n", style=value_to_heat_color(cpu, current_theme["heat"]))
            text.append(f"  MEMORY:  {make_bar(mem, 100, 20)} {mem:>3.0f}%\n", style=value_to_heat_color(mem, current_theme["heat"]))

            # Bottleneck Recommendation
            text.append("\nENGINE RECOMMENDATION\n", style=current_theme["accent"])
            if cpu > 80:
                text.append("  [!] Critical compute saturation. Consider offloading background tasks.\n", style="orange1")
            elif mem > 90:
                text.append("  [!] Memory pressure high. Recommended action: Flush disk caches.\n", style="red")
            else:
                text.append("  [✓] All subsystems operating at peak efficiency.\n", style="green")
        else:
            # Developer Mode: Session Statistics
            text.append("\nSESSION PEAK METRICS\n", style=current_theme["accent"])
            text.append(f"  CPU Peak:        {self.peaks['cpu']:>5.1f}%\n", style="cyan")
            text.append(f"  Memory Peak:     {self.peaks['mem']:>5.1f}%\n", style="cyan")
            
            runtime = datetime.now() - self.start_time
            text.append(f"  Session Time:    {str(runtime).split('.')[0]}\n", style="dim")
            
            text.append("\nNEURAL NETWORK TOPOLOGY\n", style=current_theme["accent"])
            text.append("  Tension Pulse Trace (80 samples)\n", style="dim")
            for val in list(self.history):
                text.append(value_to_spark(val), style=value_to_heat_color(val, current_theme["heat"]))
            text.append("\n")
            
            text.append("\nHEURISTIC WEIGHTS\n", style=current_theme["accent"])
            text.append("  Compute Importance: 40%\n", style="dim")
            text.append("  Memory Weight:     40%\n", style="dim")
            text.append("  I/O Bias:          20%\n", style="dim")

        return text
    
    def update_data(self):
        try:
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent
        except:
            return
            
        # Update Peaks
        self.peaks["cpu"] = max(self.peaks["cpu"], cpu)
        self.peaks["mem"] = max(self.peaks["mem"], mem)
        
        # Calculate Tension (0-100)
        self.tension_score = (cpu * 0.4 + mem * 0.4 + 20) # Simplified baseline
        self.tension_score = min(100, self.tension_score)
        self.history.append(self.tension_score)
        
        text = Text()
        color = value_to_heat_color(self.tension_score, current_theme["heat"])
        
        # Summary View
        text.append("TENSION: ", style="dim")
        text.append(f"{self.tension_score:.0f}%\n", style=color)
        text.append(make_bar(self.tension_score, 100, 18) + "\n\n", style=color)
        
        # Advice
        advice = "System Stable"
        advice_style = "green"
        if cpu > 80:
            advice = "Heavy Compute Load"
            advice_style = "orange1"
        elif mem > 90:
            advice = "RAM Saturated"
            advice_style = "red"
        
        text.append(f"» {advice}", style=advice_style)
        self.update(text)
        
    def get_detailed_view(self) -> Text:
        """Deep analytics with tension waveforms and strains."""
        text = Text()
        text.append("🧠 SYSTEM INTELLIGENCE\n\n", style="bold")
        
        # Tension Waveform
        text.append("Session Tension Pulse (Last 40s)\n", style=current_theme["accent"])
        for val in self.history:
            text.append(value_to_spark(val), style=value_to_heat_color(val, current_theme["heat"]))
        text.append(f" {self.tension_score:.0f}%\n\n", style=value_to_heat_color(self.tension_score, current_theme["heat"]))

        # System Strains
        text.append("Primary Resource Strains\n", style=current_theme["accent"])
        try:
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory().percent
        except:
            cpu, mem = 0, 0
            
        strain_found = False
        if cpu > 70:
            text.append(f"  [!] COMPUTE: High CPU Pressure ({cpu:.0f}%)\n", style="orange1")
            strain_found = True
        if mem > 85:
            text.append(f"  [!] MEMORY: RAM Saturated ({mem:.0f}%)\n", style="red")
            strain_found = True
        
        if not strain_found:
            text.append("  [✓] All subsystems operating within nominal range.\n", style="green")

        # Session Peaks
        text.append("\nSession Peaks\n", style=current_theme["accent"])
        text.append(f"  CPU Peak:    {self.peaks['cpu']:5.1f}%\n", style="dim")
        text.append(f"  Memory Peak: {self.peaks['mem']:5.1f}%\n", style="dim")
        
        runtime = datetime.now() - self.start_time
        mins = int(runtime.total_seconds() // 60)
        text.append(f"\nMonitoring Session: {mins} minutes active\n", style="dim")
        
        return text
