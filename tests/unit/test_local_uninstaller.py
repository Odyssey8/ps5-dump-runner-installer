"""Unit tests for LocalUninstaller."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.ftp.scanner import GameDump, LocationType
from src.local.uninstaller import LocalUninstaller
from src.models.uninstall import UninstallProgress, UninstallResult


@pytest.fixture
def temp_dump_dir():
    """Create a temporary dump directory with files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dump_path = Path(tmpdir) / "CUSA12345"
        dump_path.mkdir()

        # Create dump_runner files
        (dump_path / "dump_runner.elf").write_bytes(b"test elf content")
        (dump_path / "homebrew.js").write_text("test js content")

        yield dump_path


@pytest.fixture
def temp_dump_dir_empty():
    """Create a temporary dump directory without files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        dump_path = Path(tmpdir) / "CUSA12345"
        dump_path.mkdir()
        yield dump_path


@pytest.fixture
def sample_dump(temp_dump_dir):
    """Create a sample game dump pointing to temp directory."""
    return GameDump(
        path=str(temp_dump_dir),
        name="CUSA12345",
        location_type=LocationType.LOCAL,
        has_elf=True,
        has_js=True
    )


@pytest.fixture
def sample_dump_empty(temp_dump_dir_empty):
    """Create a sample game dump pointing to empty temp directory."""
    return GameDump(
        path=str(temp_dump_dir_empty),
        name="CUSA12345",
        location_type=LocationType.LOCAL,
        has_elf=False,
        has_js=False
    )


class TestLocalUninstaller:
    """Tests for LocalUninstaller class."""

    def test_init(self):
        """Test uninstaller initialization."""
        uninstaller = LocalUninstaller()
        assert uninstaller.is_cancelled is False

    def test_cancel(self):
        """Test cancel method."""
        uninstaller = LocalUninstaller()
        uninstaller.cancel()
        assert uninstaller.is_cancelled is True

    def test_reset_cancel(self):
        """Test reset_cancel method."""
        uninstaller = LocalUninstaller()
        uninstaller.cancel()
        uninstaller.reset_cancel()
        assert uninstaller.is_cancelled is False

    def test_uninstall_from_dump_success(self, sample_dump, temp_dump_dir):
        """Test successful uninstall of both files."""
        # Verify files exist before
        assert (temp_dump_dir / "dump_runner.elf").exists()
        assert (temp_dump_dir / "homebrew.js").exists()

        uninstaller = LocalUninstaller()
        result = uninstaller.uninstall_from_dump(sample_dump)

        assert result.success is True
        assert result.elf_deleted is True
        assert result.js_deleted is True
        assert result.error_message is None
        assert result.dump_path == sample_dump.path

        # Verify files are deleted
        assert not (temp_dump_dir / "dump_runner.elf").exists()
        assert not (temp_dump_dir / "homebrew.js").exists()

    def test_uninstall_from_dump_no_files(self, sample_dump_empty, temp_dump_dir_empty):
        """Test uninstall when files don't exist."""
        uninstaller = LocalUninstaller()
        result = uninstaller.uninstall_from_dump(sample_dump_empty)

        # Should succeed even if files don't exist
        assert result.success is True
        assert result.elf_deleted is False
        assert result.js_deleted is False

    def test_uninstall_from_dump_directory_not_exists(self):
        """Test uninstall when directory doesn't exist."""
        dump = GameDump(
            path="/nonexistent/path/CUSA12345",
            name="CUSA12345",
            location_type=LocationType.LOCAL
        )

        uninstaller = LocalUninstaller()
        result = uninstaller.uninstall_from_dump(dump)

        assert result.success is False
        assert "does not exist" in result.error_message

    def test_uninstall_from_dump_path_is_file(self):
        """Test uninstall when path is a file, not directory."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            file_path = f.name

        try:
            dump = GameDump(
                path=file_path,
                name="somefile",
                location_type=LocationType.LOCAL
            )

            uninstaller = LocalUninstaller()
            result = uninstaller.uninstall_from_dump(dump)

            assert result.success is False
            assert "not a directory" in result.error_message
        finally:
            Path(file_path).unlink()

    def test_uninstall_from_dump_partial_files(self, temp_dump_dir):
        """Test uninstall when only one file exists."""
        # Remove homebrew.js
        (temp_dump_dir / "homebrew.js").unlink()

        dump = GameDump(
            path=str(temp_dump_dir),
            name="CUSA12345",
            location_type=LocationType.LOCAL,
            has_elf=True,
            has_js=False
        )

        uninstaller = LocalUninstaller()
        result = uninstaller.uninstall_from_dump(dump)

        assert result.success is True
        assert result.elf_deleted is True
        assert result.js_deleted is False

    def test_uninstall_batch_success(self):
        """Test successful batch uninstall."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create multiple dump directories
            dumps = []
            for i in range(3):
                dump_path = Path(tmpdir) / f"game{i}"
                dump_path.mkdir()
                (dump_path / "dump_runner.elf").write_bytes(b"elf")
                (dump_path / "homebrew.js").write_text("js")
                dumps.append(GameDump(
                    path=str(dump_path),
                    name=f"game{i}",
                    location_type=LocationType.LOCAL
                ))

            uninstaller = LocalUninstaller()
            results = uninstaller.uninstall_batch(dumps)

            assert len(results) == 3
            assert all(r.success for r in results)

            # Verify all files deleted
            for i in range(3):
                dump_path = Path(tmpdir) / f"game{i}"
                assert not (dump_path / "dump_runner.elf").exists()
                assert not (dump_path / "homebrew.js").exists()

    def test_uninstall_batch_with_progress_callback(self):
        """Test batch uninstall invokes progress callback."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dumps = []
            for i in range(2):
                dump_path = Path(tmpdir) / f"game{i}"
                dump_path.mkdir()
                (dump_path / "dump_runner.elf").write_bytes(b"elf")
                dumps.append(GameDump(
                    path=str(dump_path),
                    name=f"game{i}",
                    location_type=LocationType.LOCAL
                ))

            progress_calls = []

            def on_progress(progress: UninstallProgress):
                progress_calls.append(progress)

            uninstaller = LocalUninstaller()
            uninstaller.uninstall_batch(dumps, on_progress=on_progress)

            # Should have progress calls: before and after each dump
            assert len(progress_calls) == 4

    def test_uninstall_batch_with_complete_callback(self):
        """Test batch uninstall invokes completion callback."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dump_path = Path(tmpdir) / "game1"
            dump_path.mkdir()
            dumps = [GameDump(
                path=str(dump_path),
                name="game1",
                location_type=LocationType.LOCAL
            )]

            complete_called = [False]
            complete_results = [None]

            def on_complete(results):
                complete_called[0] = True
                complete_results[0] = results

            uninstaller = LocalUninstaller()
            uninstaller.uninstall_batch(dumps, on_complete=on_complete)

            assert complete_called[0] is True
            assert len(complete_results[0]) == 1

    def test_uninstall_batch_cancel(self):
        """Test cancelling batch uninstall."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dumps = []
            for i in range(3):
                dump_path = Path(tmpdir) / f"game{i}"
                dump_path.mkdir()
                (dump_path / "dump_runner.elf").write_bytes(b"elf")
                dumps.append(GameDump(
                    path=str(dump_path),
                    name=f"game{i}",
                    location_type=LocationType.LOCAL
                ))

            uninstaller = LocalUninstaller()

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

            # First dump completes, remaining are marked cancelled
            assert len(results) == 3
            # First result shows cancelled status
            assert results[0].error_message == "Uninstall cancelled"
            assert results[1].error_message == "Uninstall cancelled"
            assert results[2].error_message == "Uninstall cancelled"

    def test_uninstall_batch_mixed_results(self):
        """Test batch with some failures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create one valid dump
            valid_dump = Path(tmpdir) / "valid"
            valid_dump.mkdir()
            (valid_dump / "dump_runner.elf").write_bytes(b"elf")

            dumps = [
                GameDump(path=str(valid_dump), name="valid", location_type=LocationType.LOCAL),
                GameDump(path="/nonexistent/path", name="invalid", location_type=LocationType.LOCAL),
            ]

            uninstaller = LocalUninstaller()
            results = uninstaller.uninstall_batch(dumps)

            assert len(results) == 2
            assert results[0].success is True
            assert results[1].success is False

    def test_get_batch_summary(self):
        """Test batch summary generation."""
        results = [
            UninstallResult(dump_path="/game1", success=True, duration_seconds=0.1),
            UninstallResult(dump_path="/game2", success=True, duration_seconds=0.1),
            UninstallResult(dump_path="/game3", success=False, error_message="Error", duration_seconds=0.1),
        ]

        uninstaller = LocalUninstaller()
        summary = uninstaller.get_batch_summary(results)

        assert summary["total"] == 3
        assert summary["successful"] == 2
        assert summary["failed"] == 1
        assert summary["duration_seconds"] == pytest.approx(0.3)
        assert len(summary["failures"]) == 1
        assert summary["failures"][0] == ("/game3", "Error")
