import stat as stat_module
from pathlib import Path

from rich.syntax import Syntax
from rich.text import Text

from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Footer, Static

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
    
    # Reading more than this into the terminal is neither useful nor fast.
    MAX_VIEW_SIZE = 5 * 1024 * 1024
    # Enough to tell text from binary and to fill several screens.
    SNIFF_SIZE = 64 * 1024
    HEX_PREVIEW_SIZE = 4096

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
        
    def _reject(self, message: str) -> str:
        """Return a reason this path must not be opened, or an empty string."""
        try:
            info = self.path.lstat()
        except OSError as exc:
            return f"Cannot stat file: {exc}"

        mode = info.st_mode
        if stat_module.S_ISLNK(mode):
            return "Symlink - open the target directly if you meant to view it."
        if stat_module.S_ISFIFO(mode):
            # Reading a FIFO with no writer blocks forever and takes the UI with it.
            return "Named pipe (FIFO) - reading it would block indefinitely."
        if stat_module.S_ISSOCK(mode):
            return "Socket - not a readable file."
        if stat_module.S_ISBLK(mode) or stat_module.S_ISCHR(mode):
            return "Device file - reading it can block or return endless data."
        if not stat_module.S_ISREG(mode):
            return "Not a regular file."
        if info.st_size > self.MAX_VIEW_SIZE:
            size_mb = info.st_size / (1024 * 1024)
            limit_mb = self.MAX_VIEW_SIZE / (1024 * 1024)
            return f"File is {size_mb:.1f} MB, over the {limit_mb:.0f} MB view limit."
        return ""

    def load_file(self):
        body = self.query_one("#file-body", Static)

        # Only regular files are safe to read on the UI thread: a FIFO or a
        # character device would block the event loop with no way out.
        rejection = self._reject(str(self.path))
        if rejection:
            body.update(Text(rejection, style="red"))
            return

        try:
            # One bounded read decides text vs binary and feeds the hex dump,
            # instead of reading the whole file twice.
            with open(self.path, "rb") as f:
                head = f.read(self.SNIFF_SIZE)
        except OSError as exc:
            body.update(Text(f"Error reading file: {exc}", style="red"))
            return

        # A NUL byte in the first block is the usual signal for binary content.
        is_binary = b"\x00" in head
        if not is_binary:
            try:
                head.decode("utf-8")
            except UnicodeDecodeError:
                # A multi-byte character can straddle the read boundary, so only
                # treat it as binary if the failure is not right at the end.
                is_binary = len(head) < self.SNIFF_SIZE

        if is_binary:
            self.show_hex_dump(body, head[:self.HEX_PREVIEW_SIZE])
            return

        try:
            syntax = Syntax.from_path(
                str(self.path),
                theme="monokai",
                line_numbers=True,
                word_wrap=False,
            )
            body.update(syntax)
        except (OSError, UnicodeDecodeError) as exc:
            body.update(Text(f"Error reading file: {exc}", style="red"))
            
    def show_hex_dump(self, widget, data: bytes):
        """Render a hex preview of already-read bytes."""
        try:
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
                
            if self.path.stat().st_size > len(data):
                text.append("\n... (Truncated for preview) ...", style="dim")

            widget.update(text)

        except OSError as exc:
            widget.update(Text(f"Hex dump failed: {exc}", style="red"))
