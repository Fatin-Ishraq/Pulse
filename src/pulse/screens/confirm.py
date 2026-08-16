"""
Pulse - Confirmation modal.

Every destructive action names its exact target here and waits for an explicit
answer. Escape and the default focus both land on Cancel, so a stray keypress
dismisses rather than confirms.
"""
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Container, Horizontal
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static


class ConfirmScreen(ModalScreen[bool]):
    """Ask the user to confirm a destructive action.

    Dismisses with True only if the user explicitly confirms.
    """

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("n", "cancel", "No"),
        ("y", "confirm", "Yes"),
    ]

    CSS = """
    ConfirmScreen {
        align: center middle;
        background: rgba(0, 0, 0, 0.75);
    }

    #confirm-box {
        width: 64;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: thick $error;
    }

    #confirm-title {
        width: 100%;
        text-style: bold;
        color: $error;
        padding-bottom: 1;
    }

    #confirm-target {
        width: 100%;
        padding: 1 0;
        text-style: bold;
    }

    #confirm-detail {
        width: 100%;
        color: $text-muted;
        padding-bottom: 1;
    }

    #confirm-buttons {
        width: 100%;
        height: auto;
        align: right middle;
        padding-top: 1;
    }

    #confirm-buttons Button {
        margin-left: 2;
        min-width: 14;
    }
    """

    def __init__(
        self,
        title: str,
        target: str,
        detail: str = "",
        confirm_label: str = "Confirm",
    ) -> None:
        super().__init__()
        self.title_text = title
        self.target_text = target
        self.detail_text = detail
        self.confirm_label = confirm_label

    def compose(self) -> ComposeResult:
        with Container(id="confirm-box"):
            yield Label(self.title_text, id="confirm-title")
            yield Static(self.target_text, id="confirm-target")
            if self.detail_text:
                yield Static(self.detail_text, id="confirm-detail")
            with Horizontal(id="confirm-buttons"):
                yield Button("Cancel [Esc]", id="confirm-no", variant="primary")
                yield Button(f"{self.confirm_label} [Y]", id="confirm-yes", variant="error")

    def on_mount(self) -> None:
        # Focus Cancel, so Enter on a reflex dismisses instead of destroying.
        self.query_one("#confirm-no", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.dismiss(event.button.id == "confirm-yes")

    def action_confirm(self) -> None:
        self.dismiss(True)

    def action_cancel(self) -> None:
        self.dismiss(False)


class BlockedScreen(ModalScreen[None]):
    """Tell the user an action was refused, and why."""

    BINDINGS = [
        ("escape", "dismiss_screen", "Close"),
        ("enter", "dismiss_screen", "Close"),
    ]

    CSS = """
    BlockedScreen {
        align: center middle;
        background: rgba(0, 0, 0, 0.75);
    }

    #blocked-box {
        width: 60;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: thick $warning;
    }

    #blocked-title {
        width: 100%;
        text-style: bold;
        color: $warning;
        padding-bottom: 1;
    }

    #blocked-buttons {
        width: 100%;
        height: auto;
        align: right middle;
        padding-top: 1;
    }
    """

    def __init__(self, reason: str, title: str = "Action refused") -> None:
        super().__init__()
        self.reason = reason
        self.title_text = title

    def compose(self) -> ComposeResult:
        with Container(id="blocked-box"):
            yield Label(self.title_text, id="blocked-title")
            yield Static(self.reason, id="blocked-reason")
            with Horizontal(id="blocked-buttons"):
                yield Button("OK [Esc]", id="blocked-ok", variant="primary")

    def on_mount(self) -> None:
        self.query_one("#blocked-ok", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        self.dismiss(None)

    def action_dismiss_screen(self) -> None:
        self.dismiss(None)


def confirm_kill_text(label: str, force: bool = False) -> tuple:
    """Build the (title, target, detail, button) copy for a kill confirmation."""
    if force:
        return (
            "Force kill this process?",
            label,
            "A force kill gives the process no chance to save state or shut down "
            "cleanly. Unsaved work in it will be lost.",
            "Force kill",
        )
    return (
        "Terminate this process?",
        label,
        "The process is asked to shut down. Anything it has not saved may be lost.",
        "Terminate",
    )


def confirm_container_text(operation: str, name: str) -> tuple:
    """Build the copy for a Docker container operation."""
    details = {
        "stop": "Running processes in the container are signalled to stop.",
        "restart": "The container is stopped and started again; in-flight work is lost.",
        "start": "The container is started.",
    }
    return (
        f"{operation.capitalize()} this container?",
        name,
        details.get(operation, ""),
        operation.capitalize(),
    )
