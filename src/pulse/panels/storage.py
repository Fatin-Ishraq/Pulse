import platform
import psutil
from rich.text import Text

import os
import subprocess
import shutil

from pulse.panels.base import Panel
from pulse.ui_utils import value_to_heat_color, make_bar

import datetime

from textual.widgets import DataTable, Static, Button
from textual.containers import Container, Horizontal
from textual.binding import Binding

from pulse.screens.viewer import FileViewer

class StoragePanel(Panel):
    """Storage Matrix showing all mounted drives and their health."""
    
    PANEL_NAME = "STORAGE"
    BINDINGS = [
        Binding("backspace", "go_up", "Back", priority=True),
        Binding("r", "refresh_stats", "Refresh", priority=True),
        Binding("enter", "select_item", "Enter/Select", priority=True),
    ]
    
    def __init__(self):
        super().__init__("STORAGE", "", id="storage-panel")
        # Transcendence Control States
        self.sampling_rate = 5.0 # Slow updates for disk space
        self.view_mode = "developer" # cinematic / developer
        self.current_path = None # None = Drive List, Str = Directory Path

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle footer button clicks."""
        if event.button.id == "btn_explore":
            self.action_explore()
        elif event.button.id == "btn_up":
            self.action_go_up()
        elif event.button.id == "btn_refresh":
            self.action_refresh_stats()

    def action_go_up(self):
        """Navigate up one directory."""
        if self.current_path:
            parent = os.path.dirname(self.current_path)
            if parent == self.current_path: # Root
                self.current_path = None
            else:
                self.current_path = parent
            self.refresh_content(force=True)
        else:
            self.notify("Already at Drive Root")

    def action_select_item(self):
        """Enter directory or open file."""
        try:
            table = self.app.screen.query_one("#storage_table", DataTable)
        except: return
        
        if table.cursor_row is None: return
        
        row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value
        
        # If in Drive List mode
        if self.current_path is None:
            self.current_path = row_key # Drive mount point
            self.refresh_content(force=True)
            return
            
        # If in Directory mode
        full_path = os.path.join(self.current_path, row_key)
        
        if os.path.isdir(full_path):
            self.current_path = full_path
            self.refresh_content(force=True)
        elif os.path.isfile(full_path):
            # NATIVE VIEWER
            self.app.push_screen(FileViewer(full_path))
        else:
            self.notify(f"Cannot open: {row_key}")

    def refresh_content(self, force=False):
        # We need to trigger update_transcendence
        if hasattr(self.app.screen, "query_one"):
             try:
                 self.update_transcendence(self.app.screen)
             except: pass
    
    def action_refresh_stats(self):
        """Force refresh."""
        self.refresh_content(force=True)
        self.notify("Refreshing...")

    def action_explore(self):
        """Standardize on Native Open."""
        self.action_select_item()

    def _open_os_path(self, path):
        """Cross-platform launch. 
        DEPRECATED: User requested native-only experience.
        Kept for potential legacy fallback if needed.
        """
        pass

    def compose_transcendence(self):
        """Interactive Storage Matrix."""
        with Container(id="storage-transcendence-layout"):
            with Horizontal(classes="header-section"):
                yield Static(id="storage-hero-header")
            
            yield DataTable(id="storage_table", cursor_type="row", zebra_stripes=True)
            
            with Horizontal(classes="footer-section", id="storage-actions"):
                yield Button("REFRESH [R]", id="btn_refresh", variant="primary")
                yield Static("  Enter: Select/Open | Backspace: Go Up", classes="status-text")

    def update_transcendence(self, screen):
        """Update Storage Table (Drive List or File List)."""
        table = screen.query_one("#storage_table", DataTable)
        header = screen.query_one("#storage-hero-header", Static)
        
        # Determine Mode
        if self.current_path is None:
            self._render_drive_list(table, header)
        else:
            self._render_file_list(table, header, self.current_path)

    def _render_file_list(self, table, header, path):
        # Setup Columns
        cols = list(table.columns.values())
        if not cols or cols[0].label.plain != "NAME":
            table.clear(columns=True)
            table.add_columns("NAME", "TYPE", "SIZE", "MODIFIED")
        
        header.update(f"BROWSING: {path}")
        
        # Save Cursor Position
        saved_cursor_key = None
        try:
            if table.cursor_row is not None:
                saved_cursor_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key
        except: pass

        try:
            # Efficiency: Limit to 1000 items (increased from 100)
            with os.scandir(path) as it:
                entries = sorted(list(it), key=lambda e: (not e.is_dir(), e.name))[:1000]
            
            # Clear old text rows 
            table.clear() 
            
            for entry in entries:
                try:
                    name = entry.name
                    key = name
                    
                    if entry.is_dir():
                        table.add_row(f"📂 {name}", "DIR", "", "", key=key)
                    else:
                        stat = entry.stat()
                        size = stat.st_size
                        size_str = f"{size / 1024:.1f} KB"
                        if size > 1024*1024:
                            size_str = f"{size / (1024*1024):.1f} MB"
                        
                        mtime = datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                        table.add_row(f"📄 {name}", "FILE", size_str, mtime, key=key)
                except:
                    continue
            
            # Restore Cursor
            if saved_cursor_key:
                try:
                    index = table.get_row_index(saved_cursor_key)
                    table.move_cursor(row=index)
                except: pass
                    
        except Exception as e:
            header.update(f"ACCESS DENIED / ERROR: {e}")

    def _render_drive_list(self, table, header):
        # Check current columns
        cols = list(table.columns.values())
        if not cols or cols[0].label.plain != "MOUNT":
            table.clear(columns=True)
            table.add_columns("MOUNT", "TYPE", "SIZE", "USED", "FREE", "USAGE")
            
        # Populate Drives
        # ... (Existing drive logic, slightly adapted) ...
        try:
            parts = psutil.disk_partitions()
            stats = []
            total_used = 0
            total_cap = 0
            
            seen_keys = set()
            col_keys = list(table.columns.keys()) # Safe key access
            
            current_rows = set(table.rows.keys())

            for part in parts:
                if 'cdrom' in part.opts or part.fstype == '': continue
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    total_used += usage.used
                    total_cap += usage.total
                    
                    mount = part.mountpoint
                    seen_keys.add(mount)
                    
                    pct = usage.percent
                    color = value_to_heat_color(pct)
                    
                    # Row Logic
                    row_data = [
                        mount,
                        part.fstype,
                        f"{usage.total / (1024**3):.1f} GB",
                        f"{usage.used / (1024**3):.1f} GB",
                        f"{usage.free / (1024**3):.1f} GB",
                        Text(f"{pct}% " + ("█" * int(pct/10)), style=color)
                    ]
                    
                    if mount in current_rows:
                        # Update existing
                        for i, val in enumerate(row_data):
                            table.update_cell(mount, col_keys[i], val)
                    else:
                        table.add_row(*row_data, key=mount)

                except: continue
            
            # Prune
            for k in current_rows - seen_keys:
                table.remove_row(k)
                
            if total_cap > 0:
                global_pct = (total_used / total_cap) * 100
                header.update(f"STORAGE ARRAY   GLOBAL USAGE: {global_pct:.1f}%   VOLUMES: {len(seen_keys)}")
                
        except Exception as e:
            header.update(f"STORAGE OFFLINE: {e}")
    
    def get_transcendence_view(self) -> Text:
        """Ultimate Storage Matrix with Mount Point Health & Detailed Inodes."""
        text = Text()
        text.append(f"STORAGE INFUSION ", style="bold")
        text.append(f"[{self.view_mode.upper()} MODE]\n", style="cyan")
        
        try:
            parts = psutil.disk_partitions()
            
            if self.view_mode == "cinematic":
                text.append("\nVOLUME HEALTH LANDSCAPE\n", style="cyan")
                for part in parts:
                    if 'cdrom' in part.opts or part.fstype == '': continue
                    try:
                        usage = psutil.disk_usage(part.mountpoint)
                        color = value_to_heat_color(usage.percent)
                        text.append(f"{part.mountpoint:<15}", style="cyan")
                        text.append(make_bar(usage.percent, 100, 30), style=color)
                        text.append(f" {usage.percent:>4.1f}% ", style=color)
                        text.append(f"[{usage.used/(1024**3):.1f}/{usage.total/(1024**3):.1f} GB]\n", style="dim")
                    except: continue
            else:
                # Developer Mode: Detailed Inodes & Mount Flags
                text.append("\nMOUNT POINT REGISTRY\n", style="cyan")
                text.append(f"{'MOUNT':<15} {'FSTYPE':<8} {'USAGE':<20} {'INODES':<15} {'FLAGS'}\n", style="dim")
                text.append("─" * 80 + "\n", style="dim")
                
                for part in parts:
                    if 'cdrom' in part.opts or part.fstype == '': continue
                    try:
                        usage = psutil.disk_usage(part.mountpoint)
                        color = value_to_heat_color(usage.percent)
                        
                        text.append(f"{part.mountpoint[:15]:<15}", style="cyan")
                        text.append(f"{part.fstype:<8}", style="dim")
                        text.append(make_bar(usage.percent, 100, 10) + f" {usage.percent:>4.1f}% ", style=color)
                        
                        # Inodes (posix only usually)
                        try:
                            # psutil usage object might have .inodes_percent
                            if hasattr(usage, 'inodes_percent') and usage.inodes_percent is not None:
                                i_color = value_to_heat_color(usage.inodes_percent)
                                text.append(f"{usage.inodes_percent:>5.1f}% inodes ", style=i_color)
                            else:
                                text.append("N/A inodes      ", style="dim")
                        except:
                            text.append("N/A inodes      ", style="dim")
                            
                        # Flags (shortened)
                        opts = part.opts[:20]
                        text.append(f"{opts}", style="dim")
                        text.append("\n")
                    except: continue
                
                text.append("\nI/O COUNTERS (SYSTEM-WIDE)\n", style="cyan")
                io = psutil.disk_io_counters()
                if io:
                    text.append(f"  READ:  {io.read_bytes/(1024**3):.2f} GB ({io.read_count:,} ops)\n", style="green")
                    text.append(f"  WRITE: {io.write_bytes/(1024**3):.2f} GB ({io.write_count:,} ops)\n", style="cyan")
                    text.append(f"  BUSY:  {io.busy_time/1000:.1f}s active time\n", style="yellow")

        except Exception as e:
            text.append(f"Storage Telemetry Offline: {e}", style="red")
            
        return text
    
    def update_data(self):
        text = Text()
        try:
            parts = psutil.disk_partitions()
            # Show top 3 disks in summary
            count = 0
            for part in parts:
                if 'cdrom' in part.opts or part.fstype == '':
                    continue
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    color = value_to_heat_color(usage.percent)
                    
                    drive = part.mountpoint[:2] if platform.system() == "Windows" else part.mountpoint[-8:]
                    text.append(f"{drive:<4} ", style="cyan")
                    text.append(make_bar(usage.percent, 100, 8), style=color)
                    text.append(f" {usage.percent:3.0f}%\n", style=color)
                    count += 1
                    if count >= 3: break
                except:
                    continue
        except:
            text.append("Storage info restricted", style="dim")
            
        self.update(text)
        
    def get_detailed_view(self) -> Text:
        """Full storage matrix with wide capacity bars."""
        text = Text()
        text.append("🗄️ STORAGE ANALYTICS\n\n", style="bold")
        
        try:
            parts = psutil.disk_partitions()
            text.append(f"{'VOLUME':<12} {'TYPE':<8} {'CAPACITY USAGE':<25} {'FREE':<10}\n", style="dim")
            text.append("─" * 60 + "\n", style="dim")
            
            for part in parts:
                if 'cdrom' in part.opts or part.fstype == '':
                    continue
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    color = value_to_heat_color(usage.percent)
                    
                    label = part.mountpoint[:12]
                    text.append(f"{label:<12}", style="cyan")
                    text.append(f"{part.fstype:<8}", style="dim")
                    # Wide bar
                    text.append(make_bar(usage.percent, 100, 20) + f" {usage.percent:>3.0f}% ", style=color)
                    text.append(f"{usage.free / (1024**3):>6.1f} GB\n", style="dim")
                except:
                    continue
        except:
            text.append("Access Denied to Storage API", style="red")
            
        return text
