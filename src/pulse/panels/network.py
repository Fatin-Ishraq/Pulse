from rich.text import Text

from pulse.panels.base import Panel
from pulse.ui_utils import value_to_spark, value_to_heat_color, make_bar

from textual.containers import Container, Horizontal
from textual.widgets import Static, Button, DataTable
from textual.binding import Binding

GIB = 1024 ** 3
MIB = 1024 ** 2
# Reference ceiling for the throughput bars, in KB/s.
BAR_SCALE_KBPS = 1000


class NetworkPanel(Panel):
    """Network upload/download activity."""

    PANEL_NAME = "NETWORK"

    BINDINGS = [
        Binding("f", "optimize", "Reset Counters"),
        Binding("k", "kill_connection", "Kill PID"),
        Binding("r", "refresh_stats", "Refresh"),
    ]

    def __init__(self):
        super().__init__("NETWORK", "", id="net-panel")
        self.sampling_rate = 1.0
        self.view_mode = "developer"  # cinematic / developer

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def action_optimize(self):
        """Clear the network waveforms without disturbing other history."""
        self.store.reset_network_baseline()
        self.notify("Network waveforms reset.")

    def action_refresh_stats(self):
        self.app.refresh_data()

    def action_kill_connection(self):
        """Terminate the process owning the selected connection, after confirming."""
        try:
            table = self.app.screen.query_one("#net_table", DataTable)
        except Exception:
            self.notify("Press X for the full network view to manage connections.",
                        severity="warning")
            return

        if table.cursor_row is None:
            self.notify("No connection selected.", severity="warning")
            return

        try:
            # Row key starts with the owning PID - see update_transcendence.
            raw_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value
        except (AttributeError, TypeError):
            self.notify("Could not identify the selected connection.", severity="error")
            return

        pid_str = str(raw_key).split("_")[0]
        if not pid_str.isdigit():
            self.notify("This socket has no owning process Pulse can see.",
                        severity="warning")
            return

        self.request_kill(int(pid_str))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_kill":
            self.action_kill_connection()
        elif event.button.id == "btn_refresh":
            self.action_refresh_stats()

    # ------------------------------------------------------------------
    # Summary view
    # ------------------------------------------------------------------
    def update_data(self):
        snapshot = self.snapshot
        if snapshot is None:
            self.update(self.waiting_text())
            return

        network = snapshot.network
        rates = self.rates

        text = Text()
        text.append("UP   ", style="yellow")
        text.append(f"{rates.net_sent_kbps:4.0f}KB/s ", style="dim")
        for value in list(self.history.net_sent)[-15:]:
            text.append(value_to_spark(value, 100), style="yellow")

        text.append("\nDOWN ", style="cyan")
        text.append(f"{rates.net_recv_kbps:4.0f}KB/s ", style="dim")
        for value in list(self.history.net_recv)[-15:]:
            text.append(value_to_spark(value, 100), style="cyan")

        text.append(f"\nCONNS: {network.connection_count} ", style="cyan")
        primary = network.primary_ipv4
        if primary:
            text.append(f" IP: {primary}", style="dim")

        self.update(text)

    # ------------------------------------------------------------------
    # Transcendence
    # ------------------------------------------------------------------
    def compose_transcendence(self):
        """Interactive Network Matrix."""
        with Container(id="net-transcendence-layout"):
            with Horizontal(classes="header-section"):
                yield Static(id="net-hero-header")

            yield DataTable(id="net_table", cursor_type="row", zebra_stripes=True)

            with Horizontal(classes="footer-section", id="net-actions"):
                yield Button("KILL PID [K]", id="btn_kill", variant="error")
                yield Button("REFRESH [R]", id="btn_refresh", variant="warning")

    def update_transcendence(self, screen):
        """Update the interactive network view from the current snapshot."""
        snapshot = self.snapshot
        if snapshot is None:
            return

        network = snapshot.network
        rates = self.rates

        header = Text()
        header.append(f" ▲ {rates.net_sent_kbps:6.1f} KB/s  ", style="bold yellow")
        header.append(make_bar(min(rates.net_sent_kbps, BAR_SCALE_KBPS),
                               BAR_SCALE_KBPS, 15), style="yellow")
        header.append(f"   ▼ {rates.net_recv_kbps:6.1f} KB/s  ", style="bold cyan")
        header.append(make_bar(min(rates.net_recv_kbps, BAR_SCALE_KBPS),
                               BAR_SCALE_KBPS, 15), style="cyan")
        header.append(f"   INTERFACES: {network.active_interfaces} UP", style="dim")
        screen.query_one("#net-hero-header", Static).update(header)

        table = screen.query_one("#net_table", DataTable)
        if not table.columns:
            table.add_columns("INTERFACE", "STATE", "IPv4", "SPEED", "MTU")

        # The interface list is short and stable, so a full repaint is cheap
        # and avoids the row-churn the connection table used to suffer from.
        current_rows = set(table.rows.keys())
        seen = set()
        for interface in network.interfaces:
            seen.add(interface.name)
            if interface.name in current_rows:
                continue
            state = "UP" if interface.is_up else "DOWN"
            table.add_row(
                interface.name,
                Text(state, style="green" if interface.is_up else "red"),
                interface.ipv4 or "-",
                f"{interface.speed_mbps} Mbps" if interface.speed_mbps else "-",
                str(interface.mtu),
                key=interface.name,
            )

        for stale in current_rows - seen:
            table.remove_row(stale)

    def get_transcendence_view(self) -> Text:
        """Text fallback for the full-screen view."""
        snapshot = self.snapshot
        if snapshot is None:
            return self.waiting_text()

        network = snapshot.network
        rates = self.rates

        text = Text()
        text.append("NETWORK FLOW ANALYTICS ", style="bold")
        text.append(f"[{self.view_mode.upper()} MODE]\n", style="cyan")

        text.append(f"TX: {rates.net_sent_kbps:6.1f} KB/s ", style="yellow")
        text.append(make_bar(min(rates.net_sent_kbps, BAR_SCALE_KBPS),
                             BAR_SCALE_KBPS, 20), style="yellow")
        text.append(f"  CONNS: {network.connection_count}\n", style="dim")

        text.append(f"RX: {rates.net_recv_kbps:6.1f} KB/s ", style="cyan")
        text.append(make_bar(min(rates.net_recv_kbps, BAR_SCALE_KBPS),
                             BAR_SCALE_KBPS, 20), style="cyan")
        text.append(f"  LISTENING: {network.listen_count}\n", style="dim")

        if self.view_mode == "cinematic":
            text.append("\nUPLOAD WAVEFORM\n", style="cyan")
            for value in self.history.net_sent:
                text.append(value_to_spark(value, 100), style="yellow")

            text.append("\n\nDOWNLOAD WAVEFORM\n", style="cyan")
            for value in self.history.net_recv:
                text.append(value_to_spark(value, 100), style="cyan")

            text.append("\n\nTOTAL DATA EXCHANGED (Session)\n", style="cyan")
            text.append(f"  SENT: {network.bytes_sent / GIB:.2f} GB    "
                        f"RECV: {network.bytes_recv / GIB:.2f} GB\n", style="dim")
        else:
            text.append("\nFLOW PULSE: ", style="dim")
            for sent, recv in zip(list(self.history.net_sent)[-30:],
                                  list(self.history.net_recv)[-30:]):
                text.append("▲" if sent > recv else "▼",
                            style="yellow" if sent > recv else "cyan")

            text.append("\n\nINTERFACE STATUS MATRIX\n", style="cyan")
            text.append(f"{'INTERFACE':<16} {'STATE':<8} {'SPEED':<10} {'MTU':<6}\n",
                        style="dim")
            text.append("─" * 45 + "\n", style="dim")
            for interface in network.interfaces:
                color = "green" if interface.is_up else "red"
                state = "UP" if interface.is_up else "DOWN"
                text.append(f"  {interface.name[:15]:<16} ", style="cyan")
                text.append(f"[{state:<6}] ", style=color)
                text.append(f"{interface.speed_mbps:>4}Mbps  ", style="dim")
                text.append(f"{interface.mtu:>4}\n", style="dim")

            text.append("\nSOCKET SUMMARY\n", style="cyan")
            text.append(f"  Established: {network.established_count:>4}\n",
                        style="green dim")
            text.append(f"  Listen:      {network.listen_count:>4}\n", style="dim")
            text.append(f"  Total:       {network.connection_count:>4}\n", style="dim")

        return text

    # ------------------------------------------------------------------
    # Detail view
    # ------------------------------------------------------------------
    def get_detailed_view(self) -> Text:
        """Detailed network diagnostics."""
        snapshot = self.snapshot
        if snapshot is None:
            return self.waiting_text()

        network = snapshot.network

        text = Text()
        text.append("🌐 NETWORK DIAGNOSTICS\n\n", style="bold")

        text.append("Throughput Pulse\n", style="cyan")
        text.append("  UP   ", style="yellow")
        for value in list(self.history.net_sent)[-40:]:
            text.append(value_to_spark(value, 100), style="yellow")
        text.append("\n  DOWN ", style="cyan")
        for value in list(self.history.net_recv)[-40:]:
            text.append(value_to_spark(value, 100), style="cyan")
        text.append("\n\n")

        text.append("Traffic Totals\n", style="cyan")
        text.append(f"  Sent: {network.bytes_sent / MIB:.2f} MB ", style="yellow")
        text.append(f"({network.packets_sent} pkts)\n", style="dim")
        text.append(f"  Recv: {network.bytes_recv / MIB:.2f} MB ", style="cyan")
        text.append(f"({network.packets_recv} pkts)\n", style="dim")

        text.append("\nInterface Map\n", style="cyan")
        for interface in network.interfaces:
            color = "green" if interface.is_up else "red"
            state = "UP" if interface.is_up else "DOWN"
            text.append(f"  {interface.name[:15]:<16} [{state}]", style=color)
            if interface.ipv4:
                text.append(f"  IPv4: {interface.ipv4}", style="dim")
            text.append("\n")

        return text
