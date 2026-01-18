"""FTP uninstaller for PS5 Dump Runner Installer.

Handles removing dump_runner files from game dumps via FTP.
"""

import logging
import threading
import time
from ftplib import error_perm, error_reply
from typing import Callable, List, Optional

from src.ftp.connection import FTPConnectionManager
from src.ftp.scanner import GameDump
from src.models.uninstall import UninstallProgress, UninstallResult

logger = logging.getLogger("ps5_dump_runner.ftp_uninstaller")

# Type aliases for callbacks
ProgressCallback = Callable[[UninstallProgress], None]
CompleteCallback = Callable[[List[UninstallResult]], None]


class FTPUninstaller:
    """Handles file deletion from game dumps via FTP.

    Implements the UninstallerProtocol for FTP operations.
    Uses CWD+DELETE pattern to handle special characters in paths.
    """

    def __init__(self, connection: FTPConnectionManager):
        """Initialize the uninstaller.

        Args:
            connection: Active FTP connection manager
        """
        self._connection = connection
        self._cancelled = threading.Event()

    @property
    def is_cancelled(self) -> bool:
        """True if current operation was cancelled."""
        return self._cancelled.is_set()

    def cancel(self) -> None:
        """Cancel current uninstall operation."""
        self._cancelled.set()
        logger.info("Uninstall operation cancelled by user")

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

        logger.info(f"Starting uninstall from {dump.display_name}")

        if not self._connection.is_connected:
            return UninstallResult(
                dump_path=dump.path,
                success=False,
                error_message="Not connected to FTP"
            )

        try:
            ftp = self._connection.ftp

            # Save current directory
            current_dir = ftp.pwd()

            try:
                # Change to dump directory
                ftp.cwd(dump.path)

                # Delete dump_runner.elf
                if not self._cancelled.is_set():
                    try:
                        ftp.delete("dump_runner.elf")
                        elf_deleted = True
                        logger.debug(f"Deleted dump_runner.elf from {dump.display_name}")
                    except error_reply as e:
                        # 226 = file deleted (success, but some servers raise it as exception)
                        if "226" in str(e):
                            elf_deleted = True
                            logger.debug(f"Deleted dump_runner.elf from {dump.display_name}")
                        else:
                            raise
                    except error_perm as e:
                        # 550 = file not found, treat as success
                        if "550" in str(e):
                            logger.debug(f"dump_runner.elf not found in {dump.display_name}")
                        else:
                            raise

                # Delete homebrew.js
                if not self._cancelled.is_set():
                    try:
                        ftp.delete("homebrew.js")
                        js_deleted = True
                        logger.debug(f"Deleted homebrew.js from {dump.display_name}")
                    except error_reply as e:
                        # 226 = file deleted (success, but some servers raise it as exception)
                        if "226" in str(e):
                            js_deleted = True
                            logger.debug(f"Deleted homebrew.js from {dump.display_name}")
                        else:
                            raise
                    except error_perm as e:
                        # 550 = file not found, treat as success
                        if "550" in str(e):
                            logger.debug(f"homebrew.js not found in {dump.display_name}")
                        else:
                            raise

            finally:
                # Restore original directory
                try:
                    ftp.cwd(current_dir)
                except Exception:
                    pass

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

        except error_reply as e:
            duration = time.time() - start_time
            error_msg = str(e)

            # 226 = success response, treat as success
            if "226" in error_msg:
                logger.info(f"Uninstall from {dump.display_name} completed successfully")
                return UninstallResult(
                    dump_path=dump.path,
                    success=True,
                    elf_deleted=elf_deleted,
                    js_deleted=js_deleted,
                    duration_seconds=duration
                )

            logger.error(f"Uninstall from {dump.display_name} failed: {error_msg}")
            return UninstallResult(
                dump_path=dump.path,
                success=False,
                error_message=error_msg,
                elf_deleted=elf_deleted,
                js_deleted=js_deleted,
                duration_seconds=duration
            )

        except error_perm as e:
            duration = time.time() - start_time
            error_msg = str(e)

            # 530 = not logged in (connection lost)
            if "530" in error_msg:
                error_msg = "Connection lost - not logged in"

            logger.error(f"Uninstall from {dump.display_name} failed: {error_msg}")
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
            logger.error(f"Uninstall from {dump.display_name} failed: {e}")
            return UninstallResult(
                dump_path=dump.path,
                success=False,
                error_message=str(e),
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
