"""
Pulse Actions - the only place in the app that changes system state.

Every function here is guarded: it refuses protected targets, reports what
actually happened instead of swallowing the error, and never escalates
privileges on its own. Callers are expected to confirm with the user first
(see ``pulse.screens.confirm.ConfirmScreen``).
"""
import os
import sys
from dataclasses import dataclass
from typing import Optional

import psutil

from pulse import direct_os

WINDOWS = sys.platform == 'win32'

# Windows reserves PID 0 for the System Idle Process and PID 4 for System.
_WINDOWS_RESERVED_PIDS = {0, 4}

NICE_MIN = -20
NICE_MAX = 19


@dataclass(frozen=True)
class ActionResult:
    """The outcome of a state-changing operation.

    ``can_force`` marks a failure that a stronger, explicitly confirmed retry
    might get past - it is never retried automatically.
    """
    ok: bool
    message: str
    can_force: bool = False

    def __bool__(self) -> bool:
        return self.ok


@dataclass(frozen=True)
class ProcessInfo:
    """Enough detail to show the user what they are about to act on."""
    pid: int
    name: str
    username: str

    def label(self) -> str:
        if self.username and self.username != '?':
            return f"{self.name} (PID {self.pid}, {self.username})"
        return f"{self.name} (PID {self.pid})"


def describe_process(pid: int) -> Optional[ProcessInfo]:
    """Look up a process for display. Returns None if it no longer exists."""
    try:
        proc = psutil.Process(pid)
        name = proc.name()
    except (psutil.NoSuchProcess, ValueError):
        return None
    except psutil.AccessDenied:
        return ProcessInfo(pid=pid, name='?', username='?')

    try:
        username = proc.username()
        # Windows reports DOMAIN\user; the domain is noise in a confirmation.
        if '\\' in username:
            username = username.split('\\')[-1]
    except (psutil.AccessDenied, psutil.NoSuchProcess, KeyError):
        username = '?'

    return ProcessInfo(pid=pid, name=name or '?', username=username)


def protection_reason(pid: int) -> Optional[str]:
    """Explain why a PID must not be touched, or None if it is fair game.

    These are the processes where a stray keypress takes down the user's
    session, their terminal, or the machine.
    """
    if pid is None or pid <= 0:
        return f"{pid} is not a valid process ID."

    if pid == os.getpid():
        return "That is Pulse itself. Press Q to quit instead."

    try:
        if pid == os.getppid():
            return "That is the shell Pulse is running in - killing it would close this session."
    except OSError:
        pass

    if WINDOWS:
        if pid in _WINDOWS_RESERVED_PIDS:
            return f"PID {pid} is a reserved Windows system process."
    else:
        if pid == 1:
            return "PID 1 is the init system - killing it would halt the machine."
        try:
            if pid == os.getsid(0):
                return "That is the session leader - killing it would close this terminal."
        except (OSError, AttributeError):
            pass

    return None


def kill_process(pid: int, *, force: bool = False) -> ActionResult:
    """Terminate a process, refusing protected targets.

    ``force`` sends SIGKILL (or runs taskkill /F on Windows). It is never set
    automatically - the caller must confirm the escalation separately.
    """
    reason = protection_reason(pid)
    if reason:
        return ActionResult(False, reason)

    action = direct_os.force_kill_process if force else direct_os.terminate_process
    verb = "Force killed" if force else "Terminated"

    try:
        action(pid)
    except (ProcessLookupError, psutil.NoSuchProcess):
        return ActionResult(True, f"PID {pid} had already exited.")
    except (PermissionError, psutil.AccessDenied) as exc:
        if force:
            detail = str(exc).strip()
            suffix = f" ({detail})" if detail else ""
            return ActionResult(
                False,
                f"Access denied for PID {pid} even with force{suffix}. "
                f"Run Pulse as {'administrator' if WINDOWS else 'root'} to kill it.",
            )
        return ActionResult(
            False,
            f"Access denied for PID {pid}. A force kill may work.",
            can_force=True,
        )
    except OSError as exc:
        return ActionResult(False, f"Could not kill PID {pid}: {exc}")

    return ActionResult(True, f"{verb} PID {pid}.")


def get_nice(pid: int) -> Optional[int]:
    """Current nice value, or None if it cannot be read."""
    try:
        return direct_os.get_process_nice(pid)
    except (psutil.NoSuchProcess, psutil.AccessDenied, ProcessLookupError, OSError):
        return None


def renice_process(pid: int, nice_value: int) -> ActionResult:
    """Set a process's nice value, refusing protected targets."""
    reason = protection_reason(pid)
    if reason:
        return ActionResult(False, reason)

    nice_value = max(NICE_MIN, min(NICE_MAX, nice_value))

    try:
        direct_os.renice_process(pid, nice_value)
    except (ProcessLookupError, psutil.NoSuchProcess):
        return ActionResult(False, f"PID {pid} no longer exists.")
    except (PermissionError, psutil.AccessDenied):
        # Lowering priority is usually allowed; raising it needs privileges.
        return ActionResult(
            False,
            f"Access denied setting priority on PID {pid}. "
            f"Raising priority requires {'administrator' if WINDOWS else 'root'}.",
        )
    except OSError as exc:
        return ActionResult(False, f"Could not renice PID {pid}: {exc}")

    return ActionResult(True, f"PID {pid} priority set to {nice_value}.")


def adjust_nice(pid: int, delta: int) -> ActionResult:
    """Nudge a process's nice value by ``delta``, clamped to the valid range."""
    current = get_nice(pid)
    if current is None:
        return ActionResult(False, f"Cannot read the current priority of PID {pid}.")
    return renice_process(pid, current + delta)
