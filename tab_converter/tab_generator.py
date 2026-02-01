"""
Tab Generator - Converts TabEntry objects to harmonica tab text file format.

Generates .txt tab files from MIDI-derived TabEntry objects, with automatic
chord detection, line breaks, and page breaks based on timing.
"""

from dataclasses import dataclass
from typing import List, Optional

from tab_converter.models import TabEntry, Tabs


@dataclass
class TabGeneratorConfig:
    """Configuration for tab file generation."""

    notes_per_line: int = 6  # Max notes/chords per line
    notes_per_page: int = 24  # Max notes/chords per page (4 lines)
    line_gap_threshold: float = 0.5  # Seconds of silence to force line break
    page_gap_threshold: float = 2.0  # Seconds of silence to force page break
    chord_time_tolerance: float = 0.05  # Max time diff (s) to group as chord


class TabGeneratorError(Exception):
    """Error during tab generation."""

    pass


class TabGenerator:
    """
    Generates harmonica tab text files from TabEntry objects.

    Converts MIDI-derived tabs into the standard text format:
    - Pages: `page N:` headers
    - Lines: Space-separated notes/chords
    - Notes: `6`, `-5` (blow/draw)
    - Chords: `56`, `-4-5` (consecutive holes)
    """

    def __init__(self, config: Optional[TabGeneratorConfig] = None):
        """
        Initialize tab generator.

        Args:
            config: Optional configuration for generation parameters
        """
        self.config = config or TabGeneratorConfig()

    def generate(self, tabs: Tabs) -> str:
        """
        Generate tab file content from TabEntry objects.

        Args:
            tabs: Tabs object containing TabEntry list

        Returns:
            Formatted tab file content as string

        Raises:
            TabGeneratorError: If generation fails
        """
        if not tabs.tabs:
            raise TabGeneratorError("No tabs to generate")

        # Sort tabs by time
        sorted_tabs = sorted(tabs.tabs, key=lambda t: t.time)

        # Group into chords (simultaneous notes)
        chords = self._group_into_chords(sorted_tabs)

        # Split into pages based on timing and count
        pages = self._split_into_pages(chords)

        # Format as text
        return self._format_pages(pages)

    def _group_into_chords(self, tabs: List[TabEntry]) -> List[List[TabEntry]]:
        """
        Group simultaneous notes into chords.

        Args:
            tabs: Sorted list of TabEntry objects

        Returns:
            List of chords (each chord is a list of TabEntry)
        """
        if not tabs:
            return []

        chords: List[List[TabEntry]] = []
        current_chord: List[TabEntry] = [tabs[0]]

        for tab in tabs[1:]:
            # Check if this note is simultaneous with current chord
            time_diff = abs(tab.time - current_chord[0].time)

            if time_diff <= self.config.chord_time_tolerance:
                current_chord.append(tab)
            else:
                # Save current chord, start new one
                chords.append(current_chord)
                current_chord = [tab]

        # Don't forget the last chord
        chords.append(current_chord)

        return chords

    def _split_into_pages(
        self, chords: List[List[TabEntry]]
    ) -> List[List[List[List[TabEntry]]]]:
        """
        Split chords into pages and lines.

        Args:
            chords: List of chords

        Returns:
            Nested structure: pages -> lines -> chords
        """
        if not chords:
            return []

        pages: List[List[List[List[TabEntry]]]] = []
        current_page: List[List[List[TabEntry]]] = []
        current_line: List[List[TabEntry]] = []
        page_chord_count = 0
        prev_chord_end = 0.0

        for chord in chords:
            chord_time = chord[0].time
            chord_end = max(t.time + t.duration for t in chord)

            # Calculate gap from previous chord
            gap = chord_time - prev_chord_end if prev_chord_end > 0 else 0

            # Check for page break (long pause or max notes)
            if gap >= self.config.page_gap_threshold or (
                page_chord_count >= self.config.notes_per_page and current_line
            ):
                # Save current line to page
                if current_line:
                    current_page.append(current_line)
                    current_line = []

                # Save current page
                if current_page:
                    pages.append(current_page)
                    current_page = []
                    page_chord_count = 0

            # Check for line break (medium pause or max notes per line)
            elif (
                gap >= self.config.line_gap_threshold
                or len(current_line) >= self.config.notes_per_line
            ):
                if current_line:
                    current_page.append(current_line)
                    current_line = []

            # Add chord to current line
            current_line.append(chord)
            page_chord_count += 1
            prev_chord_end = chord_end

        # Save remaining content
        if current_line:
            current_page.append(current_line)
        if current_page:
            pages.append(current_page)

        return pages

    def _format_pages(self, pages: List[List[List[List[TabEntry]]]]) -> str:
        """
        Format pages into tab file text.

        Args:
            pages: Nested structure of pages -> lines -> chords

        Returns:
            Formatted tab file content
        """
        lines = []

        for page_num, page in enumerate(pages, 1):
            lines.append(f"page {page_num}:")

            for line in page:
                formatted_chords = []
                for chord in line:
                    formatted_chords.append(self._format_chord(chord))
                lines.append(" ".join(formatted_chords))

            # Add blank line between pages (except after last)
            if page_num < len(pages):
                lines.append("")

        return "\n".join(lines)

    def _format_chord(self, chord: List[TabEntry]) -> str:
        """
        Format a chord (one or more simultaneous notes) as tab notation.

        Args:
            chord: List of TabEntry objects in the chord

        Returns:
            Formatted chord string (e.g., "6", "-5", "56", "-4-5")
        """
        if not chord:
            return ""

        # Sort by absolute hole number for consistent output
        sorted_notes = sorted(chord, key=lambda t: abs(t.tab))

        # Check if all notes are same direction (blow or draw)
        is_draw = sorted_notes[0].tab < 0

        # Build chord string
        parts = []
        for note in sorted_notes:
            hole = abs(note.tab)
            if note.tab < 0:
                parts.append(f"-{hole}")
            else:
                parts.append(str(hole))

        # For chords, join without spaces
        # e.g., blow chord: "56" (holes 5 and 6)
        # e.g., draw chord: "-4-5" (draw 4 and 5)
        if len(parts) == 1:
            result = parts[0]
        else:
            # Multi-note chord
            if is_draw:
                # Draw chord: -4-5-6
                result = "".join(parts)
            else:
                # Blow chord: 456 (just concatenate digits)
                result = "".join(str(abs(n.tab)) for n in sorted_notes)

        # Add bend notation if present
        if len(chord) == 1 and chord[0].is_bend:
            bend = chord[0].bend_notation or "'"
            result += bend

        return result
