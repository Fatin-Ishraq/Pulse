"""Tests for the sampler, mostly about what happens when a subsystem breaks."""
import pytest

from pulse.core.models import Snapshot
from pulse.core.sampler import Sampler
from pulse.core.sources.mock import MockSource


def make_sampler(**kwargs):
    source = MockSource(**kwargs)
    return Sampler(source, clock=lambda: 1000.0), source


class TestSampling:
    def test_produces_a_complete_snapshot(self):
        sampler, source = make_sampler()
        source.advance()

        snapshot = sampler.sample()

        assert isinstance(snapshot, Snapshot)
        assert snapshot.timestamp == 1000.0
        assert snapshot.cpu.core_count == 4
        assert snapshot.memory.total > 0
        assert len(snapshot.processes) == 12
        assert len(snapshot.volumes) == 2
        assert snapshot.system.hostname == "mock-host"
        assert snapshot.healthy

    def test_reads_each_subsystem_exactly_once_per_tick(self):
        """The bug this design replaces: four panels sampling CPU separately."""
        sampler, source = make_sampler()

        sampler.sample()

        assert source.call_counts["cpu"] == 1
        assert source.call_counts["memory"] == 1
        assert source.call_counts["network"] == 1

    def test_primes_the_source_before_the_first_sample(self):
        sampler, source = make_sampler()
        assert not source.primed

        sampler.sample()

        assert source.primed

    def test_priming_happens_only_once(self):
        sampler, source = make_sampler()
        sampler.sample()
        source.primed = False
        sampler.sample()
        assert not source.primed  # not re-primed

    def test_snapshots_are_independent(self):
        sampler, source = make_sampler()
        first = sampler.sample()
        source.advance(5)
        second = sampler.sample()
        assert first.cpu.per_core != second.cpu.per_core


class TestFaultIsolation:
    def test_one_broken_subsystem_does_not_break_the_tick(self):
        sampler, _ = make_sampler(fail={"network"})

        snapshot = sampler.sample()

        # Network is empty and flagged...
        assert "network" in snapshot.errors
        assert snapshot.network.bytes_sent == 0
        # ...but everything else still came through.
        assert snapshot.cpu.core_count == 4
        assert snapshot.memory.total > 0
        assert len(snapshot.processes) == 12
        assert not snapshot.healthy

    def test_records_the_error_text(self):
        sampler, _ = make_sampler(fail={"cpu"})
        snapshot = sampler.sample()
        assert "RuntimeError" in snapshot.errors["cpu"]

    def test_every_subsystem_failing_still_returns_a_snapshot(self):
        """A totally hostile machine should degrade, not crash the app."""
        sampler, _ = make_sampler(fail={
            "cpu", "memory", "disk_io", "network",
            "processes", "volumes", "system", "containers",
        })

        snapshot = sampler.sample()

        assert isinstance(snapshot, Snapshot)
        assert len(snapshot.errors) == 8
        assert snapshot.cpu.percent == 0.0
        assert snapshot.processes == ()

    def test_sample_never_raises(self):
        class Hostile:
            def __getattr__(self, name):
                def explode():
                    raise OSError("everything is broken")
                return explode

        snapshot = Sampler(Hostile()).sample()
        assert isinstance(snapshot, Snapshot)

    def test_failed_priming_does_not_stop_sampling(self):
        class BadPrime(MockSource):
            def prime(self):
                raise OSError("cannot prime")

        snapshot = Sampler(BadPrime()).sample()
        assert snapshot.cpu.core_count == 4
