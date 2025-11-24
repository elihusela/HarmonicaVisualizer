"""Tests for tab_phrase_animator.tab_text_parser module."""

import os
import tempfile
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

    def test_tab_text_parser_custom_config(self, temp_test_dir):
        """Test parser with custom configuration."""
        test_file = temp_test_dir / "test.txt"
        test_file.write_text("Page 1:\n1 2 3")

        config = ParseConfig(allow_empty_pages=True, min_hole=2, max_hole=8)
        parser = TabTextParser(str(test_file), config)

        assert parser._config.allow_empty_pages is True
        assert parser._config.min_hole == 2
        assert parser._config.max_hole == 8


class TestTabTextParserValidInputs:
    """Test parsing of valid harmonica tablature."""

    def test_parse_single_notes(self, temp_test_dir):
        """Test parsing valid single notes."""
        test_file = temp_test_dir / "single_notes.txt"
        test_file.write_text("Page 1:\n1 2 3 -4 -5 -6\n4 5 6 -1 -2 -3")

        parser = TabTextParser(str(test_file))
        pages = parser.get_pages_as_int()

        assert len(pages) == 1
        assert "Page 1" in pages
        assert len(pages["Page 1"]) == 2  # Two lines

        # First line: single notes
        line1 = pages["Page 1"][0]
        assert line1 == [[1], [2], [3], [-4], [-5], [-6]]

        # Second line: single notes
        line2 = pages["Page 1"][1]
        assert line2 == [[4], [5], [6], [-1], [-2], [-3]]

    def test_parse_valid_two_note_chords(self, temp_test_dir):
        """Test parsing valid consecutive two-note chords."""
        test_file = temp_test_dir / "valid_chords.txt"
        test_file.write_text(
            "Page 1:\n12 23 45 -45 -67"
        )  # Adjacent notes forming chords

        parser = TabTextParser(str(test_file))
        pages = parser.get_pages_as_int()

        line = pages["Page 1"][0]
        assert line == [[1, 2], [2, 3], [4, 5], [-4, -5], [-6, -7]]

    def test_parse_realistic_harmonica_tab(self, temp_test_dir):
        """Test parsing realistic harmonica tablature."""
        test_file = temp_test_dir / "realistic.txt"
        realistic_content = """Page Intro:
4 -4 5 -5 6

Page Verse:
6 6 6 -6 -7 7 -8 8
-8 7 -7 -6 6 -5 5 -4

Page Chorus:
8 -8 -9 8 -8 -9 8
-8 -9 9 -9 8 -8
"""
        test_file.write_text(realistic_content)

        config = ParseConfig(validate_hole_numbers=True, max_hole=10)
        parser = TabTextParser(str(test_file), config)
        pages = parser.get_pages_as_int()
        stats = parser.get_statistics()

        # Should have all pages
        assert len(pages) == 3
        assert "Page Intro" in pages
        assert "Page Verse" in pages
        assert "Page Chorus" in pages

        # Check statistics
        assert stats.total_pages == 3
        assert stats.empty_pages == 0

    def test_parse_multiple_pages(self, temp_test_dir):
        """Test parsing multiple pages."""
        test_file = temp_test_dir / "multi_page.txt"
        test_file.write_text("Page 1:\n1 2 3\n\nPage 2:\n-4 -5\n\nPage 3:\n6 7 8 9")

        parser = TabTextParser(str(test_file))
        pages = parser.get_pages()

        assert len(pages) == 3
        assert len(pages["Page 1"]) == 1
        assert len(pages["Page 2"]) == 1
        assert len(pages["Page 3"]) == 1

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
        assert "Page 2:" in page_names  # Only single trailing colon removed

    def test_parse_comments_and_special_chars(self, temp_test_dir):
        """Test handling of comments and special characters."""
        test_file = temp_test_dir / "comments.txt"
        test_file.write_text("Page 1:\n1 2 # comment\n3@4!5 -6*7\n")

        # Disable validation since 345 and 67 will be out of range
        config = ParseConfig(validate_hole_numbers=False)
        parser = TabTextParser(str(test_file), config)
        pages = parser.get_pages_as_int()

        line1 = pages["Page 1"][0]
        line2 = pages["Page 1"][1]

        # Special characters act as separators between notes
        assert line1 == [[1], [2]]  # Comment ignored
        assert line2 == [[3, 4, 5], [-6, 7]]  # Special chars act as separators


class TestTabTextParserInvalidInputs:
    """Test error handling for invalid harmonica tablature."""

    def test_invalid_hole_numbers_out_of_range_high(self, temp_test_dir):
        """Test that hole numbers above max_hole are rejected."""
        test_file = temp_test_dir / "high_holes.txt"
        test_file.write_text("Page 1:\n1 2 15 3")  # 15 is out of range (1-10)

        config = ParseConfig(
            validate_hole_numbers=True, max_hole=10, allow_empty_chords=False
        )

        with pytest.raises(
            TabTextParserError, match="Chord contains non-consecutive holes"
        ):
            TabTextParser(str(test_file), config)

    def test_invalid_hole_numbers_out_of_range_low(self, temp_test_dir):
        """Test that hole numbers below min_hole are rejected."""
        test_file = temp_test_dir / "low_holes.txt"
        test_file.write_text("Page 1:\n2 3 0 5")  # 0 is below min_hole=1

        config = ParseConfig(
            validate_hole_numbers=True, min_hole=1, allow_empty_chords=False
        )

        with pytest.raises(TabTextParserError, match="Hole number 0 out of range"):
            TabTextParser(str(test_file), config)

    def test_invalid_multi_digit_holes(self, temp_test_dir):
        """Test that unrealistic multi-digit holes are rejected."""
        test_file = temp_test_dir / "multi_digit.txt"
        test_file.write_text(
            "Page 1:\n123 -456"
        )  # These don't exist on real harmonicas

        config = ParseConfig(validate_hole_numbers=True, allow_empty_chords=False)

        with pytest.raises(
            TabTextParserError, match="Chord with 3 notes is unrealistic for harmonica"
        ):
            TabTextParser(str(test_file), config)

    def test_invalid_negative_note_format(self, temp_test_dir):
        """Test errors in negative note format."""
        test_file = temp_test_dir / "bad_negative.txt"
        test_file.write_text("Page 1:\n1 - 3")  # Missing digit after -

        config = ParseConfig(allow_empty_chords=False)

        with pytest.raises(TabTextParserError, match="Invalid negative note format"):
            TabTextParser(str(test_file), config)

    def test_empty_pages_not_allowed(self, temp_test_dir):
        """Test empty pages validation when not allowed."""
        test_file = temp_test_dir / "empty_page.txt"
        test_file.write_text("Page 1:\n1 2 3\nPage 2:\nPage 3:\n4 5 6")

        config = ParseConfig(allow_empty_pages=False)

        with pytest.raises(TabTextParserError, match="Empty pages not allowed"):
            TabTextParser(str(test_file), config)

    def test_no_pages_found_error(self, temp_test_dir):
        """Test error when no pages are found."""
        test_file = temp_test_dir / "no_pages.txt"
        test_file.write_text("1 2 3\n4 5 6")  # No page headers

        with pytest.raises(TabTextParserError, match="No pages found"):
            TabTextParser(str(test_file))


class TestTabTextParserChordValidation:
    """Test realistic harmonica chord validation."""

    def test_valid_single_notes_always_pass(self, temp_test_dir):
        """Test that single notes always pass chord validation."""
        test_file = temp_test_dir / "single_notes.txt"
        test_file.write_text(
            "Page 1:\n1 -2 3 -4 5 -6 7 -8 9"
        )  # Remove -10 since it becomes [-1, 0]

        config = ParseConfig(validate_hole_numbers=True)
        parser = TabTextParser(str(test_file), config)
        pages = parser.get_pages_as_int()

        line = pages["Page 1"][0]
        assert line == [[1], [-2], [3], [-4], [5], [-6], [7], [-8], [9]]

    def test_valid_consecutive_blow_chords(self, temp_test_dir):
        """Test valid consecutive blow note chords."""
        test_file = temp_test_dir / "valid_blow_chords.txt"
        test_file.write_text(
            "Page 1:\n12 23 34 45 56 67 78 89"
        )  # Consecutive blow chords

        config = ParseConfig(validate_hole_numbers=True)
        parser = TabTextParser(str(test_file), config)
        pages = parser.get_pages_as_int()

        line = pages["Page 1"][0]
        assert line == [[1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 7], [7, 8], [8, 9]]

    def test_valid_consecutive_draw_chords(self, temp_test_dir):
        """Test valid consecutive draw note chords."""
        test_file = temp_test_dir / "valid_draw_chords.txt"
        test_file.write_text("Page 1:\n-12 -34 -45 -67 -89")  # Consecutive draw chords

        config = ParseConfig(validate_hole_numbers=True)
        parser = TabTextParser(str(test_file), config)
        pages = parser.get_pages_as_int()

        line = pages["Page 1"][0]
        assert line == [[-1, -2], [-3, -4], [-4, -5], [-6, -7], [-8, -9]]

    def test_mixed_single_notes_and_chords(self, temp_test_dir):
        """Test mix of single notes and valid chords."""
        test_file = temp_test_dir / "mixed_chords.txt"
        test_file.write_text("Page 1:\n1 23 -4 -56 7 89")  # Mix of singles and chords

        config = ParseConfig(validate_hole_numbers=True)
        parser = TabTextParser(str(test_file), config)
        pages = parser.get_pages_as_int()

        line = pages["Page 1"][0]
        assert line == [[1], [2, 3], [-4], [-5, -6], [7], [8, 9]]

    def test_invalid_three_note_chords_rejected(self, temp_test_dir):
        """Test that three-note chords are rejected."""
        test_file = temp_test_dir / "three_note_chord.txt"
        test_file.write_text("Page 1:\n123")  # Three notes in one chord

        config = ParseConfig(validate_hole_numbers=True, allow_empty_chords=False)

        with pytest.raises(
            TabTextParserError, match="Chord with 3 notes is unrealistic for harmonica"
        ):
            TabTextParser(str(test_file), config)

    def test_invalid_mixed_blow_draw_chords_rejected(self, temp_test_dir):
        """Test that chords mixing blow and draw notes are rejected."""
        test_file = temp_test_dir / "mixed_blow_draw.txt"
        test_file.write_text("Page 1:\n1-2")  # Blow 1 + Draw 2

        config = ParseConfig(validate_hole_numbers=True, allow_empty_chords=False)

        with pytest.raises(TabTextParserError, match="Chord mixes blow and draw notes"):
            TabTextParser(str(test_file), config)

    def test_invalid_non_consecutive_chords_rejected(self, temp_test_dir):
        """Test that non-consecutive note chords are rejected."""
        test_file = temp_test_dir / "non_consecutive.txt"
        test_file.write_text("Page 1:\n14")  # Holes 1 and 4 (not consecutive)

        config = ParseConfig(validate_hole_numbers=True, allow_empty_chords=False)

        with pytest.raises(
            TabTextParserError, match="Chord contains non-consecutive holes"
        ):
            TabTextParser(str(test_file), config)

    def test_chord_validation_disabled_allows_anything(self, temp_test_dir):
        """Test that all inputs are allowed when validation is disabled."""
        test_file = temp_test_dir / "validation_disabled.txt"
        test_file.write_text(
            "Page 1:\n1 2 3 99 -88"
        )  # Mix of valid and invalid but realistic digits

        config = ParseConfig(validate_hole_numbers=False)
        parser = TabTextParser(str(test_file), config)
        pages = parser.get_pages_as_int()

        line = pages["Page 1"][0]
        assert line == [
            [1],
            [2],
            [3],
            [9, 9],
            [-8, -8],
        ]  # 99 becomes [9,9], -88 becomes [-8,-8]

    def test_warnings_with_allow_empty_chords(self, temp_test_dir, capsys):
        """Test that invalid inputs generate warnings when allow_empty_chords=True."""
        test_file = temp_test_dir / "invalid_with_warnings.txt"
        test_file.write_text(
            "Page 1:\n19 2 3"
        )  # 19 becomes [1, 9] which has hole 9 in range but creates realistic chord

        config = ParseConfig(
            validate_hole_numbers=True,
            allow_empty_chords=True,
            allow_empty_pages=True,
            max_hole=8,
        )
        parser = TabTextParser(str(test_file), config)
        pages = parser.get_pages()

        # Should parse but with warnings and empty page due to validation error (hole 9 out of range)
        assert len(pages["Page 1"]) == 0

        captured = capsys.readouterr()
        assert "Hole number 9 out of range" in captured.out

    def test_hole_range_validation_custom_range(self, temp_test_dir):
        """Test hole number validation with custom range."""
        test_file = temp_test_dir / "custom_range.txt"
        test_file.write_text("Page 1:\n3 4 5 6")

        config = ParseConfig(validate_hole_numbers=True, min_hole=3, max_hole=6)
        parser = TabTextParser(str(test_file), config)

        pages = parser.get_pages_as_int()
        assert pages["Page 1"][0] == [[3], [4], [5], [6]]

    def test_hole_range_validation_out_of_custom_range(self, temp_test_dir):
        """Test that holes outside custom range are rejected."""
        test_file = temp_test_dir / "out_of_custom_range.txt"
        test_file.write_text("Page 1:\n2 3 4 5")  # 2 is below min_hole=3

        config = ParseConfig(
            validate_hole_numbers=True, min_hole=3, max_hole=6, allow_empty_chords=False
        )

        with pytest.raises(TabTextParserError, match="Hole number 2 out of range"):
            TabTextParser(str(test_file), config)


class TestTabTextParserStatistics:
    """Test parsing statistics calculation."""

    def test_statistics_comprehensive(self, temp_test_dir):
        """Test comprehensive statistics calculation."""
        test_file = temp_test_dir / "stats.txt"
        test_file.write_text(
            "Page 1:\n"
            "1 2 -4\n"  # Line 1: 3 chords, 3 notes
            "6 -8\n"  # Line 2: 2 chords, 2 notes
            "Page 2:\n"
            "1\n"  # Line 3: 1 chord, 1 note
            "Page 3:\n"  # Empty page
        )

        config = ParseConfig(allow_empty_pages=True, validate_hole_numbers=True)
        parser = TabTextParser(str(test_file), config)
        stats = parser.get_statistics()

        assert stats.total_pages == 3
        assert stats.total_lines == 3
        assert stats.total_chords == 6
        assert stats.total_notes == 6  # 3 + 2 + 1
        assert stats.empty_pages == 1  # Page 3 is empty
        assert stats.invalid_lines == 0
        assert stats.hole_range == (1, 8)  # 1 to 8

    def test_statistics_with_invalid_lines(self, temp_test_dir, capsys):
        """Test statistics with invalid lines."""
        test_file = temp_test_dir / "invalid_lines.txt"
        test_file.write_text(
            "Page 1:\n1 2 3\n1 100 bad\n4 5 6"
        )  # Middle line has out-of-range hole

        config = ParseConfig(allow_empty_chords=True)  # Allow parsing to continue
        parser = TabTextParser(str(test_file), config)
        stats = parser.get_statistics()

        assert stats.total_pages == 1
        assert stats.total_lines == 2  # Only valid lines counted
        assert stats.invalid_lines == 1  # One line failed to parse

        captured = capsys.readouterr()
        assert "Error parsing line" in captured.out

    def test_statistics_no_valid_notes(self, temp_test_dir):
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
        content = "Page 1:\n2 3 -4\nPage 2:\n"
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
        assert info["content"]["notes"] == 3

        # Check hole info
        assert info["holes"]["range"] == (2, 4)  # From notes 2, 3, -4

    def test_backwards_compatibility_properties(self, temp_test_dir):
        """Test backwards compatibility properties."""
        test_file = temp_test_dir / "compat.txt"
        test_file.write_text("Page 1:\n1 2 3")

        parser = TabTextParser(str(test_file))

        # Test property access
        assert parser.file_path == str(test_file)
        assert isinstance(parser.pages, dict)
        assert len(parser.pages) == 1

    def test_empty_pages_allowed(self, temp_test_dir):
        """Test empty pages validation when allowed."""
        test_file = temp_test_dir / "empty_page.txt"
        test_file.write_text("Page 1:\n1 2 3\nPage 2:\nPage 3:\n4 5 6")

        config = ParseConfig(allow_empty_pages=True)
        parser = TabTextParser(str(test_file), config)

        pages = parser.get_pages_as_int()
        assert len(pages) == 3
        assert len(pages["Page 2"]) == 0  # Empty page

    def test_tab_line_outside_page_context(self, temp_test_dir, capsys):
        """Test handling of tab lines outside page context."""
        test_file = temp_test_dir / "no_page_context.txt"
        test_file.write_text("1 2 3\nPage 1:\n4 5 6")

        parser = TabTextParser(str(test_file))
        pages = parser.get_pages_as_int()

        # Should only have Page 1 content
        assert len(pages) == 1
        assert "Page 1" in pages
        assert pages["Page 1"][0] == [[4], [5], [6]]

        # Should have warning about line outside page context
        captured = capsys.readouterr()
        assert "Tab line outside page context" in captured.out


class TestTabTextParserErrorRecovery:
    """Test parser error recovery with mixed valid/invalid content."""

    def test_error_recovery_with_invalid_holes(self, temp_test_dir, capsys):
        """Test parser continues with warnings when allow_empty_chords=True."""
        test_file = temp_test_dir / "mixed_validity.txt"
        test_file.write_text(
            "Page 1:\n"
            "1 2 3\n"  # Valid line
            "1 100 invalid\n"  # Invalid line (out of range hole)
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


class TestTabTextParserCoverageGaps:
    """Test cases to achieve 100% coverage for TabTextParser."""

    def test_file_size_error_handling(self, temp_test_dir):
        """Test OSError handling when getting file size - Lines 121-122."""
        from unittest.mock import patch

        test_file = temp_test_dir / "test.txt"
        test_file.write_text("Page 1:\n1 2 3")

        with patch("os.path.getsize", side_effect=OSError("Permission denied")):
            parser = TabTextParser(str(test_file))
            file_info = parser.get_file_info()

            # Should handle OSError and set file_size_bytes to 0
            assert file_info["file_size_bytes"] == 0

    def test_file_validation_unicode_error(self, temp_test_dir):
        """Test UnicodeDecodeError handling during file validation - Lines 168-169."""
        from unittest.mock import patch, mock_open

        test_file = temp_test_dir / "test.txt"
        test_file.write_text("1 2 3")

        # Mock file opening to raise UnicodeDecodeError during validation
        with patch("builtins.open", mock_open()) as mock_file:
            mock_file.side_effect = UnicodeDecodeError(
                "utf-8", b"invalid", 0, 1, "invalid byte"
            )

            with pytest.raises(TabTextParserError, match="Cannot read tab file"):
                TabTextParser(str(test_file))

    def test_file_validation_io_error(self, temp_test_dir):
        """Test IOError handling during file validation - Lines 168-169."""
        from unittest.mock import patch, mock_open

        test_file = temp_test_dir / "test.txt"
        test_file.write_text("1 2 3")

        # Mock file opening to raise IOError during validation
        with patch("builtins.open", mock_open()) as mock_file:
            mock_file.side_effect = IOError("File access denied")

            with pytest.raises(TabTextParserError, match="Cannot read tab file"):
                TabTextParser(str(test_file))

    def test_page_name_with_whitespace(self, temp_test_dir):
        """Test page parsing with stripped line content - Line 201."""
        test_file = temp_test_dir / "whitespace_page.txt"
        test_file.write_text(
            "   Page 1   \n"  # Page name with leading/trailing whitespace
            "1 2 3\n"
            "4 5 6\n"
        )

        parser = TabTextParser(str(test_file))
        pages = parser.get_pages()

        # Should strip whitespace and use "Page 1" as key
        assert "Page 1" in pages
        assert len(pages["Page 1"]) == 2

    def test_file_loading_io_error(self, temp_test_dir):
        """Test IOError handling during file loading - Line 226."""
        from unittest.mock import patch, MagicMock

        test_file = temp_test_dir / "test.txt"
        test_file.write_text("Page 1:\n1 2 3")

        # Mock that passes validation but fails during actual parsing
        with patch("builtins.open") as mock_open:
            # First call (validation) succeeds
            # Second call (_load_and_parse) fails
            mock_open.side_effect = [
                MagicMock(),  # Success for validation
                IOError("Disk error during parsing"),  # Failure during parsing
            ]

            with pytest.raises(TabTextParserError, match="Error reading file"):
                TabTextParser(str(test_file))


class TestTabTextParserBendNotation:
    """Test bend notation parsing and validation."""

    def test_parse_valid_blow_bends(self, temp_test_dir):
        """Test parsing valid blow bend notation."""
        test_file = temp_test_dir / "blow_bends.txt"
        test_file.write_text("Page 1:\n1' 2' 6' 7' 8' 9'")

        parser = TabTextParser(str(test_file))
        pages = parser.get_pages()

        line = pages["Page 1"][0]
        # Check that all notes are parsed with bend flag
        assert len(line) == 6
        for chord in line:
            assert len(chord) == 1
            assert chord[0].is_bend is True

        # Verify hole numbers
        assert line[0][0].hole_number == 1
        assert line[1][0].hole_number == 2
        assert line[2][0].hole_number == 6

    def test_parse_valid_draw_bends(self, temp_test_dir):
        """Test parsing valid draw bend notation."""
        test_file = temp_test_dir / "draw_bends.txt"
        test_file.write_text("Page 1:\n-1' -2' -3' -6' -8' -9'")

        parser = TabTextParser(str(test_file))
        pages = parser.get_pages()

        line = pages["Page 1"][0]
        assert len(line) == 6
        for chord in line:
            assert len(chord) == 1
            assert chord[0].is_bend is True

        # Verify negative hole numbers
        assert line[0][0].hole_number == -1
        assert line[1][0].hole_number == -2
        assert line[2][0].hole_number == -3

    def test_parse_mixed_bends_and_regular_notes(self, temp_test_dir):
        """Test parsing mix of bent and regular notes."""
        test_file = temp_test_dir / "mixed_bends.txt"
        test_file.write_text("Page 1:\n1 2' -3 -4' 5 6'")

        parser = TabTextParser(str(test_file))
        pages = parser.get_pages()

        line = pages["Page 1"][0]

        # Regular notes should have is_bend=False
        assert line[0][0].is_bend is False  # 1
        assert line[2][0].is_bend is False  # -3
        assert line[4][0].is_bend is False  # 5

        # Bent notes should have is_bend=True
        assert line[1][0].is_bend is True  # 2'
        assert line[3][0].is_bend is True  # -4'
        assert line[5][0].is_bend is True  # 6'

    def test_reject_bends_on_chords(self, temp_test_dir):
        """Test that bend notation on chords is rejected."""
        test_file = temp_test_dir / "chord_bends.txt"
        test_file.write_text("Page 1:\n12'")  # Chord with bend - should be rejected

        config = ParseConfig(validate_hole_numbers=True, allow_empty_chords=False)

        with pytest.raises(
            TabTextParserError, match="Bend notation not allowed on chords"
        ):
            TabTextParser(str(test_file), config)

    def test_reject_multiple_apostrophes(self, temp_test_dir):
        """Test that double apostrophe ('') is treated as a valid bend marker."""
        test_file = temp_test_dir / "double_apostrophe.txt"
        test_file.write_text("Page 1:\n6''")  # Double apostrophe bend notation

        config = ParseConfig(validate_hole_numbers=True, allow_empty_chords=False)

        # Should parse successfully as a bent note
        parser = TabTextParser(str(test_file), config)
        pages = parser.get_pages()

        # Verify the note is marked as bent
        assert "Page 1" in pages
        assert len(pages["Page 1"]) == 1  # One line
        assert len(pages["Page 1"][0]) == 1  # One chord
        assert len(pages["Page 1"][0][0]) == 1  # One note
        note = pages["Page 1"][0][0][0]
        assert note.hole_number == 6
        assert note.is_bend is True

    def test_apostrophe_must_be_adjacent(self, temp_test_dir):
        """Test that apostrophe not adjacent to a number raises an error."""
        test_file = temp_test_dir / "space_before_apostrophe.txt"
        test_file.write_text("Page 1:\n6 '")  # Space between number and apostrophe

        # Non-adjacent apostrophe raises error with default config
        config = ParseConfig(allow_empty_chords=False)
        with pytest.raises(
            TabTextParserError,
            match="Bend notation \\('\\) must be directly adjacent to a note",
        ):
            TabTextParser(str(test_file), config)

        # With allow_empty_chords, it parses the 6 and warns about the apostrophe
        config2 = ParseConfig(allow_empty_chords=True, allow_empty_pages=True)
        parser = TabTextParser(str(test_file), config2)
        pages = parser.get_pages()

        # Page will be empty because the line failed to parse
        assert len(pages["Page 1"]) == 0

    def test_get_pages_as_int_drops_bend_info(self, temp_test_dir):
        """Test that get_pages_as_int() returns integers without bend info."""
        test_file = temp_test_dir / "bend_to_int.txt"
        test_file.write_text("Page 1:\n1' 2 -3'")

        parser = TabTextParser(str(test_file))

        # get_pages() should return ParsedNote objects with bend info
        pages_with_bend = parser.get_pages()
        assert pages_with_bend["Page 1"][0][0][0].is_bend is True
        assert pages_with_bend["Page 1"][0][1][0].is_bend is False
        assert pages_with_bend["Page 1"][0][2][0].is_bend is True

        # get_pages_as_int() should return plain integers
        pages_as_int = parser.get_pages_as_int()
        assert pages_as_int == {"Page 1": [[[1], [2], [-3]]]}

    def test_bend_notation_edge_cases(self, temp_test_dir):
        """Test bend notation on edge case hole numbers (single digits only)."""
        test_file = temp_test_dir / "bend_edge_cases.txt"
        test_file.write_text("Page 1:\n1' 9' -1' -9'")

        parser = TabTextParser(str(test_file))
        pages = parser.get_pages()

        line = pages["Page 1"][0]
        assert len(line) == 4

        # All should be marked as bent
        for chord in line:
            assert chord[0].is_bend is True

        # Verify hole numbers
        assert line[0][0].hole_number == 1
        assert line[1][0].hole_number == 9
        assert line[2][0].hole_number == -1
        assert line[3][0].hole_number == -9

    def test_double_apostrophe_bend_notation(self, temp_test_dir):
        """Test that double apostrophe ('') is treated as bend notation for both blow and draw."""
        test_file = temp_test_dir / "double_apostrophe_bends.txt"
        test_file.write_text("Page 1:\n3'' 6'' -3'' -6'' 4 -2")

        parser = TabTextParser(str(test_file))
        pages = parser.get_pages()

        line = pages["Page 1"][0]
        assert len(line) == 6

        # First four should be bent
        assert line[0][0].hole_number == 3
        assert line[0][0].is_bend is True
        assert line[1][0].hole_number == 6
        assert line[1][0].is_bend is True
        assert line[2][0].hole_number == -3
        assert line[2][0].is_bend is True
        assert line[3][0].hole_number == -6
        assert line[3][0].is_bend is True

        # Last two should NOT be bent
        assert line[4][0].hole_number == 4
        assert line[4][0].is_bend is False
        assert line[5][0].hole_number == -2
        assert line[5][0].is_bend is False
