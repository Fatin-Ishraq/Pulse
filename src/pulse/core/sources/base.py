"""
The contract a metric source has to satisfy.

Sources answer one question each and return model objects. They are allowed to
be slow and to raise - the sampler runs them off the event loop and isolates
their failures. They are not allowed to import anything from the UI.
"""
from __future__ import annotations

from typing import Protocol, Tuple, runtime_checkable

from pulse.core.models import (
    ContainerSample,
    CpuSample,
    DiskIOSample,
    MemorySample,
    NetworkSample,
    ProcessSample,
    SystemSample,
    VolumeSample,
)


@runtime_checkable
class MetricSource(Protocol):
    """Where a Snapshot's numbers come from.

    Implemented by the live system, and by fakes for tests and replay.
    """

    def cpu(self) -> CpuSample:
        ...

    def memory(self) -> MemorySample:
        ...

    def disk_io(self) -> DiskIOSample:
        ...

    def network(self) -> NetworkSample:
        ...

    def processes(self) -> Tuple[ProcessSample, ...]:
        ...

    def volumes(self) -> Tuple[VolumeSample, ...]:
        ...

    def system(self) -> SystemSample:
        ...

    def containers(self) -> Tuple[ContainerSample, ...]:
        ...

    def prime(self) -> None:
        """Warm up delta-based counters so the first real reading is meaningful."""
