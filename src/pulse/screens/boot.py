from random import choice
from textual.screen import Screen
from textual.widgets import Static

from pulse.state import current_theme

class BootScreen(Screen):
    """Cinematic boot sequence."""
    
    CSS = """
    BootScreen {
        align: center middle;
        background: black;
    }
    #boot-text {
        text-align: center;
        text-style: bold;
    }
    """
    
    def compose(self):
        yield Static("INITIALIZING PULSE CORE...", id="boot-text")
        
    def on_mount(self):
        self.query_one("#boot-text").styles.color = current_theme["focus"]
        self.styles.background = current_theme["bg"]
        self.steps = [
            "CONNECTING TO NEURAL NET...",
            "ALLOCATING QUANTUM BUFFERS...",
            "DECRYPTING SECURE CHANNELS...",
            "ESTABLEstablishing UPLINK...",
            "SYSTEM READY."
        ]
        self.step_idx = 0
        self.set_interval(0.5, self.next_step)
        
    def next_step(self):
        if self.step_idx < len(self.steps):
            matrix = "".join(choice("01XYZ") for _ in range(40))
            text = f"{matrix}\n\n{self.steps[self.step_idx]}\n\n{matrix}"
            self.query_one("#boot-text", Static).update(text)
            self.step_idx += 1
        else:
            self.app.pop_screen()
            # Restore help binding instructions
            self.app.sub_title = f"{current_theme['name']} — {current_theme['desc']} (Press ? for Help)"
