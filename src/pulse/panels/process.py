import psutil
from rich.text import Text

from pulse.panels.base import Panel
from pulse.state import current_theme
from pulse.ui_utils import value_to_heat_color

class ProcessPanel(Panel):
    """Process list showing top consumers (CPU/MEM)."""
    
    PANEL_NAME = "PROCESSES"
    BINDINGS = [
        ("c", "sort('cpu')", "Sort CPU"),
        ("m", "sort('mem')", "Sort Mem"),
    ]
    
    def __init__(self):
        super().__init__("TOP PROCS", "", id="process-panel")
        self.last_procs = []
        self.sort_key = 'cpu'  # or 'mem'
        # Transcendence Control States
        self.sampling_rate = 2.0  # Slower default for processes
        self.view_mode = "developer" # cinematic / developer
        self.scaling_mode = "auto" 
    
    def get_transcendence_view(self) -> Text:
        """Ultimate Process Flow Analytics."""
        text = Text()
        text.append(f"PROCESS INFUSION ", style="bold")
        text.append(f"[{self.view_mode.upper()} MODE] ", style=current_theme["focus"])
        text.append(f"SORT: {self.sort_key.upper()}\n", style="dim")
        
        if not self.last_procs:
            return Text("Initializing process telemetry...")

        if self.view_mode == "cinematic":
            # Cinematic: Visual dominance
            text.append("\nHIGH-CONSUMPTION LANDSCAPE\n", style=current_theme["accent"])
            for p in self.last_procs[:15]:
                val = p[self.sort_key]
                color = value_to_heat_color(val if self.sort_key == 'cpu' else val * 5, current_theme["heat"])
                text.append(f"{p['name'][:15]:<15} ", style=current_theme["accent"])
                bar_len = int(min(val, 100) / 2) if self.sort_key == 'cpu' else int(min(val*5, 100) / 2)
                from pulse.ui_utils import make_bar
                text.append(make_bar(val if self.sort_key == 'cpu' else val*5, 100, 30), style=color)
                text.append(f" {val:>4.1f}% ", style=color)
                text.append(f"PID: {p['pid']}\n", style="dim")
        else:
            # Developer Mode: Detailed Statistics
            text.append("\nPROCESS REGISTRY DEPTH\n", style=current_theme["accent"])
            text.append(f"{'PID':<7} {'CPU%':<7} {'MEM%':<7} {'THREADS':<8} {'USER':<12} {'NAME'}\n", style="dim")
            text.append("─" * 80 + "\n", style="dim")
            
            for p in self.last_procs[:25]:
                try:
                    proc = psutil.Process(p['pid'])
                    # Supplemental data for dev mode
                    threads = proc.num_threads()
                    username = proc.username()[:12]
                    
                    cpu_c = value_to_heat_color(p['cpu'], current_theme["heat"])
                    mem_c = value_to_heat_color(p['mem'] * 5, current_theme["heat"])
                    
                    text.append(f"{p['pid']:<7}", style="dim")
                    text.append(f"{p['cpu']:>5.1f}% ", style=cpu_c)
                    text.append(f"{p['mem']:>5.1f}% ", style=mem_c)
                    text.append(f"{threads:<8}", style="dim")
                    text.append(f"{username:<12}", style="dim")
                    text.append(f"{p['name']}\n", style=current_theme["write"])
                except:
                    # Fallback to last_procs data if pid vanished
                    text.append(f"{p['pid']:<7} {p['cpu']:>5.1f}% {p['mem']:>5.1f}% {'?':<8} {'?':<12} {p['name']}\n", style="dim")
            
            # Status Matrix
            text.append("\nSYSTEM STATE DISTRIBUTION\n", style=current_theme["accent"])
            counts = {'running': 0, 'sleeping': 0, 'idle': 0, 'other': 0}
            for p in psutil.process_iter(['status']):
                s = p.info['status']
                if s in counts: counts[s] += 1
                else: counts['other'] += 1
            
            for s, c in counts.items():
                text.append(f"  {s.upper():<10}: {c:>4}  ", style="dim")
                text.append("█" * (c // 20) + "░" * (10 - (c // 20)) + "\n", style=current_theme["focus"])
                
        return text
    
    def action_sort(self, mode: str):
        """Sort the process list."""
        self.sort_key = mode
        self.refresh_content()
        # Visual feedback
        self.notify(f"Sorting by {mode.upper()}")
        
    def update_data(self):
        procs = []
        try:
            for p in psutil.process_iter(['name', 'cpu_percent', 'memory_percent', 'pid']):
                try:
                    # Filter out very low usage to speed up
                    entry = p.info
                    cpu = entry.get('cpu_percent') or 0
                    mem = entry.get('memory_percent') or 0
                    
                    if cpu < 0.1 and mem < 0.1:
                        continue
                        
                    procs.append({
                        'name': entry.get('name') or '?',
                        'cpu': cpu,
                        'mem': mem,
                        'pid': entry.get('pid') or 0,
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except:
            pass
        
        # Sort based on current mode
        procs.sort(key=lambda x: x[self.sort_key], reverse=True)
        self.last_procs = procs[:50]  # Expanded list for detailed view
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
            color = value_to_heat_color(val if self.sort_key == 'cpu' else val * 3, current_theme["heat"]) # fast hack scaling for mem
            
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
        text.append(f"Sorted by: {sort_mode}   ", style=current_theme["accent"])
        text.append(f"{hint}\n\n", style="dim")
        
        text.append("PID      CPU%   MEM%   NAME\n", style=current_theme["write"])
        text.append("─" * 40 + "\n", style="dim")
        
        for p in self.last_procs:
            cpu_val = p['cpu']
            mem_val = p['mem']
            
            # fast scaling for heatmap colors
            cpu_color = value_to_heat_color(cpu_val, current_theme["heat"])
            mem_color = value_to_heat_color(mem_val * 4, current_theme["heat"]) 
            
            text.append(f"{p['pid']:<8}", style="dim")
            text.append(f"{cpu_val:5.1f}%  ", style=cpu_color)
            text.append(f"{mem_val:5.1f}%  ", style=mem_color)
            text.append(f"{p['name']}\n")
        
        return text
