"""
Pulse Core - metrics, sampling, and state.

Nothing in this package imports Textual or Rich. The UI depends on core; core
does not know the UI exists. That is what makes it testable headless, and what
would let a future exporter or web frontend reuse it unchanged.

The pieces:

- ``models``  - frozen dataclasses; one tick is one ``Snapshot``
- ``sources`` - where numbers come from (the live system, or a mock)
- ``sampler`` - one source poll -> one Snapshot, with failures isolated
- ``store``   - the latest Snapshot plus history, rates, and peaks

Guarded state-changing operations live in ``pulse.actions`` and are re-exported
here for convenience.
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
from pulse.core.models import (
    BatterySample,
    ContainerSample,
    CpuSample,
    DiskIOSample,
    InterfaceInfo,
    MemorySample,
    NetworkSample,
    ProcessSample,
    Snapshot,
    SystemSample,
    VolumeSample,
)
from pulse.core.sampler import Sampler
from pulse.core.sources import MetricSource, MockSource, SystemSource
from pulse.core.store import History, MetricStore, Peaks, Rates

# Low-level metric functions. Panels should read from a MetricStore instead;
# these remain for direct_os-level access and the existing test suite.
init = direct_os.init
get_memory_info = direct_os.get_memory_info
get_cpu_percents = direct_os.get_cpu_percents
get_process_list = direct_os.get_process_list
get_network_stats = direct_os.get_network_stats
get_disk_info = direct_os.get_disk_info

__all__ = [
    # Actions
    "ActionResult",
    "ProcessInfo",
    "adjust_nice",
    "describe_process",
    "get_nice",
    "kill_process",
    "protection_reason",
    "renice_process",
    # Models
    "BatterySample",
    "ContainerSample",
    "CpuSample",
    "DiskIOSample",
    "InterfaceInfo",
    "MemorySample",
    "NetworkSample",
    "ProcessSample",
    "Snapshot",
    "SystemSample",
    "VolumeSample",
    # Machinery
    "History",
    "MetricSource",
    "MetricStore",
    "MockSource",
    "Peaks",
    "Rates",
    "Sampler",
    "SystemSource",
    # Low-level metrics
    "get_cpu_percents",
    "get_disk_info",
    "get_memory_info",
    "get_network_stats",
    "get_process_list",
    "init",
]
