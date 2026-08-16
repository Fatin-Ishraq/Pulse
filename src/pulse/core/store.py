"""
Holds the latest Snapshot, the history behind it, and everything derived.

Rates are computed here, once per tick, from two consecutive snapshots. Before
this existed, each panel tracked its own ``last_net``/``last_io`` and divided by
an assumed one-second interval, so the numbers drifted apart whenever the
refresh rate changed or a tick ran late.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional, Tuple

from pulse.core.models import Snapshot

# 80 samples is what the widest waveform in the UI draws.
HISTORY_LENGTH = 80


@dataclass(frozen=True)
class Rates:
    """Per-second values derived from two consecutive snapshots."""

    interval: float = 0.0
    net_sent_kbps: float = 0.0
    net_recv_kbps: float = 0.0
    disk_read_mbps: float = 0.0
    disk_write_mbps: float = 0.0
    disk_read_latency_ms: float = 0.0
    disk_write_latency_ms: float = 0.0


@dataclass
class Peaks:
    """Session highs, for the Insight panel."""

    cpu: float = 0.0
    memory: float = 0.0
    net_sent_kbps: float = 0.0
    net_recv_kbps: float = 0.0
    disk_read_mbps: float = 0.0
    disk_write_mbps: float = 0.0


@dataclass
class History:
    """Bounded ring buffers for the waveform views."""

    maxlen: int = HISTORY_LENGTH
    cpu: Deque[float] = field(default_factory=lambda: deque(maxlen=HISTORY_LENGTH))
    memory: Deque[float] = field(default_factory=lambda: deque(maxlen=HISTORY_LENGTH))
    net_sent: Deque[float] = field(default_factory=lambda: deque(maxlen=HISTORY_LENGTH))
    net_recv: Deque[float] = field(default_factory=lambda: deque(maxlen=HISTORY_LENGTH))
    disk_read: Deque[float] = field(default_factory=lambda: deque(maxlen=HISTORY_LENGTH))
    disk_write: Deque[float] = field(default_factory=lambda: deque(maxlen=HISTORY_LENGTH))
    tension: Deque[float] = field(default_factory=lambda: deque(maxlen=HISTORY_LENGTH))


class MetricStore:
    """The single place the UI reads from.

    Panels ask the store for the current snapshot and its history; they never
    sample anything themselves.
    """

    def __init__(self, history_length: int = HISTORY_LENGTH) -> None:
        self.history_length = history_length
        self.history = History(maxlen=history_length)
        self.peaks = Peaks()
        self.rates = Rates()

        self._snapshot: Optional[Snapshot] = None
        self._previous: Optional[Snapshot] = None
        self._per_core: List[Deque[float]] = []
        self._started_at: Optional[float] = None
        self.tick_count = 0

        # Rebuild the deques at the requested length.
        if history_length != HISTORY_LENGTH:
            for name in ("cpu", "memory", "net_sent", "net_recv",
                         "disk_read", "disk_write", "tension"):
                setattr(self.history, name, deque(maxlen=history_length))

    # ------------------------------------------------------------------
    # Reading
    # ------------------------------------------------------------------
    @property
    def snapshot(self) -> Optional[Snapshot]:
        """The most recent snapshot, or None before the first tick."""
        return self._snapshot

    @property
    def ready(self) -> bool:
        return self._snapshot is not None

    @property
    def uptime_seconds(self) -> float:
        """How long this Pulse session has been sampling."""
        if self._started_at is None or self._snapshot is None:
            return 0.0
        return self._snapshot.timestamp - self._started_at

    def per_core_history(self, index: int) -> Tuple[float, ...]:
        if 0 <= index < len(self._per_core):
            return tuple(self._per_core[index])
        return ()

    @property
    def tension(self) -> float:
        """A rough "how stressed is this machine" score, 0-100.

        Deliberately simple and documented as a heuristic: a weighted blend of
        CPU, memory, and I/O saturation. It is not a model of anything.
        """
        if self._snapshot is None:
            return 0.0

        cpu = self._snapshot.cpu.percent
        memory = self._snapshot.memory.percent
        # 50 MB/s of combined throughput counts as fully saturated.
        io = min(100.0, (self.rates.disk_read_mbps + self.rates.disk_write_mbps) * 2.0)
        return min(100.0, cpu * 0.4 + memory * 0.4 + io * 0.2)

    # ------------------------------------------------------------------
    # Writing
    # ------------------------------------------------------------------
    def push(self, snapshot: Snapshot) -> None:
        """Record a new tick and update everything derived from it."""
        self._previous = self._snapshot
        self._snapshot = snapshot
        self.tick_count += 1

        if self._started_at is None:
            self._started_at = snapshot.timestamp

        self.rates = self._derive_rates(self._previous, snapshot)
        self._update_history(snapshot)
        self._update_peaks(snapshot)

    @staticmethod
    def _derive_rates(previous: Optional[Snapshot], current: Snapshot) -> Rates:
        """Per-second rates between two snapshots.

        Uses the real elapsed time between them, so a late or reconfigured tick
        reports the correct rate instead of assuming one second passed.
        """
        if previous is None:
            return Rates()

        interval = current.timestamp - previous.timestamp
        if interval <= 0:
            return Rates()

        def per_second(now: int, before: int, divisor: float) -> float:
            delta = now - before
            # Counters reset when an interface or device goes away.
            if delta < 0:
                return 0.0
            return delta / divisor / interval

        read_ops = current.disk_io.read_count - previous.disk_io.read_count
        write_ops = current.disk_io.write_count - previous.disk_io.write_count
        read_time = current.disk_io.read_time_ms - previous.disk_io.read_time_ms
        write_time = current.disk_io.write_time_ms - previous.disk_io.write_time_ms

        return Rates(
            interval=interval,
            net_sent_kbps=per_second(current.network.bytes_sent,
                                     previous.network.bytes_sent, 1024),
            net_recv_kbps=per_second(current.network.bytes_recv,
                                     previous.network.bytes_recv, 1024),
            disk_read_mbps=per_second(current.disk_io.read_bytes,
                                      previous.disk_io.read_bytes, 1024 ** 2),
            disk_write_mbps=per_second(current.disk_io.write_bytes,
                                       previous.disk_io.write_bytes, 1024 ** 2),
            disk_read_latency_ms=(read_time / read_ops) if read_ops > 0 else 0.0,
            disk_write_latency_ms=(write_time / write_ops) if write_ops > 0 else 0.0,
        )

    def _update_history(self, snapshot: Snapshot) -> None:
        self.history.cpu.append(snapshot.cpu.percent)
        self.history.memory.append(snapshot.memory.percent)
        self.history.net_sent.append(self.rates.net_sent_kbps)
        self.history.net_recv.append(self.rates.net_recv_kbps)
        self.history.disk_read.append(self.rates.disk_read_mbps)
        self.history.disk_write.append(self.rates.disk_write_mbps)
        self.history.tension.append(self.tension)

        # Grow the per-core buffers if the core count changed (or on first tick).
        while len(self._per_core) < snapshot.cpu.core_count:
            self._per_core.append(deque(maxlen=self.history_length))
        for index, value in enumerate(snapshot.cpu.per_core):
            self._per_core[index].append(value)

    def _update_peaks(self, snapshot: Snapshot) -> None:
        self.peaks.cpu = max(self.peaks.cpu, snapshot.cpu.percent)
        self.peaks.memory = max(self.peaks.memory, snapshot.memory.percent)
        self.peaks.net_sent_kbps = max(self.peaks.net_sent_kbps, self.rates.net_sent_kbps)
        self.peaks.net_recv_kbps = max(self.peaks.net_recv_kbps, self.rates.net_recv_kbps)
        self.peaks.disk_read_mbps = max(self.peaks.disk_read_mbps, self.rates.disk_read_mbps)
        self.peaks.disk_write_mbps = max(self.peaks.disk_write_mbps, self.rates.disk_write_mbps)

    def reset_network_baseline(self) -> None:
        """Clear the network waveforms without disturbing other history."""
        self.history.net_sent.clear()
        self.history.net_recv.clear()
        self.peaks.net_sent_kbps = 0.0
        self.peaks.net_recv_kbps = 0.0
