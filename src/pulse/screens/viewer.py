from pathlib import Path
from rich.syntax import Syntax
from rich.text import Text

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Header, Footer, Static

class FileViewer(ModalScreen):
    """A modal screen for viewing file content natively."""
    
    BINDINGS = [
        ("escape", "dismiss", "Close"),
        ("q", "dismiss", "Close"),
        ("backspace", "dismiss", "Close"),
    ]
    
    CSS = """
    FileViewer {
        align: center middle;
        background: rgba(0,0,0,0.8);
    }
    
    #viewer-container {
        width: 80%;
        height: 80%;
        background: $surface;
        border: solid $primary;
        padding: 0 1;
    }
    
    #viewer-header {
        dock: top;
        height: 3;
        content-align: center middle;
        text-style: bold;
        background: $primary-background;
        border-bottom: solid $primary;
    }
    
    #viewer-content {
        height: 1fr;
    }
    """
    
    def __init__(self, path: str):
        super().__init__()
        self.path = Path(path)
        
    def compose(self) -> ComposeResult:
        with Container(id="viewer-container"):
            yield Static(f"📄 {self.path.name}", id="viewer-header")
            with VerticalScroll(id="viewer-content"):
                yield Static(id="file-body")
            yield Footer()
            
    def on_mount(self):
        """Load content async."""
        self.load_file()
        
    def load_file(self):
        body = self.query_one("#file-body", Static)
        try:
            stat = self.path.stat()
            if stat.st_size > 5 * 1024 * 1024:
                body.update(Text("File too large to view natively (Legacy Limit: 5MB)", style="red"))
                return
                
            # Basic Binary Check
            is_binary = False
            try:
                with open(self.path, "tr", encoding="utf-8") as f:
                    content = f.read()
            except UnicodeDecodeError:
                is_binary = True
                
            if is_binary:
                self.show_hex_dump(body)
            else:
                # Syntax Highlight
                syntax = Syntax.from_path(
                    str(self.path),
                    theme="monokai",
                    line_numbers=True,
                    word_wrap=False
                )
                body.update(syntax)
                
        except Exception as e:
            body.update(Text(f"Error reading file: {e}", style="red"))
            
    def show_hex_dump(self, widget):
        """Render a cool hex dump."""
        try:
            with open(self.path, "rb") as f:
                data = f.read(4096) # Read first 4KB for preview
                
            text = Text()
            text.append(f"BINARY FILE DETECTED - HEX PREVIEW ({len(data)} bytes)\n\n", style="bold yellow")
            
            # Simple Hex Dump logic
            for i in range(0, len(data), 16):
                chunk = data[i:i+16]
                
                # Offset
                text.append(f"{i:08x}  ", style="dim")
                
                # Hex
                for byte in chunk:
                    text.append(f"{byte:02x} ", style="cyan")
                
                # Padding
                if len(chunk) < 16:
                    text.append("   " * (16 - len(chunk)))
                    
                text.append("  |")
                
                # ASCII
                for byte in chunk:
                    if 32 <= byte <= 126:
                        text.append(chr(byte), style="green")
                    else:
                        text.append(".", style="dim")
                text.append("|\n")
                
            if self.path.stat().st_size > 4096:
                text.append("\n... (Truncated for preview) ...", style="dim")
                
            widget.update(text)
            
        except Exception as e:
            widget.update(f"Hex dump failed: {e}")
