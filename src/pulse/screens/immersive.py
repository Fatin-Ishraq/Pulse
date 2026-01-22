from textual.screen import Screen
from textual.containers import Container, Horizontal
from textual.widgets import Static, Button



class ImmersiveScreen(Screen):
    """Fullscreen high-density telemetry console with interactive controls."""
    
    BINDINGS = [
        ("escape", "app.pop_screen", "Back to Grid"),
        ("x", "app.pop_screen", "Back to Grid"),
        ("p", "toggle_rate", "Toggle Precision"),
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
            # Dynamic Composition: Check if panel supports interactive transcendence
            if hasattr(self.source_panel, "compose_transcendence"):
                yield from self.source_panel.compose_transcendence()
            else:
                # Fallback: Static Text View
                yield Static(id="transcendence-content")
            
            with Horizontal(id="control-bar"):
                yield Button("PRECISION [P]", id="btn-rate", variant="success")
                yield Button("SCALING [S]", id="btn-scale", variant="warning")
                yield Button("OPTIMIZE [F]", id="btn-optimize", variant="default")
                yield Button("BACK [X]", id="btn-back", variant="error")
            
    def on_mount(self):
        self.screen.styles.background = "transparent"
        
        # Container style
        self.styles.align = ("center", "middle")
        # Hide buttons based on panel capabilities
        self.query_one("#btn-rate").visible = hasattr(self.source_panel, "sampling_rate")
        self.query_one("#btn-scale").visible = hasattr(self.source_panel, "scaling_mode")
        self.query_one("#btn-optimize").visible = hasattr(self.source_panel, "optimize") or hasattr(self.source_panel, "action_optimize")
        
        # Size the Aether canvas if applicable
        self._update_aether_size()
        
        self.refresh_view()
        
        # Use panel's sampling rate (e.g., 0.05s for Aether's 20 FPS)
        interval = getattr(self.source_panel, "sampling_rate", 1.0)
        self.refresh_timer = self.set_interval(interval, self.refresh_view)
        
        # Auto-Focus Control Logic
        try:
            self.query_one("DataTable").focus()
        except:
            pass
    
    def _update_aether_size(self):
        """Update Aether engine size based on container dimensions."""
        if hasattr(self.source_panel, "set_aether_size"):
            try:
                container = self.query_one("#hero-console")
                # Get actual terminal-based size (subtract for borders/padding)
                width = container.size.width - 4 if container.size.width > 10 else 80
                height = container.size.height - 8 if container.size.height > 12 else 20
                self.source_panel.set_aether_size(max(40, width), max(10, height))
            except:
                self.source_panel.set_aether_size(80, 20)
    
    def on_resize(self, event):
        """Handle terminal resize."""
        self._update_aether_size()

    async def on_key(self, event):
        """Forward keys to source panel bindings."""
        if hasattr(self.source_panel, "BINDINGS"):
            for b in self.source_panel.BINDINGS:
                # Handle Binding objects vs Tuple shortcuts
                b_key = b.key if hasattr(b, "key") else b[0]
                b_action = b.action if hasattr(b, "action") else b[1]
                
                if b_key == event.key:
                    action_name = b_action
                    method_name = f"action_{action_name}"
                    if hasattr(self.source_panel, method_name):
                        getattr(self.source_panel, method_name)()
                        event.stop()
                        return

    def on_data_table_row_selected(self, event):
        """Handle Enter/Select on Tables."""
        if hasattr(self.source_panel, "action_select_item"):
            self.source_panel.action_select_item()
        elif hasattr(self.source_panel, "on_table_selected"):
             self.source_panel.on_table_selected(event)

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "btn-rate":
            self.action_toggle_rate()
        elif event.button.id == "btn-scale":
            self.action_cycle_scale()
        elif event.button.id == "btn-optimize":
            self.action_optimize()
        elif event.button.id == "btn-back":
            self.app.pop_screen()
        else:
            # Delegate other buttons (panel-specific) to the source panel
            if hasattr(self.source_panel, "on_button_pressed"):
                self.source_panel.on_button_pressed(event)
                # Re-focus table after button press to keep keyboard working
                try: self.query_one("DataTable").focus()
                except: pass

    def action_toggle_precision(self):
        self.action_toggle_rate()

    def action_optimize(self):
        """Trigger optimization on the source panel if supported."""
        if hasattr(self.source_panel, "action_optimize"):
            self.source_panel.action_optimize()
        elif hasattr(self.source_panel, "optimize"):
            self.source_panel.optimize()
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
        # In interactive mode (widgets), the panel manages its own updates via its own timer/logic
        # We only need to drive updates for the static text view fallback
        try:
            content = self.query_one("#transcendence-content", Static)
        except:
            # If no static content widget, we assume interactive mode is handling itself
            # checking if source panel needs explicit update call though
            if hasattr(self.source_panel, "update_transcendence"):
                self.source_panel.update_transcendence(self)
            return
        
        # In Transcendence Mode, we allow the screen to drive the panel's updates
        # if the rate is different from the main app.
        if hasattr(self.source_panel, "sampling_rate") and self.source_panel.sampling_rate < 1.0:
            self.source_panel.update_data()
        
        container_style = self.query_one("#hero-console").styles
        container_style.border = ("thick", "cyan")
        container_style.background = "transparent"
        
        if hasattr(self.source_panel, "get_transcendence_view"):
            text = self.source_panel.get_transcendence_view()
        else:
            text = self.source_panel.get_detailed_view()
            
        content.update(text)
