"""
Pulse - Theme Definitions

Cinematic color palettes for the system monitor.
"""

# =============================================================================
# THEME SYSTEM - Multiple cinematic color palettes
# =============================================================================

THEMES = {
    "bridge": {
        "name": "BRIDGE",
        "desc": "Cool blues — starship command deck",
        "heat": ["#4488ff", "#00d4ff", "#00ff88", "#ffdd00", "#ff4444"],
        "accent": "#00ffff",
        "focus": "#55ffff",
        "spark_cpu": "#00ffff",
        "spark_ram": "#ff00ff", 
        "spark_io": "#0088ff",
        "read": "#00ffff",
        "write": "#0088ff",
        "alarm": "#ff4444",
        "bg": "#00050a",
        "primary": "#004488",
    },
    "reactor": {
        "name": "REACTOR",
        "desc": "Hot oranges — nuclear core",
        "heat": ["#884400", "#ff6600", "#ff9900", "#ffcc00", "#ff0000"],
        "accent": "#ff8800",
        "focus": "#ffff00",
        "spark_cpu": "#ff8800",
        "spark_ram": "#ffff00",
        "spark_io": "#ff4400",
        "read": "#ffff00",
        "write": "#ff4400",
        "alarm": "#ff0000",
        "bg": "#0a0500",
        "primary": "#884400",
    },
    "matrix": {
        "name": "MATRIX",
        "desc": "Green mono — classic hacker",
        "heat": ["#003300", "#006600", "#009900", "#00cc00", "#00ff00"],
        "accent": "#00ff00",
        "focus": "#55ff55",
        "spark_cpu": "#00ff00",
        "spark_ram": "#00ff00",
        "spark_io": "#008800",
        "read": "#00ff00",
        "write": "#00ff00",
        "alarm": "#ff0000",
        "bg": "#000a00",
        "primary": "#004400",
    },
    "vapor": {
        "name": "VAPOR",
        "desc": "Synthwave pinks & cyans",
        "heat": ["#8800ff", "#ff00ff", "#ff0088", "#ff4488", "#ff0044"],
        "accent": "#ff00ff",
        "focus": "#ff55ff",
        "spark_cpu": "#ff00ff",
        "spark_ram": "#00ffff",
        "spark_io": "#ff00ff",
        "read": "#00ffff",
        "write": "#ff00ff",
        "alarm": "#ff0088",
        "bg": "#0a000a",
        "primary": "#440044",
    },
    "mono": {
        "name": "MONO",
        "desc": "Grayscale — pure focus",
        "heat": ["#444444", "#666666", "#888888", "#aaaaaa", "#ffffff"],
        "accent": "#aaaaaa",
        "focus": "#ffffff",
        "spark_cpu": "#aaaaaa",
        "spark_ram": "#ffffff",
        "spark_io": "#cccccc",
        "read": "#cccccc",
        "write": "#ffffff",
        "alarm": "#ffffff",
        "bg": "#000000",
        "primary": "#444444",
    },
}

THEME_ORDER = ["bridge", "reactor", "matrix", "vapor", "mono"]
