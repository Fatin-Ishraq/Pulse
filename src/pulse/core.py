"""
Pulse Core - Hardware Interface Layer

Read-only metrics come from ``pulse.direct_os``. State-changing operations are
re-exported from ``pulse.actions``, which is the guarded layer: it refuses
protected targets and reports failures instead of swallowing them.
"""
from pulse import direct_os
from pulse.actions import (
    ActionResult,
    ProcessInfo,
    adjust_nice,
    describe_process,
    get_nice,
    kill_process,
    protection_reason,
    renice_process,
)

# Metrics (read-only)
init = direct_os.init
get_memory_info = direct_os.get_memory_info
get_cpu_percents = direct_os.get_cpu_percents
get_process_list = direct_os.get_process_list
get_network_stats = direct_os.get_network_stats
get_disk_info = direct_os.get_disk_info

__all__ = [
    "ActionResult",
    "ProcessInfo",
    "adjust_nice",
    "describe_process",
    "get_cpu_percents",
    "get_disk_info",
    "get_memory_info",
    "get_network_stats",
    "get_nice",
    "get_process_list",
    "init",
    "kill_process",
    "protection_reason",
    "renice_process",
]
