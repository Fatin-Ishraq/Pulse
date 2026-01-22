"""
Pulse - Graphics Utilities

Helper functions for text-based graphics, sparklines, and heat maps.
"""

SPARK_CHARS = "  ▂▃▄▅▆▇█"
BLOCK_CHARS = " ▏▎▍▌▋▊▉█"

def value_to_spark(value: float, max_val: float = 100) -> str:
    """Convert a value to a sparkline character."""
    if max_val == 0:
        return SPARK_CHARS[0]
    normalized = min(max(value, 0) / max_val, 1.0) # Ensure no negative
    index = int(normalized * (len(SPARK_CHARS) - 1))
    return SPARK_CHARS[index]

def value_to_heat_color(value: float, heat_colors: list[str] = None) -> str:
    """Get a theme-aware semantic color based on value (0-100)."""
    # Textual/Rich requires standard color names or hex codes
    if value < 50:
        return "green"
    elif value < 80:
        return "yellow"
    else:
        return "red"

def make_bar(value: float, max_val: float, width: int) -> str:
    """Create a high-resolution progress bar string."""
    if max_val == 0:
        return " " * width
        
    ratio = min(max(value, 0) / max_val, 1.0)
    full_blocks = int(ratio * width)
    remainder = (ratio * width) - full_blocks
    
    # Calculate partial block for the end
    remainder_idx = int(remainder * (len(BLOCK_CHARS) - 1))
    partial_block = BLOCK_CHARS[remainder_idx] if remainder_idx > 0 else ""
    
    # Check if we need padding
    padding = width - full_blocks - (1 if partial_block else 0)
    
    bar = ("█" * full_blocks) + partial_block + ("·" * padding)
    return bar[:width] # Safety clip
