"""FTP LIST command output parser.

Parses Unix-style LIST command output to extract directory names.
Used as fallback when NLST command is not supported by FTP server.
"""

import logging
import re
from typing import List

logger = logging.getLogger("ps5_dump_runner.list_parser")


def parse_list_output(list_output: str) -> List[str]:
    """
    Parse Unix-style LIST command output to extract directory names.

    The LIST command returns full directory listings with metadata in this format:
    drwxr-xr-x  2 user group 4096 Jan  1 12:00 dirname

    This function extracts only the directory names, ignoring files and metadata.

    Args:
        list_output: Raw output from FTP LIST command

    Returns:
        List of directory names (excluding files)

    Examples:
        >>> output = "drwxr-xr-x  2 root root 4096 Jan  1 12:00 CUSA12345\\n"
        >>> parse_list_output(output)
        ['CUSA12345']

        >>> output = "-rw-r--r--  1 root root 1024 Jan  1 12:00 file.txt\\n"
        >>> parse_list_output(output)  # Files are ignored
        []
    """
    directories = []

    if not list_output or not list_output.strip():
        logger.debug("LIST output is empty")
        return directories

    lines = list_output.strip().split('\n')
    logger.debug(f"Parsing {len(lines)} lines from LIST output")

    for line in lines:
        # Skip empty lines
        if not line.strip():
            continue

        # Parse Unix-style LIST output
        # Format: drwxr-xr-x  2 user group 4096 Jan  1 12:00 dirname
        # First character 'd' indicates directory, '-' indicates file

        parts = line.split()

        # Need at least: permissions user group size month day time name
        if len(parts) < 8:
            logger.debug(f"Skipping malformed line: {line}")
            continue

        permissions = parts[0]

        # Check if this is a directory (starts with 'd')
        if not permissions.startswith('d'):
            logger.debug(f"Skipping non-directory: {line}")
            continue

        # Directory name is the last part (may contain spaces)
        # Join all parts after the timestamp to handle names with spaces
        # Format: permissions links user group size month day time name [name...]
        dirname = ' '.join(parts[8:])

        # Skip . and .. special directories
        if dirname in ('.', '..'):
            logger.debug(f"Skipping special directory: {dirname}")
            continue

        directories.append(dirname)
        logger.debug(f"Found directory: {dirname}")

    logger.info(f"Parsed {len(directories)} directories from LIST output")
    return directories


def parse_list_output_flexible(list_output: str) -> List[str]:
    """
    Parse LIST output with flexible format detection.

    Handles various FTP server LIST formats:
    - Unix-style (most common): drwxr-xr-x  2 user group 4096 Jan  1 12:00 dirname
    - Windows-style: 01-01-2024  12:00PM       <DIR>          dirname
    - Simplified: drwxr-xr-x dirname

    Args:
        list_output: Raw output from FTP LIST command

    Returns:
        List of directory names
    """
    directories = []

    if not list_output or not list_output.strip():
        return directories

    lines = list_output.strip().split('\n')

    for line in lines:
        if not line.strip():
            continue

        # Try Unix-style format first (most common)
        if line.startswith('d'):
            parts = line.split()
            if len(parts) >= 8:
                dirname = ' '.join(parts[8:])
                if dirname not in ('.', '..'):
                    directories.append(dirname)
                    continue

        # Try Windows-style format
        if '<DIR>' in line:
            # Format: MM-DD-YYYY  HH:MMAM/PM       <DIR>          dirname
            parts = line.split('<DIR>')
            if len(parts) >= 2:
                dirname = parts[1].strip()
                if dirname and dirname not in ('.', '..'):
                    directories.append(dirname)
                    continue

        # Try simplified format (permissions + name only)
        match = re.match(r'^d[rwx-]{9}\s+(.+)$', line)
        if match:
            dirname = match.group(1).strip()
            if dirname not in ('.', '..'):
                directories.append(dirname)
                continue

        logger.debug(f"Could not parse line format: {line}")

    logger.info(f"Parsed {len(directories)} directories from LIST output (flexible mode)")
    return directories
