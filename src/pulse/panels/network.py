from collections import deque
import psutil
from rich.text import Text

from pulse.panels.base import Panel
from pulse.ui_utils import value_to_spark, value_to_heat_color, make_bar

from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Static, Button, DataTable
from textual.binding import Binding

class NetworkPanel(Panel):
    """Network upload/download activity."""
    
    BINDINGS = [
        Binding("f", "optimize", "Reset Counters"),
        Binding("k", "kill_connection", "Kill PID"),
        Binding("r", "refresh_stats", "Refresh"),
    ]
    
    def __init__(self):
        super().__init__("NETWORK", "", id="net-panel")
        self.up_history = deque(maxlen=80) 
        self.down_history = deque(maxlen=80)
        try:
            self.last_net = psutil.net_io_counters()
        except:
            self.last_net = None
            
        # Transcendence Control States
        self.sampling_rate = 1.0
        self.view_mode = "developer" # cinematic / developer
        self.selected_pid = None

    def compose_transcendence(self):
        """Interactive Network Matrix."""
        with Container(id="net-transcendence-layout"):
            # Top: Hero Stats
            with Horizontal(classes="header-section"):
                yield Static(id="net-hero-header")
            
            # Middle: Interactive Table
            yield DataTable(id="net_table", cursor_type="row", zebra_stripes=True)
            
            # Bottom: Actions
            with Horizontal(classes="footer-section", id="net-actions"):
                yield Button("KILL PID [K]", id="btn_kill", variant="error")
                yield Button("REFRESH [R]", id="btn_refresh", variant="warning")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_kill":
            self.action_kill_connection()
        elif event.button.id == "btn_refresh":
            self.action_refresh_stats()

    def action_refresh_stats(self):
        self.update_data()
        self.refresh_content(force=True)

    def action_kill_connection(self):
        """Kill the process owning the selected connection."""
        try:
            table = self.app.screen.query_one("#net_table", DataTable)
            if table.cursor_row is None: return
            
            # Key is PID_PORT (e.g. "1234_8080") or "Unknown_..."
            raw_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value
            
            if "Unknown" in raw_key:
                self.notify("Cannot kill unknown process", severity="error")
                return
                
            # Extract PID (first part of key)
            pid_str = raw_key.split("_")[0]
            pid = int(pid_str)
            
            try:
                # Try standard kill
                proc = psutil.Process(pid)
                proc.kill()
                self.notify(f"Terminated process {pid}")
            except psutil.AccessDenied:
                # Fallback to Force Kill (Windows)
                if platform.system() == "Windows":
                    self.notify(f"Access Denied. Attempting FORCE KILL on {pid}...", severity="warning")
                    subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                    # Check if it died?
                    try:
                        psutil.Process(pid)
                        self.notify("Force Kill Failed. Run Pulse as Admin.", severity="error")
                    except psutil.NoSuchProcess:
                        self.notify(f"Force Kill Successful: {pid}")
                else:
                    self.notify("Access Denied (Run as Root)", severity="error")
            except psutil.NoSuchProcess:
                self.notify(f"Process {pid} no longer exists.")
                
            # Optimistic UI update (remove row immediately)
            table.remove_row(raw_key)
            self.update_data()
            
        except Exception as e:
            self.notify(f"Kill error: {e}", severity="error")

    def refresh_content(self, force=False):
        if hasattr(self.app.screen, "query_one"):
             try:
                 self.update_transcendence(self.app.screen)
             except: pass

    def update_transcendence(self, screen):
        """Update interactive network view."""
        self.update_data() # Update global counters
        
        # 1. Hero Header
        try:
            up = self.up_history[-1] if self.up_history else 0
            down = self.down_history[-1] if self.down_history else 0
            header_widget = screen.query_one("#net-hero-header", Static)
            
            head = Text()
            head.append(f" ▲ {up:6.1f} KB/s  ", style="bold yellow")
            head.append(make_bar(min(up, 1000), 1000, 15), style="yellow")
            head.append(f"   ▼ {down:6.1f} KB/s  ", style="bold cyan")
            head.append(make_bar(min(down, 1000), 1000, 15), style="cyan")
            
            # Interface Summary
            stats = psutil.net_if_stats()
            active_nics = [n for n, s in stats.items() if s.isup]
            head.append(f"   INTERFACES: {len(active_nics)} UP", style="dim")
            
            header_widget.update(head)
            
            # 2. DataTable
            table = screen.query_one("#net_table", DataTable)
            
            # Setup columns
            cols = list(table.columns.values())
            if not cols:
                table.add_columns("PROTO", "L-WT", "LOCAL IP", "REMOTE IP", "STATUS", "PID", "PROCESS")
            
            # Get Connections
            conns = psutil.net_connections(kind='inet')
            # Filter: Show established or listen (skip time_wait to reduce noise?)
            # Letting user see everything for now, maybe sort by state
            active_conns = sorted(conns, key=lambda c: (c.status != 'ESTABLISHED', c.laddr.port))
            
            # Prune limit
            active_conns = active_conns[:200]
            
            seen_pids = set()
            current_rows = set(table.rows.keys())
            
            # Reuse logic to update rows
            for c in active_conns:
                try:
                    pid = c.pid if c.pid else "Unknown"
                    key = str(pid) + "_" + str(c.laddr.port) # Unique key per socket
                    seen_pids.add(key)
                    
                    row_data = []
                    
                    # Proto
                    row_data.append("TCP" if c.type == 1 else "UDP")
                    # L-Port (Weight/Port)
                    row_data.append(str(c.laddr.port))
                    # Local
                    row_data.append(f"{c.laddr.ip}")
                    # Remote
                    r_str = f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else "*"
                    row_data.append(r_str)
                    # Status
                    style = "green" if c.status == "ESTABLISHED" else "dim"
                    row_data.append(Text(c.status, style=style))
                    # PID
                    row_data.append(str(pid))
                    # Process
                    if pid != "Unknown":
                        try:
                            p = psutil.Process(pid)
                            row_data.append(p.name())
                        except:
                            row_data.append("?")
                    else:
                        row_data.append("System")
                        
                    # Row Key needs to be PID for killing? 
                    # Actually valid key needs to be unique for the ROW.
                    # But action_kill wants PID. We can parse it from cell or use a mapping.
                    # I'll use `pid` as key, BUT one pid has multiple sockets. 
                    # So key must be `key` (pid_port). But then `coordinate_to_cell_key` returns that.
                    # I need to store PID in row logic.
                    
                    if key in current_rows:
                        # Update (Status might change)
                         # Updating every cell is expensive. 
                         # For network, constant churn. Let's mostly just Add/Remove.
                         pass 
                    else:
                        # To enable killing, the row key should probably simple, 
                        # but we need to extract PID.
                        # I'll make the row key = PID (string). 
                        # WAIT: Duplicate PIDs (chrome has 50 conns). 
                        # DataTable keys must be unique. 
                        # So I cannot use PID as row key. 
                        # I will use `key` (pid_port) as row key.
                        # Then in kill action, I will parse the PID column.
                        table.add_row(*row_data, key=key)

                except: continue
            
            # Remove old
            for k in current_rows - seen_pids:
                 table.remove_row(k)
                 
                 
        except Exception:
            pass

    def get_transcendence_view(self) -> Text:
         # Legacy fallback
         return super().get_transcendence_view()
         
    def get_detailed_view(self) -> Text:
         return super().get_detailed_view() # Guard



    def action_optimize(self):
        """Reset network session counters."""
        try:
            self.last_net = psutil.net_io_counters()
            self.up_history.clear()
            self.down_history.clear()
            self.notify("Network Session Counters Reset", severity="information")
        except:
            self.notify("Failed to reset network counters", severity="error")
        self.refresh()
    
    def update_data(self):
        try:
            current = psutil.net_io_counters()
        except:
            return

        if not self.last_net:
            self.last_net = current
            return
            
        # Calculate rates (bytes per second if interval is 1s, but we'll use delta)
        sent_rate = (current.bytes_sent - self.last_net.bytes_sent) / 1024  # KB
        recv_rate = (current.bytes_recv - self.last_net.bytes_recv) / 1024  # KB
        self.last_net = current
        
        self.up_history.append(min(sent_rate, 1000)) # Cap for sparkline scaling
        self.down_history.append(min(recv_rate, 1000))
        
        text = Text()
        # Traffic summary
        text.append("UP   ", style="yellow")
        text.append(f"{sent_rate:4.0f}KB/s ", style="dim")
        for val in list(self.up_history)[-15:]:
            text.append(value_to_spark(val, 100), style="yellow")
        
        text.append("\nDOWN ", style="cyan")
        text.append(f"{recv_rate:4.0f}KB/s ", style="dim")
        for val in list(self.down_history)[-15:]:
            text.append(value_to_spark(val, 100), style="cyan")
        
        # Connectivity Consolidation
        try:
            conns = len(psutil.net_connections(kind='inet'))
            text.append(f"\nCONNS: {conns} ", style="cyan")
            
            # Show first active IP as primary hint
            addrs = psutil.net_if_addrs()
            found_ip = False
            for nic_name, nic_addrs in addrs.items():
                for addr in nic_addrs:
                    if addr.family == 2 and not addr.address.startswith("127."):
                        text.append(f" IP: {addr.address}", style="dim")
                        found_ip = True
                        break
                if found_ip: break
        except:
            pass
            
        self.update(text)

    def get_transcendence_view(self) -> Text:
        """Immersive Network console with throughput pulses and interface mapping."""
        text = Text()
        try:
            net = psutil.net_io_counters()
            conns = psutil.net_connections(kind='inet')
        except:
            return Text("Network Telemetry Offline")

        from pulse.ui_utils import make_bar

        # --- HERO HEADER ---
        text.append(f"NETWORK FLOW ANALYTICS ", style="bold")
        text.append(f"[{self.view_mode.upper()} MODE]\n", style="cyan")
        
        recent_up = self.up_history[-1] if self.up_history else 0
        recent_down = self.down_history[-1] if self.down_history else 0
        
        text.append(f"TX: {recent_up:6.1f} KB/s ", style="yellow")
        text.append(make_bar(min(recent_up, 1000), 1000, 20), style="yellow")
        text.append(f"  TCP CONNS: {len([c for c in conns if c.type == 1])}\n", style="dim")
        
        text.append(f"RX: {recent_down:6.1f} KB/s ", style="cyan")
        text.append(make_bar(min(recent_down, 1000), 1000, 20), style="cyan")
        text.append(f"  UDP CONNS: {len([c for c in conns if c.type == 2])}\n", style="dim")

        if self.view_mode == "cinematic":
            # Massive Waveform Focus
            text.append("\nUPLOAD WAVEFORM (80s)\n", style="cyan")
            for val in self.up_history:
                text.append(value_to_spark(val, 100), style="yellow")
            
            text.append("\n\nDOWNLOAD WAVEFORM (80s)\n", style="cyan")
            for val in self.down_history:
                text.append(value_to_spark(val, 100), style="cyan")
                
            text.append("\n\nTOTAL DATA EXCHANGED (Session)\n", style="cyan")
            text.append(f"  SENT: {net.bytes_sent/(1024**3):.2f} GB    RECV: {net.bytes_recv/(1024**3):.2f} GB\n", style="dim")
        else:
            # Developer Focus: Interface Map & Socket Stats
            text.append("\n80s FLOW PULSE: ", style="dim")
            for val_up, val_down in zip(list(self.up_history)[-30:], list(self.down_history)[-30:]):
                text.append("▲" if val_up > val_down else "▼", style="yellow" if val_up > val_down else "cyan")
            
            text.append("\n\nINTERFACE STATUS MATRIX\n", style="cyan")
            try:
                stats = psutil.net_if_stats()
                addrs = psutil.net_if_addrs()
                text.append(f"{'INTERFACE':<16} {'STATE':<8} {'SPEED':<10} {'MTU':<6}\n", style="dim")
                text.append("─" * 45 + "\n", style="dim")
                for nic, s in stats.items():
                    color = "green" if s.isup else "red"
                    state = "UP" if s.isup else "DOWN"
                    text.append(f"  {nic[:15]:<16} ", style="cyan")
                    text.append(f"[{state:<6}] ", style=color)
                    text.append(f"{s.speed:>4}Mbps  ", style="dim")
                    text.append(f"{s.mtu:>4}\n", style="dim")
            except:
                text.append("Interface matrix unavailable\n", style="red")

            text.append("\nSOCKET BACKLOG\n", style="cyan")
            text.append(f"  Established: {len([c for c in conns if c.status == 'ESTABLISHED']):>4}\n", style="green dim")
            text.append(f"  Listen:      {len([c for c in conns if c.status == 'LISTEN']):>4}\n", style="dim")
            text.append(f"  Time Wait:   {len([c for c in conns if c.status == 'TIME_WAIT']):>4}\n", style="dim")

        return text

    def get_detailed_view(self) -> Text:
        """Detailed network diagnostics with 40s waveforms."""
        text = Text()
        text.append("🌐 NETWORK DIAGNOSTICS\n\n", style="bold")
        
        try:
            net = psutil.net_io_counters()
        except:
            return Text("Network telemetry unavailable")
            
        # Waveforms
        text.append("Throughput Pulse (Last 40s)\n", style="cyan")
        text.append("  UP   ", style="yellow")
        for val in list(self.up_history)[-40:]:
            text.append(value_to_spark(val, 100), style="yellow")
        text.append("\n  DOWN ", style="cyan")
        for val in list(self.down_history)[-40:]:
            text.append(value_to_spark(val, 100), style="cyan")
        text.append("\n\n")

        # Session Totals
        text.append("Traffic Totals\n", style="cyan")
        text.append(f"  Sent: {net.bytes_sent / (1024**2):.2f} MB ", style="yellow")
        text.append(f"({net.packets_sent} pkts)\n", style="dim")
        text.append(f"  Recv: {net.bytes_recv / (1024**2):.2f} MB ", style="cyan")
        text.append(f"({net.packets_recv} pkts)\n", style="dim")

        # Interfaces
        try:
            addrs = psutil.net_if_addrs()
            stats = psutil.net_if_stats()
            text.append("\nInterface Map\n", style="cyan")
            for nic, nic_addrs in addrs.items():
                is_up = stats[nic].isup if nic in stats else False
                status = "UP" if is_up else "DOWN"
                color = "green" if is_up else "red"
                text.append(f"  {nic[:15]:<16} [{status}]", style=color)
                for addr in nic_addrs:
                    if addr.family == 2:
                        text.append(f"  IPv4: {addr.address}", style="dim")
                        break
                text.append("\n")
        except:
            pass
            
        return text
