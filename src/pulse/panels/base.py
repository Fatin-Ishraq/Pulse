"""Base class shared by every dashboard panel."""
from typing import Callable, Optional

from rich.text import Text
from textual.widgets import Static

from pulse import core
from pulse.actions import ActionResult
from pulse.core.models import Snapshot
from pulse.core.store import MetricStore
from pulse.screens.confirm import (
    BlockedScreen,
    ConfirmScreen,
    confirm_container_text,
    confirm_kill_text,
)


class Panel(Static, can_focus=True):
    """Base class for all dashboard panels.

    Also provides the guarded entry points for destructive actions, so no
    panel has to re-implement "ask first, then report what really happened".
    """

    # Each panel type defines what detailed view it provides
    PANEL_NAME = "Panel"

    def __init__(self, title: str, content: str = "", **kwargs):
        super().__init__(content, **kwargs)
        self.border_title = title

    def get_detailed_view(self) -> Text:
        """Override in subclasses to provide detailed view for main panel."""
        return Text("No details available")

    def on_click(self) -> None:
        """Focus the panel when clicked."""
        self.focus()

    # ------------------------------------------------------------------
    # Metric access
    #
    # Panels read from the shared store; they never sample anything. That is
    # what keeps every number on screen consistent within a tick, and keeps
    # blocking system calls off the event loop.
    # ------------------------------------------------------------------
    @property
    def store(self) -> MetricStore:
        return self.app.store

    @property
    def snapshot(self) -> Optional[Snapshot]:
        """The current tick, or None before the first sample lands."""
        return self.app.store.snapshot

    @property
    def history(self):
        return self.app.store.history

    @property
    def rates(self):
        return self.app.store.rates

    def waiting_text(self) -> Text:
        """Placeholder shown until the first snapshot arrives."""
        return Text("Acquiring telemetry...", style="dim")

    # ------------------------------------------------------------------
    # Guarded actions
    # ------------------------------------------------------------------
    def report(self, result: ActionResult) -> None:
        """Surface an action's real outcome, success or failure."""
        self.notify(
            result.message,
            severity="information" if result.ok else "error",
        )

    def _ask(
        self,
        title: str,
        target: str,
        detail: str,
        confirm_label: str,
        on_confirm: Callable[[], None],
    ) -> None:
        """Push a confirmation and run ``on_confirm`` only on an explicit yes."""

        def handle(confirmed: Optional[bool]) -> None:
            if confirmed:
                on_confirm()

        self.app.push_screen(
            ConfirmScreen(title, target, detail, confirm_label),
            handle,
        )

    def request_kill(self, pid: Optional[int]) -> None:
        """Confirm and then terminate a process.

        Protected targets are refused outright. A privilege failure offers a
        force kill as a separate, explicitly confirmed step - it never
        escalates on its own.
        """
        if pid is None:
            self.notify("No process selected.", severity="warning")
            return

        reason = core.protection_reason(pid)
        if reason:
            self.app.push_screen(BlockedScreen(reason))
            return

        info = core.describe_process(pid)
        if info is None:
            self.notify(f"PID {pid} no longer exists.", severity="warning")
            return

        label = info.label()

        def do_kill() -> None:
            result = core.kill_process(pid)
            if result.can_force:
                self._ask(*confirm_kill_text(label, force=True),
                          on_confirm=lambda: self.report(core.kill_process(pid, force=True)))
                return
            self.report(result)

        self._ask(*confirm_kill_text(label), on_confirm=do_kill)

    def request_renice(self, pid: Optional[int], delta: int) -> None:
        """Adjust a process's priority, refusing protected targets.

        Renicing is reversible, so it reports rather than prompting - but it
        still refuses protected PIDs and never claims success it did not get.
        """
        if pid is None:
            self.notify("No process selected.", severity="warning")
            return
        self.report(core.adjust_nice(pid, delta))

    def request_container_action(
        self,
        operation: str,
        container_id: Optional[str],
        name: str,
        run: Callable[[], ActionResult],
    ) -> None:
        """Confirm and then run a Docker container operation."""
        if not container_id:
            self.notify("No container selected.", severity="warning")
            return

        self._ask(
            *confirm_container_text(operation, name),
            on_confirm=lambda: self.report(run()),
        )
