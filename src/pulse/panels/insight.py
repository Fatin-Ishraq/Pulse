from datetime import datetime
from collections import deque
import psutil
from rich.text import Text

from pulse.panels.base import Panel
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
        self.history = deque(maxlen=80)
        self.start_time = datetime.now()
        
        # Transcendence Control States
        self.sampling_rate = 0.05  # Fast refresh for Aether (20 FPS)
        self.view_mode = "aether"  # aether / developer
        self.scaling_mode = "auto"
        
        # Aether Engine (lazy init)
        self._aether_engine = None
        self._aether_width = 80
        self._aether_height = 24
        
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
    
    def _get_aether_engine(self):
        """Lazy initialization of the Aether engine."""
        if self._aether_engine is None:
            from pulse.aether.engine import AetherEngine
            self._aether_engine = AetherEngine(self._aether_width, self._aether_height)
        return self._aether_engine
    
    def set_aether_size(self, width: int, height: int):
        """Set the Aether canvas size."""
        self._aether_width = width
        self._aether_height = height
        if self._aether_engine:
            self._aether_engine.resize(width, height)

    def get_transcendence_view(self) -> Text:
        """Render the Aether visualization or developer stats."""
        text = Text()
        
        if self.view_mode == "aether":
            # === AETHER MODE ===
            engine = self._get_aether_engine()
            
            # Render a frame
            frame = engine.render_frame()
            status = engine.get_status_line()
            atmosphere = engine.get_atmosphere_char()
            
            # Build the output
            text.append(f" {atmosphere} ", style="bold cyan")
            text.append(status, style="dim")
            text.append(f" {atmosphere}\n\n", style="bold cyan")
            text.append(frame, style="cyan")
            
        elif self.view_mode == "developer":
            # Developer Mode: Session Statistics
            text.append("NEURAL INSIGHT ENGINE ", style="bold")
            text.append("[DEVELOPER MODE]\n", style="cyan")
            
            text.append("\nSESSION PEAK METRICS\n", style="cyan")
            text.append(f"  CPU Peak:        {self.peaks['cpu']:>5.1f}%\n", style="cyan")
            text.append(f"  Memory Peak:     {self.peaks['mem']:>5.1f}%\n", style="cyan")
            
            runtime = datetime.now() - self.start_time
            text.append(f"  Session Time:    {str(runtime).split('.')[0]}\n", style="dim")
            
            text.append("\nNEURAL NETWORK TOPOLOGY\n", style="cyan")
            text.append("  Tension Pulse Trace (80 samples)\n", style="dim")
            for val in list(self.history):
                text.append(value_to_spark(val), style=value_to_heat_color(val))
            text.append("\n")
            
            text.append("\nHEURISTIC WEIGHTS\n", style="cyan")
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
        self.tension_score = (cpu * 0.4 + mem * 0.4 + 20)
        self.tension_score = min(100, self.tension_score)
        self.history.append(self.tension_score)
        
        text = Text()
        color = value_to_heat_color(self.tension_score)
        
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
        text.append("Session Tension Pulse (Last 40s)\n", style="cyan")
        for val in self.history:
            text.append(value_to_spark(val), style=value_to_heat_color(val))
        text.append(f" {self.tension_score:.0f}%\n\n", style=value_to_heat_color(self.tension_score))

        # System Strains
        text.append("Primary Resource Strains\n", style="cyan")
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
        text.append("\nSession Peaks\n", style="cyan")
        text.append(f"  CPU Peak:    {self.peaks['cpu']:5.1f}%\n", style="dim")
        text.append(f"  Memory Peak: {self.peaks['mem']:5.1f}%\n", style="dim")
        
        runtime = datetime.now() - self.start_time
        mins = int(runtime.total_seconds() // 60)
        text.append(f"\nMonitoring Session: {mins} minutes active\n", style="dim")
        
        return text
