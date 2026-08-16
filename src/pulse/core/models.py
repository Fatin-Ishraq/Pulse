"""
Immutable sample types.

Everything here is a frozen dataclass with no behaviour beyond simple derived
properties. One poll of a source produces one ``Snapshot``, and every widget
renders from that same object - so the CPU number in the sidebar is the same
number the process table was sorted by.

Nothing in this module imports Textual, Rich, or psutil.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Optional, Tuple


@dataclass(frozen=True)
class CpuSample:
    """Processor load for a single tick."""

    per_core: Tuple[float, ...] = ()
    frequency_mhz: Optional[float] = None
    load_average: Optional[Tuple[float, float, float]] = None
    context_switches: Optional[int] = None
    interrupts: Optional[int] = None
    syscalls: Optional[int] = None

    @property
    def percent(self) -> float:
        """Mean load across all cores."""
        if not self.per_core:
            return 0.0
        return sum(self.per_core) / len(self.per_core)

    @property
    def core_count(self) -> int:
        return len(self.per_core)


@dataclass(frozen=True)
class MemorySample:
    """Physical and swap memory for a single tick."""

    total: int = 0
    available: int = 0
    used: int = 0
    free: int = 0
    percent: float = 0.0
    cached: Optional[int] = None
    buffers: Optional[int] = None
    swap_total: int = 0
    swap_used: int = 0
    swap_free: int = 0

    @property
    def swap_percent(self) -> float:
        if not self.swap_total:
            return 0.0
        return self.swap_used / self.swap_total * 100.0


@dataclass(frozen=True)
class DiskIOSample:
    """Cumulative disk I/O counters.

    These are totals since boot, not rates. Rates are derived by the store from
    two consecutive snapshots, so nothing else has to track its own deltas.
    """

    read_bytes: int = 0
    write_bytes: int = 0
    read_count: int = 0
    write_count: int = 0
    read_time_ms: int = 0
    write_time_ms: int = 0
    per_disk: Mapping[str, "DiskIOSample"] = field(default_factory=dict)


@dataclass(frozen=True)
class InterfaceInfo:
    """One network interface."""

    name: str
    is_up: bool = False
    speed_mbps: int = 0
    mtu: int = 0
    ipv4: Optional[str] = None


@dataclass(frozen=True)
class NetworkSample:
    """Cumulative network counters plus interface state."""

    bytes_sent: int = 0
    bytes_recv: int = 0
    packets_sent: int = 0
    packets_recv: int = 0
    interfaces: Tuple[InterfaceInfo, ...] = ()
    connection_count: int = 0
    established_count: int = 0
    listen_count: int = 0

    @property
    def primary_ipv4(self) -> Optional[str]:
        """First non-loopback IPv4 address, for the summary line."""
        for interface in self.interfaces:
            if interface.ipv4 and not interface.ipv4.startswith("127."):
                return interface.ipv4
        return None

    @property
    def active_interfaces(self) -> int:
        return sum(1 for interface in self.interfaces if interface.is_up)


@dataclass(frozen=True)
class ProcessSample:
    """One process at one instant."""

    pid: int
    name: str = "?"
    cpu_percent: float = 0.0
    memory_bytes: int = 0
    username: str = "?"
    status: str = "?"
    num_threads: int = 0

    def memory_percent(self, total_memory: int) -> float:
        if not total_memory:
            return 0.0
        return self.memory_bytes / total_memory * 100.0


@dataclass(frozen=True)
class VolumeSample:
    """A mounted filesystem."""

    device: str = ""
    mountpoint: str = ""
    fstype: str = ""
    total: int = 0
    used: int = 0
    free: int = 0
    percent: float = 0.0


@dataclass(frozen=True)
class BatterySample:
    percent: float = 0.0
    power_plugged: bool = False
    seconds_left: Optional[int] = None


@dataclass(frozen=True)
class SystemSample:
    """Host facts that change rarely or never."""

    hostname: str = ""
    platform_name: str = ""
    platform_release: str = ""
    platform_version: str = ""
    architecture: str = ""
    processor: str = ""
    boot_time: float = 0.0
    battery: Optional[BatterySample] = None


@dataclass(frozen=True)
class ContainerSample:
    """One Docker container."""

    id: str = ""
    name: str = ""
    image: str = ""
    status: str = "unknown"
    state: str = "unknown"


@dataclass(frozen=True)
class Snapshot:
    """Everything measured in one tick.

    A snapshot is a single consistent view: the sampler builds it once and all
    panels read the same instance, so numbers cannot disagree across the UI.
    """

    timestamp: float = 0.0
    cpu: CpuSample = field(default_factory=CpuSample)
    memory: MemorySample = field(default_factory=MemorySample)
    disk_io: DiskIOSample = field(default_factory=DiskIOSample)
    network: NetworkSample = field(default_factory=NetworkSample)
    processes: Tuple[ProcessSample, ...] = ()
    volumes: Tuple[VolumeSample, ...] = ()
    system: SystemSample = field(default_factory=SystemSample)
    containers: Tuple[ContainerSample, ...] = ()

    # Subsystems that raised while being sampled, mapped to the error text.
    # A failing metric degrades its own panel instead of blanking the tick.
    errors: Mapping[str, str] = field(default_factory=dict)

    def top_processes(self, key: str = "cpu", limit: int = 10) -> Tuple[ProcessSample, ...]:
        """Processes sorted by ``cpu`` or ``mem``, highest first."""
        if key == "mem":
            ordered = sorted(self.processes, key=lambda p: p.memory_bytes, reverse=True)
        else:
            ordered = sorted(self.processes, key=lambda p: p.cpu_percent, reverse=True)
        return tuple(ordered[:limit])

    def find_process(self, pid: int) -> Optional[ProcessSample]:
        for process in self.processes:
            if process.pid == pid:
                return process
        return None

    @property
    def healthy(self) -> bool:
        return not self.errors
