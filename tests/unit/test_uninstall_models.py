"""Unit tests for uninstall data models."""

import pytest

from src.models.uninstall import UninstallResult, UninstallProgress
from src.ftp.scanner import GameDump, LocationType


class TestUninstallResult:
    """Tests for UninstallResult dataclass."""

    def test_create_successful_result(self):
        """Test creating a successful uninstall result."""
        result = UninstallResult(
            dump_path="/mnt/usb0/game1",
            success=True,
            elf_deleted=True,
            js_deleted=True,
            duration_seconds=1.5
        )

        assert result.dump_path == "/mnt/usb0/game1"
        assert result.success is True
        assert result.error_message is None
        assert result.elf_deleted is True
        assert result.js_deleted is True
        assert result.duration_seconds == 1.5

    def test_create_failed_result(self):
        """Test creating a failed uninstall result."""
        result = UninstallResult(
            dump_path="/mnt/usb0/game2",
            success=False,
            error_message="Permission denied",
            elf_deleted=False,
            js_deleted=False,
            duration_seconds=0.1
        )

        assert result.dump_path == "/mnt/usb0/game2"
        assert result.success is False
        assert result.error_message == "Permission denied"
        assert result.elf_deleted is False
        assert result.js_deleted is False

    def test_partial_deletion_result(self):
        """Test result where only one file was deleted."""
        result = UninstallResult(
            dump_path="/mnt/usb0/game3",
            success=True,
            elf_deleted=True,
            js_deleted=False,
            duration_seconds=0.5
        )

        assert result.success is True
        assert result.elf_deleted is True
        assert result.js_deleted is False

    def test_default_values(self):
        """Test default values for optional fields."""
        result = UninstallResult(
            dump_path="/mnt/usb0/game4",
            success=True
        )

        assert result.error_message is None
        assert result.elf_deleted is False
        assert result.js_deleted is False
        assert result.duration_seconds == 0.0


class TestUninstallProgress:
    """Tests for UninstallProgress dataclass."""

    def test_create_progress(self):
        """Test creating progress object."""
        dump = GameDump(
            path="/mnt/usb0/game1",
            name="game1",
            location_type=LocationType.USB
        )

        progress = UninstallProgress(
            current_dump=dump,
            current_file="dump_runner.elf",
            dumps_completed=2,
            dumps_total=5
        )

        assert progress.current_dump == dump
        assert progress.current_file == "dump_runner.elf"
        assert progress.dumps_completed == 2
        assert progress.dumps_total == 5

    def test_percent_complete(self):
        """Test percentage calculation."""
        dump = GameDump(
            path="/mnt/usb0/game1",
            name="game1",
            location_type=LocationType.USB
        )

        progress = UninstallProgress(
            current_dump=dump,
            current_file="homebrew.js",
            dumps_completed=3,
            dumps_total=10
        )

        assert progress.percent_complete == 30.0

    def test_percent_complete_zero_total(self):
        """Test percentage calculation with zero total."""
        dump = GameDump(
            path="/mnt/usb0/game1",
            name="game1",
            location_type=LocationType.USB
        )

        progress = UninstallProgress(
            current_dump=dump,
            current_file="dump_runner.elf",
            dumps_completed=0,
            dumps_total=0
        )

        assert progress.percent_complete == 0.0

    def test_percent_complete_full(self):
        """Test percentage calculation at 100%."""
        dump = GameDump(
            path="/mnt/usb0/game1",
            name="game1",
            location_type=LocationType.USB
        )

        progress = UninstallProgress(
            current_dump=dump,
            current_file="homebrew.js",
            dumps_completed=5,
            dumps_total=5
        )

        assert progress.percent_complete == 100.0
