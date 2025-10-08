"""
Tab Matcher - Matches parsed tab text with MIDI-derived tab timings.

EXPERIMENTAL FEATURE: Attempts to match tab notation from text files
with timing information from MIDI-generated tabs.

NOTE: This component is complex and may need significant improvement.
See TODO: Analyze and improve tab matching algorithm for better accuracy.
"""

from typing import Dict, List, Optional
from tab_converter.models import TabEntry, Tabs
from tab_phrase_animator.tab_text_parser import ParsedNote


class TabMatcherError(Exception):
    """Custom exception for tab matching errors."""

    pass


class TabMatcher:
    """
    Matches parsed tab chords (from text file) against MIDI-derived Tabs.

    EXPERIMENTAL: This component attempts to synchronize tab notation from text files
    with timing information derived from MIDI analysis. The current algorithm is basic
    and may not handle complex musical phrases accurately.

    TODO: Analyze and contemplate improvements to the matching algorithm:
    - Better handling of chord matching
    - Improved note-to-timing alignment
    - Support for different musical time signatures
    - Handling of grace notes and ornaments
    - More robust error handling for mismatched sequences
    """

    def __init__(self, enable_debug: bool = False):
        """
        Initialize tab matcher.

        Args:
            enable_debug: Whether to print detailed matching debug information
        """
        self.enable_debug = enable_debug
        self._match_statistics = {
            "total_chords_processed": 0,
            "successful_matches": 0,
            "failed_matches": 0,
            "notes_matched": 0,
            "notes_unmatched": 0,
        }

    def match(
        self, midi_tabs: Tabs, parsed_pages: Dict[str, List[List[List[ParsedNote]]]]
    ) -> Dict[str, List[List[Optional[List[TabEntry]]]]]:
        """
        Match parsed tab chords against MIDI-derived tab entries.

        Args:
            midi_tabs: Tabs object with MIDI-derived timing information
            parsed_pages: Dict of page -> lines -> chords -> ParsedNote objects

        Returns:
            Dict mapping pages to lines to chords to matched TabEntries

        Raises:
            TabMatcherError: If matching process fails critically
        """
        if not midi_tabs.tabs:
            raise TabMatcherError("No MIDI tabs provided for matching")

        if not parsed_pages:
            raise TabMatcherError("No parsed pages provided for matching")

        # Reset statistics
        self._reset_statistics()

        # Create working copy of MIDI entries, sorted by time
        midi_entries: List[TabEntry] = sorted(midi_tabs.tabs, key=lambda e: e.time)
        result: Dict[str, List[List[Optional[List[TabEntry]]]]] = {}

        if self.enable_debug:
            print(f"🔍 Starting tab matching with {len(midi_entries)} MIDI entries")

        try:
            for page_name, lines in parsed_pages.items():
                if self.enable_debug:
                    print(f"📄 Processing page: {page_name}")

                page_result = self._match_page(page_name, lines, midi_entries)
                result[page_name] = page_result

            self._print_match_statistics()
            return result

        except Exception as e:
            raise TabMatcherError(f"Tab matching failed: {e}")

    def _match_page(
        self,
        page_name: str,
        lines: List[List[List[ParsedNote]]],
        midi_entries: List[TabEntry],
    ) -> List[List[Optional[List[TabEntry]]]]:
        """Match a single page of tab notation."""
        page_result: List[List[Optional[List[TabEntry]]]] = []

        for line_idx, line in enumerate(lines):
            line_result = self._match_line(
                f"{page_name}:L{line_idx}", line, midi_entries
            )
            page_result.append(line_result)

        return page_result

    def _match_line(
        self,
        line_name: str,
        line: List[List[ParsedNote]],
        midi_entries: List[TabEntry],
    ) -> List[Optional[List[TabEntry]]]:
        """Match a single line of tab notation."""
        line_result: List[Optional[List[TabEntry]]] = []

        for chord_idx, chord in enumerate(line):
            self._match_statistics["total_chords_processed"] += 1

            matched_entries = self._match_chord(
                f"{line_name}:C{chord_idx}", chord, midi_entries
            )

            if matched_entries:
                self._match_statistics["successful_matches"] += 1
                line_result.append(matched_entries)
            else:
                self._match_statistics["failed_matches"] += 1
                if self.enable_debug:
                    print(f"⚠️  No matches found for chord {chord}")
                line_result.append(None)

        return line_result

    def _match_chord(
        self, chord_name: str, chord: List[ParsedNote], midi_entries: List[TabEntry]
    ) -> List[TabEntry] | None:
        """
        Match a single chord (list of ParsedNote objects) with MIDI entries.

        TODO: Improve this algorithm - current implementation is very basic:
        - Uses simple first-match strategy
        - Doesn't consider timing proximity
        - Doesn't handle chord inversions or variations
        - May not work well with complex musical phrases
        """
        matched_entries: List[TabEntry] = []

        for parsed_note in chord:
            match_found = False

            # Simple first-match algorithm (TODO: improve this)
            for idx, entry in enumerate(midi_entries):
                if entry.tab == parsed_note.hole_number:
                    matched_entries.append(
                        TabEntry(
                            tab=parsed_note.hole_number,
                            time=entry.time,
                            duration=entry.duration,
                            confidence=entry.confidence,
                            is_bend=parsed_note.is_bend,
                        )
                    )
                    midi_entries.pop(idx)
                    match_found = True
                    self._match_statistics["notes_matched"] += 1

                    if self.enable_debug:
                        bend_marker = "'" if parsed_note.is_bend else ""
                        print(
                            f"✅ Matched note {parsed_note.hole_number}{bend_marker} at time {entry.time}"
                        )
                    break

            if not match_found:
                self._match_statistics["notes_unmatched"] += 1
                if self.enable_debug:
                    print(f"❌ No MIDI entry found for note {parsed_note.hole_number}")

        return matched_entries if matched_entries else None

    def _reset_statistics(self) -> None:
        """Reset matching statistics."""
        for key in self._match_statistics:
            self._match_statistics[key] = 0

    def _print_match_statistics(self) -> None:
        """Print matching statistics summary."""
        stats = self._match_statistics
        total_chords = stats["total_chords_processed"]
        success_rate = (
            (stats["successful_matches"] / total_chords * 100)
            if total_chords > 0
            else 0
        )

        print("📊 Tab Matching Statistics:")
        print(f"   Chords processed: {total_chords}")
        print(
            f"   Successful matches: {stats['successful_matches']} ({success_rate:.1f}%)"
        )
        print(f"   Failed matches: {stats['failed_matches']}")
        print(f"   Notes matched: {stats['notes_matched']}")
        print(f"   Notes unmatched: {stats['notes_unmatched']}")

    def get_statistics(self) -> Dict[str, int]:
        """Get current matching statistics."""
        return self._match_statistics.copy()
