"""
Pulse Core - Hardware Interface Layer
Unified access to Rust-accelerated metrics with Python fallback.
"""
import sys

try:
    import pulse_core
    HAS_RUST = True
except ImportError:
    pulse_core = None
    HAS_RUST = False

def init():
    """Initialize the Rust core system monitor if available."""
    if HAS_RUST:
        try:
            pulse_core.init_system()
        except Exception:
            pass

def get_cpu_percents(fallback_func):
    """Get CPU percentages from Rust or fallback."""
    if HAS_RUST:
        try:
            return pulse_core.get_cpu_percents() or fallback_func()
        except Exception:
            return fallback_func()
    return fallback_func()

def get_memory_info(fallback_func):
    """Get Memory info from Rust or fallback."""
    if HAS_RUST:
        try:
            return pulse_core.get_memory_info()
        except Exception:
            return fallback_func()
    return fallback_func()

def get_process_list(fallback_func):
    """Get list of processes from Rust or fallback."""
    if HAS_RUST:
        try:
            return pulse_core.get_process_list()
        except Exception:
            return fallback_func()
    return fallback_func()
