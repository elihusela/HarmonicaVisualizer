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
        pages = parser.get_pages()

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
        pages = parser.get_pages()

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
        pages = parser.get_pages()
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
        pages = parser.get_pages()

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
        pages = parser.get_pages()

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
        pages = parser.get_pages()

        line = pages["Page 1"][0]
        assert line == [[1, 2], [2, 3], [3, 4], [4, 5], [5, 6], [6, 7], [7, 8], [8, 9]]

    def test_valid_consecutive_draw_chords(self, temp_test_dir):
        """Test valid consecutive draw note chords."""
        test_file = temp_test_dir / "valid_draw_chords.txt"
        test_file.write_text("Page 1:\n-12 -34 -45 -67 -89")  # Consecutive draw chords

        config = ParseConfig(validate_hole_numbers=True)
        parser = TabTextParser(str(test_file), config)
        pages = parser.get_pages()

        line = pages["Page 1"][0]
        assert line == [[-1, -2], [-3, -4], [-4, -5], [-6, -7], [-8, -9]]

    def test_mixed_single_notes_and_chords(self, temp_test_dir):
        """Test mix of single notes and valid chords."""
        test_file = temp_test_dir / "mixed_chords.txt"
        test_file.write_text("Page 1:\n1 23 -4 -56 7 89")  # Mix of singles and chords

        config = ParseConfig(validate_hole_numbers=True)
        parser = TabTextParser(str(test_file), config)
        pages = parser.get_pages()

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
        pages = parser.get_pages()

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

        pages = parser.get_pages()
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

        pages = parser.get_pages()
        assert len(pages) == 3
        assert len(pages["Page 2"]) == 0  # Empty page

    def test_tab_line_outside_page_context(self, temp_test_dir, capsys):
        """Test handling of tab lines outside page context."""
        test_file = temp_test_dir / "no_page_context.txt"
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
