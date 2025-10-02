"""Tests for tab_phrase_animator.tab_matcher module."""

import pytest
from unittest.mock import patch

from tab_phrase_animator.tab_matcher import (
    TabMatcher,
    TabMatcherError,
)
from tab_converter.models import TabEntry, Tabs


class TestTabMatcherInitialization:
    """Test TabMatcher initialization."""

    def test_init_default(self):
        """Test default initialization."""
        matcher = TabMatcher()
        assert matcher.enable_debug is False
        assert matcher._match_statistics == {
            "total_chords_processed": 0,
            "successful_matches": 0,
            "failed_matches": 0,
            "notes_matched": 0,
            "notes_unmatched": 0,
        }

    def test_init_with_debug(self):
        """Test initialization with debug enabled."""
        matcher = TabMatcher(enable_debug=True)
        assert matcher.enable_debug is True
        assert isinstance(matcher._match_statistics, dict)

    def test_statistics_initialization(self):
        """Test that statistics are properly initialized."""
        matcher = TabMatcher()
        stats = matcher.get_statistics()

        expected_keys = {
            "total_chords_processed",
            "successful_matches",
            "failed_matches",
            "notes_matched",
            "notes_unmatched"
        }
        assert set(stats.keys()) == expected_keys
        assert all(value == 0 for value in stats.values())


class TestTabMatcherValidation:
    """Test input validation and error handling."""

    def test_match_empty_midi_tabs(self):
        """Test matching with empty MIDI tabs."""
        matcher = TabMatcher()
        empty_tabs = Tabs(tabs=[])
        parsed_pages = {"Page 1": [[[1, 2]]]}

        with pytest.raises(TabMatcherError, match="No MIDI tabs provided"):
            matcher.match(empty_tabs, parsed_pages)

    def test_match_empty_parsed_pages(self, sample_midi_tabs):
        """Test matching with empty parsed pages."""
        matcher = TabMatcher()
        empty_pages = {}

        with pytest.raises(TabMatcherError, match="No parsed pages provided"):
            matcher.match(sample_midi_tabs, empty_pages)

    def test_match_midi_tabs_none_tabs_attribute(self):
        """Test matching when tabs attribute is None."""
        matcher = TabMatcher()
        tabs_with_none = Tabs(tabs=None)
        parsed_pages = {"Page 1": [[[1]]]}

        with pytest.raises(TabMatcherError, match="No MIDI tabs provided"):
            matcher.match(tabs_with_none, parsed_pages)


class TestTabMatcherBasicMatching:
    """Test basic tab matching functionality."""

    def test_simple_single_note_match(self):
        """Test matching a single note successfully."""
        matcher = TabMatcher()
        midi_tabs = Tabs(tabs=[
            TabEntry(tab=1, time=1.0, duration=0.5, confidence=0.8)
        ])
        parsed_pages = {"Page 1": [[[1]]]}

        result = matcher.match(midi_tabs, parsed_pages)

        assert "Page 1" in result
        assert len(result["Page 1"]) == 1  # One line
        assert len(result["Page 1"][0]) == 1  # One chord
        assert result["Page 1"][0][0] is not None
        assert len(result["Page 1"][0][0]) == 1  # One note in chord
        assert result["Page 1"][0][0][0].tab == 1

    def test_multiple_notes_match(self):
        """Test matching multiple notes in sequence."""
        matcher = TabMatcher()
        midi_tabs = Tabs(tabs=[
            TabEntry(tab=1, time=1.0, duration=0.5, confidence=0.8),
            TabEntry(tab=2, time=1.5, duration=0.5, confidence=0.8),
            TabEntry(tab=-3, time=2.0, duration=0.5, confidence=0.8),
        ])
        parsed_pages = {"Page 1": [[[1], [2], [-3]]]}

        result = matcher.match(midi_tabs, parsed_pages)

        page_result = result["Page 1"][0]  # First line
        assert len(page_result) == 3  # Three chords
        assert page_result[0][0].tab == 1
        assert page_result[1][0].tab == 2
        assert page_result[2][0].tab == -3

    def test_chord_matching(self):
        """Test matching chords (multiple notes played together)."""
        matcher = TabMatcher()
        midi_tabs = Tabs(tabs=[
            TabEntry(tab=1, time=1.0, duration=0.5, confidence=0.8),
            TabEntry(tab=2, time=1.0, duration=0.5, confidence=0.8),
            TabEntry(tab=3, time=1.5, duration=0.5, confidence=0.8),
        ])
        parsed_pages = {"Page 1": [[[1, 2], [3]]]}

        result = matcher.match(midi_tabs, parsed_pages)

        page_result = result["Page 1"][0]  # First line
        assert len(page_result) == 2  # Two chords

        # First chord should have two notes
        first_chord = page_result[0]
        assert len(first_chord) == 2
        chord_tabs = [entry.tab for entry in first_chord]
        assert 1 in chord_tabs
        assert 2 in chord_tabs

        # Second chord should have one note
        second_chord = page_result[1]
        assert len(second_chord) == 1
        assert second_chord[0].tab == 3

    def test_no_match_found(self):
        """Test behavior when no match is found for a note."""
        matcher = TabMatcher()
        midi_tabs = Tabs(tabs=[
            TabEntry(tab=1, time=1.0, duration=0.5, confidence=0.8)
        ])
        parsed_pages = {"Page 1": [[[2]]]}  # Looking for tab 2, but only have tab 1

        result = matcher.match(midi_tabs, parsed_pages)

        assert result["Page 1"][0][0] is None  # No match found

    def test_partial_chord_matching(self):
        """Test matching when only some notes in a chord are found."""
        matcher = TabMatcher()
        midi_tabs = Tabs(tabs=[
            TabEntry(tab=1, time=1.0, duration=0.5, confidence=0.8),
            # Missing tab=2
            TabEntry(tab=3, time=1.5, duration=0.5, confidence=0.8),
        ])
        parsed_pages = {"Page 1": [[[1, 2]]]}  # Chord needs both 1 and 2

        result = matcher.match(midi_tabs, parsed_pages)

        # Should get a chord with only the matched note
        chord_result = result["Page 1"][0][0]
        assert chord_result is not None
        assert len(chord_result) == 1  # Only one note matched
        assert chord_result[0].tab == 1


class TestTabMatcherMultiplePages:
    """Test matching across multiple pages."""

    def test_multiple_pages_matching(self):
        """Test matching across multiple pages."""
        matcher = TabMatcher()
        midi_tabs = Tabs(tabs=[
            TabEntry(tab=1, time=1.0, duration=0.5, confidence=0.8),
            TabEntry(tab=2, time=1.5, duration=0.5, confidence=0.8),
            TabEntry(tab=3, time=2.0, duration=0.5, confidence=0.8),
            TabEntry(tab=4, time=2.5, duration=0.5, confidence=0.8),
        ])
        parsed_pages = {
            "Page 1": [[[1], [2]]],
            "Page 2": [[[3], [4]]],
        }

        result = matcher.match(midi_tabs, parsed_pages)

        assert "Page 1" in result
        assert "Page 2" in result
        assert result["Page 1"][0][0][0].tab == 1
        assert result["Page 1"][0][1][0].tab == 2
        assert result["Page 2"][0][0][0].tab == 3
        assert result["Page 2"][0][1][0].tab == 4

    def test_multiple_lines_per_page(self):
        """Test matching multiple lines within a page."""
        matcher = TabMatcher()
        midi_tabs = Tabs(tabs=[
            TabEntry(tab=1, time=1.0, duration=0.5, confidence=0.8),
            TabEntry(tab=2, time=1.5, duration=0.5, confidence=0.8),
            TabEntry(tab=3, time=2.0, duration=0.5, confidence=0.8),
            TabEntry(tab=4, time=2.5, duration=0.5, confidence=0.8),
        ])
        parsed_pages = {
            "Page 1": [
                [[1], [2]],  # Line 1
                [[3], [4]],  # Line 2
            ]
        }

        result = matcher.match(midi_tabs, parsed_pages)

        page_result = result["Page 1"]
        assert len(page_result) == 2  # Two lines
        assert page_result[0][0][0].tab == 1  # Line 1, Chord 1
        assert page_result[0][1][0].tab == 2  # Line 1, Chord 2
        assert page_result[1][0][0].tab == 3  # Line 2, Chord 1
        assert page_result[1][1][0].tab == 4  # Line 2, Chord 2


class TestTabMatcherAlgorithmBehavior:
    """Test the specific behavior of the matching algorithm."""

    def test_first_match_algorithm(self):
        """Test that the algorithm uses first-match strategy."""
        matcher = TabMatcher()
        # Create duplicate entries for the same tab
        midi_tabs = Tabs(tabs=[
            TabEntry(tab=1, time=1.0, duration=0.5, confidence=0.8),
            TabEntry(tab=1, time=2.0, duration=0.5, confidence=0.9),  # Same tab, different time
            TabEntry(tab=2, time=3.0, duration=0.5, confidence=0.8),
        ])
        parsed_pages = {"Page 1": [[[1], [1], [2]]]}

        result = matcher.match(midi_tabs, parsed_pages)

        page_result = result["Page 1"][0]

        # First chord should match first MIDI entry
        assert page_result[0][0].time == 1.0

        # Second chord should match second MIDI entry (first was consumed)
        assert page_result[1][0].time == 2.0

        # Third chord should match the remaining entry
        assert page_result[2][0].tab == 2

    def test_midi_entry_consumption(self):
        """Test that MIDI entries are consumed after matching."""
        matcher = TabMatcher()
        midi_tabs = Tabs(tabs=[
            TabEntry(tab=1, time=1.0, duration=0.5, confidence=0.8),
            TabEntry(tab=2, time=2.0, duration=0.5, confidence=0.8),
        ])
        parsed_pages = {"Page 1": [[[1], [1]]]}  # Two chords looking for tab 1

        result = matcher.match(midi_tabs, parsed_pages)

        page_result = result["Page 1"][0]

        # First chord should find the tab 1 entry
        assert page_result[0] is not None
        assert page_result[0][0].tab == 1

        # Second chord should not find tab 1 (it was consumed)
        assert page_result[1] is None

    def test_tab_entry_copying(self):
        """Test that TabEntry objects are properly copied in results."""
        matcher = TabMatcher()
        original_entry = TabEntry(tab=1, time=1.5, duration=0.3, confidence=0.9)
        midi_tabs = Tabs(tabs=[original_entry])
        parsed_pages = {"Page 1": [[[1]]]}

        result = matcher.match(midi_tabs, parsed_pages)

        matched_entry = result["Page 1"][0][0][0]

        # Verify all attributes are copied correctly
        assert matched_entry.tab == original_entry.tab
        assert matched_entry.time == original_entry.time
        assert matched_entry.duration == original_entry.duration
        assert matched_entry.confidence == original_entry.confidence

        # Verify it's a different object (not the same reference)
        assert matched_entry is not original_entry


class TestTabMatcherStatistics:
    """Test statistics tracking and reporting."""

    def test_statistics_tracking_successful_matches(self):
        """Test statistics tracking for successful matches."""
        matcher = TabMatcher()
        midi_tabs = Tabs(tabs=[
            TabEntry(tab=1, time=1.0, duration=0.5, confidence=0.8),
            TabEntry(tab=2, time=1.5, duration=0.5, confidence=0.8),
        ])
        parsed_pages = {"Page 1": [[[1], [2]]]}

        matcher.match(midi_tabs, parsed_pages)
        stats = matcher.get_statistics()

        assert stats["total_chords_processed"] == 2
        assert stats["successful_matches"] == 2
        assert stats["failed_matches"] == 0
        assert stats["notes_matched"] == 2
        assert stats["notes_unmatched"] == 0

    def test_statistics_tracking_failed_matches(self):
        """Test statistics tracking for failed matches."""
        matcher = TabMatcher()
        midi_tabs = Tabs(tabs=[
            TabEntry(tab=1, time=1.0, duration=0.5, confidence=0.8),
        ])
        parsed_pages = {"Page 1": [[[2], [3]]]}  # Looking for tabs that don't exist

        matcher.match(midi_tabs, parsed_pages)
        stats = matcher.get_statistics()

        assert stats["total_chords_processed"] == 2
        assert stats["successful_matches"] == 0
        assert stats["failed_matches"] == 2
        assert stats["notes_matched"] == 0
        assert stats["notes_unmatched"] == 2

    def test_statistics_tracking_mixed_results(self):
        """Test statistics tracking for mixed successful and failed matches."""
        matcher = TabMatcher()
        midi_tabs = Tabs(tabs=[
            TabEntry(tab=1, time=1.0, duration=0.5, confidence=0.8),
            TabEntry(tab=2, time=1.5, duration=0.5, confidence=0.8),
        ])
        parsed_pages = {"Page 1": [[[1, 3], [2, 4]]]}  # Mixed valid/invalid notes

        matcher.match(midi_tabs, parsed_pages)
        stats = matcher.get_statistics()

        assert stats["total_chords_processed"] == 2
        assert stats["successful_matches"] == 2  # Both chords had at least one match
        assert stats["failed_matches"] == 0
        assert stats["notes_matched"] == 2  # Notes 1 and 2 matched
        assert stats["notes_unmatched"] == 2  # Notes 3 and 4 didn't match

    def test_statistics_reset_between_matches(self):
        """Test that statistics are reset between different match operations."""
        matcher = TabMatcher()

        # First match operation
        midi_tabs1 = Tabs(tabs=[TabEntry(tab=1, time=1.0, duration=0.5, confidence=0.8)])
        parsed_pages1 = {"Page 1": [[[1]]]}
        matcher.match(midi_tabs1, parsed_pages1)

        # Second match operation should reset statistics
        midi_tabs2 = Tabs(tabs=[TabEntry(tab=2, time=2.0, duration=0.5, confidence=0.8)])
        parsed_pages2 = {"Page 1": [[[2], [3]]]}  # One match, one miss
        matcher.match(midi_tabs2, parsed_pages2)

        stats = matcher.get_statistics()

        # Should only reflect the second operation
        assert stats["total_chords_processed"] == 2
        assert stats["successful_matches"] == 1
        assert stats["failed_matches"] == 1

    def test_statistics_copying(self):
        """Test that statistics are properly copied and isolated."""
        matcher = TabMatcher()
        midi_tabs = Tabs(tabs=[TabEntry(tab=1, time=1.0, duration=0.5, confidence=0.8)])
        parsed_pages = {"Page 1": [[[1]]]}

        matcher.match(midi_tabs, parsed_pages)
        stats_copy = matcher.get_statistics()

        # Modify internal statistics
        matcher._match_statistics["total_chords_processed"] = 999

        # Verify copy is unaffected
        assert stats_copy["total_chords_processed"] == 1


class TestTabMatcherDebugMode:
    """Test debug mode functionality."""

    def test_debug_output_enabled(self):
        """Test debug output when debug mode is enabled."""
        matcher = TabMatcher(enable_debug=True)
        midi_tabs = Tabs(tabs=[
            TabEntry(tab=1, time=1.0, duration=0.5, confidence=0.8),
        ])
        parsed_pages = {"Page 1": [[[1], [2]]]}  # One match, one miss

        with patch("builtins.print") as mock_print:
            matcher.match(midi_tabs, parsed_pages)

        # Verify debug output was printed
        print_calls = [call[0][0] for call in mock_print.call_args_list]

        # Should have debug messages
        assert any("Starting tab matching" in call for call in print_calls)
        assert any("Processing page: Page 1" in call for call in print_calls)
        assert any("Matched note 1" in call for call in print_calls)
        assert any("No MIDI entry found for note 2" in call for call in print_calls)
        assert any("Tab Matching Statistics" in call for call in print_calls)

    def test_debug_output_disabled(self):
        """Test that debug output is suppressed when debug mode is disabled."""
        matcher = TabMatcher(enable_debug=False)
        midi_tabs = Tabs(tabs=[
            TabEntry(tab=1, time=1.0, duration=0.5, confidence=0.8),
        ])
        parsed_pages = {"Page 1": [[[1]]]}

        with patch("builtins.print") as mock_print:
            matcher.match(midi_tabs, parsed_pages)

        # Should only have statistics output, not detailed debug messages
        print_calls = [call[0][0] for call in mock_print.call_args_list]

        # Should not have detailed debug messages
        assert not any("Processing page:" in call for call in print_calls)
        assert not any("Matched note" in call for call in print_calls)

        # Should still have statistics
        assert any("Tab Matching Statistics" in call for call in print_calls)


class TestTabMatcherErrorHandling:
    """Test error handling and edge cases."""

    def test_match_with_exception_during_processing(self):
        """Test error handling when an exception occurs during matching."""
        matcher = TabMatcher()

        # Create a scenario that might cause an exception
        midi_tabs = Tabs(tabs=[TabEntry(tab=1, time=1.0, duration=0.5, confidence=0.8)])
        parsed_pages = {"Page 1": [[[1]]]}

        # Mock the _match_page method to raise an exception
        with patch.object(matcher, '_match_page', side_effect=ValueError("Test error")):
            with pytest.raises(TabMatcherError, match="Tab matching failed"):
                matcher.match(midi_tabs, parsed_pages)

    def test_match_with_empty_chords_in_parsed_pages(self):
        """Test matching when parsed pages contain empty chords."""
        matcher = TabMatcher()
        midi_tabs = Tabs(tabs=[
            TabEntry(tab=1, time=1.0, duration=0.5, confidence=0.8),
        ])
        parsed_pages = {"Page 1": [[[1], [], []]]}  # Mixed content with empty chords

        result = matcher.match(midi_tabs, parsed_pages)

        page_result = result["Page 1"][0]
        assert page_result[0] is not None  # First chord matched
        assert page_result[1] is None  # Empty chord
        assert page_result[2] is None  # Empty chord

    def test_match_with_zero_confidence_entry(self):
        """Test matching with MIDI entry that has zero confidence."""
        matcher = TabMatcher()
        midi_tabs = Tabs(tabs=[
            TabEntry(tab=1, time=1.0, duration=0.5, confidence=0.0),  # Zero confidence
        ])
        parsed_pages = {"Page 1": [[[1]]]}

        result = matcher.match(midi_tabs, parsed_pages)

        # Should still match and preserve the confidence value
        matched_entry = result["Page 1"][0][0][0]
        assert matched_entry.tab == 1
        assert matched_entry.confidence == 0.0

    def test_match_with_negative_duration(self):
        """Test matching with MIDI entry that has negative duration."""
        matcher = TabMatcher()
        midi_tabs = Tabs(tabs=[
            TabEntry(tab=1, time=1.0, duration=-0.1, confidence=0.8),  # Negative duration
        ])
        parsed_pages = {"Page 1": [[[1]]]}

        result = matcher.match(midi_tabs, parsed_pages)

        # Should still match and preserve the duration value
        matched_entry = result["Page 1"][0][0][0]
        assert matched_entry.tab == 1
        assert matched_entry.duration == -0.1

    def test_large_scale_matching(self):
        """Test matching with a large number of entries."""
        matcher = TabMatcher()

        # Create many MIDI entries
        midi_entries = [
            TabEntry(tab=i % 10 + 1, time=i * 0.1, duration=0.05, confidence=0.8)
            for i in range(100)
        ]
        midi_tabs = Tabs(tabs=midi_entries)

        # Create many parsed entries
        parsed_pages = {
            f"Page {i}": [[[j % 10 + 1] for j in range(10)]]
            for i in range(10)
        }

        result = matcher.match(midi_tabs, parsed_pages)

        # Verify structure is maintained
        assert len(result) == 10  # 10 pages
        for page_name, page_result in result.items():
            assert len(page_result) == 1  # 1 line per page
            assert len(page_result[0]) == 10  # 10 chords per line

        # Verify statistics make sense
        stats = matcher.get_statistics()
        assert stats["total_chords_processed"] == 100  # 10 pages * 10 chords