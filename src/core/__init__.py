"""Core module for shared abstractions and interfaces.

This module provides:
- ScanMode: Operating mode enumeration (FTP vs Local)
- ScannerProtocol: Abstract interface for scanner implementations
- UploaderProtocol: Abstract interface for uploader implementations
"""

from src.core.scanner_base import ScanMode, ScannerProtocol, UploaderProtocol

__all__ = ["ScanMode", "ScannerProtocol", "UploaderProtocol"]
