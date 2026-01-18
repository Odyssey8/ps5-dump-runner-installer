"""Path constants and discovery for PS5 Dump Runner FTP Installer.

Defines PS5 FTP scan paths and application data directories.
"""

import os
import sys
from pathlib import Path
from typing import List


# Application name for config directories
APP_NAME = "PS5DumpRunnerInstaller"


# PS5 FTP scan paths (directories containing game dumps)
SCAN_PATHS: List[str] = [
    # Internal storage - homebrew
    "/data/homebrew/",
    # Internal storage - etaHEN
    "/data/etaHEN/games/",
    # USB storage devices (usb0-usb7) - homebrew
    *[f"/mnt/usb{i}/homebrew/" for i in range(8)],
    # USB storage devices (usb0-usb6) - etaHEN
    *[f"/mnt/usb{i}/etaHEN/games/" for i in range(7)],
    # Extended storage devices (ext0-ext7) - homebrew
    *[f"/mnt/ext{i}/homebrew/" for i in range(8)],
    # Extended storage devices (ext0-ext1) - etaHEN
    *[f"/mnt/ext{i}/etaHEN/games/" for i in range(2)],
]


# Files to upload to each dump
DUMP_RUNNER_FILES = [
    "dump_runner.elf",
    "homebrew.js",
]


def get_app_data_dir() -> Path:
    """
    Get the application data directory.

    Returns:
        Path to app data directory (created if not exists)

    Platform-specific locations:
        - Windows: %APPDATA%/PS5DumpRunnerInstaller
        - Linux: ~/.config/PS5DumpRunnerInstaller
        - macOS: ~/Library/Application Support/PS5DumpRunnerInstaller
    """
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))

    app_dir = base / APP_NAME
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def get_settings_path() -> Path:
    """
    Get the path to the settings JSON file.

    Returns:
        Path to settings.json
    """
    return get_app_data_dir() / "settings.json"


def get_cache_dir() -> Path:
    """
    Get the cache directory for downloaded releases.

    Returns:
        Path to cache directory (created if not exists)
    """
    cache_dir = get_app_data_dir() / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def get_releases_cache_dir() -> Path:
    """
    Get the directory for cached release downloads.

    Returns:
        Path to releases cache directory (created if not exists)
    """
    releases_dir = get_cache_dir() / "releases"
    releases_dir.mkdir(parents=True, exist_ok=True)
    return releases_dir


def get_log_dir() -> Path:
    """
    Get the directory for log files.

    Returns:
        Path to logs directory (created if not exists)
    """
    log_dir = get_app_data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_log_file_path() -> Path:
    """
    Get the path to the main log file.

    Returns:
        Path to application log file
    """
    return get_log_dir() / "app.log"


def get_location_type_from_path(ftp_path: str) -> str:
    """
    Determine the location type from an FTP path.

    Args:
        ftp_path: FTP path to analyze

    Returns:
        Specific location type string:
        - 'internal' for /data/ paths
        - 'usb0' through 'usb7' for specific USB storage devices
        - 'ext0' or 'ext1' for specific external storage devices
        - 'usb' or 'external' as fallback for unrecognized device numbers
        - 'unknown' for unrecognized paths

    Supports both homebrew and etaHEN paths:
        - /data/homebrew/ and /data/etaHEN/games/ -> 'internal'
        - /mnt/usb#/homebrew/ and /mnt/usb#/etaHEN/games/ -> 'usb#'
        - /mnt/ext#/homebrew/ and /mnt/ext#/etaHEN/games/ -> 'ext#'
    """
    import re

    if ftp_path.startswith("/data/"):
        return "internal"
    elif ftp_path.startswith("/mnt/usb"):
        # Extract USB device number (usb0-usb7)
        match = re.match(r"/mnt/usb(\d+)", ftp_path)
        if match:
            device_num = int(match.group(1))
            if 0 <= device_num <= 7:
                return f"usb{device_num}"
        return "usb"  # Fallback for unrecognized device number
    elif ftp_path.startswith("/mnt/ext"):
        # Extract external device number (ext0-ext1)
        match = re.match(r"/mnt/ext(\d+)", ftp_path)
        if match:
            device_num = int(match.group(1))
            if 0 <= device_num <= 1:
                return f"ext{device_num}"
        return "external"  # Fallback for unrecognized device number
    else:
        return "unknown"
