"""Tests for tab_phrase_animator.tab_text_parser module."""

import os
import tempfile
from unittest.mock import patch
import pytest

from tab_phrase_animator.tab_text_parser import (
    TabTextParser,
    ParseConfig,
    ParseStatistics,
    TabTextParserError,
)


class TestParseConfig:
    """Test ParseConfig dataclass."""

    def test_parse_config_default_values(self):
        """Test ParseConfig with default values."""
        config = ParseConfig()

        assert config.allow_empty_pages is False
        assert config.allow_empty_chords is True
        assert config.validate_hole_numbers is True
        assert config.min_hole == 1
        assert config.max_hole == 10
        assert config.encoding == "utf-8"

    def test_parse_config_custom_values(self):
        """Test ParseConfig with custom values."""
        config = ParseConfig(
            allow_empty_pages=True,
            allow_empty_chords=False,
            validate_hole_numbers=False,
            min_hole=2,
            max_hole=8,
            encoding="latin-1",
        )

        assert config.allow_empty_pages is True
        assert config.allow_empty_chords is False
        assert config.validate_hole_numbers is False
        assert config.min_hole == 2
        assert config.max_hole == 8
        assert config.encoding == "latin-1"

    def test_parse_config_edge_cases(self):
        """Test ParseConfig with edge case values."""
        # Very restrictive range
        config = ParseConfig(min_hole=5, max_hole=5)
        assert config.min_hole == 5
        assert config.max_hole == 5

        # Wide range
        config_wide = ParseConfig(min_hole=1, max_hole=20)
        assert config_wide.min_hole == 1
        assert config_wide.max_hole == 20


class TestParseStatistics:
    """Test ParseStatistics dataclass."""

    def test_parse_statistics_creation(self):
        """Test ParseStatistics creation with all fields."""
        stats = ParseStatistics(
            total_pages=3,
            total_lines=15,
            total_chords=45,
            total_notes=120,
            empty_pages=1,
            invalid_lines=2,
            hole_range=(1, 8),
        )

        assert stats.total_pages == 3
        assert stats.total_lines == 15
        assert stats.total_chords == 45
        assert stats.total_notes == 120
        assert stats.empty_pages == 1
        assert stats.invalid_lines == 2
        assert stats.hole_range == (1, 8)

    def test_parse_statistics_zero_values(self):
        """Test ParseStatistics with zero values."""
        stats = ParseStatistics(
            total_pages=0,
            total_lines=0,
            total_chords=0,
            total_notes=0,
            empty_pages=0,
            invalid_lines=0,
            hole_range=(0, 0),
        )

        assert stats.total_pages == 0
        assert stats.total_lines == 0
        assert stats.total_chords == 0
        assert stats.total_notes == 0
        assert stats.empty_pages == 0
        assert stats.invalid_lines == 0
        assert stats.hole_range == (0, 0)


class TestTabTextParserInitialization:
    """Test TabTextParser initialization and file validation."""

    def test_tab_text_parser_file_not_found(self):
        """Test parser with non-existent file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            non_existent_file = os.path.join(temp_dir, "nonexistent.txt")

            with pytest.raises(TabTextParserError, match="Tab file not found"):
                TabTextParser(non_existent_file)

    def test_tab_text_parser_path_is_directory(self, temp_test_dir):
        """Test parser with directory path instead of file."""
        with pytest.raises(TabTextParserError, match="Path is not a file"):
            TabTextParser(str(temp_test_dir))

    @patch("builtins.open", side_effect=IOError("Permission denied"))
    def test_tab_text_parser_unreadable_file(self, mock_file, temp_test_dir):
        """Test parser with unreadable file."""
        test_file = temp_test_dir / "test.txt"
        test_file.write_text("Page 1:\n1 2 3")

        with pytest.raises(TabTextParserError, match="Cannot read tab file"):
            TabTextParser(str(test_file))

    @patch(
        "builtins.open", side_effect=UnicodeDecodeError("utf-8", b"", 0, 1, "invalid")
    )
    def test_tab_text_parser_encoding_error(self, mock_file, temp_test_dir):
        """Test parser with encoding error."""
        test_file = temp_test_dir / "test.txt"
        test_file.write_text("Page 1:\n1 2 3")

        with pytest.raises(TabTextParserError, match="Cannot read tab file"):
            TabTextParser(str(test_file))

    def test_tab_text_parser_custom_config(self, temp_test_dir):
        """Test parser with custom configuration."""
        test_file = temp_test_dir / "test.txt"
        test_file.write_text("Page 1:\n1 2 3")

        config = ParseConfig(allow_empty_pages=True, min_hole=2, max_hole=8)
        parser = TabTextParser(str(test_file), config)

        assert parser._config.allow_empty_pages is True
        assert parser._config.min_hole == 2
        assert parser._config.max_hole == 8


class TestTabTextParserBasicParsing:
    """Test basic tab file parsing functionality."""

    def test_parse_single_page_simple(self, temp_test_dir):
        """Test parsing a simple single-page tab file."""
        test_file = temp_test_dir / "simple.txt"
        test_file.write_text("Page 1:\n1 2 3\n-4 -5 -6")

        parser = TabTextParser(str(test_file))
        pages = parser.get_pages()

        assert len(pages) == 1
        assert "Page 1" in pages
        assert len(pages["Page 1"]) == 2  # Two lines

        # First line: three chords, each with one note
        line1 = pages["Page 1"][0]
        assert len(line1) == 3
        assert line1[0] == [1]
        assert line1[1] == [2]
        assert line1[2] == [3]

        # Second line: three chords with negative notes
        line2 = pages["Page 1"][1]
        assert len(line2) == 3
        assert line2[0] == [-4]
        assert line2[1] == [-5]
        assert line2[2] == [-6]

    def test_parse_multiple_pages(self, temp_test_dir):
        """Test parsing multiple pages."""
        test_file = temp_test_dir / "multi_page.txt"
        test_file.write_text("Page 1:\n1 2 3\n\nPage 2:\n-4 -5\n\nPage 3:\n6 7 8 9")

        parser = TabTextParser(str(test_file))
        pages = parser.get_pages()

        assert len(pages) == 3
        assert "Page 1" in pages
        assert "Page 2" in pages
        assert "Page 3" in pages

        # Verify page contents
        assert len(pages["Page 1"]) == 1
        assert len(pages["Page 2"]) == 1
        assert len(pages["Page 3"]) == 1

    def test_parse_complex_chords(self, temp_test_dir):
        """Test parsing complex chords with multiple notes."""
        test_file = temp_test_dir / "complex.txt"
        test_file.write_text("Page 1:\n123 -456 78 -91")

        parser = TabTextParser(str(test_file))
        pages = parser.get_pages()

        line = pages["Page 1"][0]
        assert len(line) == 4

        # First chord: 1, 2, 3 (blow chord)
        assert line[0] == [1, 2, 3]

        # Second chord: -4, -5, -6 (draw chord)
        assert line[1] == [-4, -5, -6]

        # Third chord: 7, 8 (blow chord)
        assert line[2] == [7, 8]

        # Fourth chord: -9, -1 (draw chord)
        assert line[3] == [-9, -1]

    def test_parse_mixed_format(self, temp_test_dir):
        """Test parsing mixed positive and negative notes."""
        test_file = temp_test_dir / "mixed.txt"
        test_file.write_text("Page 1:\n1 -2 34 -56 7")

        parser = TabTextParser(str(test_file))
        pages = parser.get_pages()

        line = pages["Page 1"][0]
        assert len(line) == 5
        assert line[0] == [1]
        assert line[1] == [-2]
        assert line[2] == [3, 4]
        assert line[3] == [-5, -6]
        assert line[4] == [7]

    def test_parse_empty_lines_ignored(self, temp_test_dir):
        """Test that empty lines are ignored."""
        test_file = temp_test_dir / "empty_lines.txt"
        test_file.write_text("Page 1:\n\n1 2 3\n\n\n-4 -5\n\n")

        parser = TabTextParser(str(test_file))
        pages = parser.get_pages()

        assert len(pages["Page 1"]) == 2  # Only non-empty lines counted


class TestTabTextParserAdvancedParsing:
    """Test advanced parsing scenarios and edge cases."""

    def test_parse_page_header_variations(self, temp_test_dir):
        """Test various page header formats."""
        test_file = temp_test_dir / "headers.txt"
        test_file.write_text(
            "page 1:\n1 2\nPage 2:\n3 4\nPAGE 3:\n5 6\npage intro:\n7 8"
        )

        parser = TabTextParser(str(test_file))
        pages = parser.get_pages()

        assert len(pages) == 4
        assert "page 1" in pages
        assert "Page 2" in pages
        assert "PAGE 3" in pages
        assert "page intro" in pages

    def test_parse_page_header_with_colon_removed(self, temp_test_dir):
        """Test that colons are removed from page headers."""
        test_file = temp_test_dir / "colon_headers.txt"
        test_file.write_text("Page 1:\n1 2\nPage 2::\n3 4")

        parser = TabTextParser(str(test_file))
        page_names = parser.get_page_names()

        assert "Page 1" in page_names
        assert "Page 2:" in page_names  # Only trailing colon removed

    def test_parse_comments_and_special_chars(self, temp_test_dir):
        """Test handling of comments and special characters."""
        test_file = temp_test_dir / "comments.txt"
        test_file.write_text("Page 1:\n1 2 # comment\n3@4!5 -6*7\n")

        parser = TabTextParser(str(test_file))
        pages = parser.get_pages()

        line1 = pages["Page 1"][0]
        line2 = pages["Page 1"][1]

        # Special characters should be ignored, only digits and spaces matter
        assert line1 == [[1], [2]]  # Comment ignored
        assert line2 == [[3, 4, 5], [-6, 7]]  # Special chars ignored

    def test_parse_hole_validation_enabled(self, temp_test_dir):
        """Test hole number validation when enabled."""
        test_file = temp_test_dir / "invalid_holes.txt"
        test_file.write_text("Page 1:\n1 2 15 3")  # 15 is out of range (1-10)

        config = ParseConfig(validate_hole_numbers=True, max_hole=10)

        with pytest.raises(TabTextParserError, match="Hole number 15 out of range"):
            TabTextParser(str(test_file), config)

    def test_parse_hole_validation_disabled(self, temp_test_dir):
        """Test hole number validation when disabled."""
        test_file = temp_test_dir / "invalid_holes.txt"
        test_file.write_text("Page 1:\n1 2 15 3")

        config = ParseConfig(validate_hole_numbers=False)
        parser = TabTextParser(str(test_file), config)

        pages = parser.get_pages()
        line = pages["Page 1"][0]
        assert line == [[1], [2], [1, 5], [3]]  # 15 parsed as 1, 5

    def test_parse_negative_note_format_errors(self, temp_test_dir):
        """Test errors in negative note format."""
        test_file = temp_test_dir / "bad_negative.txt"
        test_file.write_text("Page 1:\n1 - 3")  # Missing digit after -

        config = ParseConfig(allow_empty_chords=False)

        with pytest.raises(TabTextParserError, match="Invalid negative note format"):
            TabTextParser(str(test_file), config)

    def test_parse_tab_line_outside_page_context(self, temp_test_dir, capsys):
        """Test handling of tab lines outside page context."""
        test_file = temp_test_dir / "no_page.txt"
        test_file.write_text("1 2 3\nPage 1:\n4 5 6")

        parser = TabTextParser(str(test_file))
        pages = parser.get_pages()

        # Should only have Page 1 content
        assert len(pages) == 1
        assert "Page 1" in pages
        assert pages["Page 1"][0] == [[4], [5], [6]]

        # Should have warning about line outside page context
        captured = capsys.readouterr()
        assert "Tab line outside page context" in captured.out


class TestTabTextParserStatistics:
    """Test parsing statistics calculation."""

    def test_statistics_comprehensive(self, temp_test_dir):
        """Test comprehensive statistics calculation."""
        test_file = temp_test_dir / "stats.txt"
        test_file.write_text(
            "Page 1:\n"
            "1 23 -45\n"  # Line 1: 3 chords, 5 notes (1, 2+3, -4+-5)
            "67 -89\n"  # Line 2: 2 chords, 4 notes (6+7, -8+-9)
            "Page 2:\n"
            "1\n"  # Line 3: 1 chord, 1 note (just 1, no zero)
            "Page 3:\n"  # Empty page
        )

        config = ParseConfig(allow_empty_pages=True, validate_hole_numbers=True)
        parser = TabTextParser(str(test_file), config)
        stats = parser.get_statistics()

        assert stats.total_pages == 3
        assert stats.total_lines == 3
        assert stats.total_chords == 6
        assert stats.total_notes == 10  # 5 + 4 + 1
        assert stats.empty_pages == 1  # Page 3 is empty
        assert stats.invalid_lines == 0
        assert stats.hole_range == (1, 9)  # 1 to 9 (no zero hole)

    def test_statistics_empty_file_error(self, temp_test_dir):
        """Test statistics with empty file."""
        test_file = temp_test_dir / "empty.txt"
        test_file.write_text("")

        with pytest.raises(TabTextParserError, match="No pages found"):
            TabTextParser(str(test_file))

    def test_statistics_no_notes(self, temp_test_dir):
        """Test statistics when no valid notes are found."""
        test_file = temp_test_dir / "no_notes.txt"
        test_file.write_text("Page 1:\n# just comments\n@ symbols only")

        parser = TabTextParser(str(test_file))
        stats = parser.get_statistics()

        assert stats.total_pages == 1
        assert stats.total_lines == 2
        assert stats.total_chords == 0
        assert stats.total_notes == 0
        assert stats.hole_range == (0, 0)

    def test_statistics_invalid_lines(self, temp_test_dir, capsys):
        """Test statistics with invalid lines."""
        test_file = temp_test_dir / "invalid.txt"
        test_file.write_text("Page 1:\n1 2 3\n1 - bad\n4 5 6")

        config = ParseConfig(allow_empty_chords=True)  # Allow parsing to continue
        parser = TabTextParser(str(test_file), config)
        stats = parser.get_statistics()

        assert stats.total_pages == 1
        assert stats.total_lines == 2  # Only valid lines counted
        assert stats.invalid_lines == 1  # One line failed to parse

        # Should have warning about parse error
        captured = capsys.readouterr()
        assert "Error parsing line" in captured.out


class TestTabTextParserValidation:
    """Test tab file validation and error handling."""

    def test_empty_pages_not_allowed(self, temp_test_dir):
        """Test empty pages validation when not allowed."""
        test_file = temp_test_dir / "empty_page.txt"
        test_file.write_text("Page 1:\n1 2 3\nPage 2:\nPage 3:\n4 5 6")

        config = ParseConfig(allow_empty_pages=False)

        with pytest.raises(TabTextParserError, match="Empty pages not allowed"):
            TabTextParser(str(test_file), config)

    def test_empty_pages_allowed(self, temp_test_dir):
        """Test empty pages validation when allowed."""
        test_file = temp_test_dir / "empty_page.txt"
        test_file.write_text("Page 1:\n1 2 3\nPage 2:\nPage 3:\n4 5 6")

        config = ParseConfig(allow_empty_pages=True)
        parser = TabTextParser(str(test_file), config)

        pages = parser.get_pages()
        assert len(pages) == 3
        assert len(pages["Page 2"]) == 0  # Empty page

    def test_hole_range_validation_custom_range(self, temp_test_dir):
        """Test hole number validation with custom range."""
        test_file = temp_test_dir / "custom_range.txt"
        test_file.write_text("Page 1:\n3 4 5 6")

        config = ParseConfig(validate_hole_numbers=True, min_hole=3, max_hole=6)
        parser = TabTextParser(str(test_file), config)

        pages = parser.get_pages()
        assert pages["Page 1"][0] == [[3], [4], [5], [6]]

    def test_hole_range_validation_out_of_range(self, temp_test_dir):
        """Test hole number validation with out-of-range values."""
        test_file = temp_test_dir / "out_of_range.txt"
        test_file.write_text("Page 1:\n2 3 4 5")  # 2 is below min_hole=3

        config = ParseConfig(validate_hole_numbers=True, min_hole=3, max_hole=6)

        with pytest.raises(TabTextParserError, match="Hole number 2 out of range"):
            TabTextParser(str(test_file), config)


class TestTabTextParserGetters:
    """Test parser getter methods and properties."""

    def test_get_pages_copy(self, temp_test_dir):
        """Test that get_pages returns a copy."""
        test_file = temp_test_dir / "test.txt"
        test_file.write_text("Page 1:\n1 2 3")

        parser = TabTextParser(str(test_file))
        pages1 = parser.get_pages()
        pages2 = parser.get_pages()

        # Should be equal but not the same object
        assert pages1 == pages2
        assert pages1 is not pages2

        # Modifying copy shouldn't affect original
        pages1["New Page"] = []
        pages2 = parser.get_pages()
        assert "New Page" not in pages2

    def test_get_page_names_order(self, temp_test_dir):
        """Test that page names are returned in order."""
        test_file = temp_test_dir / "ordered.txt"
        test_file.write_text("Page 3:\n1\nPage 1:\n2\nPage 2:\n3")

        parser = TabTextParser(str(test_file))
        page_names = parser.get_page_names()

        # Should preserve order from file
        assert page_names == ["Page 3", "Page 1", "Page 2"]

    def test_get_file_info_comprehensive(self, temp_test_dir):
        """Test comprehensive file info."""
        test_file = temp_test_dir / "info_test.txt"
        content = "Page 1:\n1 23 -45\nPage 2:\n"
        test_file.write_text(content)

        config = ParseConfig(
            allow_empty_pages=True,
            validate_hole_numbers=True,
            min_hole=2,
            max_hole=8,
        )
        parser = TabTextParser(str(test_file), config)
        info = parser.get_file_info()

        # Check file properties
        assert info["file_path"] == str(test_file)
        assert info["file_size_bytes"] == len(content.encode("utf-8"))
        assert info["encoding"] == "utf-8"

        # Check page info
        assert info["pages"]["total"] == 2
        assert info["pages"]["names"] == ["Page 1", "Page 2"]
        assert info["pages"]["empty"] == 1

        # Check content info
        assert info["content"]["lines"] == 1
        assert info["content"]["chords"] == 3
        assert info["content"]["notes"] == 5
        assert info["content"]["invalid_lines"] == 0

        # Check hole info
        assert info["holes"]["range"] == (1, 5)  # From notes 1, 2, 3, -4, -5
        assert info["holes"]["min_allowed"] == 2
        assert info["holes"]["max_allowed"] == 8

        # Check config info
        assert info["config"]["allow_empty_pages"] is True
        assert info["config"]["validate_hole_numbers"] is True

    def test_backwards_compatibility_properties(self, temp_test_dir):
        """Test backwards compatibility properties."""
        test_file = temp_test_dir / "compat.txt"
        test_file.write_text("Page 1:\n1 2 3")

        parser = TabTextParser(str(test_file))

        # Test property access
        assert parser.file_path == str(test_file)
        assert isinstance(parser.pages, dict)
        assert len(parser.pages) == 1


class TestTabTextParserIntegration:
    """Test integration scenarios and real-world use cases."""

    def test_realistic_tab_file(self, temp_test_dir):
        """Test parsing a realistic harmonica tab file."""
        test_file = temp_test_dir / "realistic.txt"
        realistic_content = """Page Intro:
4 -4 5 -5 6

Page Verse 1:
6 6 6 -6 -7 7 -8 8
-8 7 -7 -6 6 -5 5 -4

Page Chorus:
8 -8 -9 8 -8 -9 8
-8 -9 9 -9 8 -8

Page Bridge:
-3 4 -4 5 -5 6 -6 7

Page Outro:
7 -7 6 -6 5 -5 4 -4 4
"""
        test_file.write_text(realistic_content)

        config = ParseConfig(
            validate_hole_numbers=True, max_hole=10
        )  # Allow up to hole 10
        parser = TabTextParser(str(test_file), config)
        pages = parser.get_pages()
        stats = parser.get_statistics()

        # Should have all pages
        assert len(pages) == 5
        expected_pages = [
            "Page Intro",
            "Page Verse 1",
            "Page Chorus",
            "Page Bridge",
            "Page Outro",
        ]
        assert all(page in pages for page in expected_pages)

        # Check statistics
        assert stats.total_pages == 5
        assert stats.total_lines == 8
        assert stats.hole_range == (3, 10)  # From -3 to -10 (abs values)
        assert stats.empty_pages == 0

    def test_error_recovery_parsing(self, temp_test_dir, capsys):
        """Test parser error recovery with mixed valid/invalid content."""
        test_file = temp_test_dir / "mixed_validity.txt"
        test_file.write_text(
            "Page 1:\n"
            "1 2 3\n"  # Valid line
            "1 - invalid\n"  # Invalid line (bad negative format)
            "4 5 6\n"  # Valid line
            "Page 2:\n"
            "7 8 9\n"  # Valid line
        )

        config = ParseConfig(allow_empty_chords=True)  # Allow parsing to continue
        parser = TabTextParser(str(test_file), config)

        pages = parser.get_pages()
        stats = parser.get_statistics()

        # Should have parsed valid content
        assert len(pages) == 2
        assert len(pages["Page 1"]) == 2  # Only valid lines
        assert len(pages["Page 2"]) == 1

        # Should track invalid lines
        assert stats.invalid_lines == 1

        # Should have warnings
        captured = capsys.readouterr()
        assert "Error parsing line" in captured.out

    @patch("os.path.getsize", side_effect=OSError("File not accessible"))
    def test_file_info_size_error_handling(self, mock_getsize, temp_test_dir):
        """Test file info when file size cannot be determined."""
        test_file = temp_test_dir / "size_error.txt"
        test_file.write_text("Page 1:\n1 2 3")

        parser = TabTextParser(str(test_file))
        info = parser.get_file_info()

        # Should handle size error gracefully
        assert info["file_size_bytes"] == 0
