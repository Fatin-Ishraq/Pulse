from random import choice, randint
from textual.screen import Screen
from textual.widgets import Static
from textual.containers import Container, Vertical

LOGO = r"""
██████╗ ██╗   ██╗██╗     ███████╗███████╗
██╔══██╗██║   ██║██║     ██╔════╝██╔════╝
██████╔╝██║   ██║██║     ███████╗█████╗  
██╔═══╝ ██║   ██║██║     ╚════██║██╔══╝  
██║     ╚██████╔╝███████╗███████║███████╗
╚═╝      ╚═════╝ ╚══════╝╚══════╝╚══════╝
"""  # "PULSE" in ANSI Shadow font style

class BootScreen(Screen):
    """Cinematic boot sequence with elevated aesthetics."""
    
    CSS = """
    BootScreen {
        align: center middle;
        background: #000000;
        color: #00ff88;
    }
    
    #boot-container {
        width: 80;
        height: auto;
        border: heavy #004400;
        background: #000500;
        padding: 1 2;
    }
    
    #logo {
        width: 100%;
        text-align: center;
        color: #00ff88;
        padding-bottom: 1;
        border-bottom: solid #004400;
    }
    
    #params {
        height: 10;
        content-align: center middle;
        color: #00aa55;
    }
    
    .loading-bar {
        color: #00ffff;
    }
    """
    
    def compose(self):
        with Container(id="boot-container"):
            yield Static(LOGO, id="logo")
            yield Static("", id="params")
            
    def on_mount(self):
        self.steps = [
            "Initializing Neural Core",
            "Loading Modules: CPU, MEM, NET",
            "Calibrating Sensors...",
            "Establishing Uplink",
            "System Ready"
        ]
        self.step_idx = 0
        self.ticks = 0
        self.progress = 0
        self.blink_state = True
        
        # Faster interval for smooth animation
        self.set_interval(0.1, self.animate_frame)
        
    def animate_frame(self):
        # Progress bar logic
        width = 60
        filled = int((self.progress / 100) * width)
        bar = "█" * filled + "░" * (width - filled)
        
        # Status text logic
        if self.progress < 100:
            self.progress += randint(5, 12)  # Faster loading
            if self.progress > 100: self.progress = 100
            
        # Step logic - change text every ~20 ticks (2.0s roughly, fast)
        current_text = self.steps[min(self.step_idx, len(self.steps)-1)]
        if self.progress > (self.step_idx + 1) * (100 / len(self.steps)):
            self.step_idx += 1
            
        # Blinking cursor
        cursor = " " if self.ticks % 4 < 2 else "█"
        self.ticks += 1
        
        # Render
        output = f"\n{current_text}...\n\n[{bar}]\n\n{self.progress}%"
        self.query_one("#params", Static).update(output)
        
        # Finish condition
        if self.progress >= 100 and self.ticks > 30: # Wait a bit at 100%
            self.app.pop_screen()
