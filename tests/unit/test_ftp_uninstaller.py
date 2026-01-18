"""Unit tests for FTPUninstaller."""

from ftplib import error_perm, error_reply
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from src.ftp.scanner import GameDump, LocationType
from src.ftp.uninstaller import FTPUninstaller
from src.models.uninstall import UninstallProgress, UninstallResult


@pytest.fixture
def mock_connection():
    """Create a mock FTP connection manager."""
    connection = MagicMock()
    connection.is_connected = True
    connection.ftp = MagicMock()
    connection.ftp.pwd.return_value = "/"
    return connection


@pytest.fixture
def sample_dump():
    """Create a sample game dump."""
    return GameDump(
        path="/mnt/usb0/CUSA12345",
        name="CUSA12345",
        location_type=LocationType.USB,
        has_elf=True,
        has_js=True
    )


class TestFTPUninstaller:
    """Tests for FTPUninstaller class."""

    def test_init(self, mock_connection):
        """Test uninstaller initialization."""
        uninstaller = FTPUninstaller(mock_connection)
        assert uninstaller.is_cancelled is False

    def test_cancel(self, mock_connection):
        """Test cancel method."""
        uninstaller = FTPUninstaller(mock_connection)
        uninstaller.cancel()
        assert uninstaller.is_cancelled is True

    def test_reset_cancel(self, mock_connection):
        """Test reset_cancel method."""
        uninstaller = FTPUninstaller(mock_connection)
        uninstaller.cancel()
        uninstaller.reset_cancel()
        assert uninstaller.is_cancelled is False

    def test_uninstall_from_dump_success(self, mock_connection, sample_dump):
        """Test successful uninstall of both files."""
        uninstaller = FTPUninstaller(mock_connection)
        result = uninstaller.uninstall_from_dump(sample_dump)

        assert result.success is True
        assert result.elf_deleted is True
        assert result.js_deleted is True
        assert result.error_message is None
        assert result.dump_path == sample_dump.path

        # Verify FTP commands
        mock_connection.ftp.cwd.assert_any_call(sample_dump.path)
        mock_connection.ftp.delete.assert_any_call("dump_runner.elf")
        mock_connection.ftp.delete.assert_any_call("homebrew.js")

    def test_uninstall_from_dump_not_connected(self, mock_connection, sample_dump):
        """Test uninstall when not connected."""
        mock_connection.is_connected = False
        uninstaller = FTPUninstaller(mock_connection)
        result = uninstaller.uninstall_from_dump(sample_dump)

        assert result.success is False
        assert "Not connected" in result.error_message

    def test_uninstall_from_dump_file_not_found(self, mock_connection, sample_dump):
        """Test uninstall when files don't exist (550 error)."""

        def delete_side_effect(filename):
            raise error_perm("550 File not found")

        mock_connection.ftp.delete.side_effect = delete_side_effect

        uninstaller = FTPUninstaller(mock_connection)
        result = uninstaller.uninstall_from_dump(sample_dump)

        # File not found is treated as success
        assert result.success is True
        assert result.elf_deleted is False
        assert result.js_deleted is False

    def test_uninstall_from_dump_226_success_response(self, mock_connection, sample_dump):
        """Test uninstall when server returns 226 as error_reply (PS5 FTP behavior)."""

        def delete_side_effect(filename):
            # Some FTP servers (like PS5) raise 226 as an exception
            raise error_reply("226 File deleted")

        mock_connection.ftp.delete.side_effect = delete_side_effect

        uninstaller = FTPUninstaller(mock_connection)
        result = uninstaller.uninstall_from_dump(sample_dump)

        # 226 is a success code, should be treated as success
        assert result.success is True
        assert result.elf_deleted is True
        assert result.js_deleted is True

    def test_uninstall_from_dump_permission_error(self, mock_connection, sample_dump):
        """Test uninstall with permission error."""

        def delete_side_effect(filename):
            raise error_perm("553 Permission denied")

        mock_connection.ftp.delete.side_effect = delete_side_effect

        uninstaller = FTPUninstaller(mock_connection)
        result = uninstaller.uninstall_from_dump(sample_dump)

        assert result.success is False
        assert "553" in result.error_message

    def test_uninstall_from_dump_connection_lost(self, mock_connection, sample_dump):
        """Test uninstall when connection is lost."""

        def delete_side_effect(filename):
            raise error_perm("530 Not logged in")

        mock_connection.ftp.delete.side_effect = delete_side_effect

        uninstaller = FTPUninstaller(mock_connection)
        result = uninstaller.uninstall_from_dump(sample_dump)

        assert result.success is False
        assert "Connection lost" in result.error_message or "530" in result.error_message

    def test_uninstall_from_dump_partial_success(self, mock_connection, sample_dump):
        """Test uninstall where only ELF is deleted before error."""
        call_count = [0]

        def delete_side_effect(filename):
            call_count[0] += 1
            if call_count[0] == 1:
                return  # First file succeeds
            raise error_perm("553 Permission denied")

        mock_connection.ftp.delete.side_effect = delete_side_effect

        uninstaller = FTPUninstaller(mock_connection)
        result = uninstaller.uninstall_from_dump(sample_dump)

        assert result.success is False
        assert result.elf_deleted is True
        assert result.js_deleted is False

    def test_uninstall_batch_success(self, mock_connection):
        """Test successful batch uninstall."""
        dumps = [
            GameDump(path="/mnt/usb0/game1", name="game1", location_type=LocationType.USB),
            GameDump(path="/mnt/usb0/game2", name="game2", location_type=LocationType.USB),
            GameDump(path="/mnt/usb0/game3", name="game3", location_type=LocationType.USB),
        ]

        uninstaller = FTPUninstaller(mock_connection)
        results = uninstaller.uninstall_batch(dumps)

        assert len(results) == 3
        assert all(r.success for r in results)

    def test_uninstall_batch_with_progress_callback(self, mock_connection):
        """Test batch uninstall invokes progress callback."""
        dumps = [
            GameDump(path="/mnt/usb0/game1", name="game1", location_type=LocationType.USB),
            GameDump(path="/mnt/usb0/game2", name="game2", location_type=LocationType.USB),
        ]

        progress_calls = []

        def on_progress(progress: UninstallProgress):
            progress_calls.append(progress)

        uninstaller = FTPUninstaller(mock_connection)
        uninstaller.uninstall_batch(dumps, on_progress=on_progress)

        # Should have progress calls: before and after each dump
        assert len(progress_calls) == 4

    def test_uninstall_batch_with_complete_callback(self, mock_connection):
        """Test batch uninstall invokes completion callback."""
        dumps = [
            GameDump(path="/mnt/usb0/game1", name="game1", location_type=LocationType.USB),
        ]

        complete_called = [False]
        complete_results = [None]

        def on_complete(results):
            complete_called[0] = True
            complete_results[0] = results

        uninstaller = FTPUninstaller(mock_connection)
        uninstaller.uninstall_batch(dumps, on_complete=on_complete)

        assert complete_called[0] is True
        assert len(complete_results[0]) == 1

    def test_uninstall_batch_cancel(self, mock_connection):
        """Test cancelling batch uninstall."""
        dumps = [
            GameDump(path="/mnt/usb0/game1", name="game1", location_type=LocationType.USB),
            GameDump(path="/mnt/usb0/game2", name="game2", location_type=LocationType.USB),
            GameDump(path="/mnt/usb0/game3", name="game3", location_type=LocationType.USB),
        ]

        uninstaller = FTPUninstaller(mock_connection)

        # Cancel after first dump
        call_count = [0]
        original_uninstall = uninstaller.uninstall_from_dump

        def uninstall_with_cancel(dump):
            call_count[0] += 1
            if call_count[0] == 1:
                uninstaller.cancel()
            return original_uninstall(dump)

        uninstaller.uninstall_from_dump = uninstall_with_cancel
        results = uninstaller.uninstall_batch(dumps)

        # First dump completes (with cancel), remaining are marked cancelled
        assert len(results) == 3
        assert results[0].error_message == "Uninstall cancelled"
        assert results[1].error_message == "Uninstall cancelled"
        assert results[2].error_message == "Uninstall cancelled"

    def test_get_batch_summary(self, mock_connection):
        """Test batch summary generation."""
        results = [
            UninstallResult(dump_path="/game1", success=True, duration_seconds=1.0),
            UninstallResult(dump_path="/game2", success=True, duration_seconds=0.5),
            UninstallResult(dump_path="/game3", success=False, error_message="Error", duration_seconds=0.2),
        ]

        uninstaller = FTPUninstaller(mock_connection)
        summary = uninstaller.get_batch_summary(results)

        assert summary["total"] == 3
        assert summary["successful"] == 2
        assert summary["failed"] == 1
        assert summary["duration_seconds"] == 1.7
        assert len(summary["failures"]) == 1
        assert summary["failures"][0] == ("/game3", "Error")
