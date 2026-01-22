"""
Pulse - Main Application

A cinematic terminal-based system monitor. Every panel animates.
Nothing is static. This is not a dashboard — it's an instrument panel.

Controls:
  T     - Cycle themes: Nord → Dracula → Monokai → Dark → Solarized → Gruvbox
  Tab   - Focus next panel (highlighted border + detailed view)
  Shift+Tab - Focus previous panel
  F     - Freeze/unfreeze updates
  X     - Maximize focused widget (Transcendence Mode)
  Q     - Quit
"""

from typing import Iterable

from textual.app import App, SystemCommand
from textual.containers import Container, Vertical
from textual.screen import Screen
from textual.widgets import Header, Footer



# Import Panels
from pulse.panels.base import Panel
from pulse.panels.cpu import CPUPanel
from pulse.panels.memory import MemoryPanel
from pulse.panels.disk import DiskIOPanel
from pulse.panels.network import NetworkPanel
from pulse.panels.storage import StoragePanel
from pulse.panels.docker import DockerPanel
from pulse.panels.process import ProcessPanel
from pulse.panels.insight import InsightPanel
from pulse.panels.main_view import MainViewPanel

# Import Screens
from pulse.screens.boot import BootScreen
from pulse.screens.help import HelpScreen
from pulse.screens.immersive import ImmersiveScreen
from pulse.config import load_config, save_config


# Theme definitions
THEMES = [
    "nord",
    "dracula", 
    "monokai",
    "textual-dark",
    "solarized-dark",
    "gruvbox",
]

class PulseApp(App):
    """A cinematic terminal-based system monitor."""
    
    TITLE = "P U L S E"
    COMMAND_PALETTE_BINDING = "b"  # Open command palette with B key
    
    # Import theme CSS
    CSS_PATH = "themes.tcss"
    
    CSS = """
    Screen { background: transparent; }
    
    #grid-container {
        layout: grid;
        grid-size: 3 1;
        grid-columns: 28 1fr 28;
        padding: 1;
        height: 100%;
        grid-gutter: 1;
    }
    
    Panel {
        padding: 0 1;
        height: 1fr;
        overflow-y: auto;
        background: transparent;
        opacity: 0.6;
        transition: opacity 300ms;
    }
    
    Panel:focus-within {
        opacity: 1.0;
    }
    
    #main-panel {
        opacity: 1.0;
    }
    
    .alarm {
        text-style: bold;
    }

    #sidebar-left, #sidebar-right, #theater {
        height: 100%;
    }

    /* Column Specifics */
    #sidebar-left {
        width: 28;
    }
    #theater {
        width: 1fr;
    }
    #sidebar-right {
        width: 28;
    }

    /* Component Heights */
    #main-panel { height: 1.5fr; }
    #process-panel { height: 1fr; }
    #insight-panel { height: 1fr; }
    #cpu-panel, #memory-panel, #net-panel, #disk-panel, #storage-panel, #docker-panel { height: 1fr; }

    /* CPU Transcendence Layout */
    #cpu-transcendence-layout, #mem-transcendence-layout, #net-transcendence-layout, #proc-transcendence-layout, #storage-transcendence-layout {
        layout: vertical;
        padding: 1;
    }
    .header-section {
        height: auto;
        padding-bottom: 1;
        border-bottom: solid $primary-background;
    }
    .core-section {
        height: 1fr;
        padding: 1 0;
    }
    .process-section {
        height: 12;
        border-top: solid $primary-background;
        padding-top: 1;
    }
    .section-title {
        color: $text-muted;
        text-style: bold;
        padding-bottom: 1;
    }
    #process-control-box {
        height: auto;
    }
    .process-info {
        width: 1fr;
    }
    #process-actions {
        width: 30;
    }
    #process-actions Button {
        width: 100%;
        margin-bottom: 1;
    }
    
    #storage-actions, #net-actions, #proc-actions {
        width: 100%;
        height: auto;
        dock: bottom;
        padding-top: 1;
        border-top: solid $primary-background;
    }
    #storage-actions Button, #net-actions Button, #proc-actions Button {
        margin-right: 1;
        min-width: 16;
    }

    """
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("t", "cycle_theme", "Theme"),
        ("f", "freeze", "Freeze"),
        # Arrow Key Navigation
        ("up", "move_focus('up')", "Up"),
        ("down", "move_focus('down')", "Down"),
        ("left", "move_focus('left')", "Left"),
        ("right", "move_focus('right')", "Right"),
        
        ("tab", "focus_next", "Next"),
        ("shift+tab", "focus_previous", "Prev"),
        ("question_mark", "help", "Help"),
        ("h", "help", "Help"),
        ("x", "maximize_immersive", "Maximize"),
    ]
    
    def action_move_focus(self, direction: str):
        """Intelligent spatial navigation for the grid."""
        # Grid Layout:
        # Col 0 (Left): CPU, Mem, Storage
        # Col 1 (Mid): MainView, Process, Disk
        # Col 2 (Right): Net, Kernel, Insight
        
        # Get current focused widget
        current = self.focused
        if not isinstance(current, Panel):
            # Default to main panel if focus is lost/weird
            self.query_one("#main-panel").focus()
            return

        # Define the grid map (Panel IDs)
        grid_map = [
            ["cpu-panel", "main-panel", "net-panel"],        # Row 0
            ["memory-panel", "process-panel", "docker-panel"], # Row 1
            ["storage-panel", "disk-panel", "insight-panel"]   # Row 2
        ]
        
        # Find current position
        r, c = -1, -1
        current_id = current.id
        for row_idx, row in enumerate(grid_map):
            if current_id in row:
                r, c = row_idx, row.index(current_id)
                break
        
        if r == -1: return # Should not happen for panels
        
        # Calculate new position
        if direction == "up":
            r = max(0, r - 1)
        elif direction == "down":
            r = min(len(grid_map) - 1, r + 1)
        elif direction == "left":
            c = max(0, c - 1)
        elif direction == "right":
            c = min(len(grid_map[0]) - 1, c + 1)
            
        # Focus new widget
        target_id = grid_map[r][c]
        self.query_one(f"#{target_id}").focus()
    
    def action_maximize_immersive(self):
        """Maximize focused widget into Immersive Transcendence mode."""
        focused = self.focused
        if isinstance(focused, Panel):
            self.push_screen(ImmersiveScreen(focused))
    

    def action_help(self):
        """Show help screen."""
        self.push_screen(HelpScreen())
    
    def get_system_commands(self, screen: Screen) -> Iterable[SystemCommand]:
        """Filter system commands to remove maximize and limit themes."""
        for cmd in super().get_system_commands(screen):
            title_lower = cmd.title.lower()
            # Skip maximize command (we keep the X key shortcut, just hide from palette)
            if "maximize" in title_lower:
                continue
            # Filter theme commands to only our 6 themes
            if title_lower.startswith("theme:"):
                # Extract theme name after "theme: "
                theme_name = cmd.title.split(": ", 1)[1].lower() if ": " in cmd.title else ""
                if theme_name not in THEMES:
                    continue
            yield cmd
    
    def __init__(self):
        super().__init__()
        self.frozen = False
        
        # Load Config
        self.config = load_config()
        
        # Determine theme index from config
        saved_theme = self.config.get("ui", {}).get("theme", "nord")
        try:
            self.theme_index = THEMES.index(saved_theme)
        except ValueError:
            self.theme_index = 0
    
    def compose(self):
        yield Header()
        with Container(id="grid-container"):
            # Left Sidebar (3 widgets)
            with Vertical(id="sidebar-left"):
                yield CPUPanel()
                yield MemoryPanel()
                yield StoragePanel()
            
            # Center Theater (3 widgets)
            with Vertical(id="theater"):
                yield MainViewPanel()
                yield ProcessPanel()
                yield DiskIOPanel()
            
            # Right Sidebar (3 widgets)
            with Vertical(id="sidebar-right"):
                yield NetworkPanel()
                yield DockerPanel(id="docker-panel")
                yield InsightPanel()
        yield Footer()
    
    def on_mount(self):
        """Start the update timer."""
        # Push boot screen immediately
        self.push_screen(BootScreen())
        
        # Apply initial theme
        self.apply_theme()
        
        refresh_rate = self.config.get("core", {}).get("refresh_rate", 1.0)
        self.set_interval(refresh_rate, self.refresh_data)
        self.refresh_data()
    
    def apply_theme(self):
        """Apply the current theme."""
        theme = THEMES[self.theme_index]
        self.theme = theme
        self.sub_title = f"Theme: {theme.upper()} (Press ? for Help)"
    
    def on_descendant_focus(self, event):
        """Called when any widget inside the app gains focus."""
        focused = event.widget
        main_panel = self.query_one("#main-panel", MainViewPanel)
        
        # Find if focused widget is a Panel or inside one
        target_panel = None
        if isinstance(focused, Panel):
            target_panel = focused
        else:
            # Check ancestors (e.g. if a Button inside a Panel is focused)
            for ancestor in focused.ancestors:
                if isinstance(ancestor, Panel):
                    target_panel = ancestor
                    break
        
        # Update Main Panel content
        if target_panel and target_panel.id != "main-panel":
            main_panel.focused_panel = target_panel
            main_panel.update_data()
        else:
            main_panel.focused_panel = None
    
    def on_descendant_blur(self, event):
        """Called when a widget loses focus."""
        pass
    
    def refresh_data(self):
        """Refresh all panels."""
        if self.frozen:
            return
        self.query_one("#cpu-panel", CPUPanel).update_data()
        self.query_one("#memory-panel", MemoryPanel).update_data()
        self.query_one("#net-panel", NetworkPanel).update_data()
        self.query_one("#disk-panel", DiskIOPanel).update_data()
        self.query_one("#storage-panel", StoragePanel).update_data()
        self.query_one("#docker-panel", DockerPanel).update_data()
        self.query_one("#process-panel", ProcessPanel).update_data()
        self.query_one("#main-panel", MainViewPanel).update_data()
        self.query_one("#insight-panel", InsightPanel).update_data()
    
    
    def action_cycle_theme(self):
        """Cycle through available themes."""
        self.theme_index = (self.theme_index + 1) % len(THEMES)
        self.apply_theme()
        
        # Save preference
        current_theme = THEMES[self.theme_index]
        if "ui" not in self.config:
            self.config["ui"] = {}
        self.config["ui"]["theme"] = current_theme
        save_config(self.config)

        # explicity set sub_title again to ensure update, though apply_theme does it
        # The issue might be that apply_theme uses `self.sub_title = ...` which should work.
        # Let's ensure refresh_data doesn't overwrite it or something.
        self.refresh_data()  # Refresh to show visual updates immediately
    
    def action_freeze(self):
        """Toggle freeze state."""
        self.frozen = not self.frozen
        theme = THEMES[self.theme_index]
        if self.frozen:
            self.sub_title = "FROZEN ❄ (Press F to Unfreeze)"
        else:
            self.sub_title = f"Theme: {theme.upper()} (Press ? for Help)"


def main():
    app = PulseApp()
    app.run()


if __name__ == "__main__":
    main()
