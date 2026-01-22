import psutil
from rich.text import Text

from pulse.panels.base import Panel
from pulse.ui_utils import value_to_heat_color, make_bar

from textual.widgets import DataTable, Static, Button
from textual.containers import Container, Horizontal, Vertical
from textual.binding import Binding

from pulse import core

class ProcessPanel(Panel):
    """Process list showing top consumers (CPU/MEM)."""
    
    PANEL_NAME = "PROCESSES"
    BINDINGS = [
        ("c", "sort('cpu')", "Sort CPU"),
        ("m", "sort('mem')", "Sort Mem"),
        Binding("k", "kill_process", "Kill", priority=True),
        Binding("plus", "renice_up", "Nice +", priority=True),
        Binding("minus", "renice_down", "Nice -", priority=True),
    ]
    
    def __init__(self):
        super().__init__("TOP PROCS", "", id="process-panel")
        self.last_procs = []
        self.sort_key = 'cpu'  # or 'mem'
        # Transcendence Control States
        self.sampling_rate = 2.0  # Slower default for processes
        self.view_mode = "developer" # cinematic / developer
        self.selected_pid = None
        
        core.init()

    def action_kill_process(self):
        """Kill selected process."""
        try:
            table = self.query_one("#proc_table", DataTable)
            if table.cursor_row is None:
                self.notify("No process selected", severity="error")
                return
            row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
            pid = int(row_key.value)
            
            res = core.kill_process(pid)
            self.notify(res, severity="information" if "erminated" in res or "illed" in res else "error")
        except Exception as e:
            self.notify(f"Kill failed: {e}", severity="error")

    def action_renice_up(self):
        """Decrease priority (nice +1)."""
        self._renice(1)

    def action_renice_down(self):
        """Increase priority (nice -1)."""
        self._renice(-1)

    def _renice(self, delta):
        def do_renice(pid):
            try:
                p = psutil.Process(pid)
                new = max(-20, min(19, p.nice() + delta))
                core.renice_process(pid, new)
                return f"Nice -> {new}"
            except:
                return "Renice failed"
        self._action_on_selected(do_renice, "Reniced")

    def _action_on_selected(self, func, verb):
        try:
            table = self.app.screen.query_one("#proc_table", DataTable)
        except:
            self.notify("Action only available in Transcendence Mode", severity="warning")
            return

        if table.cursor_row is None:
            self.notify("No process selected", severity="error")
            return
            
        try:
            row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
            pid = int(row_key.value)
            
            res = func(pid)
            msg = res if isinstance(res, str) else f"{verb} PID {pid}"
            self.notify(msg)
        except Exception as e:
            self.notify(f"Action failed: {e}", severity="error")

    def compose_transcendence(self):
        """Interactive Process Table."""
        with Container(id="proc-transcendence-layout"):
            with Horizontal(classes="header-section"):
                yield Static(id="proc-hero-header")
            
            yield DataTable(id="proc_table", cursor_type="row", zebra_stripes=True)
            
            with Horizontal(id="proc-footer", classes="footer-section"):
                yield Button("KILL [K]", id="btn_kill", variant="error")
                yield Button("RENICE +", id="btn_renice_up", variant="default")
                yield Button("RENICE -", id="btn_renice_down", variant="default")
                yield Button("CPU [C]", id="btn_sort_cpu", variant="primary")
                yield Button("MEM [M]", id="btn_sort_mem", variant="primary")

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn_kill":
            self.action_kill_process()
        elif event.button.id == "btn_renice_up":
            self.action_renice_up()
        elif event.button.id == "btn_renice_down":
            self.action_renice_down()
        elif event.button.id == "btn_sort_cpu":
            self.action_sort("cpu")
        elif event.button.id == "btn_sort_mem":
            self.action_sort("mem")

    def update_transcendence(self, screen):
        """Update the DataTable efficiently."""
        table = screen.query_one("#proc_table", DataTable)
        
        # Init columns if needed
        if not table.columns:
            table.add_columns("PID", "NAME", "CPU %", "MEM %", "USER", "STATUS")
        
        # Fetch data
        procs = core.get_process_list(sort_by=self.sort_key, limit=100)
        
        # Current Row Keys
        current_keys = set(table.rows.keys())
        new_keys = set()
        
        # Get explicit column keys
        col_keys = list(table.columns.keys())
        
        for p in procs:
            pid = p['pid']
            pid_key = str(pid)
            new_keys.add(pid_key)
            
            # Format Data
            name = p['name']
            cpu = p['cpu_percent']
            mem = core.get_memory_info()['total']
            mem_pct = (p['memory_info'] / mem * 100) if mem else 0
            
            # Colors
            cpu_style = value_to_heat_color(cpu)
            mem_style = value_to_heat_color(mem_pct * 5)
            
            row_data = [
                str(pid),
                name,
                Text(f"{cpu:5.1f}", style=cpu_style),
                Text(f"{mem_pct:5.1f}", style=mem_style),
                "?", # User (expensive to fetch every time, maybe skip or cache)
                "?"  # Status
            ]
            
            if pid_key in current_keys:
                # Update existing
                for col_idx, val in enumerate(row_data):
                    table.update_cell(pid_key, col_keys[col_idx], val)
            else:
                # Add new
                table.add_row(*row_data, key=pid_key)
        
        # Remove dead rows
        for key in current_keys - new_keys:
            table.remove_row(key)
            
        # Re-sort
        # We manually sort the table based on our sort key column
        sort_col = "CPU %" if self.sort_key == 'cpu' else "MEM %"
        # We need a custom sort key because the values are Rich Text
        # But Textual DataTable sort implies using raw values if possible or text string
        # Actually our Text objects sort by string representation which works for fixed width like " 12.5"
        # Let's trust core.get_process_list sorting OR trigger table sort.
        # Since we modify cells, order might drift. Let's rely on core sort and re-adding?
        # DataTable doesn't support "move row".
        # So we must use table.sort().
        
        # Hack: Textual 0.40+ sort
        try:
             table.sort(sort_col, reverse=True)
        except:
             pass

        # Update Header
        screen.query_one("#proc-hero-header", Static).update(
            f"PROCESS MANAGEMENT   SORT: {self.sort_key.upper()}   TOTAL: {len(procs)}"
        )
    
    def get_transcendence_view(self) -> Text:
        """Ultimate Process Flow Analytics."""
        text = Text()
        text.append(f"PROCESS INFUSION ", style="bold")
        text.append(f"[{self.view_mode.upper()} MODE] ", style="cyan")
        text.append(f"SORT: {self.sort_key.upper()}\n", style="dim")
        
        if not self.last_procs:
            return Text("Initializing process telemetry...")

        if self.view_mode == "cinematic":
            # Cinematic: Visual dominance
            text.append("\nHIGH-CONSUMPTION LANDSCAPE\n", style="cyan")
            for p in self.last_procs[:15]:
                val = p[self.sort_key]
                color = value_to_heat_color(val if self.sort_key == 'cpu' else val * 5)
                text.append(f"{p['name'][:15]:<15} ", style="cyan")
                text.append(make_bar(val if self.sort_key == 'cpu' else val*5, 100, 30), style=color)
                text.append(f" {val:>4.1f}% ", style=color)
                text.append(f"PID: {p['pid']}\n", style="dim")
        else:
            # Developer Mode: Detailed Statistics
            text.append("\nPROCESS REGISTRY DEPTH\n", style="cyan")
            text.append(f"{'PID':<7} {'CPU%':<7} {'MEM%':<7} {'THREADS':<8} {'USER':<12} {'NAME'}\n", style="dim")
            text.append("─" * 80 + "\n", style="dim")
            
            for p in self.last_procs[:25]:
                try:
                    proc = psutil.Process(p['pid'])
                    # Supplemental data for dev mode
                    threads = proc.num_threads()
                    username = proc.username()[:12]
                    
                    cpu_c = value_to_heat_color(p['cpu'])
                    mem_c = value_to_heat_color(p['mem'] * 5)
                    
                    text.append(f"{p['pid']:<7}", style="dim")
                    text.append(f"{p['cpu']:>5.1f}% ", style=cpu_c)
                    text.append(f"{p['mem']:>5.1f}% ", style=mem_c)
                    text.append(f"{threads:<8}", style="dim")
                    text.append(f"{username:<12}", style="dim")
                    text.append(f"{p['name']}\n", style="yellow")
                except:
                    # Fallback to last_procs data if pid vanished
                    text.append(f"{p['pid']:<7} {p['cpu']:>5.1f}% {p['mem']:>5.1f}% {'?':<8} {'?':<12} {p['name']}\n", style="dim")
            
            # Status Matrix
            text.append("\nSYSTEM STATE DISTRIBUTION\n", style="cyan")
            counts = {'running': 0, 'sleeping': 0, 'idle': 0, 'other': 0}
            for p in psutil.process_iter(['status']):
                s = p.info['status']
                if s in counts: counts[s] += 1
                else: counts['other'] += 1
            
            for s, c in counts.items():
                text.append(f"  {s.upper():<10}: {c:>4}  ", style="dim")
                text.append("█" * (c // 20) + "░" * (10 - (c // 20)) + "\n", style="cyan")
                
        return text

    def action_sort(self, mode: str):
        """Sort the process list."""
        self.sort_key = mode
        self.refresh_content()
        # Visual feedback
        self.notify(f"Sorting by {mode.upper()}")
        
    def update_data(self):
        procs = []
        
        # Get process list from Direct OS engine
        process_data = core.get_process_list(sort_by=self.sort_key, limit=60)
        
        # Get total memory for percentage calculation
        mem_info = core.get_memory_info()
        total_mem = mem_info.get('total', 1) if mem_info else 1
        
        for p in process_data:
            cpu = p.get('cpu_percent', 0)
            mem_bytes = p.get('memory_info', 0)
            mem = (mem_bytes / total_mem) * 100 if total_mem else 0
            
            if cpu < 0.1 and mem < 0.1:
                continue
                
            procs.append({
                'name': p.get('name', '?'),
                'cpu': cpu,
                'mem': mem,
                'pid': p.get('pid', 0)
            })
        
        # Sort based on current mode
        procs.sort(key=lambda x: x[self.sort_key], reverse=True)
        self.last_procs = procs[:50]
        top = procs[:4]
        
        self.render_panel(top)
        
    def render_panel(self, top_procs):
        text = Text()
        
        # Header indicating sort mode
        sort_label = "CPU" if self.sort_key == 'cpu' else "MEM"
        text.append(f"Sorted by {sort_label}\n", style="dim")
        
        for p in top_procs:
            # Choose color based on the active sort metric
            val = p[self.sort_key]
            color = value_to_heat_color(val if self.sort_key == 'cpu' else val * 3) # fast hack scaling for mem
            
            star = "★" if val > (10 if self.sort_key == 'cpu' else 5) else "·"
            text.append(f"{star} ", style=color)
            
            name = p['name'][:8]
            val_fmt = f"{val:4.1f}%"
            text.append(f"{name:<8} {val_fmt}\n", style="dim")
        
        self.update(text)
        
    def refresh_content(self):
        """Force a re-render with sorted data (called on keypress)."""
        self.update_data()
    
    def get_detailed_view(self) -> Text:
        """Detailed process table."""
        text = Text()
        text.append("⭐ TOP PROCESSES\n\n", style="bold")
        
        sort_mode = "CPU" if self.sort_key == 'cpu' else "MEMORY"
        hint = "[C] Sort CPU  [M] Sort Memory"
        text.append(f"Sorted by: {sort_mode}   ", style="cyan")
        text.append(f"{hint}\n\n", style="dim")
        
        text.append("PID      CPU%   MEM%   NAME\n", style="yellow")
        text.append("─" * 40 + "\n", style="dim")
        
        for p in self.last_procs:
            cpu_val = p['cpu']
            mem_val = p['mem']
            
            # fast scaling for heatmap colors
            cpu_color = value_to_heat_color(cpu_val)
            mem_color = value_to_heat_color(mem_val * 4) 
            
            text.append(f"{p['pid']:<8}", style="dim")
            text.append(f"{cpu_val:5.1f}%  ", style=cpu_color)
            text.append(f"{mem_val:5.1f}%  ", style=mem_color)
            text.append(f"{p['name']}\n")
        
        return text
