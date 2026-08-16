"""Tests for the immutable sample types."""
import dataclasses

import pytest

from pulse.core.models import (
    CpuSample,
    MemorySample,
    NetworkSample,
    InterfaceInfo,
    ProcessSample,
    Snapshot,
)


class TestImmutability:
    @pytest.mark.parametrize("sample", [
        CpuSample(per_core=(1.0,)),
        MemorySample(total=100),
        NetworkSample(bytes_sent=1),
        ProcessSample(pid=1),
        Snapshot(),
    ])
    def test_samples_cannot_be_mutated(self, sample):
        """A snapshot is shared across every panel, so it has to be read-only."""
        field_name = dataclasses.fields(sample)[0].name
        with pytest.raises(dataclasses.FrozenInstanceError):
            setattr(sample, field_name, None)


class TestCpuSample:
    def test_percent_is_the_mean_of_cores(self):
        assert CpuSample(per_core=(0.0, 50.0, 100.0, 50.0)).percent == 50.0

    def test_empty_sample_reports_zero(self):
        assert CpuSample().percent == 0.0
        assert CpuSample().core_count == 0

    def test_core_count_follows_the_tuple(self):
        assert CpuSample(per_core=(1.0, 2.0, 3.0)).core_count == 3


class TestMemorySample:
    def test_swap_percent(self):
        sample = MemorySample(swap_total=1000, swap_used=250)
        assert sample.swap_percent == 25.0

    def test_swap_percent_without_swap_is_zero(self):
        """Machines with swap disabled must not divide by zero."""
        assert MemorySample(swap_total=0, swap_used=0).swap_percent == 0.0


class TestNetworkSample:
    def test_primary_ipv4_skips_loopback(self):
        sample = NetworkSample(interfaces=(
            InterfaceInfo("lo", is_up=True, ipv4="127.0.0.1"),
            InterfaceInfo("eth0", is_up=True, ipv4="10.0.0.5"),
        ))
        assert sample.primary_ipv4 == "10.0.0.5"

    def test_primary_ipv4_is_none_when_only_loopback(self):
        sample = NetworkSample(interfaces=(
            InterfaceInfo("lo", is_up=True, ipv4="127.0.0.1"),
        ))
        assert sample.primary_ipv4 is None

    def test_active_interfaces_counts_only_up(self):
        sample = NetworkSample(interfaces=(
            InterfaceInfo("eth0", is_up=True),
            InterfaceInfo("wlan0", is_up=False),
            InterfaceInfo("lo", is_up=True),
        ))
        assert sample.active_interfaces == 2


class TestProcessSample:
    def test_memory_percent(self):
        process = ProcessSample(pid=1, memory_bytes=512)
        assert process.memory_percent(2048) == 25.0

    def test_memory_percent_without_total_is_zero(self):
        assert ProcessSample(pid=1, memory_bytes=512).memory_percent(0) == 0.0


class TestSnapshot:
    def _snapshot(self):
        return Snapshot(processes=(
            ProcessSample(pid=1, name="low", cpu_percent=1.0, memory_bytes=900),
            ProcessSample(pid=2, name="high", cpu_percent=90.0, memory_bytes=100),
            ProcessSample(pid=3, name="mid", cpu_percent=50.0, memory_bytes=500),
        ))

    def test_top_processes_by_cpu(self):
        top = self._snapshot().top_processes("cpu", limit=2)
        assert [p.name for p in top] == ["high", "mid"]

    def test_top_processes_by_memory(self):
        top = self._snapshot().top_processes("mem", limit=2)
        assert [p.name for p in top] == ["low", "mid"]

    def test_top_processes_respects_limit(self):
        assert len(self._snapshot().top_processes(limit=1)) == 1

    def test_find_process(self):
        assert self._snapshot().find_process(2).name == "high"
        assert self._snapshot().find_process(999) is None

    def test_healthy_reflects_errors(self):
        assert Snapshot().healthy
        assert not Snapshot(errors={"cpu": "boom"}).healthy

    def test_defaults_are_independent_between_instances(self):
        """Mutable defaults shared across snapshots would be a real hazard."""
        first, second = Snapshot(), Snapshot()
        assert first.cpu is not second.cpu
        assert first.errors is not second.errors
