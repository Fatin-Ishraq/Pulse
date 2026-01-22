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

    def compose_transcendence(self):
        """Interactive Process Management Matrix."""
        with Container(id="proc-transcendence-layout"):
            # Top: Hero Stats
            with Horizontal(classes="header-section"):
                yield Static(id="proc-hero-header")
            
            # Middle: Interactive Table
            yield DataTable(id="proc_table", cursor_type="row", zebra_stripes=True)
            
            # Bottom: Actions
            with Horizontal(classes="footer-section", id="proc-actions"):
                yield Button("KILL [K]", id="btn_kill", variant="error")
                yield Button("SORT CPU [C]", id="btn_sort_cpu", variant="primary")
                yield Button("SORT MEM [M]", id="btn_sort_mem", variant="default")
                yield Button("REFRESH [R]", id="btn_refresh", variant="warning")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_kill":
            self.action_kill_process()
        elif event.button.id == "btn_sort_cpu":
            self.action_sort("cpu")
        elif event.button.id == "btn_sort_mem":
            self.action_sort("mem")
        elif event.button.id == "btn_refresh":
            self.action_refresh_stats()

    def action_refresh_stats(self):
        self.update_data()
        self.refresh_content(force=True)

    def action_kill_process(self):
        """Kill selected process."""
        try:
            table = self.app.screen.query_one("#proc_table", DataTable)
        except:
            self.notify("Switch to Transcendence Mode [X] to manage processes", severity="warning")
            return

        if table.cursor_row is None:
            self.notify("No process selected", severity="error")
            return

        try:
            row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
            pid = int(row_key.value)
            
            self.notify(f"Attempting to kill PID {pid}...", severity="information")
            res = core.kill_process(pid)
            
            severity = "information" if "erminated" in res or "illed" in res else "error"
            self.notify(res, severity=severity)
            
            # Refresh immediately
            self.update_data()
            self.refresh_content()
            
        except Exception as e:
            self.notify(f"Kill action error: {e}", severity="error")

    # ... (keep renice methods)

    def update_transcendence(self, screen):
        """Update the DataTable efficiently with rich visualization matching NetworkPanel."""
        table = screen.query_one("#proc_table", DataTable)
        header = screen.query_one("#proc-hero-header", Static)
        
        # Init columns if needed
        if not table.columns:
            table.add_columns("PID", "NAME", "CPU %", "MEM %", "USER", "STATUS")
        
        # Fetch data
        procs = core.get_process_list(sort_by=self.sort_key, limit=100)
        
        # --- Update Header (Strictly Replicating Network Design) ---
        # Calculate System Globals
        sys_cpu = psutil.cpu_percent()
        mem_info = core.get_memory_info()
        sys_mem_pct = mem_info['percent'] if mem_info else 0
        proc_count = len(procs)
        
        head = Text()
        # CPU Block (Green) -> Replicating "Upload" style
        head.append(f" ⚡ {sys_cpu:5.1f}%   ", style="bold green")
        head.append(make_bar(sys_cpu, 100, 15), style="green")
        
        # MEM Block (Blue) -> Replicating "Download" style
        head.append(f"   💾 {sys_mem_pct:5.1f}%   ", style="bold blue")
        head.append(make_bar(sys_mem_pct, 100, 15), style="blue")
        
        # Stats Block -> Replicating "INTERFACES" style
        head.append(f"   ACTIVE TASKS: {proc_count}", style="dim")
        
        header.update(head)
        
        # --- Update Table ---
        
        # Save selection
        old_cursor_key = None
        if table.cursor_row is not None:
             try:
                 old_cursor_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
             except: pass
        
        old_scroll_y = table.scroll_y
        
        table.clear()
        
        for p in procs:
            pid = p['pid']
            pid_key = str(pid)
            
            # Format Data
            name = p['name']
            cpu = p['cpu_percent']
            mem_total = mem_info['total'] if mem_info else 1
            mem_pct = (p['memory_info'] / mem_total * 100)
            
            # Colors
            cpu_style = value_to_heat_color(cpu)
            mem_style = value_to_heat_color(mem_pct * 5)
            
            # Fetch details
            user = "?"
            status = "?"
            try:
                proc = psutil.Process(pid)
                user = proc.username()
                if "\\" in user: user = user.split("\\")[1]
                status = proc.status()
            except:
                pass
            
            row_data = [
                str(pid),
                name,
                Text(f"{cpu:5.1f}", style=cpu_style),
                Text(f"{mem_pct:5.1f}", style=mem_style),
                Text(user[:10], style="dim"),
                Text(status[:10], style="dim")
            ]
            
            table.add_row(*row_data, key=pid_key)
        
        # Restore selection
        if old_cursor_key:
            try:
                new_idx = table.get_row_index(old_cursor_key)
                table.move_cursor(row=new_idx)
                table.scroll_y = old_scroll_y
            except:
                pass
    
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
        
    def refresh_content(self, force=False):
        """Force a re-render with sorted data (called on keypress)."""
        if force or hasattr(self.app.screen, "query_one"):
             try:
                 self.update_transcendence(self.app.screen)
             except: pass
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
