"""Data models for uninstall operations.

Provides dataclasses for tracking uninstall operation results and progress.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from src.ftp.scanner import GameDump


@dataclass
class UninstallResult:
    """Result of an uninstall operation for a single game dump.

    Attributes:
        dump_path: Full path to the game dump directory
        success: Whether the uninstall completed successfully
        error_message: Error description if failed
        elf_deleted: Whether dump_runner.elf was deleted
        js_deleted: Whether homebrew.js was deleted
        duration_seconds: Time taken for this uninstall
    """

    dump_path: str
    """Full path to the game dump directory."""

    success: bool
    """Whether the uninstall completed successfully."""

    error_message: Optional[str] = None
    """Error description if failed."""

    elf_deleted: bool = False
    """Whether dump_runner.elf was deleted."""

    js_deleted: bool = False
    """Whether homebrew.js was deleted."""

    duration_seconds: float = 0.0
    """Time taken for this uninstall."""


@dataclass
class UninstallProgress:
    """Progress information during a batch uninstall operation.

    Attributes:
        current_dump: The game currently being processed
        current_file: File currently being deleted
        dumps_completed: Number of dumps fully processed
        dumps_total: Total number of dumps to process
    """

    current_dump: "GameDump"
    """The game currently being processed."""

    current_file: str
    """File currently being deleted ('dump_runner.elf' or 'homebrew.js')."""

    dumps_completed: int
    """Number of dumps fully processed."""

    dumps_total: int
    """Total number of dumps to process."""

    @property
    def percent_complete(self) -> float:
        """Calculate completion percentage.

        Returns:
            Percentage complete (0-100)
        """
        if self.dumps_total == 0:
            return 0.0
        return (self.dumps_completed / self.dumps_total) * 100.0
