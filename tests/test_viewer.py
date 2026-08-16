"""Tests for the file viewer's safety checks.

The viewer reads on the UI thread, so anything that can block forever - a FIFO
with no writer, a character device - has to be refused before it is opened.
"""
import os
import sys

import pytest

from pulse.screens.viewer import FileViewer


def _reject(path) -> str:
    return FileViewer(str(path))._reject(str(path))


class TestAcceptsRegularFiles:
    def test_plain_text_file_is_allowed(self, tmp_path):
        target = tmp_path / "notes.txt"
        target.write_text("hello")
        assert _reject(target) == ""

    def test_empty_file_is_allowed(self, tmp_path):
        target = tmp_path / "empty.txt"
        target.touch()
        assert _reject(target) == ""


class TestRejectsUnsafePaths:
    def test_missing_file(self, tmp_path):
        assert "stat" in _reject(tmp_path / "nope.txt").lower()

    def test_directory(self, tmp_path):
        assert _reject(tmp_path) != ""

    def test_oversized_file(self, tmp_path, monkeypatch):
        target = tmp_path / "big.bin"
        target.write_bytes(b"x" * 2048)
        monkeypatch.setattr(FileViewer, "MAX_VIEW_SIZE", 1024)

        reason = _reject(target)
        assert "view limit" in reason

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX FIFOs")
    def test_fifo_is_refused_without_opening_it(self, tmp_path):
        """Opening a FIFO with no writer would block the event loop forever."""
        fifo = tmp_path / "pipe"
        os.mkfifo(fifo)

        reason = _reject(fifo)
        assert "pipe" in reason.lower() or "block" in reason.lower()

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX device files")
    def test_character_device_is_refused(self):
        reason = _reject("/dev/zero")
        assert reason != ""

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX symlinks")
    def test_symlink_is_refused(self, tmp_path):
        target = tmp_path / "real.txt"
        target.write_text("data")
        link = tmp_path / "link.txt"
        link.symlink_to(target)

        assert "symlink" in _reject(link).lower()
