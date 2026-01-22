from rich.text import Text
from rich.table import Table
from textual.app import ComposeResult
from textual.widgets import DataTable, Button, Label
from textual.containers import Container, Horizontal, Vertical

from pulse.panels.base import Panel
from pulse.container_api import ContainerController

class DockerPanel(Panel):
    """
    Docker Container Monitor Panel.
    Shows summary stats in grid, full interactive management in Transcendence.
    """
    
    PANEL_NAME = "Docker"
    
    BINDINGS = [
        ("r", "restart_container", "Restart"),
        ("k", "stop_container", "Stop/Kill"),
        ("s", "start_container", "Start"),
    ]

    def __init__(self, **kwargs):
        super().__init__("DOCKER", **kwargs)
        self.controller = ContainerController()
        self.containers = []
        self.summary_stats = {"total": 0, "running": 0, "paused": 0, "stopped": 0}
        self.selected_container_id = None
        self.table_widget = None

    def update_data(self) -> None:
        """Fetch latest container data."""
        if not self.controller.is_available():
            self.update("Docker Daemon\nNOT FOUND")
            self.border_title = "DOCKER [OFFLINE]"
            return

        self.containers = self.controller.get_containers()
        
        # Calculate summary
        self.summary_stats = {"total": len(self.containers), "running": 0, "paused": 0, "stopped": 0}
        for c in self.containers:
            status = c["status"]
            if status == "running":
                self.summary_stats["running"] += 1
            elif status == "paused":
                self.summary_stats["paused"] += 1
            else:
                self.summary_stats["stopped"] += 1
        
        # Update Grid View (Text)
        status_text = (
            f"\n[bold green]● Running: {self.summary_stats['running']}[/]\n"
            f"[bold yellow]● Paused:  {self.summary_stats['paused']}[/]\n"
            f"[bold red]● Stopped: {self.summary_stats['stopped']}[/]\n\n"
            f"[bold blue]Total: {self.summary_stats['total']}[/]")
        self.update(status_text)
        self.border_title = f"DOCKER [{self.summary_stats['running']}/{self.summary_stats['total']}]"

        # Update Transcendence Table if active
        if self.table_widget:
            self._refresh_table()

    def get_detailed_view(self) -> Text:
        """Textual detail view for the main panel (sidebar preview)."""
        if not self.controller.connected:
            return Text("Docker not connected.", style="red")
            
        text = Text()
        text.append("CONTAINERS\n", style="bold underline")
        for c in self.containers[:10]: # Limit to 10 for preview
            color = "green" if c["status"] == "running" else "red"
            text.append(f"• {c['name'][:20]:<20} ", style=color)
            text.append(f"[{c['status']}]\n", style="dim")
        
        if len(self.containers) > 10:
            text.append(f"...and {len(self.containers)-10} more", style="italic")
            
        return text

    # =========================================================================
    # TRANSCENDENCE (IMMERSIVE MODE)
    # =========================================================================
    
    def compose_transcendence(self) -> ComposeResult:
        """Compose the interactive full-screen view."""
        if not self.controller.connected:
            yield Label("Docker Daemon is unreachable. Ensure Docker is running and try again.", id="docker-error")
            return

        with Vertical(id="docker-transcendence"):
            yield Label("[b]Container Operations:[/b] [green]Start (S)[/] | [red]Stop (K)[/] | [yellow]Restart (R)[/]", classes="header-section")
            
            self.table_widget = DataTable(cursor_type="row")
            self.table_widget.add_columns("ID", "Name", "Image", "Status", "State")
            yield self.table_widget

    def _refresh_table(self):
        """Update the data table without losing selection."""
        if not self.table_widget: return

        # Store selection
        cursor_row = self.table_widget.cursor_row
        
        self.table_widget.clear()
        
        # Re-populate
        for c in self.containers:
            # Colorize status
            status_style = "green" if c["status"] == "running" else "red" if c["status"] == "exited" else "yellow"
            status_cell = Text(c["status"], style=status_style)
            
            self.table_widget.add_row(
                c["id"],
                c["name"],
                c["image"],
                status_cell,
                c["state"],
                key=c["id"]  # Use ID as row key
            )
        
        # Restore selection if possible
        if cursor_row < len(self.containers):
            self.table_widget.move_cursor(row=cursor_row)

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        """Track selection."""
        self.selected_container_id = event.row_key.value

    def _get_selected_id(self):
        """Helper to get currently selected ID from table."""
        if not self.table_widget: return None
        try:
            row_key = self.table_widget.coordinate_to_cell_key(self.table_widget.cursor_coordinate).row_key
            return row_key.value
        except:
            return None

    def action_restart_container(self):
        cid = self._get_selected_id()
        if cid:
            self.app.notify(f"Restarting {cid}...")
            self.controller.restart_container(cid)
            self.update_data()

    def action_stop_container(self):
        cid = self._get_selected_id()
        if cid:
            self.app.notify(f"Stopping {cid}...")
            self.controller.stop_container(cid)
            self.update_data()

    def action_start_container(self):
        cid = self._get_selected_id()
        if cid:
            self.app.notify(f"Starting {cid}...")
            self.controller.start_container(cid)
            self.update_data()
