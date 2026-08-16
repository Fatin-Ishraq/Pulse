"""End-to-end tests driving the real UI from a deterministic fake machine.

Because the app takes an injectable source, the whole interface can now be
exercised with no real system access - which is what makes these assertions
about consistency possible at all.
"""
import asyncio
import threading

import pytest

from pulse.app import PulseApp
from pulse.core import MockSource
from pulse.panels.base import Panel

pytestmark = pytest.mark.asyncio

PANEL_IDS = [
    "cpu-panel", "memory-panel", "net-panel", "disk-panel",
    "storage-panel", "process-panel", "insight-panel", "main-panel",
    "docker-panel",
]


async def boot(pilot, app, wait_for_sample=True):
    """Settle the app, dismiss the boot screen, and wait for the first tick."""
    await pilot.pause()
    await asyncio.sleep(0.3)
    await pilot.pause()
    while len(app.screen_stack) > 1:
        app.pop_screen()
        await pilot.pause()

    if wait_for_sample:
        for _ in range(60):
            if app.store.ready:
                break
            await asyncio.sleep(0.05)
            await pilot.pause()


class TestSamplingPipeline:
    async def test_app_runs_on_a_mock_machine(self):
        app = PulseApp(source=MockSource())
        async with app.run_test(size=(140, 45)) as pilot:
            await boot(pilot, app)

            assert app.store.ready
            assert app.store.snapshot.cpu.core_count == 4
            assert app.store.snapshot.healthy

    async def test_each_subsystem_is_sampled_once_per_tick(self):
        """The core fix: four panels used to ask for CPU independently."""
        source = MockSource()
        app = PulseApp(source=source)
        async with app.run_test(size=(140, 45)) as pilot:
            await boot(pilot, app)
            ticks = app.store.tick_count

            assert source.call_counts["cpu"] == ticks
            assert source.call_counts["memory"] == ticks
            assert source.call_counts["network"] == ticks

    async def test_every_panel_reads_the_same_snapshot(self):
        """One tick, one set of numbers, everywhere on screen."""
        app = PulseApp(source=MockSource())
        async with app.run_test(size=(140, 45)) as pilot:
            await boot(pilot, app)

            snapshots = {id(panel.snapshot) for panel in app.query(Panel)}
            assert len(snapshots) == 1

    async def test_sampling_runs_off_the_event_loop(self):
        """Reading /proc and walking sockets must not happen on the render thread."""
        sampled_on = []

        class ThreadRecordingSource(MockSource):
            def cpu(self):
                sampled_on.append(threading.get_ident())
                return super().cpu()

        app = PulseApp(source=ThreadRecordingSource())
        async with app.run_test(size=(140, 45)) as pilot:
            await boot(pilot, app)

            event_loop_thread = threading.get_ident()
            assert sampled_on, "no sampling happened"
            assert all(ident != event_loop_thread for ident in sampled_on), (
                "sampling ran on the event loop thread - the UI will stutter"
            )

    async def test_snapshots_are_applied_on_the_event_loop(self):
        """Widget updates must come back to the main thread to be safe."""
        applied_on = []
        app = PulseApp(source=MockSource())
        original = app.apply_snapshot

        def record(snapshot):
            applied_on.append(threading.get_ident())
            original(snapshot)

        app.apply_snapshot = record

        async with app.run_test(size=(140, 45)) as pilot:
            await boot(pilot, app)
            assert applied_on
            assert all(ident == threading.get_ident() for ident in applied_on)

    async def test_freeze_stops_sampling(self):
        source = MockSource()
        app = PulseApp(source=source)
        async with app.run_test(size=(140, 45)) as pilot:
            await boot(pilot, app)

            await pilot.press("f")
            await pilot.pause()
            before = source.call_counts["cpu"]

            app.refresh_data()
            await pilot.pause()
            await asyncio.sleep(0.2)

            assert source.call_counts["cpu"] == before


class TestRenderingBeforeData:
    async def test_panels_render_before_the_first_snapshot(self):
        """A slow first sample must not crash the UI with None everywhere."""
        app = PulseApp(source=MockSource())
        async with app.run_test(size=(140, 45)) as pilot:
            await boot(pilot, app, wait_for_sample=False)

            # Force a repaint with an empty store.
            app.store._snapshot = None
            app.refresh_panels()
            await pilot.pause()

            for panel in app.query(Panel):
                assert panel.get_detailed_view() is not None


class TestPanelRendering:
    @pytest.mark.parametrize("panel_id", PANEL_IDS)
    async def test_panel_renders_every_view(self, panel_id):
        app = PulseApp(source=MockSource())
        async with app.run_test(size=(140, 45)) as pilot:
            await boot(pilot, app)
            panel = app.query_one(f"#{panel_id}")

            panel.update_data()
            assert panel.get_detailed_view() is not None
            if hasattr(panel, "get_transcendence_view"):
                assert panel.get_transcendence_view() is not None

    @pytest.mark.parametrize("panel_id", PANEL_IDS)
    async def test_panel_opens_full_screen(self, panel_id):
        app = PulseApp(source=MockSource())
        async with app.run_test(size=(140, 45)) as pilot:
            await boot(pilot, app)

            app.query_one(f"#{panel_id}").focus()
            await pilot.pause()
            await pilot.press("x")
            await pilot.pause()
            await asyncio.sleep(0.2)

            assert type(app.screen).__name__ == "ImmersiveScreen"

            await pilot.press("escape")
            await pilot.pause()


class TestDegradedTelemetry:
    async def test_a_failing_subsystem_does_not_break_the_ui(self):
        """A restricted net_connections should cost the network panel, not the app."""
        app = PulseApp(source=MockSource(fail={"network"}))
        async with app.run_test(size=(140, 45)) as pilot:
            await boot(pilot, app)

            snapshot = app.store.snapshot
            assert "network" in snapshot.errors
            # Everything else still rendered.
            assert snapshot.cpu.core_count == 4
            assert len(snapshot.processes) == 12
            app.refresh_panels()
            await pilot.pause()

    async def test_total_telemetry_failure_still_renders(self):
        broken = {"cpu", "memory", "disk_io", "network",
                  "processes", "volumes", "system", "containers"}
        app = PulseApp(source=MockSource(fail=broken))
        async with app.run_test(size=(140, 45)) as pilot:
            await boot(pilot, app)

            assert len(app.store.snapshot.errors) == 8
            app.refresh_panels()
            await pilot.pause()


class TestDerivedValuesReachTheUI:
    async def test_rates_are_available_after_two_ticks(self):
        source = MockSource()
        app = PulseApp(source=source)
        async with app.run_test(size=(140, 45)) as pilot:
            await boot(pilot, app)

            # Advance the fake machine so counters actually move.
            source.advance(10)
            app.refresh_data()
            for _ in range(40):
                if app.store.tick_count >= 2:
                    break
                await asyncio.sleep(0.05)
                await pilot.pause()

            assert app.store.tick_count >= 2
            assert app.store.rates.interval > 0
            assert app.store.rates.net_recv_kbps > 0

    async def test_history_accumulates_across_ticks(self):
        source = MockSource()
        app = PulseApp(source=source)
        async with app.run_test(size=(140, 45)) as pilot:
            await boot(pilot, app)

            for _ in range(3):
                source.advance()
                app.refresh_data()
                await asyncio.sleep(0.15)
                await pilot.pause()

            assert len(app.store.history.cpu) >= 2
            assert app.store.peaks.cpu > 0
