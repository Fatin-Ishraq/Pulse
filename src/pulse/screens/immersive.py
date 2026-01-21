from textual.screen import Screen
from textual.containers import Container, Horizontal
from textual.widgets import Static, Button

from pulse.state import current_theme

class ImmersiveScreen(Screen):
    """Fullscreen high-density telemetry console with interactive controls."""
    
    BINDINGS = [
        ("escape", "app.pop_screen", "Back to Grid"),
        ("x", "app.pop_screen", "Back to Grid"),
        ("m", "cycle_mode", "Toggle Mode"),
        ("r", "toggle_rate", "Toggle Rate"),
        ("s", "cycle_scale", "Toggle Scale"),
        ("f", "optimize", "Optimize"),
        ("q", "quit", "Quit"),
    ]
    
    CSS = """
    ImmersiveScreen {
        background: rgba(0,0,0,0.9);
        align: center middle;
    }
    #hero-console {
        width: 90%;
        height: 90%;
        border: thick white;
        padding: 1 2;
        background: black;
        layout: vertical;
    }
    #transcendence-content {
        height: 1fr;
    }
    #control-bar {
        height: 3;
        margin-top: 1;
        align: center middle;
        background: $primary;
        color: $text;
    }
    #control-bar Button {
        margin: 0 1;
        border: none;
        height: 1;
    }
    """
    
    def __init__(self, source_panel):
        super().__init__()
        self.source_panel = source_panel
        
    def compose(self):
        with Container(id="hero-console"):
            yield Static(id="transcendence-content")
            with Horizontal(id="control-bar"):
                yield Button("VIEW MODE [M]", id="btn-mode", variant="primary")
                yield Button("PRECISION [R]", id="btn-rate", variant="success")
                yield Button("SCALING [S]", id="btn-scale", variant="warning")
                yield Button("OPTIMIZE [F]", id="btn-optimize", variant="default")
                yield Button("BACK [X]", id="btn-back", variant="error")
            
    def on_mount(self):
        self.styles.background = "black"
        
        # Hide buttons based on panel capabilities
        self.query_one("#btn-mode").visible = hasattr(self.source_panel, "view_mode")
        self.query_one("#btn-rate").visible = hasattr(self.source_panel, "sampling_rate")
        self.query_one("#btn-scale").visible = hasattr(self.source_panel, "scaling_mode")
        self.query_one("#btn-optimize").visible = hasattr(self.source_panel, "optimize") or hasattr(self.source_panel, "action_optimize")
        
        self.refresh_view()
        # Start with standard 1.0s interval
        self.refresh_timer = self.set_interval(1.0, self.refresh_view)

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-mode":
            self.action_cycle_mode()
        elif event.button.id == "btn-rate":
            self.action_toggle_rate()
        elif event.button.id == "btn-scale":
            self.action_cycle_scale()
        elif event.button.id == "btn-optimize":
            self.action_optimize()
        elif event.button.id == "btn-back":
            self.app.pop_screen()

    def action_optimize(self):
        """Trigger optimization on the source panel if supported."""
        if hasattr(self.source_panel, "action_optimize"):
            self.source_panel.action_optimize()
        elif hasattr(self.source_panel, "optimize"):
            self.source_panel.optimize()
        self.refresh_view()

    def action_cycle_mode(self):
        if hasattr(self.source_panel, "view_mode"):
            self.source_panel.view_mode = "cinematic" if self.source_panel.view_mode == "developer" else "developer"
            self.refresh_view()

    def action_toggle_rate(self):
        if hasattr(self.source_panel, "sampling_rate"):
            # Toggle panel state
            self.source_panel.sampling_rate = 0.2 if self.source_panel.sampling_rate == 1.0 else 1.0
            # Update local timer
            self.refresh_timer.stop()
            self.refresh_timer = self.set_interval(self.source_panel.sampling_rate, self.refresh_view)
            self.refresh_view()

    def action_cycle_scale(self):
        if hasattr(self.source_panel, "scaling_mode"):
            self.source_panel.scaling_mode = "relative" if self.source_panel.scaling_mode == "absolute" else "absolute"
            self.refresh_view()

    def refresh_view(self):
        try:
            content = self.query_one("#transcendence-content", Static)
            console = self.query_one("#hero-console")
        except:
            return
        
        # In Transcendence Mode, we allow the screen to drive the panel's updates
        # if the rate is different from the main app.
        if hasattr(self.source_panel, "sampling_rate") and self.source_panel.sampling_rate < 1.0:
            self.source_panel.update_data()
            
        # Sync color from theme
        console.styles.border = ("thick", current_theme["focus"])
        
        if hasattr(self.source_panel, "get_transcendence_view"):
            text = self.source_panel.get_transcendence_view()
        else:
            text = self.source_panel.get_detailed_view()
            
        content.update(text)
