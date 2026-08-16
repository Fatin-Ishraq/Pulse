# Pulse v2 — Audit and Plan

*Audit of `pulse-monitor` 0.3.2 (~5,100 lines across 30 modules) and a plan for the next version.*

---

## Part 1 — What is actually wrong

### A. Correctness: things that silently don't work

**1. On Linux, CPU is always 0%.** `src/pulse/direct_os.py:87`:

```python
if _last_cpu_times is None or now - _last_cpu_check > 0.05:
    return [0.0] * len(current)
```

The comparison is inverted. It should bail out when *too little* time has passed. At the default 1s refresh, `1.0 > 0.05` is always true, so every reading returns zeros. This propagates into the CPU panel, the transcendence view, and the Insight "tension" score. Linux is the platform the README brags about most.

**2. On Linux, per-process CPU is hardcoded to zero.** `direct_os.py:136` — `'cpu_percent': 0,  # Would need delta tracking per-process`. So "sort by CPU", "top offender", and the kill-the-top-process flow are all meaningless there.

**3. The Windows force-kill fallback in the network panel is a `NameError`.** `panels/network.py:84,86` use `platform` and `subprocess`; neither is imported in that file. On AccessDenied the user gets `Kill error: name 'platform' is not defined`.

**4. `load_config()` returns the module-level default by reference.** `config.py:52-53` returns `DEFAULT_CONFIG` itself on first run, and `app.py:362` then mutates `config["ui"]["theme"]` — permanently polluting the global default for the rest of the process, including every later `copy.deepcopy(DEFAULT_CONFIG)`.

**5. `direct_os` has no fallback branch.** On anything that isn't Linux/Windows/macOS the module defines no functions at all, and `core.py` dies with `AttributeError` at import time.

**6. Dead and shadowed code.**
- `panels/kernel.py::SystemPanel` — 115 lines, never imported, a near-duplicate of `MainViewPanel`.
- `NetworkPanel` defines `get_transcendence_view` twice (line 220 and 290) and `get_detailed_view` twice (224 and 357). The first of each is dead — and the dead one calls `super().get_transcendence_view()`, which doesn't exist on `Panel`.
- `state.py` and `themes.py` are 0 bytes.
- `StoragePanel._open_os_path` is a `pass`.
- `logging` is imported and unused in `container_api.py`.
- `memory.py:301` contains `getattr(psutil, 'wait_procs', lambda:[])[0]` — subscripting a lambda, guaranteed `TypeError`, hidden behind a bare `except`.

**7. Version drift.** `__init__.py` says `0.1.0`, `pyproject.toml` says `0.3.2`, the README tells you to tag `v0.3.3`.

**8. The README body is duplicated verbatim** — lines 1–60 repeat at 61–121.

**9. `MemoryPanel.action_optimize` mutates widget state from a raw `threading.Timer`** (`memory.py:186`) instead of Textual's `set_timer`. It also doesn't do anything — it's a fake "optimization" that shows a notification and a progress animation.

---

### B. Security and safety

**1. One keypress destroys things, and the target picks itself.** `CPUPanel.selected_pid` is silently assigned to whatever is currently top-of-CPU on every refresh (`cpu.py:167`); `MemoryPanel` does the same for top-of-memory. `K` then kills it. No confirmation, no target display at the moment of the keypress, no protected-PID list. Press `K` at the wrong moment and you kill your compositor, your shell, or PID 1. This is the most dangerous thing in the codebase.

**2. The Docker panel is root-equivalent and connects unconditionally at startup.** `DockerPanel.__init__` calls `docker.from_env()` immediately; access to the Docker socket is effectively root on the host. Start/stop/restart are bound to single keys (`s`/`k`/`r`) with no confirmation. `docker>=6.0.0` is also a *hard* dependency, so every install pulls it whether or not the user has Docker.

**3. Windows privilege escalation happens silently.** `direct_os.py:350` runs `taskkill /F /PID <pid>` automatically on AccessDenied. The arguments are list-form so there's no injection, but the user is never asked and never told the escalation happened.

**4. Failures are swallowed and then reported as successes.** `renice_process` catches `PermissionError` and returns `None`; the caller immediately notifies `PID X Nice: -1`. The UI lies about what it did. Across the codebase: **65 bare `except:` and 23 `except Exception`** in ~5,100 lines — roughly one swallowed error every 58 lines. There is no logging anywhere, so nothing is recoverable after the fact.

**5. `FileViewer` will hang the app forever on a FIFO or device file.** `screens/viewer.py:74` does `open(path).read()` with no `stat.S_ISREG` check and no timeout. Point it at a named pipe, `/dev/zero`, or `/proc/kmsg` and the event loop blocks permanently. It also reads the whole file to test for binary and then *re-reads* it through `Syntax.from_path` — a double read of up to 5 MB on the UI thread.

**6. Config values are used unvalidated.** `refresh_rate` goes straight from user-editable TOML into `set_interval()`. `0`, a negative, or a string is a spin or a crash.

**7. Supply chain.** GitHub Actions are floating tags (`actions/checkout@v4`) rather than pinned SHAs; the `build` job has no `permissions:` block so it inherits the broad default; dependencies are unbounded (`textual>=2.0.0` — Textual ships breaking changes regularly, and this app leans on internals like `DataTable.columns`). PyPI Trusted Publishing is correctly set up, which is the one genuinely good piece.

**8. There is no permission model.** The app never checks whether it's allowed to do something before trying, never tells the user what privileges it wants, and has no read-only mode.

---

### C. Architecture

**The root problem: there is no data layer. The widgets are the data layer.**

- **84 direct `psutil.*` calls live inside `panels/` and `aether/`.** In a single 1-second tick, `psutil.cpu_percent()` is sampled independently by `CPUPanel`, `InsightPanel`, `MainViewPanel`, and `ProcessPanel` — four separate samples, four different answers on screen at once, all on the UI thread.

- **`core.py` is a 15-line re-export of `direct_os`.** It is not an abstraction: there's no seam to mock at, no way to add a replay or remote source, no way to test a panel without a real machine underneath it.

- **Everything blocks the event loop.** There is **not one `@work` decorator or `to_thread` call in the entire codebase**, despite `GEMINI.md` explicitly requiring async handling. Meanwhile the render path calls `psutil.net_connections()` (walks every socket; needs elevation on macOS), `psutil.Process(pid).username()` × 100 rows per tick in the process view, and `os.scandir` + `stat` over up to 1,000 directory entries, fully sorted before slicing.

- **Panel state is copy-pasted, not inherited.** `sampling_rate`, `view_mode`, `scaling_mode`, and `selected_pid` are re-declared independently in six panels. The `Panel` base class is 20 lines and declares none of them. `ImmersiveScreen` then probes for eight different optional methods with `hasattr()` — duck typing standing in for an interface.

- **Keybindings collide.** `f` is freeze (app), optimize (memory), and reset-counters (network). `r` is refresh in three panels and restart-container in Docker. `s` is cycle-scale in the immersive screen and start-container in Docker. `q` quits the whole app from inside the immersive view. And `ImmersiveScreen.on_key` (`immersive.py:109`) hand-rolls a binding dispatcher that walks `source_panel.BINDINGS` and calls `action_*` by string — fighting Textual's binding system instead of using it.

- **DataTables are rebuilt from scratch every tick.** `table.clear()` then re-add 100 rows, with manual cursor-and-scroll save/restore that mostly doesn't survive. `network.py:187-207` still contains the author's live reasoning about row keys as inline comments.

- **The docs oversell the code.** "Direct OS Engine … communicates directly with your kernel for high-performance metrics with near-zero overhead" — on Windows and macOS it is a thin wrapper over psutil, and psutil is a hard dependency on all three platforms regardless. The "Neural Insight Engine" is `cpu * 0.4 + mem * 0.4 + 20`. `InsightPanel.thoughts` is a list of fake AI-sounding sentences that is never even rendered. This is the first thing a reviewer notices, it costs nothing to fix, and it undermines everything else in the project.

---

### D. Repository and process

- **Root is a dumping ground.** `GEMINI.md` (an agent-instruction file) is shipped as project documentation. No `CONTRIBUTING.md`, `CHANGELOG.md`, `SECURITY.md`, `docs/`, issue templates, or PR template.
- **Tests: 2 files, ~100 lines.** Config round-trip plus three smoke assertions. Nothing covers a single panel, the immersive screen, sampling logic, or the Aether engine. The Linux CPU=0 bug sails straight through the suite because the test only asserts `isinstance(cpus[0], float)` — and `0.0` is a float.
- **CI runs `pytest` and nothing else.** No lint, no type check, no coverage gate, no build verification, no smoke test that the `pulse` console script actually launches.
- **No lockfile**, no `requirements.txt`, no `[dependency-groups]`, no pre-commit, no `.editorconfig`, no ruff/black config.
- **Package metadata is thin**: a placeholder-looking author email domain, no bug-tracker URL, no per-minor-version Python classifiers, no `Typing :: Typed`.

---

## Part 2 — The v2 plan

### Four decisions to make first

1. **Drop the "Direct OS Engine" narrative.** Make psutil the honest, documented baseline, and add platform fast paths only where you've *measured* that they matter. Right now the story costs you credibility and buys nothing.
2. **Destructive actions become opt-in and confirmed.** Read-only by default.
3. **Docker becomes an optional extra** (`pip install pulse-monitor[docker]`), lazily connected, read-only unless explicitly enabled.
4. **Re-layer the app**: sampler → store → view. This is the change that makes everything else possible.

### Target structure

```
src/pulse/
├── core/                  # zero UI imports, fully testable headless
│   ├── models.py          # frozen dataclasses: CpuSample, MemSample, Snapshot
│   ├── sources/
│   │   ├── base.py        # MetricSource protocol
│   │   ├── psutil_source.py
│   │   ├── linux_proc.py  # opt-in fast path, benchmarked against the baseline
│   │   └── mock.py        # deterministic source for tests
│   ├── sampler.py         # one tick -> one coherent Snapshot
│   ├── store.py           # ring buffers, history, peaks, derived rates
│   └── actions.py         # kill / renice / docker — the ONLY side-effecting module
├── ui/
│   ├── app.py
│   ├── widgets/           # dumb: render(snapshot) -> RenderResult
│   ├── screens/
│   └── theme/
├── config/                # schema + validation + migration
└── cli.py                 # --refresh, --read-only, --no-docker, --json, --once
```

**Rules that make this hold:**
- `core/` never imports `textual` or `rich`. It becomes reusable for an exporter, a web frontend, or a headless mode.
- One sampler tick produces one **immutable `Snapshot`**; every widget renders from that same snapshot. One syscall per metric per tick, and the same number everywhere on screen.
- Sampling runs off the event loop (`@work(thread=True)` or `asyncio.to_thread`). The UI layer never calls psutil — enforce it with a CI grep.
- Every side effect returns a typed `ActionResult(ok, message, error)`. No more `except: pass` followed by a success toast.

### Milestones

**M0 — Stop the bleeding (ship as 0.3.3, ~1 day).** Patch the current code before rewriting anything, so users on PyPI aren't left on a broken build:

- Fix the Linux CPU comparison (`>` → `<`) and add real per-process CPU delta tracking.
- Add the missing `platform` / `subprocess` imports in `network.py`.
- `copy.deepcopy(DEFAULT_CONFIG)` on the first-run path; clamp `refresh_rate` to `[0.1, 60]`.
- Add a confirmation modal for kill / renice / Docker actions; stop auto-assigning `selected_pid`.
- Guard `FileViewer` with `stat.S_ISREG` and a size check before opening.
- Delete `kernel.py`, `state.py`, `themes.py`, and the shadowed method pairs.
- De-duplicate the README; sync the three versions; rewrite the "Direct OS Engine" and "Neural Insight" claims to match reality.
- Pin GitHub Actions to commit SHAs; add `permissions: contents: read` to the build job; cap `textual` to `>=2.0,<3.0`.

**M1 — Core extraction (~1 week).** Build `models`, `sources`, `sampler`, `store`, and `mock`. Port every panel to read from the store. Delete all 84 direct psutil calls from the UI. Exit criterion: the full core test suite runs against the mock source with no real system access.

**M2 — Safety layer.** Read-only default for destructive operations (`[actions] enabled = false`); confirmation modals showing the exact target; a protected-PID list (self, PID 1, session leader); typed `ActionResult` everywhere; real error surfacing; structured logging to `$XDG_STATE_HOME/pulse/pulse.log`.

**M3 — UI rebuild.** A single `MetricPanel` base with a declared contract — no `hasattr` probing. A keymap table with zero collisions, remappable from config. Incremental DataTable updates (diff rows, update in place) instead of clear-and-rebuild. Textual's native theme system instead of the hand-rolled cycler.

**M4 — Features worth having (pick two or three, don't build all six).**

| Feature | Why |
| --- | --- |
| GPU (NVML / Apple / amdgpu) + thermals, fans, battery | The biggest real capability gap versus btop/btm |
| Alerts and thresholds | `pulse --watch "cpu>90 for 60s"` → notification + exit code; makes it useful in scripts |
| Headless export | `pulse --json --once`, `--csv` — scriptable *and* trivially testable |
| Record & replay | `pulse record` / `pulse play session.pulse` — gives you demo GIFs and deterministic UI tests from one feature |
| Remote mode | `pulse --connect host` over an SSH-tunnelled read-only socket |
| Prometheus / OTel exporter | Turns a toy into infrastructure |

Record & replay is the highest-leverage one: it pays for itself immediately in the test suite.

**M5 — Release engineering.** ruff + mypy (strict on `core/`) + pytest-cov ≥80% on core, all gating CI. `pytest-textual-snapshot` for UI regressions. A `pipx install .` smoke job that runs `pulse --version`. `CHANGELOG.md` (keep-a-changelog), real SemVer, `SECURITY.md` with a disclosure contact, `CONTRIBUTING.md`, issue templates. Move `GEMINI.md` out of the root.

### Quality gates for "professional"

These are the checks that turn the adjective into something CI can enforce:

- **Zero bare `except:`** — ruff `E722` as an error. Every caught exception is either handled or logged.
- **100% type coverage in `core/`**, mypy strict.
- **No `psutil` or OS import anywhere under `ui/`** — a one-line grep in CI.
- **Every destructive action has a test proving it asks first.**
- **`pulse --json --once` emits a stable, documented schema**, versioned separately from the app.

### Naming and release

Keep `pulse-monitor` on PyPI and release the rewrite as **1.0.0** with a documented breaking-change section in the CHANGELOG. The name is fine; the version number is what should signal the reset.

---

## Where to start

M0 first — a day of work, ships a build that isn't broken on Linux, and closes the two genuinely dangerous behaviours (one-key process kill on an auto-selected target, and unconfirmed Docker control). Then M1, because until the data layer exists, every other improvement gets built on sand.
