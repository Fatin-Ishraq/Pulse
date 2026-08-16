"""Tests for the metric sources.

SystemSource runs against the real machine, so assertions here are about shape
and plausibility rather than exact values. The point is that every method
returns a well-formed model on this platform and that the sampler contract
holds.
"""
import os

import pytest

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
from pulse.core.sampler import Sampler
from pulse.core.sources import MetricSource, MockSource, SystemSource


@pytest.fixture(scope="module")
def system_source():
    source = SystemSource()
    source.prime()
    return source


class TestProtocolConformance:
    @pytest.mark.parametrize("source", [SystemSource(), MockSource()])
    def test_sources_satisfy_the_protocol(self, source):
        assert isinstance(source, MetricSource)


class TestSystemSourceShape:
    def test_cpu(self, system_source):
        cpu = system_source.cpu()
        assert isinstance(cpu, CpuSample)
        assert cpu.core_count > 0
        assert all(0.0 <= value <= 100.0 for value in cpu.per_core)
        assert 0.0 <= cpu.percent <= 100.0

    def test_memory(self, system_source):
        memory = system_source.memory()
        assert isinstance(memory, MemorySample)
        assert memory.total > 0
        assert 0.0 <= memory.percent <= 100.0
        assert memory.used <= memory.total
        assert 0.0 <= memory.swap_percent <= 100.0

    def test_disk_io(self, system_source):
        disk = system_source.disk_io()
        assert isinstance(disk, DiskIOSample)
        assert disk.read_bytes >= 0
        assert disk.write_bytes >= 0

    def test_network(self, system_source):
        network = system_source.network()
        assert isinstance(network, NetworkSample)
        assert network.bytes_sent >= 0
        assert network.bytes_recv >= 0
        assert len(network.interfaces) > 0

    def test_processes_include_this_one(self, system_source):
        processes = system_source.processes()
        assert len(processes) > 0
        assert all(isinstance(p, ProcessSample) for p in processes)
        assert os.getpid() in {p.pid for p in processes}

    def test_process_memory_is_plausible(self, system_source):
        """Guards the statm mix-up that reported virtual size as resident."""
        me = next(p for p in system_source.processes() if p.pid == os.getpid())
        assert me.memory_bytes > 0
        # A Python test process using more than 8 GB resident means we are
        # reading the wrong field again.
        assert me.memory_bytes < 8 * 1024 ** 3

    def test_volumes(self, system_source):
        volumes = system_source.volumes()
        assert all(isinstance(v, VolumeSample) for v in volumes)
        for volume in volumes:
            assert 0.0 <= volume.percent <= 100.0
            assert volume.used <= volume.total

    def test_system(self, system_source):
        info = system_source.system()
        assert isinstance(info, SystemSample)
        assert info.hostname
        assert info.platform_name
        assert info.boot_time > 0

    def test_system_facts_are_cached_but_battery_is_not(self, system_source):
        """Host identity cannot change mid-session; battery level can."""
        first, second = system_source.system(), system_source.system()
        assert first.hostname == second.hostname
        assert first.boot_time == second.boot_time

    def test_containers_empty_without_a_controller(self, system_source):
        assert system_source.containers() == ()


class TestSystemSourceContainers:
    def test_containers_come_from_the_controller(self):
        class FakeController:
            def get_containers(self):
                return [{
                    "id": "abc", "name": "web", "image": "nginx",
                    "status": "running", "state": "running",
                }]

        containers = SystemSource(FakeController()).containers()
        assert len(containers) == 1
        assert isinstance(containers[0], ContainerSample)
        assert containers[0].name == "web"


class TestSystemSourceEndToEnd:
    def test_sampler_produces_a_healthy_snapshot_from_the_real_machine(self):
        snapshot = Sampler(SystemSource()).sample()

        assert snapshot.cpu.core_count > 0
        assert snapshot.memory.total > 0
        assert len(snapshot.processes) > 0
        # A subsystem may legitimately be restricted (net_connections on macOS),
        # but nothing should have thrown an unexpected error type.
        for name, message in snapshot.errors.items():
            pytest.fail(f"unexpected sampling failure in {name}: {message}")

    def test_consecutive_samples_yield_usable_rates(self):
        from pulse.core.store import MetricStore

        sampler = Sampler(SystemSource())
        store = MetricStore()
        store.push(sampler.sample())
        store.push(sampler.sample())

        assert store.rates.interval > 0
        assert store.rates.net_sent_kbps >= 0
        assert store.rates.disk_read_mbps >= 0


class TestMockSource:
    def test_is_deterministic(self):
        first, second = MockSource(), MockSource()
        first.advance(3)
        second.advance(3)
        assert first.cpu().per_core == second.cpu().per_core

    def test_advancing_changes_readings(self):
        source = MockSource()
        before = source.cpu().per_core
        source.advance(2)
        assert source.cpu().per_core != before

    def test_counters_increase_monotonically(self):
        source = MockSource()
        source.advance()
        first = source.network().bytes_sent
        source.advance()
        assert source.network().bytes_sent > first

    def test_processes_are_sorted_by_cpu_descending(self):
        loads = [p.cpu_percent for p in MockSource().processes()]
        assert loads == sorted(loads, reverse=True)

    def test_failure_injection(self):
        source = MockSource(fail={"cpu"})
        with pytest.raises(RuntimeError):
            source.cpu()
        # Other subsystems are unaffected.
        assert source.memory().total > 0

    def test_call_counts_are_recorded(self):
        source = MockSource()
        source.cpu()
        source.cpu()
        source.memory()
        assert source.call_counts == {"cpu": 2, "memory": 1}
