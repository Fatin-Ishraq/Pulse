"""
Pulse - Main Application

A cinematic terminal-based system monitor. Every panel animates.
Nothing is static. This is not a dashboard — it's an instrument panel.

Controls:
  T     - Cycle themes: Bridge → Reactor → Matrix → Vapor → Mono
  Tab   - Focus next panel (highlighted border + detailed view)
  Shift+Tab - Focus previous panel
  F     - Freeze/unfreeze updates
  X     - Maximize focused widget (Transcendence Mode)
  Q     - Quit
"""

from textual.app import App
from textual.containers import Container, Vertical
from textual.widgets import Header, Footer

from pulse.themes import THEMES, THEME_ORDER
import pulse.state

# Import Panels
from pulse.panels.base import Panel
from pulse.panels.cpu import CPUPanel
from pulse.panels.memory import MemoryPanel
from pulse.panels.disk import DiskIOPanel
from pulse.panels.network import NetworkPanel
from pulse.panels.storage import StoragePanel
from pulse.panels.kernel import KernelThermalPanel
from pulse.panels.process import ProcessPanel
from pulse.panels.insight import InsightPanel
from pulse.panels.main_view import MainViewPanel

# Import Screens
from pulse.screens.boot import BootScreen
from pulse.screens.help import HelpScreen
from pulse.screens.immersive import ImmersiveScreen


class PulseApp(App):
    """A cinematic terminal-based system monitor."""
    
    TITLE = "P U L S E"
    SUB_TITLE = "BRIDGE"
    
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
    #cpu-panel, #memory-panel, #net-panel, #disk-panel, #storage-panel, #kernel-panel { height: 1fr; }

    """
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("t", "cycle_theme", "Theme"),
        ("f", "freeze", "Freeze"),
        ("tab", "focus_next", "Next"),
        ("shift+tab", "focus_previous", "Prev"),
        ("question_mark", "help", "Help"),
        ("h", "help", "Help"),
        ("x", "maximize_immersive", "Maximize"),
    ]
    
    def action_maximize_immersive(self):
        """Maximize focused widget into Immersive Transcendence mode."""
        focused = self.focused
        if isinstance(focused, Panel):
            self.push_screen(ImmersiveScreen(focused))
    
    def apply_theme(self):
        """Apply the current theme colors to the app UI."""
        theme = pulse.state.current_theme
        
        # Update Screen background
        self.screen.styles.background = theme["bg"]
        
        # Update Header & Footer
        for h in self.query(Header):
            h.styles.background = theme["primary"]
            h.styles.color = theme["focus"]
        for f in self.query(Footer):
            f.styles.background = theme["primary"]
            f.styles.color = theme["accent"]

        # Update all panels
        for panel in self.query(Panel):
            # Base border style
            panel.styles.border = ("solid", theme["primary"])
            panel.styles.border_title_color = theme["primary"]
            panel.styles.color = theme["accent"]
            panel.styles.background = "transparent"
            
            # Focused panel gets high contrast
            if panel.has_focus:
                panel.styles.border = ("thick", theme["focus"])
                panel.styles.border_title_color = theme["focus"]
                panel.styles.color = theme["focus"]
                panel.styles.text_style = "bold"
            else:
                panel.styles.text_style = "none"
            
            # Specific panel overrides (like Alarms)
            if "alarm" in panel.classes:
                panel.styles.border = ("heavy", theme["alarm"])
                panel.styles.color = theme["alarm"]
                panel.styles.border_title_color = theme["alarm"]
    
    def action_help(self):
        """Show help screen."""
        self.push_screen(HelpScreen())
    
    def __init__(self):
        super().__init__()
        self.frozen = False
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
                yield KernelThermalPanel()
                yield InsightPanel()
        yield Footer()
    
    def on_mount(self):
        """Start the update timer."""
        # Push boot screen immediately
        self.push_screen(BootScreen())
        
        self.apply_theme()
        self.set_interval(1.0, self.refresh_data)
        self.refresh_data()
    
    def on_descendant_focus(self, event):
        """Called when any widget inside the app gains focus."""
        self.apply_theme() # Refresh dynamic styles
        focused = event.widget
        main_panel = self.query_one("#main-panel", MainViewPanel)
        
        # If focused widget is a Panel (but not the main panel), show its details
        if isinstance(focused, Panel) and focused.id != "main-panel":
            main_panel.focused_panel = focused
            main_panel.update_data()  # Immediately update to show new details
        else:
            main_panel.focused_panel = None
    
    def on_descendant_blur(self, event):
        """Called when a widget loses focus."""
        self.apply_theme()
    
    def refresh_data(self):
        """Refresh all panels."""
        if self.frozen:
            return
        self.query_one("#cpu-panel", CPUPanel).update_data()
        self.query_one("#memory-panel", MemoryPanel).update_data()
        self.query_one("#net-panel", NetworkPanel).update_data()
        self.query_one("#disk-panel", DiskIOPanel).update_data()
        self.query_one("#storage-panel", StoragePanel).update_data()
        self.query_one("#kernel-panel", KernelThermalPanel).update_data()
        self.query_one("#process-panel", ProcessPanel).update_data()
        self.query_one("#main-panel", MainViewPanel).update_data()
        self.query_one("#insight-panel", InsightPanel).update_data()
    
    def action_cycle_theme(self):
        """Cycle through available themes."""
        self.theme_index = (self.theme_index + 1) % len(THEME_ORDER)
        theme_key = THEME_ORDER[self.theme_index]
        pulse.state.current_theme = THEMES[theme_key]
        theme = pulse.state.current_theme
        self.sub_title = f"{theme['name']} — {theme['desc']} (Press ? for Help)"
        self.apply_theme()
        self.refresh_data()
    
    def action_freeze(self):
        self.frozen = not self.frozen
        theme = pulse.state.current_theme
        if self.frozen:
            self.sub_title = "FROZEN ❄ (Press F to Unfreeze)"
        else:
            self.sub_title = f"{theme['name']} — {theme['desc']} (Press ? for Help)"
        self.apply_theme()


def main():
    app = PulseApp()
    app.run()


if __name__ == "__main__":
    main()
