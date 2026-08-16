from datetime import datetime, timedelta

from rich.text import Text

from pulse.panels.base import Panel
from pulse.ui_utils import value_to_heat_color, make_bar

GIB = 1024 ** 3


def _format_duration(seconds: float) -> str:
    """Human-readable uptime, e.g. '3d 4h 12m'."""
    delta = timedelta(seconds=max(0, int(seconds)))
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes = remainder // 60
    if days:
        return f"{days}d {hours}h {minutes}m"
    return f"{hours}h {minutes}m"


class MainViewPanel(Panel):
    """The large central panel showing system overview or focused panel details."""

    PANEL_NAME = "SYSTEM"

    def __init__(self):
        super().__init__("SYSTEM", "", id="main-panel")
        self.focused_panel = None  # Set by the app when another panel is focused

    def _root_volume(self):
        """The volume the OS lives on, for the summary line."""
        snapshot = self.snapshot
        if snapshot is None or not snapshot.volumes:
            return None
        for volume in snapshot.volumes:
            if volume.mountpoint in ("/", "C:\\"):
                return volume
        return snapshot.volumes[0]

    def update_data(self):
        # If another panel is focused, show its detailed view instead.
        if self.focused_panel is not None:
            self.update(self.focused_panel.get_detailed_view())
            self.border_title = f"◆ {self.focused_panel.PANEL_NAME}"
            return

        self.border_title = "SYSTEM"

        snapshot = self.snapshot
        if snapshot is None:
            self.update(self.waiting_text())
            return

        text = Text()

        cpu = snapshot.cpu.percent
        text.append("CPU  ", style="bold")
        text.append(f"{cpu:5.1f}%  ", style=value_to_heat_color(cpu))
        text.append(make_bar(cpu, 100, 10) + "\n", style=value_to_heat_color(cpu))

        memory = snapshot.memory.percent
        text.append("RAM  ", style="bold")
        text.append(f"{memory:5.1f}%  ", style=value_to_heat_color(memory))
        text.append(make_bar(memory, 100, 10) + "\n", style=value_to_heat_color(memory))

        volume = self._root_volume()
        if volume is not None:
            text.append("DISK ", style="bold")
            text.append(f"{volume.percent:5.1f}%  ", style=value_to_heat_color(volume.percent))
            text.append(make_bar(volume.percent, 100, 10) + "\n",
                        style=value_to_heat_color(volume.percent))

        if snapshot.system.boot_time:
            uptime = datetime.now().timestamp() - snapshot.system.boot_time
            text.append(f"\n⏱ Up {_format_duration(uptime)}\n", style="dim")

        text.append(snapshot.system.platform_name, style="dim")

        self.update(text)

    def get_transcendence_view(self) -> Text:
        """Full-screen system dashboard."""
        snapshot = self.snapshot
        if snapshot is None:
            return self.waiting_text()

        system = snapshot.system

        text = Text()
        text.append("SYSTEM OVERVIEW\n", style="bold")
        text.append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n\n", style="dim")

        text.append("PLATFORM DETAILS\n", style="cyan")
        text.append(f"  OS:      {system.platform_name} {system.platform_release} "
                    f"({system.platform_version})\n", style="white")
        text.append(f"  Node:    {system.hostname}\n", style="dim")
        text.append(f"  Arch:    {system.architecture}\n", style="dim")
        text.append(f"  Proc:    {system.processor}\n\n", style="dim")

        if system.boot_time:
            boot = datetime.fromtimestamp(system.boot_time)
            uptime = datetime.now().timestamp() - system.boot_time
            text.append("SESSION STATUS\n", style="cyan")
            text.append(f"  Booted:  {boot.strftime('%Y-%m-%d %H:%M:%S')}\n", style="dim")
            text.append(f"  Uptime:  {_format_duration(uptime)}\n\n", style="green")

        text.append("RESOURCE UTILIZATION\n", style="cyan")

        cpu = snapshot.cpu.percent
        text.append(f"  CPU:     {cpu:5.1f}% ", style=value_to_heat_color(cpu))
        text.append(make_bar(cpu, 100, 20) + "\n", style=value_to_heat_color(cpu))

        memory = snapshot.memory
        text.append(f"  RAM:     {memory.percent:5.1f}% ",
                    style=value_to_heat_color(memory.percent))
        text.append(make_bar(memory.percent, 100, 20),
                    style=value_to_heat_color(memory.percent))
        text.append(f" ({memory.used / GIB:.1f}/{memory.total / GIB:.1f} GB)\n", style="dim")

        swap = memory.swap_percent
        text.append(f"  SWAP:    {swap:5.1f}% ", style=value_to_heat_color(swap))
        text.append(make_bar(swap, 100, 20) + "\n", style=value_to_heat_color(swap))

        volume = self._root_volume()
        if volume is not None:
            label = volume.mountpoint[:8]
            text.append(f"  DISK ({label}):{volume.percent:5.1f}% ",
                        style=value_to_heat_color(volume.percent))
            text.append(make_bar(volume.percent, 100, 20) + "\n",
                        style=value_to_heat_color(volume.percent))

        battery = system.battery
        if battery is not None:
            text.append("\nPOWER STATUS\n", style="cyan")
            plugged = "⚡ Plugged In" if battery.power_plugged else "🔋 On Battery"
            color = "green" if battery.percent > 20 else "red"
            text.append(f"  Level:   {battery.percent:.0f}% ({plugged})\n", style=color)
            if battery.seconds_left is not None:
                minutes = battery.seconds_left // 60
                text.append(f"  Est. Time: {minutes // 60}h {minutes % 60}m remaining\n",
                            style="dim")

        return text

    def get_detailed_view(self) -> Text:
        """This panel shows other panels' details, not its own."""
        return Text("System Overview - Tab to other panels for details")
