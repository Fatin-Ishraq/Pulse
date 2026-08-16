"""
Turns one poll of a source into one Snapshot.

The sampler's job is fault isolation. Each subsystem is read independently, and
a failure is recorded in ``Snapshot.errors`` and replaced with an empty sample
rather than propagating - so a machine where ``net_connections`` needs elevation
still shows CPU, memory, and disk.
"""
from __future__ import annotations

import time
from typing import Any, Callable, Dict, Optional

from pulse.core.models import (
    CpuSample,
    DiskIOSample,
    MemorySample,
    NetworkSample,
    Snapshot,
    SystemSample,
)
from pulse.core.sources.base import MetricSource


class Sampler:
    """Builds Snapshots from a MetricSource."""

    def __init__(self, source: MetricSource, clock: Callable[[], float] = time.time) -> None:
        self.source = source
        self._clock = clock
        self._primed = False

    def prime(self) -> None:
        """Warm up the source's delta-based counters."""
        try:
            self.source.prime()
        except Exception:
            # Priming is an optimisation; a failure here must not stop startup.
            pass
        self._primed = True

    def sample(self) -> Snapshot:
        """Read every subsystem once and assemble a Snapshot.

        Never raises: a broken subsystem is reported through ``errors``.
        """
        if not self._primed:
            self.prime()

        errors: Dict[str, str] = {}

        def read(name: str, call: Callable[[], Any], fallback: Any) -> Any:
            try:
                return call()
            except Exception as exc:  # noqa: BLE001 - deliberately broad
                # One subsystem failing must not blank the whole tick.
                errors[name] = f"{type(exc).__name__}: {exc}"
                return fallback

        snapshot = Snapshot(
            timestamp=self._clock(),
            cpu=read("cpu", self.source.cpu, CpuSample()),
            memory=read("memory", self.source.memory, MemorySample()),
            disk_io=read("disk_io", self.source.disk_io, DiskIOSample()),
            network=read("network", self.source.network, NetworkSample()),
            processes=read("processes", self.source.processes, ()),
            volumes=read("volumes", self.source.volumes, ()),
            system=read("system", self.source.system, SystemSample()),
            containers=read("containers", self.source.containers, ()),
            errors=errors,
        )
        return snapshot
