"""Tests for the OS metrics layer.

The headline case is ``test_cpu_percent_reports_load``: before 0.3.3 the Linux
sampler returned zeros on every call, and the old suite passed anyway because
it only checked the return type.
"""
import sys
import time

import pytest

from pulse import core, direct_os


def _burn_cpu(seconds: float) -> None:
    """Keep one core busy so there is load to measure."""
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        pass


class TestCpuPercents:
    def test_returns_one_entry_per_core(self):
        percents = core.get_cpu_percents()
        assert isinstance(percents, list)
        assert len(percents) > 0
        assert all(isinstance(p, float) for p in percents)

    def test_values_are_in_range(self):
        core.init()
        _burn_cpu(0.2)
        assert all(0.0 <= p <= 100.0 for p in core.get_cpu_percents())

    def test_cpu_percent_reports_load(self):
        """A busy core must register as busy.

        Regression test for the inverted sampling guard that made every Linux
        reading 0%.
        """
        core.init()
        _burn_cpu(0.1)
        core.get_cpu_percents()  # establish a baseline
        _burn_cpu(0.5)
        percents = core.get_cpu_percents()

        assert max(percents) > 0.0, (
            "no core registered any load while a busy loop was running - "
            "the sampler is not measuring deltas"
        )

    def test_repeated_calls_do_not_crash(self):
        for _ in range(5):
            core.get_cpu_percents()


class TestProcessList:
    def test_returns_running_processes(self):
        processes = core.get_process_list()
        assert len(processes) > 0
        for key in ("pid", "name", "cpu_percent", "memory_info"):
            assert key in processes[0]

    def test_limit_is_respected(self):
        assert len(core.get_process_list(limit=3)) <= 3

    def test_sort_by_memory_is_descending(self):
        processes = core.get_process_list(sort_by="mem", limit=10)
        sizes = [p["memory_info"] for p in processes]
        assert sizes == sorted(sizes, reverse=True)

    def test_sort_by_cpu_is_descending(self):
        processes = core.get_process_list(sort_by="cpu", limit=10)
        loads = [p["cpu_percent"] for p in processes]
        assert loads == sorted(loads, reverse=True)

    def test_this_process_reports_nonzero_memory(self):
        """Guards the Linux statm mix-up that reported virtual size, not RSS."""
        import os
        processes = {p["pid"]: p for p in core.get_process_list()}
        assert os.getpid() in processes
        assert processes[os.getpid()]["memory_info"] > 0


class TestSortAndLimit:
    def _sample(self):
        return [
            {"pid": 1, "name": "a", "cpu_percent": 5.0, "memory_info": 100},
            {"pid": 2, "name": "b", "cpu_percent": 50.0, "memory_info": 10},
            {"pid": 3, "name": "c", "cpu_percent": 1.0, "memory_info": 900},
        ]

    def test_sorts_by_cpu(self):
        result = direct_os._sort_and_limit(self._sample(), "cpu", None)
        assert [p["pid"] for p in result] == [2, 1, 3]

    def test_sorts_by_memory(self):
        result = direct_os._sort_and_limit(self._sample(), "mem", None)
        assert [p["pid"] for p in result] == [3, 1, 2]

    def test_unknown_sort_key_preserves_order(self):
        result = direct_os._sort_and_limit(self._sample(), None, None)
        assert [p["pid"] for p in result] == [1, 2, 3]

    def test_limit_applies_after_sorting(self):
        result = direct_os._sort_and_limit(self._sample(), "cpu", 1)
        assert [p["pid"] for p in result] == [2]


class TestMemoryInfo:
    def test_has_expected_keys(self):
        mem = core.get_memory_info()
        for key in ("total", "available", "used", "percent",
                    "swap_total", "swap_used"):
            assert key in mem

    def test_totals_are_consistent(self):
        mem = core.get_memory_info()
        assert mem["total"] > 0
        assert 0 <= mem["percent"] <= 100
        assert mem["used"] <= mem["total"]


class TestDiskInfo:
    def test_returns_mounted_volumes(self):
        disks = core.get_disk_info()
        assert isinstance(disks, list)
        for disk in disks:
            for key in ("device", "mountpoint", "total", "percent"):
                assert key in disk
            assert 0 <= disk["percent"] <= 100


class TestNetworkStats:
    def test_counters_are_non_negative(self):
        stats = core.get_network_stats()
        assert stats["bytes_recv"] >= 0
        assert stats["bytes_sent"] >= 0


@pytest.mark.skipif(not sys.platform.startswith("linux"),
                    reason="parses /proc/<pid>/stat, Linux only")
class TestProcStatParsing:
    def test_parses_simple_line(self):
        raw = "42 (bash) S 1 42 42 0 -1 0 0 0 0 0 " + "11 22 " + "0 " * 30
        name, ticks = direct_os._parse_proc_stat(raw)
        assert name == "bash"
        assert ticks == 33

    def test_handles_spaces_and_parens_in_process_name(self):
        """Names like "Isolated Web Co" broke the old whitespace split."""
        raw = "42 (Isolated Web Co (tab)) S 1 42 42 0 -1 0 0 0 0 0 " + "7 3 " + "0 " * 30
        name, ticks = direct_os._parse_proc_stat(raw)
        assert name == "Isolated Web Co (tab)"
        assert ticks == 10

    def test_returns_none_on_malformed_input(self):
        assert direct_os._parse_proc_stat("garbage") is None
        assert direct_os._parse_proc_stat("42 (short) S 1 2") is None
