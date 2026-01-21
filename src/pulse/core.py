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

def get_process_list(sort_by=None, limit=None, fallback_func=None):
    """Get list of processes from Rust or fallback.
    
    Args:
        sort_by (str, optional): 'cpu' or 'mem'. Defaults to None.
        limit (int, optional): Number of processes to return. Defaults to None.
        fallback_func (callable): Function to call if Rust fails.
    """
    if HAS_RUST:
        try:
            return pulse_core.get_process_list(sort_by, limit)
        except Exception:
            if fallback_func: return fallback_func()
    if fallback_func: return fallback_func()
    return []

def get_network_stats(fallback_func):
    """Get Global Network IO Stats from Rust or fallback."""
    if HAS_RUST:
        try:
            return pulse_core.get_network_stats()
        except Exception:
            return fallback_func()
    return fallback_func()

def get_disk_info(fallback_func):
    """Get Disk Usage Info from Rust or fallback."""
    if HAS_RUST:
        try:
            return pulse_core.get_disk_info()
        except Exception:
            return fallback_func()
    return fallback_func()
