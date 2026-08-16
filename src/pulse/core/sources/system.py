"""
The live system metric source.

This is the only place that talks to psutil and ``direct_os``. Each method is
independent, so a subsystem that raises (net_connections needs elevation on
macOS; disk_io_counters returns None in some containers) degrades on its own
rather than taking the tick with it.
"""
from __future__ import annotations

import platform
from typing import Dict, Optional, Tuple

import psutil

from pulse import direct_os
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

# Reading every socket is expensive and needs privileges on some platforms, so
# the connection table is capped rather than walked in full.
MAX_CONNECTIONS = 500
# Enough processes to fill any table view with room to sort.
MAX_PROCESSES = 300


class SystemSource:
    """Reads real metrics from the running machine."""

    def __init__(self, container_controller=None) -> None:
        # Optional and lazily connected - see pulse.container_api.
        self._containers = container_controller
        self._system_cache: Optional[SystemSample] = None

    def prime(self) -> None:
        """Prime the delta-based counters."""
        direct_os.init()

    # ------------------------------------------------------------------
    # CPU
    # ------------------------------------------------------------------
    def cpu(self) -> CpuSample:
        per_core = tuple(direct_os.get_cpu_percents())

        frequency = None
        try:
            freq = psutil.cpu_freq()
            if freq is not None:
                frequency = freq.current
        except (OSError, AttributeError, NotImplementedError):
            pass

        load_average = None
        try:
            load_average = tuple(psutil.getloadavg())
        except (OSError, AttributeError):
            pass

        context_switches = interrupts = syscalls = None
        try:
            stats = psutil.cpu_stats()
            context_switches = stats.ctx_switches
            interrupts = stats.interrupts
            syscalls = getattr(stats, "syscalls", None)
        except (OSError, AttributeError, RuntimeError):
            pass

        return CpuSample(
            per_core=per_core,
            frequency_mhz=frequency,
            load_average=load_average,
            context_switches=context_switches,
            interrupts=interrupts,
            syscalls=syscalls,
        )

    # ------------------------------------------------------------------
    # Memory
    # ------------------------------------------------------------------
    def memory(self) -> MemorySample:
        data = direct_os.get_memory_info()
        return MemorySample(
            total=data.get("total", 0),
            available=data.get("available", 0),
            used=data.get("used", 0),
            free=data.get("free", data.get("available", 0)),
            percent=float(data.get("percent", 0.0)),
            cached=data.get("cached"),
            buffers=data.get("buffers"),
            swap_total=data.get("swap_total", 0),
            swap_used=data.get("swap_used", 0),
            swap_free=data.get("swap_free", 0),
        )

    # ------------------------------------------------------------------
    # Disk I/O
    # ------------------------------------------------------------------
    def disk_io(self) -> DiskIOSample:
        totals = psutil.disk_io_counters()
        if totals is None:
            return DiskIOSample()

        per_disk: Dict[str, DiskIOSample] = {}
        try:
            for device, counters in (psutil.disk_io_counters(perdisk=True) or {}).items():
                per_disk[device] = self._io_sample(counters)
        except (OSError, RuntimeError):
            pass

        return self._io_sample(totals, per_disk)

    @staticmethod
    def _io_sample(counters, per_disk=None) -> DiskIOSample:
        return DiskIOSample(
            read_bytes=counters.read_bytes,
            write_bytes=counters.write_bytes,
            read_count=counters.read_count,
            write_count=counters.write_count,
            read_time_ms=getattr(counters, "read_time", 0),
            write_time_ms=getattr(counters, "write_time", 0),
            per_disk=per_disk or {},
        )

    # ------------------------------------------------------------------
    # Network
    # ------------------------------------------------------------------
    def network(self) -> NetworkSample:
        counters = psutil.net_io_counters()
        sent = counters.bytes_sent if counters else 0
        recv = counters.bytes_recv if counters else 0
        packets_sent = counters.packets_sent if counters else 0
        packets_recv = counters.packets_recv if counters else 0

        interfaces = self._interfaces()

        total = established = listening = 0
        try:
            connections = psutil.net_connections(kind="inet")[:MAX_CONNECTIONS]
            total = len(connections)
            established = sum(1 for c in connections if c.status == "ESTABLISHED")
            listening = sum(1 for c in connections if c.status == "LISTEN")
        except (psutil.AccessDenied, OSError, RuntimeError):
            # Needs elevation on macOS; the rest of the sample is still good.
            pass

        return NetworkSample(
            bytes_sent=sent,
            bytes_recv=recv,
            packets_sent=packets_sent,
            packets_recv=packets_recv,
            interfaces=interfaces,
            connection_count=total,
            established_count=established,
            listen_count=listening,
        )

    @staticmethod
    def _interfaces() -> Tuple[InterfaceInfo, ...]:
        try:
            stats = psutil.net_if_stats()
            addresses = psutil.net_if_addrs()
        except (OSError, RuntimeError):
            return ()

        interfaces = []
        for name, stat in stats.items():
            ipv4 = None
            for address in addresses.get(name, []):
                # AF_INET is 2 on every platform psutil supports.
                if int(address.family) == 2:
                    ipv4 = address.address
                    break
            interfaces.append(InterfaceInfo(
                name=name,
                is_up=stat.isup,
                speed_mbps=stat.speed,
                mtu=stat.mtu,
                ipv4=ipv4,
            ))
        return tuple(interfaces)

    # ------------------------------------------------------------------
    # Processes
    # ------------------------------------------------------------------
    def processes(self) -> Tuple[ProcessSample, ...]:
        raw = direct_os.get_process_list(limit=MAX_PROCESSES)

        samples = []
        for entry in raw:
            pid = entry["pid"]
            username, status, threads = self._process_details(pid)
            samples.append(ProcessSample(
                pid=pid,
                name=entry.get("name", "?"),
                cpu_percent=entry.get("cpu_percent", 0.0),
                memory_bytes=entry.get("memory_info", 0),
                username=username,
                status=status,
                num_threads=threads,
            ))
        return tuple(samples)

    @staticmethod
    def _process_details(pid: int):
        """Best-effort extras. Missing ones are not worth failing a tick over."""
        username, status, threads = "?", "?", 0
        try:
            proc = psutil.Process(pid)
            with proc.oneshot():
                try:
                    username = proc.username()
                    if "\\" in username:
                        username = username.split("\\")[-1]
                except (psutil.AccessDenied, KeyError):
                    pass
                try:
                    status = proc.status()
                except psutil.AccessDenied:
                    pass
                try:
                    threads = proc.num_threads()
                except psutil.AccessDenied:
                    pass
        except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
            pass
        return username, status, threads

    # ------------------------------------------------------------------
    # Volumes
    # ------------------------------------------------------------------
    def volumes(self) -> Tuple[VolumeSample, ...]:
        return tuple(
            VolumeSample(
                device=disk["device"],
                mountpoint=disk["mountpoint"],
                fstype=disk["fstype"],
                total=disk["total"],
                used=disk["used"],
                free=disk["free"],
                percent=disk["percent"],
            )
            for disk in direct_os.get_disk_info()
        )

    # ------------------------------------------------------------------
    # System
    # ------------------------------------------------------------------
    def system(self) -> SystemSample:
        # Host identity does not change while the app runs; only the battery
        # is re-read each tick.
        if self._system_cache is None:
            uname = platform.uname()
            try:
                boot_time = psutil.boot_time()
            except (OSError, RuntimeError):
                boot_time = 0.0

            self._system_cache = SystemSample(
                hostname=uname.node,
                platform_name=uname.system,
                platform_release=uname.release,
                platform_version=uname.version,
                architecture=uname.machine,
                processor=uname.processor,
                boot_time=boot_time,
            )

        base = self._system_cache
        return SystemSample(
            hostname=base.hostname,
            platform_name=base.platform_name,
            platform_release=base.platform_release,
            platform_version=base.platform_version,
            architecture=base.architecture,
            processor=base.processor,
            boot_time=base.boot_time,
            battery=self._battery(),
        )

    @staticmethod
    def _battery() -> Optional[BatterySample]:
        try:
            battery = psutil.sensors_battery()
        except (AttributeError, OSError, NotImplementedError):
            return None
        if battery is None:
            return None

        seconds_left = battery.secsleft
        if seconds_left in (psutil.POWER_TIME_UNLIMITED, psutil.POWER_TIME_UNKNOWN):
            seconds_left = None

        return BatterySample(
            percent=battery.percent,
            power_plugged=bool(battery.power_plugged),
            seconds_left=seconds_left,
        )

    # ------------------------------------------------------------------
    # Containers
    # ------------------------------------------------------------------
    def containers(self) -> Tuple[ContainerSample, ...]:
        if self._containers is None:
            return ()
        return tuple(
            ContainerSample(
                id=entry["id"],
                name=entry["name"],
                image=entry["image"],
                status=entry["status"],
                state=entry["state"],
            )
            for entry in self._containers.get_containers()
        )
