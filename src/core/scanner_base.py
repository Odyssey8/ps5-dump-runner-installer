"""Base interfaces and enums for scanner and uploader implementations.

Provides abstract interfaces that allow the UI to work with both FTP and
local filesystem operations through a common API.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Callable, List, Optional, Protocol

if TYPE_CHECKING:
    from src.ftp.scanner import GameDump


class ScanMode(Enum):
    """Operating mode of the application."""

    FTP = "ftp"
    """Connected to PS5 via FTP."""

    LOCAL = "local"
    """Scanning local/portable drive."""


@dataclass
class UploadResult:
    """Result of an upload operation."""

    dump_path: str
    """Path to the game dump."""

    success: bool
    """Whether the upload succeeded."""

    error_message: Optional[str] = None
    """Error message if upload failed."""


class ScannerProtocol(Protocol):
    """Abstract interface for scanner implementations.

    Both DumpScanner (FTP) and LocalScanner implement this interface,
    allowing the UI to work with either mode through the same API.
    """

    @property
    def dumps(self) -> List["GameDump"]:
        """List of discovered dumps from last scan."""
        ...

    @property
    def last_scan(self) -> Optional[datetime]:
        """Timestamp of last scan."""
        ...

    def scan(self) -> List["GameDump"]:
        """
        Scan configured paths for game dumps.

        Returns:
            List of discovered GameDump objects
        """
        ...

    def refresh(self, dump: "GameDump") -> "GameDump":
        """
        Refresh status of a single dump.

        Args:
            dump: GameDump to refresh

        Returns:
            Updated GameDump with current status
        """
        ...


# Type aliases for callbacks (using Any to allow flexibility for different implementations)
from typing import Any
ProgressCallback = Callable[..., None]
"""Callback for progress updates (implementation-specific)"""

CompletionCallback = Callable[["GameDump", UploadResult], None]
"""Callback when a single dump upload completes."""


class UploaderProtocol(Protocol):
    """Abstract interface for uploader implementations.

    Both FileUploader (FTP) and LocalUploader implement this interface,
    allowing the UI to work with either mode through the same API.
    """

    @property
    def is_cancelled(self) -> bool:
        """True if upload has been cancelled."""
        ...

    def upload_to_dump(
        self,
        dump: "GameDump",
        elf_path: str,
        js_path: str,
        on_progress: Optional[ProgressCallback] = None,
    ) -> UploadResult:
        """
        Upload dump_runner files to a single game dump.

        Args:
            dump: Target GameDump
            elf_path: Path to dump_runner.elf file
            js_path: Path to homebrew.js file
            on_progress: Optional callback for progress updates

        Returns:
            UploadResult indicating success or failure
        """
        ...

    def upload_batch(
        self,
        dumps: List["GameDump"],
        elf_path: str,
        js_path: str,
        on_progress: Optional[ProgressCallback] = None,
        on_complete: Optional[CompletionCallback] = None,
    ) -> List[UploadResult]:
        """
        Upload dump_runner files to multiple game dumps.

        Args:
            dumps: List of target GameDumps
            elf_path: Path to dump_runner.elf file
            js_path: Path to homebrew.js file
            on_progress: Optional callback for progress updates
            on_complete: Optional callback when each dump completes

        Returns:
            List of UploadResult for each dump
        """
        ...

    def cancel(self) -> None:
        """Cancel any ongoing upload operation."""
        ...
