"""Tests for the store: derived rates, history bounds, and peaks."""
import pytest

from pulse.core.models import (
    CpuSample,
    DiskIOSample,
    MemorySample,
    NetworkSample,
    Snapshot,
)
from pulse.core.store import MetricStore


def snapshot(timestamp=0.0, cpu=0.0, memory=0.0, sent=0, recv=0,
             read=0, write=0, read_count=0, write_count=0,
             read_time=0, write_time=0, cores=4):
    return Snapshot(
        timestamp=timestamp,
        cpu=CpuSample(per_core=tuple([cpu] * cores)),
        memory=MemorySample(total=1000, used=int(memory * 10), percent=memory),
        network=NetworkSample(bytes_sent=sent, bytes_recv=recv),
        disk_io=DiskIOSample(read_bytes=read, write_bytes=write,
                             read_count=read_count, write_count=write_count,
                             read_time_ms=read_time, write_time_ms=write_time),
    )


class TestFirstTick:
    def test_store_starts_empty(self):
        store = MetricStore()
        assert not store.ready
        assert store.snapshot is None
        assert store.tension == 0.0

    def test_first_push_has_no_rates(self):
        """There is nothing to diff against yet, so rates must read zero."""
        store = MetricStore()
        store.push(snapshot(timestamp=100.0, sent=5000))

        assert store.ready
        assert store.rates.net_sent_kbps == 0.0
        assert store.rates.interval == 0.0


class TestDerivedRates:
    def test_network_rate_uses_real_elapsed_time(self):
        store = MetricStore()
        store.push(snapshot(timestamp=100.0, sent=0, recv=0))
        # 2048 bytes over 2 seconds = 1 KB/s
        store.push(snapshot(timestamp=102.0, sent=2048, recv=4096))

        assert store.rates.net_sent_kbps == pytest.approx(1.0)
        assert store.rates.net_recv_kbps == pytest.approx(2.0)

    def test_rate_scales_with_the_interval(self):
        """The old code divided by an assumed 1s, so a 4s tick read 4x high."""
        store = MetricStore()
        store.push(snapshot(timestamp=0.0, sent=0))
        store.push(snapshot(timestamp=4.0, sent=4096))

        assert store.rates.net_sent_kbps == pytest.approx(1.0)
        assert store.rates.interval == pytest.approx(4.0)

    def test_disk_throughput(self):
        mib = 1024 ** 2
        store = MetricStore()
        store.push(snapshot(timestamp=0.0))
        store.push(snapshot(timestamp=2.0, read=10 * mib, write=4 * mib))

        assert store.rates.disk_read_mbps == pytest.approx(5.0)
        assert store.rates.disk_write_mbps == pytest.approx(2.0)

    def test_disk_latency_is_time_over_ops(self):
        store = MetricStore()
        store.push(snapshot(timestamp=0.0))
        store.push(snapshot(timestamp=1.0, read_count=10, read_time=50,
                            write_count=4, write_time=20))

        assert store.rates.disk_read_latency_ms == pytest.approx(5.0)
        assert store.rates.disk_write_latency_ms == pytest.approx(5.0)

    def test_latency_without_operations_is_zero(self):
        store = MetricStore()
        store.push(snapshot(timestamp=0.0))
        store.push(snapshot(timestamp=1.0, read_count=0, read_time=0))
        assert store.rates.disk_read_latency_ms == 0.0

    def test_counter_reset_does_not_produce_negative_rates(self):
        """Interfaces going away can make a cumulative counter go backwards."""
        store = MetricStore()
        store.push(snapshot(timestamp=0.0, sent=100000))
        store.push(snapshot(timestamp=1.0, sent=5))

        assert store.rates.net_sent_kbps == 0.0

    def test_zero_interval_is_survivable(self):
        store = MetricStore()
        store.push(snapshot(timestamp=5.0, sent=0))
        store.push(snapshot(timestamp=5.0, sent=9999))
        assert store.rates.net_sent_kbps == 0.0

    def test_backwards_clock_is_survivable(self):
        store = MetricStore()
        store.push(snapshot(timestamp=10.0))
        store.push(snapshot(timestamp=9.0, sent=1024))
        assert store.rates.net_sent_kbps == 0.0


class TestHistory:
    def test_history_grows_with_ticks(self):
        store = MetricStore()
        for i in range(5):
            store.push(snapshot(timestamp=float(i), cpu=10.0 * i))

        assert list(store.history.cpu) == [0.0, 10.0, 20.0, 30.0, 40.0]

    def test_history_is_bounded(self):
        store = MetricStore(history_length=10)
        for i in range(50):
            store.push(snapshot(timestamp=float(i), cpu=float(i)))

        assert len(store.history.cpu) == 10
        # Keeps the newest samples, not the oldest.
        assert list(store.history.cpu)[-1] == 49.0

    def test_per_core_history_is_tracked(self):
        store = MetricStore()
        for i in range(3):
            store.push(snapshot(timestamp=float(i), cpu=float(i * 10), cores=2))

        assert store.per_core_history(0) == (0.0, 10.0, 20.0)
        assert store.per_core_history(1) == (0.0, 10.0, 20.0)

    def test_per_core_history_out_of_range_is_empty(self):
        store = MetricStore()
        store.push(snapshot(cores=2))
        assert store.per_core_history(99) == ()

    def test_core_count_growing_is_handled(self):
        """CPU hotplug should not raise."""
        store = MetricStore()
        store.push(snapshot(timestamp=0.0, cores=2))
        store.push(snapshot(timestamp=1.0, cores=8))
        assert len(store.per_core_history(7)) == 1


class TestPeaks:
    def test_tracks_session_highs(self):
        store = MetricStore()
        store.push(snapshot(timestamp=0.0, cpu=20.0, memory=30.0))
        store.push(snapshot(timestamp=1.0, cpu=90.0, memory=40.0))
        store.push(snapshot(timestamp=2.0, cpu=10.0, memory=20.0))

        assert store.peaks.cpu == 90.0
        assert store.peaks.memory == 40.0

    def test_network_peaks_track_rates(self):
        store = MetricStore()
        store.push(snapshot(timestamp=0.0))
        store.push(snapshot(timestamp=1.0, sent=10240))
        store.push(snapshot(timestamp=2.0, sent=10240))

        assert store.peaks.net_sent_kbps == pytest.approx(10.0)


class TestTension:
    def test_blends_cpu_memory_and_io(self):
        store = MetricStore()
        store.push(snapshot(timestamp=0.0, cpu=100.0, memory=100.0))
        # 0.4 * 100 + 0.4 * 100 + 0 = 80
        assert store.tension == pytest.approx(80.0)

    def test_is_capped_at_100(self):
        mib = 1024 ** 2
        store = MetricStore()
        store.push(snapshot(timestamp=0.0))
        store.push(snapshot(timestamp=1.0, cpu=100.0, memory=100.0,
                            read=999 * mib, write=999 * mib))
        assert store.tension <= 100.0

    def test_idle_machine_scores_low(self):
        store = MetricStore()
        store.push(snapshot(timestamp=0.0, cpu=0.0, memory=0.0))
        assert store.tension == 0.0


class TestSessionTracking:
    def test_uptime_measures_from_the_first_tick(self):
        store = MetricStore()
        store.push(snapshot(timestamp=1000.0))
        store.push(snapshot(timestamp=1042.0))
        assert store.uptime_seconds == pytest.approx(42.0)

    def test_tick_count(self):
        store = MetricStore()
        for i in range(7):
            store.push(snapshot(timestamp=float(i)))
        assert store.tick_count == 7

    def test_network_baseline_reset_leaves_other_history(self):
        store = MetricStore()
        for i in range(5):
            store.push(snapshot(timestamp=float(i), cpu=50.0, sent=i * 1024))

        store.reset_network_baseline()

        assert len(store.history.net_sent) == 0
        assert store.peaks.net_sent_kbps == 0.0
        assert len(store.history.cpu) == 5
