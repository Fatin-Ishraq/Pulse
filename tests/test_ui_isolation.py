"""Tests that the UI layer stays out of the metrics business.

These are architectural guards. Before the core existed, panels sampled psutil
directly from their render path - 80-odd call sites, four of them asking for
CPU in the same tick and getting four different answers. If someone reaches for
psutil in a panel again, these fail.
"""
import ast
import pathlib

import pytest

import pulse

PACKAGE_ROOT = pathlib.Path(pulse.__file__).parent

# Directories that render. Nothing here may collect its own metrics.
UI_DIRECTORIES = ["panels", "screens", "aether"]

# Modules allowed to touch the system directly, and why.
SAMPLING_MODULES = {
    "direct_os.py",       # the per-platform OS layer
    "actions.py",         # guarded kill/renice, needs process lookup
    "system.py",          # the one metric source
    "container_api.py",   # the Docker client
}


def _python_files(directory: str):
    return sorted((PACKAGE_ROOT / directory).rglob("*.py"))


def _imported_modules(path: pathlib.Path):
    """Top-level module names imported by a file."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
    return modules


@pytest.mark.parametrize("directory", UI_DIRECTORIES)
def test_ui_layer_does_not_import_psutil(directory):
    offenders = [
        path.name for path in _python_files(directory)
        if "psutil" in _imported_modules(path)
    ]
    assert not offenders, (
        f"{directory}/ must read from the store, not sample directly. "
        f"Offending files: {offenders}"
    )


@pytest.mark.parametrize("directory", UI_DIRECTORIES)
def test_ui_layer_does_not_shell_out(directory):
    """A panel spawning a subprocess is a metrics call wearing a disguise."""
    offenders = [
        path.name for path in _python_files(directory)
        if "subprocess" in _imported_modules(path)
    ]
    assert not offenders, f"{directory}/ should not run subprocesses: {offenders}"


def test_core_does_not_import_the_ui():
    """The dependency arrow points one way: UI depends on core, never back.

    This is what lets core be tested headless and reused by a future exporter.
    """
    forbidden = {"textual", "rich"}
    offenders = {}

    for path in (PACKAGE_ROOT / "core").rglob("*.py"):
        leaked = _imported_modules(path) & forbidden
        if leaked:
            offenders[path.name] = sorted(leaked)

    assert not offenders, f"pulse.core must not import UI libraries: {offenders}"


def test_only_designated_modules_sample_the_system():
    """Keeps the set of files that touch psutil small and deliberate."""
    offenders = [
        str(path.relative_to(PACKAGE_ROOT))
        for path in PACKAGE_ROOT.rglob("*.py")
        if "psutil" in _imported_modules(path) and path.name not in SAMPLING_MODULES
    ]
    assert not offenders, (
        "New psutil call site outside the sampling layer. Either read from the "
        f"store or add the module to SAMPLING_MODULES deliberately: {offenders}"
    )
