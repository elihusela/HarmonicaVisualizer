"""
TabTextParser - Parses harmonica tablature text files.

Handles loading and parsing of tab files with page-based organization,
validation, and comprehensive error handling.
"""

import os
from dataclasses import dataclass
from typing import Dict, List, Optional, NamedTuple


class ParsedNote(NamedTuple):
    """Represents a parsed note with bend information."""

    hole_number: int  # Positive for blow, negative for draw
    is_bend: bool = False
    bend_notation: str = ""  # Original bend notation: "'", "''", "*", or "\u2019"


@dataclass
class ParseConfig:
    """Configuration for tab file parsing."""

    allow_empty_pages: bool = False
    allow_empty_chords: bool = True
    validate_hole_numbers: bool = True
    min_hole: int = 1
    max_hole: int = 10
    encoding: str = "utf-8"


@dataclass
class ParseStatistics:
    """Statistics about the parsed tab file."""

    total_pages: int
    total_lines: int
    total_chords: int
    total_notes: int
    empty_pages: int
    invalid_lines: int
    hole_range: tuple[int, int]  # (min_hole, max_hole)


class TabTextParserError(Exception):
    """Custom exception for tab parsing errors."""

    pass


class TabTextParser:
    """
    Parses harmonica tablature text files into structured data.

    Handles page-based tab organization with comprehensive validation,
    error handling, and parsing statistics. Supports various tab formats
    and provides detailed feedback on parsing issues.
    """

    def __init__(self, file_path: str, config: Optional[ParseConfig] = None):
        """
        Initialize tab text parser.

        Args:
            file_path: Path to the tab text file
            config: Optional parsing configuration

        Raises:
            TabTextParserError: If file cannot be loaded or is invalid
        """
        self._file_path = file_path
        self._config = config or ParseConfig()
        self._statistics = ParseStatistics(
            total_pages=0,
            total_lines=0,
            total_chords=0,
            total_notes=0,
            empty_pages=0,
            invalid_lines=0,
            hole_range=(0, 0),
        )

        # Validate file exists
        self._validate_file()

        # Parse the file
        self._pages = self._load_and_parse()

        # Calculate final statistics
        self._finalize_statistics()

    def get_pages(self) -> Dict[str, List[List[List[ParsedNote]]]]:
        """
        Get parsed tab pages with bend information.

        Returns:
            Dictionary mapping page names to lists of lines of chords (ParsedNote objects)
        """
        return self._pages.copy()

    def get_pages_as_int(self) -> Dict[str, List[List[List[int]]]]:
        """
        Get parsed tab pages as hole numbers only (backwards compatibility).

        Returns:
            Dictionary mapping page names to lists of lines of chords (int hole numbers)
        """
        result: Dict[str, List[List[List[int]]]] = {}
        for page_name, lines in self._pages.items():
            result[page_name] = [
                [[note.hole_number for note in chord] for chord in line]
                for line in lines
            ]
        return result

    def get_statistics(self) -> ParseStatistics:
        """
        Get parsing statistics.

        Returns:
            ParseStatistics object with detailed parsing information
        """
        return self._statistics

    def get_page_names(self) -> List[str]:
        """
        Get list of parsed page names in order.

        Returns:
            List of page names
        """
        return list(self._pages.keys())

    def get_file_info(self) -> dict:
        """
        Get comprehensive file and parsing information.

        Returns:
            Dict with file properties and parsing statistics
        """
        try:
            file_size = os.path.getsize(self._file_path)
        except OSError:
            file_size = 0

        return {
            "file_path": self._file_path,
            "file_size_bytes": file_size,
            "encoding": self._config.encoding,
            "pages": {
                "total": self._statistics.total_pages,
                "names": self.get_page_names(),
                "empty": self._statistics.empty_pages,
            },
            "content": {
                "lines": self._statistics.total_lines,
                "chords": self._statistics.total_chords,
                "notes": self._statistics.total_notes,
                "invalid_lines": self._statistics.invalid_lines,
            },
            "holes": {
                "range": self._statistics.hole_range,
                "min_allowed": self._config.min_hole,
                "max_allowed": self._config.max_hole,
            },
            "config": {
                "allow_empty_pages": self._config.allow_empty_pages,
                "allow_empty_chords": self._config.allow_empty_chords,
                "validate_hole_numbers": self._config.validate_hole_numbers,
            },
        }

    def _validate_file(self) -> None:
        """
        Validate that the tab file exists and is accessible.

        Raises:
            TabTextParserError: If file validation fails
        """
        if not os.path.exists(self._file_path):
            raise TabTextParserError(f"Tab file not found: {self._file_path}")

        if not os.path.isfile(self._file_path):
            raise TabTextParserError(f"Path is not a file: {self._file_path}")

        # Check if file is readable
        try:
            with open(self._file_path, "r", encoding=self._config.encoding):
                pass
        except (IOError, UnicodeDecodeError) as e:
            raise TabTextParserError(f"Cannot read tab file {self._file_path}: {e}")

    def _load_and_parse(self) -> Dict[str, List[List[List[ParsedNote]]]]:
        """
        Load and parse the tab file.

        Returns:
            Dictionary mapping page names to parsed content

        Raises:
            TabTextParserError: If parsing fails
        """
        pages: Dict[str, List[List[List[ParsedNote]]]] = {}
        current_page: Optional[str] = None
        line_number = 0

        try:
            with open(self._file_path, "r", encoding=self._config.encoding) as f:
                for raw_line in f:
                    line_number += 1
                    line = raw_line.strip()

                    # Skip empty lines
                    if not line:
                        continue

                    # Check for page header
                    if line.lower().startswith("page"):
                        # Remove only single trailing colon, not multiple
                        if line.endswith(":"):
                            current_page = line[:-1].strip()
                        else:
                            current_page = line.strip()
                        pages[current_page] = []
                        self._statistics.total_pages += 1
                        continue

                    # Parse tab line if we have a current page
                    if current_page and line:
                        try:
                            chords = self._parse_tab_line(line, line_number)
                            pages[current_page].append(chords)
                            self._statistics.total_lines += 1
                        except Exception as e:
                            print(f"⚠️  Warning: Error parsing line {line_number}: {e}")
                            self._statistics.invalid_lines += 1
                            if not self._config.allow_empty_chords:
                                raise TabTextParserError(
                                    f"Parse error at line {line_number}: {e}"
                                )
                    elif line:
                        print(
                            f"⚠️  Warning: Tab line outside page context at line {line_number}: {line}"
                        )
                        self._statistics.invalid_lines += 1

        except IOError as e:
            raise TabTextParserError(f"Error reading file {self._file_path}: {e}")

        # Validate parsed content
        self._validate_parsed_content(pages)

        return pages

    def _parse_digits_to_holes(self, digits_str: str) -> List[int]:
        """
        Parse a string of digits into a list of hole numbers.

        Handles both single-digit holes (1-9) and the two-digit hole 10.
        For chords like "56", returns [5, 6]. For "10", returns [10].
        For "910", returns [9, 10].

        Args:
            digits_str: String of digits to parse

        Returns:
            List of hole numbers (positive integers)
        """
        holes: List[int] = []
        i = 0
        while i < len(digits_str):
            # Check if we have "10" at this position
            if i + 1 < len(digits_str) and digits_str[i : i + 2] == "10":
                holes.append(10)
                i += 2
            else:
                holes.append(int(digits_str[i]))
                i += 1
        return holes

    def _parse_tab_line(self, line: str, line_number: int) -> List[List[ParsedNote]]:
        """
        Parse a single tab line into chords with bend notation support.

        Args:
            line: Raw tab line to parse
            line_number: Line number for error reporting

        Returns:
            List of chords, where each chord is a list of ParsedNote objects

        Raises:
            TabTextParserError: If parsing fails
        """
        chords: List[List[ParsedNote]] = []
        current_chord: List[ParsedNote] = []
        i = 0

        while i < len(line):
            char = line[i]

            if char == "-":
                # Parse negative (draw) notes
                i += 1
                if i >= len(line) or not line[i].isdigit():
                    raise TabTextParserError(
                        f"Invalid negative note format at position {i}"
                    )

                # Collect consecutive digits after '-'
                start_pos = i
                while i < len(line) and line[i].isdigit():
                    i += 1

                digits_str = line[start_pos:i]

                # Check if there's a bend marker after all digits
                # Supports: ' (straight), '' (double quote), ' (curly U+2019), * (asterisk)
                has_bend_marker = False
                bend_notation = ""
                if i < len(line):
                    # Check for '' (two single quotes)
                    if i + 1 < len(line) and line[i : i + 2] == "''":
                        has_bend_marker = True
                        bend_notation = "''"
                        i += 2  # consume both quotes
                    # Check for single character bend markers
                    elif line[i] in ("'", "*", "\u2019"):
                        has_bend_marker = True
                        bend_notation = line[i]
                        i += 1  # consume the bend marker

                # Parse digits into hole numbers (handles "10" correctly)
                hole_numbers = self._parse_digits_to_holes(digits_str)
                for idx, hole_num in enumerate(hole_numbers):
                    hole_number = -hole_num  # Make negative for draw notes
                    self._validate_hole_number(hole_number, line_number)

                    # Only the last hole in the sequence can have a bend
                    is_bend = has_bend_marker and (idx == len(hole_numbers) - 1)
                    note_bend_notation = bend_notation if is_bend else ""

                    current_chord.append(
                        ParsedNote(hole_number, is_bend, note_bend_notation)
                    )
                    self._statistics.total_notes += 1

            elif char.isdigit():
                # Parse positive (blow) notes
                start_pos = i
                while i < len(line) and line[i].isdigit():
                    i += 1

                digits_str = line[start_pos:i]

                # Check if there's a bend marker after all digits
                # Supports: ' (straight), '' (double quote), ' (curly U+2019), * (asterisk)
                has_bend_marker = False
                bend_notation = ""
                if i < len(line):
                    # Check for '' (two single quotes)
                    if i + 1 < len(line) and line[i : i + 2] == "''":
                        has_bend_marker = True
                        bend_notation = "''"
                        i += 2  # consume both quotes
                    # Check for single character bend markers
                    elif line[i] in ("'", "*", "\u2019"):
                        has_bend_marker = True
                        bend_notation = line[i]
                        i += 1  # consume the bend marker

                # Parse digits into hole numbers (handles "10" correctly)
                hole_numbers = self._parse_digits_to_holes(digits_str)
                for idx, hole_number in enumerate(hole_numbers):
                    self._validate_hole_number(hole_number, line_number)

                    # Only the last hole in the sequence can have a bend
                    is_bend = has_bend_marker and (idx == len(hole_numbers) - 1)
                    note_bend_notation = bend_notation if is_bend else ""

                    current_chord.append(
                        ParsedNote(hole_number, is_bend, note_bend_notation)
                    )
                    self._statistics.total_notes += 1

            elif char.isspace():
                # Space separates chords
                if current_chord:
                    self._validate_chord(current_chord, line_number)
                    chords.append(current_chord)
                    self._statistics.total_chords += 1
                    current_chord = []
                i += 1

            elif char in ("'", "*", "\u2019"):
                # Check if it's a '' (double single quote) pattern
                if char == "'" and i + 1 < len(line) and line[i + 1] == "'":
                    # Bend marker '' without adjacent digit - invalid
                    raise TabTextParserError(
                        f"Bend notation ('') must be directly adjacent to a note at position {i}"
                    )
                else:
                    # Single bend marker without adjacent digit - invalid
                    raise TabTextParserError(
                        f"Bend notation ({char}) must be directly adjacent to a note at position {i}"
                    )

            else:
                # Skip other characters (comments, etc.)
                i += 1

        # Add final chord if exists
        if current_chord:
            self._validate_chord(current_chord, line_number)
            chords.append(current_chord)
            self._statistics.total_chords += 1

        return chords

    def _validate_hole_number(self, hole_number: int, line_number: int) -> None:
        """
        Validate that a hole number is within acceptable range.

        Args:
            hole_number: Hole number to validate (positive or negative)
            line_number: Line number for error reporting

        Raises:
            TabTextParserError: If hole number is invalid
        """
        if not self._config.validate_hole_numbers:
            return

        abs_hole = abs(hole_number)
        if not (self._config.min_hole <= abs_hole <= self._config.max_hole):
            raise TabTextParserError(
                f"Hole number {hole_number} out of range [{self._config.min_hole}, {self._config.max_hole}] "
                f"at line {line_number}"
            )

    def _validate_chord(self, chord: List[ParsedNote], line_number: int) -> None:
        """
        Validate that a chord follows realistic harmonica constraints.

        Args:
            chord: List of ParsedNote objects in the chord
            line_number: Line number for error reporting

        Raises:
            TabTextParserError: If chord is invalid
        """
        if not self._config.validate_hole_numbers or len(chord) <= 1:
            return

        # Check if any notes have bends - bends only allowed on single notes
        bent_notes = [note for note in chord if note.is_bend]
        if bent_notes and len(chord) > 1:
            raise TabTextParserError(
                f"Bend notation not allowed on chords at line {line_number}. "
                f"Bends can only be applied to single notes."
            )

        # No more than 3 notes in a chord (realistic harmonica limitation)
        if len(chord) > 3:
            raise TabTextParserError(
                f"Chord with {len(chord)} notes is unrealistic for harmonica at line {line_number}. "
                f"Maximum 3 notes allowed."
            )

        # All notes in chord must be same type (all blow or all draw)
        signs = [1 if note.hole_number > 0 else -1 for note in chord]
        if len(set(signs)) > 1:
            raise TabTextParserError(
                f"Chord mixes blow and draw notes at line {line_number}. "
                f"All notes in a chord must be same type."
            )

        # Notes must be written in ascending order (smallest hole first, e.g. 56 not 65)
        abs_holes_as_written = [abs(note.hole_number) for note in chord]
        if abs_holes_as_written != sorted(abs_holes_as_written):
            raise TabTextParserError(
                f"Chord notes must be written in ascending order (smallest hole first) at line {line_number}. "
                f"Got holes {abs_holes_as_written}, expected {sorted(abs_holes_as_written)}."
            )

        # Notes must be consecutive holes (e.g., 1,2 or -4,-5 but not 1,4 or -2,-6)
        abs_holes = abs_holes_as_written
        for i in range(1, len(abs_holes)):
            if abs_holes[i] - abs_holes[i - 1] != 1:
                raise TabTextParserError(
                    f"Chord contains non-consecutive holes at line {line_number}. "
                    f"Harmonica chords must be consecutive holes."
                )

    def _validate_parsed_content(
        self, pages: Dict[str, List[List[List[ParsedNote]]]]
    ) -> None:
        """
        Validate the overall parsed content structure.

        Args:
            pages: Parsed pages to validate

        Raises:
            TabTextParserError: If content validation fails
        """
        if not pages:
            raise TabTextParserError("No pages found in tab file")

        # Check for empty pages if not allowed
        if not self._config.allow_empty_pages:
            empty_pages = [name for name, content in pages.items() if not content]
            if empty_pages:
                raise TabTextParserError(f"Empty pages not allowed: {empty_pages}")

        # Update empty page count
        self._statistics.empty_pages = len(
            [content for content in pages.values() if not content]
        )

    def _finalize_statistics(self) -> None:
        """
        Calculate final statistics after parsing is complete.
        """
        if self._statistics.total_notes > 0:
            # Find hole range from all parsed notes
            all_holes: List[int] = []
            for page_content in self._pages.values():
                for line in page_content:
                    for chord in line:
                        all_holes.extend(abs(note.hole_number) for note in chord)

            if all_holes:
                self._statistics.hole_range = (min(all_holes), max(all_holes))

    # Backwards compatibility properties
    @property
    def file_path(self) -> str:
        """File path property for backwards compatibility."""
        return self._file_path

    @property
    def pages(self) -> Dict[str, List[List[List[int]]]]:
        """Pages property for backwards compatibility - returns hole numbers only."""
        return self.get_pages_as_int()
