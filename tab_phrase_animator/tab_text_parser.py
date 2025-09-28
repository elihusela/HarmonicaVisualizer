"""
TabTextParser - Parses harmonica tablature text files.

Handles loading and parsing of tab files with page-based organization,
validation, and comprehensive error handling.
"""

import os
from dataclasses import dataclass
from typing import Dict, List, Optional


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

    def get_pages(self) -> Dict[str, List[List[List[int]]]]:
        """
        Get parsed tab pages.

        Returns:
            Dictionary mapping page names to lists of lines of chords
        """
        return self._pages.copy()

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

    def _load_and_parse(self) -> Dict[str, List[List[List[int]]]]:
        """
        Load and parse the tab file.

        Returns:
            Dictionary mapping page names to parsed content

        Raises:
            TabTextParserError: If parsing fails
        """
        pages: Dict[str, List[List[List[int]]]] = {}
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
                        current_page = line.rstrip(":").strip()
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

    def _parse_tab_line(self, line: str, line_number: int) -> List[List[int]]:
        """
        Parse a single tab line into chords.

        Args:
            line: Raw tab line to parse
            line_number: Line number for error reporting

        Returns:
            List of chords, where each chord is a list of hole numbers

        Raises:
            TabTextParserError: If parsing fails
        """
        chords: List[List[int]] = []
        current_chord: List[int] = []
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
                for digit_char in digits_str:
                    hole_number = -int(digit_char)
                    self._validate_hole_number(hole_number, line_number)
                    current_chord.append(hole_number)
                    self._statistics.total_notes += 1

            elif char.isdigit():
                # Parse positive (blow) notes
                start_pos = i
                while i < len(line) and line[i].isdigit():
                    i += 1

                digits_str = line[start_pos:i]
                for digit_char in digits_str:
                    hole_number = int(digit_char)
                    self._validate_hole_number(hole_number, line_number)
                    current_chord.append(hole_number)
                    self._statistics.total_notes += 1

            elif char.isspace():
                # Space separates chords
                if current_chord:
                    chords.append(current_chord)
                    self._statistics.total_chords += 1
                    current_chord = []
                i += 1

            else:
                # Skip other characters (comments, etc.)
                i += 1

        # Add final chord if exists
        if current_chord:
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

    def _validate_parsed_content(self, pages: Dict[str, List[List[List[int]]]]) -> None:
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
                        all_holes.extend(abs(note) for note in chord)

            if all_holes:
                self._statistics.hole_range = (min(all_holes), max(all_holes))

    # Backwards compatibility properties
    @property
    def file_path(self) -> str:
        """File path property for backwards compatibility."""
        return self._file_path

    @property
    def pages(self) -> Dict[str, List[List[List[int]]]]:
        """Pages property for backwards compatibility."""
        return self._pages
