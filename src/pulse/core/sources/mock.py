"""
A deterministic metric source.

Lets the whole core - and eventually the whole UI - be tested without touching
the real machine. Values follow a fixed script, so a test can assert exact
numbers instead of ranges, and a subsystem can be made to fail on demand.
"""
from __future__ import annotations

import math
from typing import Dict, Optional, Set, Tuple

from pulse.core.models import (
    BatterySample,
    ContainerSample,
    CpuSample,
    DiskIOSample,
    InterfaceInfo,
    MemorySample,
    NetworkSample,
    ProcessSample,
    SystemSample,
    VolumeSample,
)

GIB = 1024 ** 3


class MockSource:
    """A fake machine that behaves the same way every run.

    CPU and memory follow a sine wave so history buffers fill with something
    varied but predictable. Counters advance by a fixed amount per tick, which
    makes derived rates exactly checkable.
    """

    def __init__(
        self,
        core_count: int = 4,
        total_memory: int = 16 * GIB,
        process_count: int = 12,
        bytes_per_tick: int = 1024 * 1024,
        fail: Optional[Set[str]] = None,
    ) -> None:
        self.core_count = core_count
        self.total_memory = total_memory
        self.process_count = process_count
        self.bytes_per_tick = bytes_per_tick
        # Subsystem names that should raise, so fault isolation can be tested.
        self.fail = set(fail or ())

        self.tick = 0
        self.primed = False
        self.call_counts: Dict[str, int] = {}

    # ------------------------------------------------------------------
    def prime(self) -> None:
        self.primed = True

    def advance(self, ticks: int = 1) -> None:
        """Move the fake machine forward in time."""
        self.tick += ticks

    def _record(self, name: str) -> None:
        self.call_counts[name] = self.call_counts.get(name, 0) + 1
        if name in self.fail:
            raise RuntimeError(f"mock {name} failure")

    def _wave(self, offset: float = 0.0, amplitude: float = 40.0,
              baseline: float = 50.0) -> float:
        value = baseline + amplitude * math.sin((self.tick + offset) / 3.0)
        return max(0.0, min(100.0, value))

    # ------------------------------------------------------------------
    def cpu(self) -> CpuSample:
        self._record("cpu")
        return CpuSample(
            per_core=tuple(self._wave(offset=i) for i in range(self.core_count)),
            frequency_mhz=2400.0,
            load_average=(1.0, 1.5, 2.0),
            context_switches=1000 * (self.tick + 1),
            interrupts=500 * (self.tick + 1),
            syscalls=2000 * (self.tick + 1),
        )

    def memory(self) -> MemorySample:
        self._record("memory")
        percent = self._wave(offset=1.5, amplitude=20.0, baseline=60.0)
        used = int(self.total_memory * percent / 100)
        swap_total = 4 * GIB
        return MemorySample(
            total=self.total_memory,
            available=self.total_memory - used,
            used=used,
            free=self.total_memory - used,
            percent=percent,
            cached=2 * GIB,
            buffers=GIB,
            swap_total=swap_total,
            swap_used=swap_total // 4,
            swap_free=swap_total - swap_total // 4,
        )

    def disk_io(self) -> DiskIOSample:
        self._record("disk_io")
        read = self.bytes_per_tick * self.tick
        write = self.bytes_per_tick * self.tick // 2
        return DiskIOSample(
            read_bytes=read,
            write_bytes=write,
            read_count=10 * self.tick,
            write_count=5 * self.tick,
            read_time_ms=20 * self.tick,
            write_time_ms=10 * self.tick,
            per_disk={
                "disk0": DiskIOSample(read_bytes=read, write_bytes=write,
                                      read_count=10 * self.tick,
                                      write_count=5 * self.tick),
            },
        )

    def network(self) -> NetworkSample:
        self._record("network")
        return NetworkSample(
            bytes_sent=self.bytes_per_tick * self.tick,
            bytes_recv=self.bytes_per_tick * self.tick * 2,
            packets_sent=100 * self.tick,
            packets_recv=200 * self.tick,
            interfaces=(
                InterfaceInfo("eth0", is_up=True, speed_mbps=1000, mtu=1500,
                              ipv4="192.168.1.10"),
                InterfaceInfo("lo", is_up=True, speed_mbps=0, mtu=65536,
                              ipv4="127.0.0.1"),
                InterfaceInfo("wlan0", is_up=False, speed_mbps=0, mtu=1500),
            ),
            connection_count=42,
            established_count=12,
            listen_count=8,
        )

    def processes(self) -> Tuple[ProcessSample, ...]:
        self._record("processes")
        return tuple(
            ProcessSample(
                pid=1000 + i,
                name=f"proc{i}",
                # Descending, so ordering assertions are unambiguous.
                cpu_percent=float(self.process_count - i),
                memory_bytes=(self.process_count - i) * 64 * 1024 * 1024,
                username="tester",
                status="running" if i % 2 == 0 else "sleeping",
                num_threads=i + 1,
            )
            for i in range(self.process_count)
        )

    def volumes(self) -> Tuple[VolumeSample, ...]:
        self._record("volumes")
        return (
            VolumeSample(device="/dev/sda1", mountpoint="/", fstype="ext4",
                         total=512 * GIB, used=256 * GIB, free=256 * GIB,
                         percent=50.0),
            VolumeSample(device="/dev/sda2", mountpoint="/home", fstype="ext4",
                         total=1024 * GIB, used=900 * GIB, free=124 * GIB,
                         percent=87.9),
        )

    def system(self) -> SystemSample:
        self._record("system")
        return SystemSample(
            hostname="mock-host",
            platform_name="MockOS",
            platform_release="1.0",
            platform_version="1.0.0",
            architecture="x86_64",
            processor="Mock CPU",
            boot_time=1_700_000_000.0,
            battery=BatterySample(percent=75.0, power_plugged=False,
                                  seconds_left=3600),
        )

    def containers(self) -> Tuple[ContainerSample, ...]:
        self._record("containers")
        return (
            ContainerSample(id="abc123", name="web", image="nginx:latest",
                            status="running", state="running"),
            ContainerSample(id="def456", name="db", image="postgres:16",
                            status="exited", state="exited"),
        )
