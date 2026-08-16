# Pulse - notes for AI coding agents

Context for agents working in this repository. Humans should start with the
[README](../README.md) and the [v2 plan](pulse-v2-plan.md).

## What this is

A terminal system monitor built with [Textual](https://textual.textualize.io/),
[Rich](https://github.com/Textualize/rich), and
[psutil](https://github.com/giampaolo/psutil). Python 3.10+, built with
Hatchling.

## Layout

```
src/pulse/
├── app.py            # PulseApp, the grid layout, global bindings, main()
├── core/             # metrics layer - NO Textual or Rich imports
│   ├── models.py     # frozen dataclasses; one tick is one Snapshot
│   ├── sources/      # system.py (real), mock.py (deterministic)
│   ├── sampler.py    # one source poll -> one Snapshot, failures isolated
│   └── store.py      # latest Snapshot + history, rates, peaks
├── direct_os.py      # per-platform metrics; /proc on Linux, psutil elsewhere
├── actions.py        # the ONLY module that changes system state
├── config.py         # load/save + validation of config.toml
├── container_api.py  # optional Docker integration (extra: [docker])
├── ui_utils.py       # sparklines, bars, heat colours
├── panels/           # one widget per subsystem; all inherit panels.base.Panel
├── screens/          # boot, help, immersive, confirm, viewer
└── aether/           # the ASCII 3D visualisation in the Insight panel
```

## Rules that matter

**Anything that changes system state goes through `actions.py`.** It refuses
protected PIDs, never escalates privileges on its own, and returns an
`ActionResult` rather than swallowing the error. Do not call `os.kill`,
`psutil.Process.kill`, or `subprocess`-based kills from a panel.

**Destructive actions confirm first.** Use `Panel.request_kill`,
`Panel.request_renice`, or `Panel.request_container_action` — they push
`ConfirmScreen` and report the outcome. Do not add a code path that destroys
something on a single keypress.

**`direct_os` primitives raise; `actions` catches.** Keep that split: the low
level reports failure honestly, the guarded layer decides what to do about it.

**Do not add bare `except:`.** There are still many in the UI layer from before
0.3.3; do not add more, and narrow the ones you touch. A swallowed exception
here means the UI shows stale or wrong numbers with no way to find out why.

**Config values are untrusted input.** Anything read from `config.toml` goes
through `config.validate_*` before use.

**Panels never sample.** Read from `self.snapshot`, `self.history`,
`self.rates`, or `self.store` on `Panel`. One tick produces one `Snapshot` that
every widget shares, which is why the numbers agree across the UI. Sampling
runs on a worker thread; a panel that calls psutil puts a blocking syscall back
on the render path. `tests/test_ui_isolation.py` enforces this — it parses the
imports of everything under `panels/`, `screens/`, and `aether/` and fails if
psutil or subprocess appears.

**Guard against `None`.** `self.snapshot` is `None` until the first sample
lands. Return `self.waiting_text()` rather than assuming data exists.

**The dependency arrow points one way.** `pulse.core` must not import Textual
or Rich; that is also enforced by a test.

## Known debt

The full-screen views still probe panels with `hasattr` for eight optional
methods instead of declaring an interface, and the keymap has collisions —
`f` means three different things depending on focus, `r` means four. That is
M3 in [pulse-v2-plan.md](pulse-v2-plan.md).

## Development

```bash
pip install -e ".[test]"
pytest
pulse            # or: python -m pulse
```

Tests that drive the UI use Textual's `run_test()` pilot; see
`tests/test_app.py`. The `tests/test_actions.py` and `tests/test_config.py`
modules are held to 85% coverage in CI — keep them that way.
