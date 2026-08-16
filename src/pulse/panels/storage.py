import datetime
import os
import platform

from rich.text import Text

from pulse.panels.base import Panel
from pulse.ui_utils import value_to_heat_color, make_bar

from textual.widgets import DataTable, Static, Button
from textual.containers import Container, Horizontal
from textual.binding import Binding

from pulse.screens.viewer import FileViewer

GIB = 1024 ** 3
# Directory listings are read on demand; this caps the work for huge folders.
MAX_ENTRIES = 1000


class StoragePanel(Panel):
    """Storage matrix showing mounted volumes, with a file browser."""

    PANEL_NAME = "STORAGE"
    BINDINGS = [
        Binding("backspace", "go_up", "Back", priority=True),
        Binding("r", "refresh_stats", "Refresh", priority=True),
        Binding("enter", "select_item", "Enter/Select", priority=True),
    ]

    def __init__(self):
        super().__init__("STORAGE", "", id="storage-panel")
        self.sampling_rate = 5.0
        self.view_mode = "developer"
        self.current_path = None  # None = volume list, str = directory path

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def action_go_up(self):
        """Navigate up one directory."""
        if not self.current_path:
            self.notify("Already at the volume list.")
            return

        parent = os.path.dirname(self.current_path)
        self.current_path = None if parent == self.current_path else parent
        self._repaint()

    def action_select_item(self):
        """Enter a directory or open a file."""
        try:
            table = self.app.screen.query_one("#storage_table", DataTable)
        except Exception:
            return

        if table.cursor_row is None:
            return

        try:
            row_key = table.coordinate_to_cell_key(table.cursor_coordinate).row_key.value
        except (AttributeError, TypeError):
            return

        # Volume list mode: the key is a mount point.
        if self.current_path is None:
            self.current_path = row_key
            self._repaint()
            return

        full_path = os.path.join(self.current_path, row_key)
        if os.path.isdir(full_path):
            self.current_path = full_path
            self._repaint()
        elif os.path.isfile(full_path):
            # FileViewer refuses anything that is not a regular file.
            self.app.push_screen(FileViewer(full_path))
        else:
            self.notify(f"Cannot open: {row_key}")

    def action_refresh_stats(self):
        self.app.refresh_data()
        self._repaint()

    def action_explore(self):
        self.action_select_item()

    def _repaint(self):
        """Redraw the browser after a navigation change."""
        try:
            self.update_transcendence(self.app.screen)
        except Exception:
            pass

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn_refresh":
            self.action_refresh_stats()
        elif event.button.id == "btn_up":
            self.action_go_up()

    # ------------------------------------------------------------------
    # Summary view
    # ------------------------------------------------------------------
    def update_data(self):
        snapshot = self.snapshot
        if snapshot is None:
            self.update(self.waiting_text())
            return

        text = Text()
        if not snapshot.volumes:
            text.append("No volumes detected", style="dim")
            self.update(text)
            return

        for volume in snapshot.volumes[:3]:
            color = value_to_heat_color(volume.percent)
            if platform.system() == "Windows":
                label = volume.mountpoint[:2]
            else:
                label = volume.mountpoint[-8:]
            text.append(f"{label:<4} ", style="cyan")
            text.append(make_bar(volume.percent, 100, 8), style=color)
            text.append(f" {volume.percent:3.0f}%\n", style=color)

        self.update(text)

    # ------------------------------------------------------------------
    # Transcendence
    # ------------------------------------------------------------------
    def compose_transcendence(self):
        """Interactive Storage Matrix."""
        with Container(id="storage-transcendence-layout"):
            with Horizontal(classes="header-section"):
                yield Static(id="storage-hero-header")

            yield DataTable(id="storage_table", cursor_type="row", zebra_stripes=True)

            with Horizontal(classes="footer-section", id="storage-actions"):
                yield Button("REFRESH [R]", id="btn_refresh", variant="primary")
                yield Button("UP [Backspace]", id="btn_up", variant="default")
                yield Static("  Enter: Select/Open", classes="status-text")

    def update_transcendence(self, screen):
        """Show either the volume list or a directory listing."""
        table = screen.query_one("#storage_table", DataTable)
        header = screen.query_one("#storage-hero-header", Static)

        if self.current_path is None:
            self._render_volumes(table, header)
        else:
            self._render_directory(table, header, self.current_path)

    def _render_volumes(self, table, header):
        """Volume list, straight from the snapshot."""
        snapshot = self.snapshot
        if snapshot is None:
            return

        columns = list(table.columns.values())
        if not columns or columns[0].label.plain != "MOUNT":
            table.clear(columns=True)
            table.add_columns("MOUNT", "TYPE", "SIZE", "USED", "FREE", "USAGE")

        column_keys = list(table.columns.keys())
        current_rows = set(table.rows.keys())
        seen = set()

        total_used = total_capacity = 0
        for volume in snapshot.volumes:
            key = volume.mountpoint
            seen.add(key)
            total_used += volume.used
            total_capacity += volume.total

            color = value_to_heat_color(volume.percent)
            row = [
                volume.mountpoint,
                volume.fstype,
                f"{volume.total / GIB:.1f} GB",
                f"{volume.used / GIB:.1f} GB",
                f"{volume.free / GIB:.1f} GB",
                Text(f"{volume.percent:.0f}% " + "█" * int(volume.percent / 10), style=color),
            ]

            if key in current_rows:
                for index, value in enumerate(row):
                    table.update_cell(key, column_keys[index], value)
            else:
                table.add_row(*row, key=key)

        for stale in current_rows - seen:
            table.remove_row(stale)

        if total_capacity:
            global_percent = total_used / total_capacity * 100
            header.update(f"STORAGE ARRAY   GLOBAL USAGE: {global_percent:.1f}%   "
                          f"VOLUMES: {len(seen)}   [Enter to browse]")
        else:
            header.update("STORAGE ARRAY   No volumes detected")

    def _render_directory(self, table, header, path):
        """Directory listing. Read on demand, not part of the sampling tick."""
        columns = list(table.columns.values())
        if not columns or columns[0].label.plain != "NAME":
            table.clear(columns=True)
            table.add_columns("NAME", "TYPE", "SIZE", "MODIFIED")

        header.update(f"BROWSING: {path}   [Backspace to go up]")

        saved_cursor = None
        try:
            if table.cursor_row is not None:
                saved_cursor = table.coordinate_to_cell_key(
                    table.cursor_coordinate).row_key
        except Exception:
            pass

        try:
            with os.scandir(path) as entries:
                listing = sorted(entries, key=lambda e: (not e.is_dir(), e.name))
                listing = listing[:MAX_ENTRIES]
        except OSError as exc:
            header.update(f"CANNOT READ {path}: {exc}")
            return

        table.clear()
        truncated = False
        for entry in listing:
            try:
                if entry.is_dir():
                    table.add_row(f"📂 {entry.name}", "DIR", "", "", key=entry.name)
                    continue

                stat = entry.stat()
                size = stat.st_size
                if size > 1024 * 1024:
                    size_text = f"{size / (1024 * 1024):.1f} MB"
                else:
                    size_text = f"{size / 1024:.1f} KB"
                modified = datetime.datetime.fromtimestamp(
                    stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                table.add_row(f"📄 {entry.name}", "FILE", size_text, modified,
                              key=entry.name)
            except OSError:
                continue

        if len(listing) >= MAX_ENTRIES:
            truncated = True
        if truncated:
            header.update(f"BROWSING: {path}   (showing first {MAX_ENTRIES} entries)")

        if saved_cursor:
            try:
                table.move_cursor(row=table.get_row_index(saved_cursor))
            except Exception:
                pass

    def get_transcendence_view(self) -> Text:
        """Text fallback for the full-screen view."""
        if self.snapshot is None:
            return self.waiting_text()
        return self.get_detailed_view()

    # ------------------------------------------------------------------
    # Detail view
    # ------------------------------------------------------------------
    def get_detailed_view(self) -> Text:
        """Full storage matrix with wide capacity bars."""
        snapshot = self.snapshot
        if snapshot is None:
            return self.waiting_text()

        text = Text()
        text.append("🗄️ STORAGE ANALYTICS\n\n", style="bold")

        if not snapshot.volumes:
            text.append("No volumes detected.", style="dim")
            return text

        text.append(f"{'VOLUME':<12} {'TYPE':<8} {'CAPACITY USAGE':<25} {'FREE':<10}\n",
                    style="dim")
        text.append("─" * 60 + "\n", style="dim")

        for volume in snapshot.volumes:
            color = value_to_heat_color(volume.percent)
            text.append(f"{volume.mountpoint[:12]:<12}", style="cyan")
            text.append(f"{volume.fstype:<8}", style="dim")
            text.append(make_bar(volume.percent, 100, 20) + f" {volume.percent:>3.0f}% ",
                        style=color)
            text.append(f"{volume.free / GIB:>6.1f} GB\n", style="dim")

        return text
