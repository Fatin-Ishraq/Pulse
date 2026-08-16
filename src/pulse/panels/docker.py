from rich.text import Text
from textual.app import ComposeResult
from textual.widgets import DataTable, Label
from textual.containers import Vertical

from pulse.panels.base import Panel
from pulse.container_api import ContainerController


class DockerPanel(Panel):
    """Docker container monitor.

    Summary counts in the grid, full management in the full-screen view.
    Container data arrives through the shared snapshot; the controller is only
    used for the state-changing operations, which always confirm first.
    """

    PANEL_NAME = "Docker"

    BINDINGS = [
        ("r", "restart_container", "Restart"),
        ("k", "stop_container", "Stop/Kill"),
        ("s", "start_container", "Start"),
    ]

    def __init__(self, controller=None, **kwargs):
        super().__init__("DOCKER", **kwargs)
        # Does not touch the Docker socket until something asks it to - that
        # socket is root-equivalent on the host.
        self.controller = controller if controller is not None else ContainerController()
        self.table_widget = None

    @property
    def containers(self):
        snapshot = self.snapshot
        return snapshot.containers if snapshot else ()

    # ------------------------------------------------------------------
    # Summary view
    # ------------------------------------------------------------------
    def update_data(self) -> None:
        if not self.controller.available:
            self.update(self.controller.status_text())
            self.border_title = "DOCKER [N/A]"
            return

        if not self.controller.connected:
            self.update(self.controller.status_text())
            self.border_title = "DOCKER [OFFLINE]"
            return

        containers = self.containers
        running = sum(1 for c in containers if c.status == "running")
        paused = sum(1 for c in containers if c.status == "paused")
        stopped = len(containers) - running - paused

        self.update(
            f"\n[bold green]● Running: {running}[/]\n"
            f"[bold yellow]● Paused:  {paused}[/]\n"
            f"[bold red]● Stopped: {stopped}[/]\n\n"
            f"[bold blue]Total: {len(containers)}[/]"
        )
        self.border_title = f"DOCKER [{running}/{len(containers)}]"

        if self.table_widget:
            self._refresh_table()

    def get_detailed_view(self) -> Text:
        """Sidebar preview."""
        if not self.controller.connected:
            return Text(self.controller.status_text(), style="red")

        containers = self.containers
        text = Text()
        text.append("CONTAINERS\n", style="bold underline")
        for container in containers[:10]:
            color = "green" if container.status == "running" else "red"
            text.append(f"• {container.name[:20]:<20} ", style=color)
            text.append(f"[{container.status}]\n", style="dim")

        if len(containers) > 10:
            text.append(f"...and {len(containers) - 10} more", style="italic")

        return text

    # ------------------------------------------------------------------
    # Transcendence
    # ------------------------------------------------------------------
    def compose_transcendence(self) -> ComposeResult:
        """Compose the interactive full-screen view."""
        # First point where the user has actually asked to manage containers,
        # so this is where the connection attempt belongs.
        if not self.controller.is_available():
            yield Label(self.controller.last_error or "Docker daemon is unreachable.",
                        id="docker-error")
            return

        with Vertical(id="docker-transcendence"):
            yield Label(
                "[b]Container Operations:[/b] [green]Start (S)[/] | "
                "[red]Stop (K)[/] | [yellow]Restart (R)[/]",
                classes="header-section",
            )

            self.table_widget = DataTable(cursor_type="row")
            self.table_widget.add_columns("ID", "Name", "Image", "Status", "State")
            yield self.table_widget

    def _refresh_table(self):
        """Update the table in place so the selected row does not jump."""
        table = self.table_widget
        if not table:
            return

        column_keys = list(table.columns.keys())
        current_rows = set(table.rows.keys())
        seen = set()

        for container in self.containers:
            seen.add(container.id)
            style = (
                "green" if container.status == "running"
                else "red" if container.status == "exited"
                else "yellow"
            )
            row = [
                container.id,
                container.name,
                container.image,
                Text(container.status, style=style),
                container.state,
            ]

            if container.id in current_rows:
                for index, value in enumerate(row):
                    table.update_cell(container.id, column_keys[index], value)
            else:
                table.add_row(*row, key=container.id)

        for stale in current_rows - seen:
            table.remove_row(stale)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _get_selected_id(self):
        if not self.table_widget:
            return None
        try:
            row_key = self.table_widget.coordinate_to_cell_key(
                self.table_widget.cursor_coordinate).row_key
            return row_key.value
        except (AttributeError, TypeError, ValueError):
            return None

    def _container_name(self, container_id: str) -> str:
        for container in self.containers:
            if container.id == container_id:
                return f"{container.name} ({container_id})"
        return container_id

    def _request(self, operation: str) -> None:
        """Confirm, then run a container operation and report what happened."""
        container_id = self._get_selected_id()

        def run():
            result = getattr(self.controller, f"{operation}_container")(container_id)
            self.app.refresh_data()
            return result

        self.request_container_action(
            operation,
            container_id,
            self._container_name(container_id) if container_id else "",
            run,
        )

    def action_restart_container(self):
        self._request("restart")

    def action_stop_container(self):
        self._request("stop")

    def action_start_container(self):
        self._request("start")
