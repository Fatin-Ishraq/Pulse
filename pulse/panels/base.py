from rich.text import Text
from textual.widgets import Static

class Panel(Static, can_focus=True):
    """Base class for all dashboard panels. Now focusable!"""
    
    # Each panel type defines what detailed view it provides
    PANEL_NAME = "Panel"
    
    def __init__(self, title: str, content: str = "", **kwargs):
        super().__init__(content, **kwargs)
        self.border_title = title
    
    def get_detailed_view(self) -> Text:
        """Override in subclasses to provide detailed view for main panel."""
        return Text("No details available")

    def on_click(self) -> None:
        """Focus the panel when clicked."""
        self.focus()
