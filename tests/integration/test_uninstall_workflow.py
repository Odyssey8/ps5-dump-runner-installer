"""Integration tests for uninstall workflow."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.ftp.scanner import GameDump, LocationType
from src.ftp.uninstaller import FTPUninstaller
from src.local.uninstaller import LocalUninstaller
from src.models.uninstall import UninstallProgress, UninstallResult


class TestLocalUninstallWorkflow:
    """Integration tests for local uninstall workflow."""

    def test_single_game_uninstall_workflow(self):
        """Test complete workflow for uninstalling from a single game."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup: Create dump directory with files
            dump_path = Path(tmpdir) / "CUSA12345"
            dump_path.mkdir()
            (dump_path / "dump_runner.elf").write_bytes(b"elf content")
            (dump_path / "homebrew.js").write_text("js content")

            dump = GameDump(
                path=str(dump_path),
                name="CUSA12345",
                location_type=LocationType.LOCAL,
                has_elf=True,
                has_js=True
            )

            # Execute: Uninstall
            uninstaller = LocalUninstaller()
            result = uninstaller.uninstall_from_dump(dump)

            # Verify: Files deleted, result successful
            assert result.success is True
            assert result.elf_deleted is True
            assert result.js_deleted is True
            assert not (dump_path / "dump_runner.elf").exists()
            assert not (dump_path / "homebrew.js").exists()

    def test_batch_uninstall_workflow_with_progress(self):
        """Test complete batch uninstall with progress tracking."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup: Create multiple dump directories
            dumps = []
            for i in range(3):
                dump_path = Path(tmpdir) / f"CUSA1234{i}"
                dump_path.mkdir()
                (dump_path / "dump_runner.elf").write_bytes(b"elf")
                (dump_path / "homebrew.js").write_text("js")
                dumps.append(GameDump(
                    path=str(dump_path),
                    name=f"CUSA1234{i}",
                    location_type=LocationType.LOCAL,
                    has_elf=True,
                    has_js=True
                ))

            # Track progress
            progress_updates = []
            complete_called = [False]
            final_results = [None]

            def on_progress(progress: UninstallProgress):
                progress_updates.append({
                    "dump_name": progress.current_dump.name,
                    "completed": progress.dumps_completed,
                    "total": progress.dumps_total,
                    "percent": progress.percent_complete
                })

            def on_complete(results):
                complete_called[0] = True
                final_results[0] = results

            # Execute: Batch uninstall
            uninstaller = LocalUninstaller()
            results = uninstaller.uninstall_batch(
                dumps,
                on_progress=on_progress,
                on_complete=on_complete
            )

            # Verify: All successful
            assert len(results) == 3
            assert all(r.success for r in results)
            assert complete_called[0] is True
            assert len(final_results[0]) == 3

            # Verify progress was tracked
            assert len(progress_updates) == 6  # 2 per dump (before and after)

            # Verify all files deleted
            for i in range(3):
                dump_path = Path(tmpdir) / f"CUSA1234{i}"
                assert not (dump_path / "dump_runner.elf").exists()
                assert not (dump_path / "homebrew.js").exists()


class TestFTPUninstallWorkflow:
    """Integration tests for FTP uninstall workflow."""

    def test_single_game_uninstall_workflow(self):
        """Test complete workflow for uninstalling from a single game via FTP."""
        # Setup: Mock FTP connection
        mock_connection = MagicMock()
        mock_connection.is_connected = True
        mock_connection.ftp = MagicMock()
        mock_connection.ftp.pwd.return_value = "/"

        dump = GameDump(
            path="/mnt/usb0/CUSA12345",
            name="CUSA12345",
            location_type=LocationType.USB,
            has_elf=True,
            has_js=True
        )

        # Execute: Uninstall
        uninstaller = FTPUninstaller(mock_connection)
        result = uninstaller.uninstall_from_dump(dump)

        # Verify: Result successful, FTP commands called
        assert result.success is True
        assert result.elf_deleted is True
        assert result.js_deleted is True

        # Verify FTP commands
        mock_connection.ftp.cwd.assert_called()
        mock_connection.ftp.delete.assert_any_call("dump_runner.elf")
        mock_connection.ftp.delete.assert_any_call("homebrew.js")

    def test_batch_uninstall_workflow_with_partial_failure(self):
        """Test batch uninstall where some games fail."""
        # Setup: Mock FTP connection with failures
        mock_connection = MagicMock()
        mock_connection.is_connected = True
        mock_connection.ftp = MagicMock()
        mock_connection.ftp.pwd.return_value = "/"

        # Make second dump fail - track unique dump paths to fail game2
        def cwd_side_effect(path):
            if path == "/mnt/usb0/game2":
                from ftplib import error_perm
                raise error_perm("550 Directory not found")

        mock_connection.ftp.cwd.side_effect = cwd_side_effect

        dumps = [
            GameDump(path="/mnt/usb0/game1", name="game1", location_type=LocationType.USB),
            GameDump(path="/mnt/usb0/game2", name="game2", location_type=LocationType.USB),
            GameDump(path="/mnt/usb0/game3", name="game3", location_type=LocationType.USB),
        ]

        # Execute
        uninstaller = FTPUninstaller(mock_connection)
        results = uninstaller.uninstall_batch(dumps)

        # Verify: One success, one failure, one success
        assert len(results) == 3
        assert results[0].success is True
        assert results[1].success is False  # This one failed
        assert results[2].success is True

        # Verify summary
        summary = uninstaller.get_batch_summary(results)
        assert summary["successful"] == 2
        assert summary["failed"] == 1

    def test_batch_uninstall_cancel_during_operation(self):
        """Test cancelling batch uninstall mid-operation."""
        # Setup: Mock FTP connection
        mock_connection = MagicMock()
        mock_connection.is_connected = True
        mock_connection.ftp = MagicMock()
        mock_connection.ftp.pwd.return_value = "/"

        dumps = [
            GameDump(path="/mnt/usb0/game1", name="game1", location_type=LocationType.USB),
            GameDump(path="/mnt/usb0/game2", name="game2", location_type=LocationType.USB),
            GameDump(path="/mnt/usb0/game3", name="game3", location_type=LocationType.USB),
        ]

        # Track progress and cancel after first dump
        progress_count = [0]

        def on_progress(progress: UninstallProgress):
            progress_count[0] += 1
            # After completing first dump (progress_count == 2 means after first dump)
            if progress_count[0] == 2:
                uninstaller.cancel()

        uninstaller = FTPUninstaller(mock_connection)
        results = uninstaller.uninstall_batch(dumps, on_progress=on_progress)

        # First dump should succeed, rest should be cancelled
        assert len(results) == 3
        assert results[0].success is True
        # Remaining are cancelled
        assert results[1].success is False
        assert results[1].error_message == "Uninstall cancelled"
        assert results[2].success is False
        assert results[2].error_message == "Uninstall cancelled"


class TestLocalUninstallCancelWorkflow:
    """Tests for local uninstall cancel scenarios."""

    def test_batch_uninstall_cancel_during_operation(self):
        """Test cancelling local batch uninstall mid-operation."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup: Create multiple dump directories
            dumps = []
            for i in range(3):
                dump_path = Path(tmpdir) / f"CUSA1234{i}"
                dump_path.mkdir()
                (dump_path / "dump_runner.elf").write_bytes(b"elf")
                (dump_path / "homebrew.js").write_text("js")
                dumps.append(GameDump(
                    path=str(dump_path),
                    name=f"CUSA1234{i}",
                    location_type=LocationType.LOCAL,
                    has_elf=True,
                    has_js=True
                ))

            # Track progress and cancel after first dump
            progress_count = [0]

            def on_progress(progress: UninstallProgress):
                progress_count[0] += 1
                # After completing first dump
                if progress_count[0] == 2:
                    uninstaller.cancel()

            uninstaller = LocalUninstaller()
            results = uninstaller.uninstall_batch(dumps, on_progress=on_progress)

            # First dump should succeed, rest should be cancelled
            assert len(results) == 3
            assert results[0].success is True
            # Remaining are cancelled
            assert results[1].success is False
            assert results[1].error_message == "Uninstall cancelled"
            assert results[2].success is False
            assert results[2].error_message == "Uninstall cancelled"

            # First dump's files should be deleted
            first_dump_path = Path(tmpdir) / "CUSA12340"
            assert not (first_dump_path / "dump_runner.elf").exists()
            assert not (first_dump_path / "homebrew.js").exists()

            # Remaining dumps' files should still exist
            for i in range(1, 3):
                dump_path = Path(tmpdir) / f"CUSA1234{i}"
                assert (dump_path / "dump_runner.elf").exists()
                assert (dump_path / "homebrew.js").exists()
