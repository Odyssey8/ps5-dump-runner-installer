"""Local uninstaller for PS5 Dump Runner Installer.

Handles removing dump_runner files from local game dump directories.
"""

import logging
import threading
import time
from pathlib import Path
from typing import Callable, List, Optional

from src.ftp.scanner import GameDump
from src.models.uninstall import UninstallProgress, UninstallResult

logger = logging.getLogger("ps5_dump_runner.local_uninstaller")

# Type aliases for callbacks
ProgressCallback = Callable[[UninstallProgress], None]
CompleteCallback = Callable[[List[UninstallResult]], None]


class LocalUninstaller:
    """Handles file deletion from local game dumps.

    Implements the UninstallerProtocol for local filesystem operations.
    Uses Path.unlink(missing_ok=True) for safe deletion.
    """

    def __init__(self):
        """Initialize the local uninstaller."""
        self._cancelled = threading.Event()

    @property
    def is_cancelled(self) -> bool:
        """True if current operation was cancelled."""
        return self._cancelled.is_set()

    def cancel(self) -> None:
        """Cancel current uninstall operation."""
        self._cancelled.set()
        logger.info("Local uninstall operation cancelled by user")

    def reset_cancel(self) -> None:
        """Reset cancellation flag for new operation."""
        self._cancelled.clear()

    def uninstall_from_dump(self, dump: GameDump) -> UninstallResult:
        """Uninstall dump_runner files from a single game dump.

        Args:
            dump: Target game dump

        Returns:
            UninstallResult with operation outcome
        """
        start_time = time.time()
        elf_deleted = False
        js_deleted = False

        logger.info(f"Starting local uninstall from {dump.display_name}")

        dump_path = Path(dump.path)

        # Verify dump directory exists
        if not dump_path.exists():
            duration = time.time() - start_time
            error_msg = f"Directory does not exist: {dump.path}"
            logger.error(error_msg)
            return UninstallResult(
                dump_path=dump.path,
                success=False,
                error_message=error_msg,
                duration_seconds=duration
            )

        if not dump_path.is_dir():
            duration = time.time() - start_time
            error_msg = f"Path is not a directory: {dump.path}"
            logger.error(error_msg)
            return UninstallResult(
                dump_path=dump.path,
                success=False,
                error_message=error_msg,
                duration_seconds=duration
            )

        try:
            # Delete dump_runner.elf
            if not self._cancelled.is_set():
                elf_path = dump_path / "dump_runner.elf"
                if elf_path.exists():
                    elf_path.unlink()
                    elf_deleted = True
                    logger.debug(f"Deleted dump_runner.elf from {dump.display_name}")
                else:
                    logger.debug(f"dump_runner.elf not found in {dump.display_name}")

            # Delete homebrew.js
            if not self._cancelled.is_set():
                js_path = dump_path / "homebrew.js"
                if js_path.exists():
                    js_path.unlink()
                    js_deleted = True
                    logger.debug(f"Deleted homebrew.js from {dump.display_name}")
                else:
                    logger.debug(f"homebrew.js not found in {dump.display_name}")

            duration = time.time() - start_time

            if self._cancelled.is_set():
                logger.warning(f"Uninstall from {dump.display_name} cancelled")
                return UninstallResult(
                    dump_path=dump.path,
                    success=False,
                    error_message="Uninstall cancelled",
                    elf_deleted=elf_deleted,
                    js_deleted=js_deleted,
                    duration_seconds=duration
                )

            logger.info(f"Uninstall from {dump.display_name} completed successfully")
            return UninstallResult(
                dump_path=dump.path,
                success=True,
                elf_deleted=elf_deleted,
                js_deleted=js_deleted,
                duration_seconds=duration
            )

        except PermissionError as e:
            duration = time.time() - start_time
            error_msg = f"Permission denied: Cannot delete files in {dump.path}"
            logger.error(f"Permission error for {dump.display_name}: {e}")
            return UninstallResult(
                dump_path=dump.path,
                success=False,
                error_message=error_msg,
                elf_deleted=elf_deleted,
                js_deleted=js_deleted,
                duration_seconds=duration
            )

        except OSError as e:
            duration = time.time() - start_time
            # Check for common OSError causes
            if "Read-only file system" in str(e):
                error_msg = "Drive is read-only. Cannot delete files."
            else:
                error_msg = f"File system error: {str(e)}"

            logger.error(f"OS error for {dump.display_name}: {e}")
            return UninstallResult(
                dump_path=dump.path,
                success=False,
                error_message=error_msg,
                elf_deleted=elf_deleted,
                js_deleted=js_deleted,
                duration_seconds=duration
            )

        except Exception as e:
            duration = time.time() - start_time
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(f"Unexpected error for {dump.display_name}: {e}", exc_info=True)
            return UninstallResult(
                dump_path=dump.path,
                success=False,
                error_message=error_msg,
                elf_deleted=elf_deleted,
                js_deleted=js_deleted,
                duration_seconds=duration
            )

    def uninstall_batch(
        self,
        dumps: List[GameDump],
        on_progress: Optional[ProgressCallback] = None,
        on_complete: Optional[CompleteCallback] = None
    ) -> List[UninstallResult]:
        """Uninstall from multiple game dumps with progress reporting.

        Args:
            dumps: List of GameDump objects to uninstall from
            on_progress: Callback invoked with UninstallProgress after each dump
            on_complete: Callback invoked when all dumps processed

        Returns:
            List of UninstallResult for each dump
        """
        self.reset_cancel()
        results: List[UninstallResult] = []

        for i, dump in enumerate(dumps):
            if self._cancelled.is_set():
                # Add cancelled result for remaining dumps
                results.append(UninstallResult(
                    dump_path=dump.path,
                    success=False,
                    error_message="Uninstall cancelled"
                ))
                continue

            # Report progress before starting this dump
            if on_progress:
                progress = UninstallProgress(
                    current_dump=dump,
                    current_file="dump_runner.elf",
                    dumps_completed=i,
                    dumps_total=len(dumps)
                )
                on_progress(progress)

            # Uninstall from this dump
            result = self.uninstall_from_dump(dump)
            results.append(result)

            # Report progress after completing this dump
            if on_progress:
                progress = UninstallProgress(
                    current_dump=dump,
                    current_file="",
                    dumps_completed=i + 1,
                    dumps_total=len(dumps)
                )
                on_progress(progress)

        # Call completion callback
        if on_complete:
            on_complete(results)

        return results

    def get_batch_summary(self, results: List[UninstallResult]) -> dict:
        """Get summary statistics for a batch uninstall.

        Args:
            results: List of uninstall results

        Returns:
            Dictionary with summary statistics
        """
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        total_time = sum(r.duration_seconds for r in results)

        return {
            "total": len(results),
            "successful": len(successful),
            "failed": len(failed),
            "duration_seconds": total_time,
            "failures": [(r.dump_path, r.error_message) for r in failed]
        }
