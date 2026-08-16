"""End-to-end tests that drive the real app through Textual's test pilot.

These exist mainly to pin down the safety behaviour: a destructive keypress must
open a confirmation, cancelling must leave the target alone, and protected
processes must be refused outright.
"""
import asyncio
import os
import subprocess
import sys

import psutil
import pytest

from pulse.app import PulseApp
from pulse.panels.cpu import CPUPanel

pytestmark = pytest.mark.asyncio


@pytest.fixture
def victim():
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    yield proc
    if proc.poll() is None:
        proc.kill()
        proc.wait(timeout=5)


async def _boot(pilot, app):
    """Settle the app and dismiss the boot screen."""
    await pilot.pause()
    await asyncio.sleep(0.3)
    await pilot.pause()
    while len(app.screen_stack) > 1:
        app.pop_screen()
        await pilot.pause()


class TestAppLifecycle:
    async def test_app_starts_and_refreshes(self):
        app = PulseApp()
        async with app.run_test(size=(140, 45)) as pilot:
            await _boot(pilot, app)
            app.refresh_data()
            await pilot.pause()
            assert app.query_one("#cpu-panel") is not None

    async def test_freeze_stops_updates(self):
        app = PulseApp()
        async with app.run_test(size=(140, 45)) as pilot:
            await _boot(pilot, app)
            assert app.frozen is False
            await pilot.press("f")
            await pilot.pause()
            assert app.frozen is True

    async def test_theme_cycles_and_persists_to_config(self):
        app = PulseApp()
        async with app.run_test(size=(140, 45)) as pilot:
            await _boot(pilot, app)
            before = app.theme_index
            await pilot.press("t")
            await pilot.pause()
            assert app.theme_index != before
            assert app.config["ui"]["theme"] == app.theme

    async def test_immersive_view_opens_and_closes(self):
        app = PulseApp()
        async with app.run_test(size=(140, 45)) as pilot:
            await _boot(pilot, app)
            app.query_one("#cpu-panel").focus()
            await pilot.pause()
            await pilot.press("x")
            await pilot.pause()
            await asyncio.sleep(0.2)
            assert type(app.screen).__name__ == "ImmersiveScreen"
            await pilot.press("escape")
            await pilot.pause()
            assert type(app.screen).__name__ != "ImmersiveScreen"


class TestDestructiveActionsAreGuarded:
    async def test_kill_asks_before_acting(self, victim):
        app = PulseApp()
        async with app.run_test(size=(140, 45)) as pilot:
            await _boot(pilot, app)
            panel = app.query_one("#cpu-panel", CPUPanel)
            panel.top_pid = victim.pid

            panel.action_kill_process()
            await pilot.pause()
            await asyncio.sleep(0.2)

            assert type(app.screen).__name__ == "ConfirmScreen"
            assert psutil.pid_exists(victim.pid)

    async def test_cancelling_leaves_the_process_alive(self, victim):
        app = PulseApp()
        async with app.run_test(size=(140, 45)) as pilot:
            await _boot(pilot, app)
            panel = app.query_one("#cpu-panel", CPUPanel)
            panel.top_pid = victim.pid

            panel.action_kill_process()
            await pilot.pause()
            await asyncio.sleep(0.2)
            await pilot.press("escape")
            await pilot.pause()
            await asyncio.sleep(0.3)

            assert victim.poll() is None

    async def test_confirming_actually_kills(self, victim):
        app = PulseApp()
        async with app.run_test(size=(140, 45)) as pilot:
            await _boot(pilot, app)
            panel = app.query_one("#cpu-panel", CPUPanel)
            panel.top_pid = victim.pid

            panel.action_kill_process()
            await pilot.pause()
            await asyncio.sleep(0.2)
            await pilot.press("y")
            await pilot.pause()
            await asyncio.sleep(0.6)

            assert victim.poll() is not None

    async def test_protected_process_is_refused(self):
        app = PulseApp()
        async with app.run_test(size=(140, 45)) as pilot:
            await _boot(pilot, app)
            panel = app.query_one("#cpu-panel", CPUPanel)
            panel.top_pid = os.getpid()

            panel.action_kill_process()
            await pilot.pause()
            await asyncio.sleep(0.2)

            # Refusal, not a confirmation prompt - there is nothing to confirm.
            assert type(app.screen).__name__ == "BlockedScreen"
            assert psutil.pid_exists(os.getpid())
