from rich.text import Text

from pulse.panels.base import Panel
from pulse.ui_utils import value_to_spark, value_to_heat_color, make_bar


def _format_duration(seconds: float) -> str:
    total = int(max(0, seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    if hours:
        return f"{hours}h {minutes}m"
    if minutes:
        return f"{minutes}m {secs}s"
    return f"{secs}s"


class InsightPanel(Panel):
    """System pressure summary and session analytics.

    The "tension" score is a documented heuristic - a weighted blend of CPU,
    memory and I/O saturation. It is not a model or a prediction.
    """

    PANEL_NAME = "INTELLIGENCE"

    def __init__(self):
        super().__init__("INTELLIGENCE", "", id="insight-panel")

        # Transcendence Control States
        self.sampling_rate = 0.05  # Fast refresh for the Aether visualisation
        self.view_mode = "aether"  # aether / developer
        self.scaling_mode = "auto"

        # Aether Engine (lazy init - it is pure animation, not telemetry)
        self._aether_engine = None
        self._aether_width = 80
        self._aether_height = 24

    def _get_aether_engine(self):
        if self._aether_engine is None:
            from pulse.aether.engine import AetherEngine
            self._aether_engine = AetherEngine(self._aether_width, self._aether_height)
        return self._aether_engine

    def set_aether_size(self, width: int, height: int):
        self._aether_width = width
        self._aether_height = height
        if self._aether_engine:
            self._aether_engine.resize(width, height)

    # ------------------------------------------------------------------
    # Summary view
    # ------------------------------------------------------------------
    def update_data(self):
        snapshot = self.snapshot
        if snapshot is None:
            self.update(self.waiting_text())
            return

        tension = self.store.tension
        color = value_to_heat_color(tension)

        text = Text()
        text.append("TENSION: ", style="dim")
        text.append(f"{tension:.0f}%\n", style=color)
        text.append(make_bar(tension, 100, 18) + "\n\n", style=color)

        text.append(f"» {self._advice(snapshot)}", style=self._advice_style(snapshot))
        self.update(text)

    def _advice(self, snapshot) -> str:
        if snapshot.cpu.percent > 80:
            return "Heavy Compute Load"
        if snapshot.memory.percent > 90:
            return "RAM Saturated"
        if self.rates.disk_read_mbps + self.rates.disk_write_mbps > 40:
            return "Heavy Disk Traffic"
        return "System Stable"

    def _advice_style(self, snapshot) -> str:
        if snapshot.memory.percent > 90:
            return "red"
        if snapshot.cpu.percent > 80:
            return "orange1"
        return "green"

    # ------------------------------------------------------------------
    # Transcendence
    # ------------------------------------------------------------------
    def get_transcendence_view(self) -> Text:
        """Render the Aether visualisation or the developer stats."""
        text = Text()

        if self.view_mode == "aether":
            engine = self._get_aether_engine()
            snapshot = self.snapshot
            if snapshot is not None:
                # The engine animates from the shared snapshot rather than
                # sampling the machine itself.
                engine.set_metrics(
                    cpu=snapshot.cpu.percent,
                    memory=snapshot.memory.percent,
                    io_intensity=min(1.0, (self.rates.disk_read_mbps
                                           + self.rates.disk_write_mbps) / 50.0),
                    cpu_history=self.history.cpu,
                )

            text.append(f" {engine.get_atmosphere_char()} ", style="bold cyan")
            text.append(engine.get_status_line(), style="dim")
            text.append(f" {engine.get_atmosphere_char()}\n\n", style="bold cyan")
            text.append(engine.render_frame(), style="cyan")
            return text

        # Developer mode: session statistics
        peaks = self.store.peaks

        text.append("SYSTEM INSIGHT ", style="bold")
        text.append("[DEVELOPER MODE]\n", style="cyan")

        text.append("\nSESSION PEAK METRICS\n", style="cyan")
        text.append(f"  CPU Peak:        {peaks.cpu:>5.1f}%\n", style="cyan")
        text.append(f"  Memory Peak:     {peaks.memory:>5.1f}%\n", style="cyan")
        text.append(f"  Net Up Peak:     {peaks.net_sent_kbps:>7.1f} KB/s\n", style="yellow")
        text.append(f"  Net Down Peak:   {peaks.net_recv_kbps:>7.1f} KB/s\n", style="yellow")
        text.append(f"  Disk Read Peak:  {peaks.disk_read_mbps:>7.2f} MB/s\n", style="green")
        text.append(f"  Disk Write Peak: {peaks.disk_write_mbps:>7.2f} MB/s\n", style="green")

        text.append(f"\n  Session Time:    {_format_duration(self.store.uptime_seconds)}\n",
                    style="dim")
        text.append(f"  Ticks Sampled:   {self.store.tick_count}\n", style="dim")

        text.append("\nTENSION TRACE\n", style="cyan")
        for value in self.history.tension:
            text.append(value_to_spark(value), style=value_to_heat_color(value))
        text.append("\n")

        text.append("\nHEURISTIC WEIGHTS\n", style="cyan")
        text.append("  Compute:  40%\n", style="dim")
        text.append("  Memory:   40%\n", style="dim")
        text.append("  Disk I/O: 20%\n", style="dim")

        snapshot = self.snapshot
        if snapshot is not None and snapshot.errors:
            text.append("\nDEGRADED SUBSYSTEMS\n", style="red")
            for name, message in snapshot.errors.items():
                text.append(f"  {name}: {message}\n", style="red dim")

        return text

    # ------------------------------------------------------------------
    # Detail view
    # ------------------------------------------------------------------
    def get_detailed_view(self) -> Text:
        """Deep analytics with tension waveform and current strains."""
        snapshot = self.snapshot
        if snapshot is None:
            return self.waiting_text()

        tension = self.store.tension
        peaks = self.store.peaks

        text = Text()
        text.append("🧠 SYSTEM INTELLIGENCE\n\n", style="bold")

        text.append("Session Tension Pulse\n", style="cyan")
        for value in self.history.tension:
            text.append(value_to_spark(value), style=value_to_heat_color(value))
        text.append(f" {tension:.0f}%\n\n", style=value_to_heat_color(tension))

        text.append("Primary Resource Strains\n", style="cyan")
        strain_found = False
        if snapshot.cpu.percent > 70:
            text.append(f"  [!] COMPUTE: High CPU Pressure ({snapshot.cpu.percent:.0f}%)\n",
                        style="orange1")
            strain_found = True
        if snapshot.memory.percent > 85:
            text.append(f"  [!] MEMORY: RAM Saturated ({snapshot.memory.percent:.0f}%)\n",
                        style="red")
            strain_found = True
        if self.rates.disk_read_mbps + self.rates.disk_write_mbps > 40:
            text.append("  [!] STORAGE: Heavy disk traffic\n", style="orange1")
            strain_found = True
        if snapshot.errors:
            text.append(f"  [!] TELEMETRY: {len(snapshot.errors)} subsystem(s) degraded\n",
                        style="red")
            strain_found = True

        if not strain_found:
            text.append("  [✓] All subsystems operating within nominal range.\n",
                        style="green")

        text.append("\nSession Peaks\n", style="cyan")
        text.append(f"  CPU Peak:    {peaks.cpu:5.1f}%\n", style="dim")
        text.append(f"  Memory Peak: {peaks.memory:5.1f}%\n", style="dim")

        text.append(f"\nMonitoring Session: {_format_duration(self.store.uptime_seconds)}\n",
                    style="dim")

        return text
