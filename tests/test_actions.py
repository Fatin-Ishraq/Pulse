"""Tests for the guarded action layer.

These cover the behaviour that used to be missing entirely: refusing to touch
protected processes, and reporting failures instead of claiming success.
"""
import os
import subprocess
import sys
import time

import psutil
import pytest

from pulse import actions


@pytest.fixture
def victim():
    """A short-lived child process that tests may kill."""
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    yield proc
    if proc.poll() is None:
        proc.kill()
        proc.wait(timeout=5)


def _wait_for_exit(proc, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            return True
        time.sleep(0.05)
    return False


class TestActionResult:
    def test_truthiness_follows_ok(self):
        assert actions.ActionResult(True, "done")
        assert not actions.ActionResult(False, "nope")


class TestProtection:
    def test_refuses_pulse_itself(self):
        reason = actions.protection_reason(os.getpid())
        assert reason is not None
        assert "Pulse itself" in reason

    def test_refuses_parent_process(self):
        reason = actions.protection_reason(os.getppid())
        assert reason is not None

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX init process")
    def test_refuses_init(self):
        assert actions.protection_reason(1) is not None

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows reserved PIDs")
    def test_refuses_windows_reserved_pids(self):
        assert actions.protection_reason(0) is not None
        assert actions.protection_reason(4) is not None

    def test_refuses_invalid_pid(self):
        assert actions.protection_reason(-1) is not None

    def test_allows_ordinary_process(self, victim):
        assert actions.protection_reason(victim.pid) is None

    def test_kill_refuses_protected_without_touching_it(self):
        result = actions.kill_process(os.getpid())
        assert not result.ok
        assert not result.can_force
        # The obvious failure mode: refusing but killing anyway.
        assert psutil.pid_exists(os.getpid())

    def test_renice_refuses_protected(self):
        result = actions.renice_process(os.getpid(), 5)
        assert not result.ok


class TestKill:
    def test_kills_ordinary_process(self, victim):
        result = actions.kill_process(victim.pid)
        assert result.ok, result.message
        assert _wait_for_exit(victim)

    def test_reports_already_exited(self, victim):
        victim.kill()
        victim.wait(timeout=5)
        result = actions.kill_process(victim.pid)
        # Already gone is a success from the caller's point of view, but it must
        # say so rather than claiming it did the killing.
        assert result.ok
        assert "already" in result.message.lower()

    def test_never_escalates_on_its_own(self, monkeypatch, victim):
        """A denied kill reports can_force; it must not force behind the scenes."""
        forced = []

        def deny(pid):
            raise PermissionError("denied")

        monkeypatch.setattr(actions.direct_os, "terminate_process", deny)
        monkeypatch.setattr(actions.direct_os, "force_kill_process",
                            lambda pid: forced.append(pid))

        result = actions.kill_process(victim.pid)

        assert not result.ok
        assert result.can_force
        assert forced == [], "kill_process must not force without being asked"

    def test_force_is_used_only_when_requested(self, monkeypatch, victim):
        forced = []
        monkeypatch.setattr(actions.direct_os, "force_kill_process",
                            lambda pid: forced.append(pid))

        result = actions.kill_process(victim.pid, force=True)

        assert result.ok
        assert forced == [victim.pid]


class TestDescribeProcess:
    def test_describes_running_process(self, victim):
        info = actions.describe_process(victim.pid)
        assert info is not None
        assert info.pid == victim.pid
        assert str(victim.pid) in info.label()

    def test_returns_none_for_dead_process(self, victim):
        victim.kill()
        victim.wait(timeout=5)
        # PIDs can be recycled, but not this fast in practice.
        assert actions.describe_process(victim.pid) is None


class TestDescribeProcessEdgeCases:
    def test_access_denied_still_yields_a_label(self, monkeypatch, victim):
        class Denied:
            def __init__(self, pid):
                pass

            def name(self):
                raise psutil.AccessDenied()

        monkeypatch.setattr(actions.psutil, "Process", Denied)
        info = actions.describe_process(victim.pid)
        assert info is not None
        assert info.name == "?"
        assert f"PID {victim.pid}" in info.label()

    def test_unreadable_username_falls_back(self, monkeypatch, victim):
        class PartialAccess:
            def __init__(self, pid):
                pass

            def name(self):
                return "victim.exe"

            def username(self):
                raise psutil.AccessDenied()

        monkeypatch.setattr(actions.psutil, "Process", PartialAccess)
        info = actions.describe_process(victim.pid)
        assert info.username == "?"
        # With no username the label stays short rather than showing "?".
        assert info.label() == f"victim.exe (PID {victim.pid})"

    def test_domain_is_stripped_from_windows_usernames(self, monkeypatch, victim):
        class DomainUser:
            def __init__(self, pid):
                pass

            def name(self):
                return "app.exe"

            def username(self):
                return "CORP\\alice"

        monkeypatch.setattr(actions.psutil, "Process", DomainUser)
        info = actions.describe_process(victim.pid)
        assert info.username == "alice"
        assert "alice" in info.label()

    def test_invalid_pid_is_handled(self):
        assert actions.describe_process(-5) is None


class TestFailureReporting:
    def test_kill_reports_os_errors(self, monkeypatch, victim):
        def broken(pid):
            raise OSError("kernel said no")

        monkeypatch.setattr(actions.direct_os, "terminate_process", broken)
        result = actions.kill_process(victim.pid)

        assert not result.ok
        assert "kernel said no" in result.message

    def test_denied_force_kill_names_the_privilege_needed(self, monkeypatch, victim):
        def deny(pid):
            raise PermissionError("still denied")

        monkeypatch.setattr(actions.direct_os, "force_kill_process", deny)
        result = actions.kill_process(victim.pid, force=True)

        assert not result.ok
        # Already forcing, so there is nothing stronger left to offer.
        assert not result.can_force
        assert "administrator" in result.message or "root" in result.message

    def test_renice_reports_vanished_process(self, monkeypatch, victim):
        def gone(pid, nice):
            raise ProcessLookupError()

        monkeypatch.setattr(actions.direct_os, "renice_process", gone)
        result = actions.renice_process(victim.pid, 1)

        assert not result.ok
        assert "no longer exists" in result.message

    def test_renice_reports_os_errors(self, monkeypatch, victim):
        def broken(pid, nice):
            raise OSError("bad value")

        monkeypatch.setattr(actions.direct_os, "renice_process", broken)
        result = actions.renice_process(victim.pid, 1)

        assert not result.ok
        assert "bad value" in result.message


class TestNiceLookup:
    def test_reads_current_nice(self, victim):
        value = actions.get_nice(victim.pid)
        assert value is None or isinstance(value, int)

    def test_returns_none_when_unreadable(self, monkeypatch, victim):
        def deny(pid):
            raise psutil.AccessDenied()

        monkeypatch.setattr(actions.direct_os, "get_process_nice", deny)
        assert actions.get_nice(victim.pid) is None

    def test_adjust_nice_applies_the_delta(self, monkeypatch, victim):
        applied = []
        monkeypatch.setattr(actions.direct_os, "get_process_nice", lambda pid: 5)
        monkeypatch.setattr(actions.direct_os, "renice_process",
                            lambda pid, nice: applied.append(nice))

        result = actions.adjust_nice(victim.pid, 3)

        assert result.ok
        assert applied == [8]

    def test_adjust_nice_fails_loudly_when_current_is_unknown(self, monkeypatch, victim):
        monkeypatch.setattr(actions.direct_os, "get_process_nice",
                            lambda pid: (_ for _ in ()).throw(psutil.AccessDenied()))
        result = actions.adjust_nice(victim.pid, 1)

        assert not result.ok
        assert "current priority" in result.message


class TestRenice:
    def test_clamps_to_valid_range(self, monkeypatch, victim):
        applied = []
        monkeypatch.setattr(actions.direct_os, "renice_process",
                            lambda pid, nice: applied.append(nice))

        actions.renice_process(victim.pid, 500)
        actions.renice_process(victim.pid, -500)

        assert applied == [actions.NICE_MAX, actions.NICE_MIN]

    def test_reports_failure_instead_of_claiming_success(self, monkeypatch, victim):
        def deny(pid, nice):
            raise PermissionError("denied")

        monkeypatch.setattr(actions.direct_os, "renice_process", deny)
        result = actions.renice_process(victim.pid, 5)

        assert not result.ok
        assert "denied" in result.message.lower()
