# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-08-17

A correctness and safety release. No new features; several things that looked
like they worked did not.

Versioned 0.4.0 rather than 0.3.x for two reasons. Docker is no longer a default
dependency, which changes what `pip install pulse-monitor` gives you. And the
0.3.3-0.3.7 range is unusable: those tags were pushed against code that still
declared 0.3.2, and the 0.3.3 on PyPI was published from a commit that never
reached `main`. Nothing in that range describes the code it claims to.

### Fixed

- **CPU usage always read 0% on Linux.** The sampling guard in `direct_os` was
  inverted, so every call returned zeros at any refresh rate above 0.05s. This
  affected the CPU panel, the transcendence view, and the Insight tension score.
- **Per-process CPU was hardcoded to 0 on Linux**, which made "sort by CPU" and
  "top offender" meaningless. Real per-process CPU deltas are now tracked.
- **Per-process memory on Linux reported virtual size instead of RSS**, hugely
  overstating usage. It now reads the resident field from `statm`.
- **Process names containing spaces or parentheses were parsed incorrectly** on
  Linux (for example "Isolated Web Co"), shifting every field after the name.
- **The network panel's force-kill path raised `NameError`** — it used
  `platform` and `subprocess` without importing them.
- **The first config load handed out the module-level defaults by reference**,
  so changing the theme permanently rewrote the in-process defaults.
- **`kill_process` returned a string on Windows and `None` elsewhere**, so the
  process panel crashed when reporting the result on Linux and macOS.
- Pulse no longer fails to import on platforms other than Linux, Windows, and
  macOS; there is now a psutil-backed fallback.

### Security

- **Destructive actions now confirm before acting.** Terminating a process,
  changing its priority, and starting, stopping, or restarting a container all
  name the exact target and wait for an explicit yes. Cancel is the default
  focus, so a stray Enter dismisses rather than destroys.
- **Protected processes are refused outright**: Pulse itself, its parent shell,
  PID 1 and the session leader on POSIX, and the reserved Windows system PIDs.
- **No silent privilege escalation.** A denied kill used to run `taskkill /F`
  automatically on Windows. It now reports the denial and offers a force kill as
  a separate, explicitly confirmed step.
- **Failures are reported instead of swallowed.** Renicing a process without
  permission used to show a success message. All state-changing operations now
  return a result that says what actually happened.
- **The file viewer refuses anything that is not a regular file.** Opening a
  FIFO or character device would block the UI thread forever with no way out.
  Symlinks, sockets, device files, and oversized files are rejected up front,
  and the binary sniff no longer reads the file twice.
- **Docker is now an optional extra** (`pip install pulse-monitor[docker]`).
  Access to the Docker socket is root-equivalent, so it is no longer installed
  by default, no longer connects at startup, and backs off after a failed
  connection instead of retrying on every frame.
- Config values are validated before use. `refresh_rate` is clamped to
  0.1-60.0s and unknown themes fall back to the default, instead of going
  straight into `set_interval()`.

### Added

- `pulse --version` and `pulse --help`.
- Regression tests for every fix above, including end-to-end tests that drive
  the real app and assert a destructive keypress opens a confirmation.
- CI now enforces a coverage floor, holds the action and config modules to 85%,
  and smoke-tests that the built wheel installs and launches.

### Changed

- Package version is now read from `src/pulse/__init__.py`, so it cannot drift
  from `pyproject.toml` again (it was 0.1.0 in one place and 0.3.2 in the other).
- README no longer claims a "Direct OS Engine" that talks to the kernel with
  "near-zero overhead" on platforms where it is a psutil wrapper, and describes
  what each platform actually does.
- The memory panel's "optimize" action has been removed. It performed no
  optimization; it showed a progress animation and updated widget state from a
  raw `threading.Timer` outside Textual's event loop.

### Removed

- `panels/kernel.py` (dead duplicate of the main view panel), the empty
  `state.py` and `themes.py`, shadowed duplicate methods in the network panel,
  and several unused imports.

## [0.3.3] - 2026-01-27 [YANKED IN SPIRIT]

Published to PyPI from a commit that was never merged to `main`. Identical to
0.3.2 apart from the version string, so it carries every bug listed above.
Upgrade to 0.4.0.

## [0.3.2] - 2026-03

Initial published release line.

[0.4.0]: https://github.com/Fatin-Ishraq/Pulse/releases/tag/v0.4.0
