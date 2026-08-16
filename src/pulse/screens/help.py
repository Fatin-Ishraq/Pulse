from textual.screen import ModalScreen
from textual.containers import Container
from textual.widgets import Markdown



class HelpScreen(ModalScreen):
    """Modal help screen overlay."""
    
    CSS = """
    HelpScreen {
        align: center middle;
        background: rgba(0,0,0,0.8);
    }
    
    #help-container {
        width: 60;
        height: auto;
        padding: 1 2;
    }
    """
    
    def on_mount(self):
        """Apply theme to modal."""
        container = self.query_one("#help-container")
        container.styles.border = ("heavy", "cyan")
        container.styles.background = "black"
        container.styles.color = "white"
        self.query_one(Markdown).styles.color = "cyan"
    
    def compose(self):
        help_md = """
# PULSE CONTROLS

| Key | Action |
| :-: | :--- |
| **T** | Cycle Theme (Nord/Dracula/Monokai/Dark/Solarized/Gruvbox) |
| **F** | Freeze / Unfreeze Updates |
| **X** | Enter / Exit full-screen panel view |
| **Arrows** | Move focus around the grid |
| **Tab** | Focus Next Panel + Detailed View |
| **S-Tab** | Focus Previous Panel |
| **C** | Sort Processes by CPU |
| **M** | Sort Processes by Memory |
| **K** | Terminate selected process (asks first) |
| **+ / -** | Lower / raise process priority |
| **? / H** | Toggle Help Screen |
| **Q** | Quit Application |

Destructive actions always confirm and name their target. Pulse refuses to
touch itself, your shell, or system-critical processes.

*Press any key or click to dismiss*
        """
        with Container(id="help-container"):
            yield Markdown(help_md)
            
    def on_key(self, event):
        self.dismiss()
        
    def on_click(self):
        self.dismiss()
