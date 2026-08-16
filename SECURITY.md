# Security Policy

## Supported versions

| Version | Supported |
| --- | --- |
| 0.3.3 and later | ✅ |
| earlier | ❌ |

## Reporting a vulnerability

Please report security issues privately through
[GitHub Security Advisories](https://github.com/Fatin-Ishraq/Pulse/security/advisories/new)
rather than opening a public issue.

Include what you were doing, what happened, and the platform and Pulse version.
Expect an initial response within a week.

## What Pulse does with your system

Pulse is a monitor, but it is not read-only. Knowing what it can do is part of
using it safely.

**It can change system state.** Pulse can terminate processes, change their
priority, and start, stop, or restart Docker containers. Every one of these
actions names its exact target and requires an explicit confirmation first.

**It refuses to touch critical processes.** Pulse itself, its parent shell,
PID 1 and the session leader on POSIX, and the reserved Windows system PIDs are
rejected outright, with no confirmation offered.

**It never escalates privileges on its own.** If an action is denied, Pulse
reports the denial. A force kill is offered as a separate, explicitly confirmed
step; it is never attempted automatically.

**It runs with your privileges, and no more.** Pulse does not request
elevation. Running it as root or administrator gives it the power to kill
anything on the machine — do that only if you need it.

**Docker access is opt-in.** The Docker socket is root-equivalent on the host,
so container support ships as a separate extra
(`pip install "pulse-monitor[docker]"`), is not installed by default, and does
not connect until you open the Docker panel.

**It reads files you point it at.** The storage browser opens files with your
own permissions. It refuses anything that is not a regular file — symlinks,
FIFOs, sockets, and device files — and caps the size it will read.

**It sends nothing anywhere.** Pulse has no network client, no telemetry, and
no auto-update. Its only writes are the config file in your user config
directory.
