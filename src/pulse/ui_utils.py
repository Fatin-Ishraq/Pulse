"""
Pulse - Graphics Utilities

Helper functions for text-based graphics, sparklines, and heat maps.
"""

SPARK_CHARS = "▁▂▃▄▅▆▇█"

def value_to_spark(value: float, max_val: float = 100) -> str:
    """Convert a value to a sparkline character."""
    if max_val == 0:
        return SPARK_CHARS[0]
    normalized = min(value / max_val, 1.0)
    index = int(normalized * (len(SPARK_CHARS) - 1))
    return SPARK_CHARS[index]

def value_to_heat_color(value: float, heat_colors: list[str] = None) -> str:
    """Get a color from the heat palette based on value (0-100)."""
    if heat_colors is None:
        # Default heat gradient: blue -> cyan -> green -> yellow -> red
        heat_colors = ["#4488ff", "#00d4ff", "#00ff88", "#ffdd00", "#ff4444"]
    index = min(int(value / 20), len(heat_colors) - 1)
    return heat_colors[index]

def make_bar(value: float, max_val: float, width: int) -> str:
    """Create a progress bar string."""
    if max_val == 0:
        return "░" * width
    ratio = min(value / max_val, 1.0)
    filled = int(ratio * width)
    return "█" * filled + "░" * (width - filled)
