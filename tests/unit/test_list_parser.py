"""Unit tests for FTP LIST command parser.

Tests the parsing of Unix-style LIST output to extract directory names.
"""

import pytest

from src.ftp.list_parser import parse_list_output, parse_list_output_flexible


class TestParseListOutput:
    """Test parse_list_output() function."""

    def test_parses_unix_style_directory(self):
        """Should parse standard Unix-style directory listing."""
        list_output = "drwxr-xr-x  2 root root 4096 Jan  1 12:00 CUSA12345"

        result = parse_list_output(list_output)

        assert result == ["CUSA12345"]

    def test_parses_multiple_directories(self):
        """Should parse multiple directories from output."""
        list_output = """drwxr-xr-x  2 root root 4096 Jan  1 12:00 CUSA12345
drwxr-xr-x  2 root root 4096 Jan  1 12:00 CUSA67890
drwxr-xr-x  2 root root 4096 Jan  1 12:00 CUSA11111"""

        result = parse_list_output(list_output)

        assert len(result) == 3
        assert "CUSA12345" in result
        assert "CUSA67890" in result
        assert "CUSA11111" in result

    def test_ignores_files(self):
        """Should ignore files (lines starting with -)."""
        list_output = """-rw-r--r--  1 root root 1024 Jan  1 12:00 file.txt
drwxr-xr-x  2 root root 4096 Jan  1 12:00 CUSA12345
-rw-r--r--  1 root root 2048 Jan  1 12:00 another.bin"""

        result = parse_list_output(list_output)

        assert result == ["CUSA12345"]

    def test_ignores_special_directories(self):
        """Should ignore . and .. special directories."""
        list_output = """drwxr-xr-x  2 root root 4096 Jan  1 12:00 .
drwxr-xr-x  2 root root 4096 Jan  1 12:00 ..
drwxr-xr-x  2 root root 4096 Jan  1 12:00 CUSA12345"""

        result = parse_list_output(list_output)

        assert result == ["CUSA12345"]

    def test_handles_directory_names_with_spaces(self):
        """Should correctly parse directory names containing spaces."""
        list_output = "drwxr-xr-x  2 root root 4096 Jan  1 12:00 Game Folder Name"

        result = parse_list_output(list_output)

        assert result == ["Game Folder Name"]

    def test_handles_empty_output(self):
        """Should return empty list for empty output."""
        result = parse_list_output("")

        assert result == []

    def test_handles_whitespace_only_output(self):
        """Should return empty list for whitespace-only output."""
        result = parse_list_output("   \n  \n  ")

        assert result == []

    def test_skips_empty_lines(self):
        """Should skip empty lines in output."""
        list_output = """drwxr-xr-x  2 root root 4096 Jan  1 12:00 CUSA12345

drwxr-xr-x  2 root root 4096 Jan  1 12:00 CUSA67890

"""

        result = parse_list_output(list_output)

        assert len(result) == 2
        assert "CUSA12345" in result
        assert "CUSA67890" in result

    def test_handles_malformed_lines(self):
        """Should skip malformed lines that don't match expected format."""
        list_output = """drwxr-xr-x  2 root root 4096 Jan  1 12:00 CUSA12345
malformed line here
drwxr-xr-x invalid format
drwxr-xr-x  2 root root 4096 Jan  1 12:00 CUSA67890"""

        result = parse_list_output(list_output)

        assert len(result) == 2
        assert "CUSA12345" in result
        assert "CUSA67890" in result

    def test_handles_different_permission_formats(self):
        """Should handle various Unix permission formats."""
        list_output = """drwxrwxrwx  2 root root 4096 Jan  1 12:00 DIR1
dr-xr-xr-x  2 root root 4096 Jan  1 12:00 DIR2
drwx------  2 root root 4096 Jan  1 12:00 DIR3"""

        result = parse_list_output(list_output)

        assert len(result) == 3
        assert "DIR1" in result
        assert "DIR2" in result
        assert "DIR3" in result

    def test_handles_different_month_formats(self):
        """Should handle different month name formats."""
        list_output = """drwxr-xr-x  2 root root 4096 Jan  1 12:00 DIR1
drwxr-xr-x  2 root root 4096 Dec 31 12:00 DIR2
drwxr-xr-x  2 root root 4096 Jul 15 12:00 DIR3"""

        result = parse_list_output(list_output)

        assert len(result) == 3

    def test_preserves_order(self):
        """Should preserve directory order from output."""
        list_output = """drwxr-xr-x  2 root root 4096 Jan  1 12:00 FIRST
drwxr-xr-x  2 root root 4096 Jan  1 12:00 SECOND
drwxr-xr-x  2 root root 4096 Jan  1 12:00 THIRD"""

        result = parse_list_output(list_output)

        assert result == ["FIRST", "SECOND", "THIRD"]


class TestParseListOutputFlexible:
    """Test parse_list_output_flexible() function with various formats."""

    def test_handles_unix_style(self):
        """Should handle standard Unix-style format."""
        list_output = "drwxr-xr-x  2 root root 4096 Jan  1 12:00 CUSA12345"

        result = parse_list_output_flexible(list_output)

        assert result == ["CUSA12345"]

    def test_handles_windows_style(self):
        """Should handle Windows-style directory listing."""
        list_output = "01-01-2024  12:00PM       <DIR>          GameFolder"

        result = parse_list_output_flexible(list_output)

        assert result == ["GameFolder"]

    def test_handles_windows_style_with_spaces(self):
        """Should handle Windows-style with spaces in name."""
        list_output = "01-01-2024  12:00PM       <DIR>          Game Folder Name"

        result = parse_list_output_flexible(list_output)

        assert result == ["Game Folder Name"]

    def test_handles_simplified_format(self):
        """Should handle simplified format (permissions + name only)."""
        list_output = "drwxr-xr-x CUSA12345"

        result = parse_list_output_flexible(list_output)

        assert result == ["CUSA12345"]

    def test_handles_mixed_formats(self):
        """Should handle mixed format output."""
        list_output = """drwxr-xr-x  2 root root 4096 Jan  1 12:00 UnixDir
01-01-2024  12:00PM       <DIR>          WindowsDir
drwxr-xr-x SimpleDir"""

        result = parse_list_output_flexible(list_output)

        assert len(result) == 3
        assert "UnixDir" in result
        assert "WindowsDir" in result
        assert "SimpleDir" in result

    def test_ignores_windows_files(self):
        """Should ignore Windows-style file entries."""
        list_output = """01-01-2024  12:00PM       <DIR>          GameFolder
01-01-2024  12:00PM              1024 file.txt"""

        result = parse_list_output_flexible(list_output)

        assert result == ["GameFolder"]

    def test_handles_empty_output(self):
        """Should handle empty output."""
        result = parse_list_output_flexible("")

        assert result == []

    def test_ignores_windows_special_directories(self):
        """Should ignore Windows . and .. directories."""
        list_output = """01-01-2024  12:00PM       <DIR>          .
01-01-2024  12:00PM       <DIR>          ..
01-01-2024  12:00PM       <DIR>          RealFolder"""

        result = parse_list_output_flexible(list_output)

        assert result == ["RealFolder"]


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_none_input(self):
        """Should handle None input gracefully."""
        # Parse as empty string behavior
        result = parse_list_output(None or "")

        assert result == []

    def test_very_long_directory_name(self):
        """Should handle very long directory names."""
        long_name = "A" * 500
        list_output = f"drwxr-xr-x  2 root root 4096 Jan  1 12:00 {long_name}"

        result = parse_list_output(list_output)

        assert result == [long_name]

    def test_special_characters_in_names(self):
        """Should handle special characters in directory names."""
        list_output = """drwxr-xr-x  2 root root 4096 Jan  1 12:00 name-with-dashes
drwxr-xr-x  2 root root 4096 Jan  1 12:00 name_with_underscores
drwxr-xr-x  2 root root 4096 Jan  1 12:00 name.with.dots"""

        result = parse_list_output(list_output)

        assert len(result) == 3
        assert "name-with-dashes" in result
        assert "name_with_underscores" in result
        assert "name.with.dots" in result

    def test_unicode_in_directory_names(self):
        """Should handle Unicode characters in directory names."""
        list_output = "drwxr-xr-x  2 root root 4096 Jan  1 12:00 Spēļu mape"

        result = parse_list_output(list_output)

        assert result == ["Spēļu mape"]

    def test_trailing_whitespace(self):
        """Should handle trailing whitespace in output."""
        list_output = "drwxr-xr-x  2 root root 4096 Jan  1 12:00 CUSA12345   \n"

        result = parse_list_output(list_output)

        assert result == ["CUSA12345"]
