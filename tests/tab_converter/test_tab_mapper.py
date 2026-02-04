"""Tests for tab_converter.tab_mapper - MIDI to harmonica tab conversion."""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from tab_converter.consts import C_HARMONICA_MAPPING
from tab_converter.models import TabEntry, Tabs
from tab_converter.tab_mapper import TabMapper, TabMapperError


class TestTabMapperInitialization:
    """Test TabMapper initialization and setup."""

    def test_tabmapper_creation_valid(self, harmonica_hole_mapping, temp_test_dir):
        """Test TabMapper creation with valid parameters."""
        mapper = TabMapper(harmonica_hole_mapping, str(temp_test_dir))

        assert mapper._mapping == harmonica_hole_mapping
        assert mapper._json_outputs_path == temp_test_dir
        assert temp_test_dir.exists()

    def test_tabmapper_creation_empty_mapping(self, temp_test_dir):
        """Test TabMapper creation with empty mapping raises error."""
        with pytest.raises(TabMapperError, match="Harmonica mapping cannot be empty"):
            TabMapper({}, str(temp_test_dir))

    def test_tabmapper_creates_output_directory(self, harmonica_hole_mapping):
        """Test that TabMapper creates output directory if it doesn't exist."""
        non_existent_path = "/tmp/test_harmonica_tabs_output"

        # Clean up any existing directory
        import shutil

        if Path(non_existent_path).exists():
            shutil.rmtree(non_existent_path)

        mapper = TabMapper(harmonica_hole_mapping, non_existent_path)
        assert mapper._json_outputs_path.exists()

        # Clean up
        shutil.rmtree(non_existent_path)

    def test_tabmapper_with_c_harmonica_mapping(self, temp_test_dir):
        """Test TabMapper with actual C harmonica mapping."""
        mapper = TabMapper(C_HARMONICA_MAPPING, str(temp_test_dir))
        assert len(mapper._mapping) == len(C_HARMONICA_MAPPING)
        assert 60 in mapper._mapping  # C4
        assert mapper._mapping[60] == 1  # Blow hole 1


class TestNoteEventConversion:
    """Test conversion of individual note events to TabEntry objects."""

    def test_convert_valid_note_event(self, harmonica_hole_mapping, temp_test_dir):
        """Test conversion of valid note event to TabEntry."""
        mapper = TabMapper(harmonica_hole_mapping, str(temp_test_dir))

        # Event tuple: (start, end, pitch, confidence, activation)
        event_tuple = (1.0, 2.5, 60, 0.9, [0.1, 0.8, 0.5])

        tab_entry = mapper._convert_note_event_to_tab(event_tuple)

        assert tab_entry is not None
        assert tab_entry.tab == 1  # C4 -> Hole 1 blow
        assert tab_entry.time == 1.0
        assert tab_entry.duration == 1.5  # 2.5 - 1.0
        assert tab_entry.confidence == 0.9

    def test_convert_unmapped_pitch(self, harmonica_hole_mapping, temp_test_dir):
        """Test conversion of unmapped pitch returns None."""
        mapper = TabMapper(harmonica_hole_mapping, str(temp_test_dir))

        # Pitch 50 is not in our test mapping
        event_tuple = (1.0, 2.0, 50, 0.8, [0.5])

        tab_entry = mapper._convert_note_event_to_tab(event_tuple)
        assert tab_entry is None

    def test_convert_invalid_timing(self, harmonica_hole_mapping, temp_test_dir):
        """Test conversion with invalid timing (end <= start)."""
        mapper = TabMapper(harmonica_hole_mapping, str(temp_test_dir))

        # End time equals start time
        event_tuple = (2.0, 2.0, 60, 0.8, [0.5])

        with patch("builtins.print") as mock_print:
            tab_entry = mapper._convert_note_event_to_tab(event_tuple)
            assert tab_entry is None
            mock_print.assert_called_with("⚠️  Warning: Invalid timing for pitch 60")

    def test_convert_negative_duration(self, harmonica_hole_mapping, temp_test_dir):
        """Test conversion with negative duration (end < start)."""
        mapper = TabMapper(harmonica_hole_mapping, str(temp_test_dir))

        # End time before start time
        event_tuple = (2.0, 1.0, 60, 0.8, [0.5])

        with patch("builtins.print"):
            tab_entry = mapper._convert_note_event_to_tab(event_tuple)
            assert tab_entry is None

    def test_convert_draw_note(self, harmonica_hole_mapping, temp_test_dir):
        """Test conversion of draw note (negative tab value)."""
        mapper = TabMapper(harmonica_hole_mapping, str(temp_test_dir))

        # E4 (pitch 64) -> Draw hole -1 in our test mapping
        event_tuple = (0.5, 1.2, 64, 0.85, [0.5])

        tab_entry = mapper._convert_note_event_to_tab(event_tuple)

        assert tab_entry is not None
        assert tab_entry.tab == -1  # Draw note
        assert tab_entry.time == 0.5
        assert tab_entry.duration == 0.7
        assert tab_entry.confidence == 0.85

    def test_convert_precision_rounding(self, harmonica_hole_mapping, temp_test_dir):
        """Test that values are rounded to 5 decimal places."""
        mapper = TabMapper(harmonica_hole_mapping, str(temp_test_dir))

        # Use floating point numbers that would need rounding
        event_tuple = (1.123456789, 2.987654321, 60, 0.876543219, [0.5])

        tab_entry = mapper._convert_note_event_to_tab(event_tuple)

        assert tab_entry.time == 1.12346  # Rounded to 5 decimal places
        assert tab_entry.duration == 1.8642  # 2.98765 - 1.12346
        assert tab_entry.confidence == 0.87654


class TestNoteEventsToTabs:
    """Test conversion of multiple note events to Tabs object."""

    def test_convert_multiple_events_success(
        self, harmonica_hole_mapping, temp_test_dir
    ):
        """Test successful conversion of multiple note events."""
        mapper = TabMapper(harmonica_hole_mapping, str(temp_test_dir))

        events = [
            (0.0, 1.0, 60, 0.9, [0.5]),  # C4 -> Hole 1 blow
            (1.0, 2.0, 64, 0.85, [0.5]),  # E4 -> Hole 1 draw
            (2.0, 3.0, 67, 0.95, [0.5]),  # G4 -> Hole 2 blow
        ]

        with patch("builtins.print"):
            tabs = mapper.note_events_to_tabs(events)

        assert isinstance(tabs, Tabs)
        assert len(tabs.tabs) == 3

        # Check they're sorted by time
        assert tabs.tabs[0].time == 0.0
        assert tabs.tabs[1].time == 1.0
        assert tabs.tabs[2].time == 2.0

        # Check tab values
        assert tabs.tabs[0].tab == 1  # Blow
        assert tabs.tabs[1].tab == -1  # Draw
        assert tabs.tabs[2].tab == 2  # Blow

    def test_convert_empty_events_raises_error(
        self, harmonica_hole_mapping, temp_test_dir
    ):
        """Test that empty events list raises error."""
        mapper = TabMapper(harmonica_hole_mapping, str(temp_test_dir))

        with pytest.raises(TabMapperError, match="No note events provided"):
            mapper.note_events_to_tabs([])

    def test_convert_all_unmapped_events_raises_error(
        self, harmonica_hole_mapping, temp_test_dir
    ):
        """Test that all unmapped events raises error."""
        mapper = TabMapper(harmonica_hole_mapping, str(temp_test_dir))

        # All pitches not in mapping
        events = [
            (0.0, 1.0, 50, 0.9, [0.5]),
            (1.0, 2.0, 51, 0.85, [0.5]),
            (2.0, 3.0, 52, 0.95, [0.5]),
        ]

        with patch("builtins.print"):
            with pytest.raises(
                TabMapperError, match="No valid harmonica tabs could be created"
            ):
                mapper.note_events_to_tabs(events)

    def test_convert_mixed_valid_invalid_events(
        self, harmonica_hole_mapping, temp_test_dir
    ):
        """Test conversion with mix of valid and invalid events."""
        mapper = TabMapper(harmonica_hole_mapping, str(temp_test_dir))

        events = [
            (0.0, 1.0, 60, 0.9, [0.5]),  # Valid: C4 -> Hole 1 blow
            (1.0, 2.0, 50, 0.85, [0.5]),  # Invalid: unmapped pitch
            (2.0, 3.0, 67, 0.95, [0.5]),  # Valid: G4 -> Hole 2 blow
            (3.0, 3.0, 72, 0.8, [0.5]),  # Invalid: zero duration
        ]

        with patch("builtins.print") as mock_print:
            tabs = mapper.note_events_to_tabs(events)

        assert len(tabs.tabs) == 2  # Only 2 valid events
        assert tabs.tabs[0].tab == 1  # C4
        assert tabs.tabs[1].tab == 2  # G4

        # Check warning message was printed
        expected_call = "🎼 Mapped 2 valid tabs, skipped 2 notes"
        mock_print.assert_any_call(expected_call)

    def test_convert_events_sorted_by_time(self, harmonica_hole_mapping, temp_test_dir):
        """Test that result tabs are sorted by time regardless of input order."""
        mapper = TabMapper(harmonica_hole_mapping, str(temp_test_dir))

        # Events in non-chronological order
        events = [
            (2.0, 3.0, 67, 0.95, [0.5]),  # G4 at time 2.0
            (0.0, 1.0, 60, 0.9, [0.5]),  # C4 at time 0.0
            (1.0, 2.0, 64, 0.85, [0.5]),  # E4 at time 1.0
        ]

        with patch("builtins.print"):
            tabs = mapper.note_events_to_tabs(events)

        # Should be sorted by time
        times = [entry.time for entry in tabs.tabs]
        assert times == [0.0, 1.0, 2.0]

    def test_convert_malformed_event_tuple(self, harmonica_hole_mapping, temp_test_dir):
        """Test handling of malformed event tuples."""
        mapper = TabMapper(harmonica_hole_mapping, str(temp_test_dir))

        events = [
            (0.0, 1.0, 60, 0.9, [0.5]),  # Valid event
            (1.0, 2.0),  # Malformed: too few elements
            (2.0, 3.0, 67, 0.95, [0.5]),  # Valid event
        ]

        with patch("builtins.print") as mock_print:
            tabs = mapper.note_events_to_tabs(events)

        assert len(tabs.tabs) == 2  # Only valid events converted
        # Check that warning was printed for malformed event
        assert any(
            "Skipping invalid note event" in str(call)
            for call in mock_print.call_args_list
        )


class TestTabsJsonSaving:
    """Test JSON saving functionality."""

    def test_save_tabs_to_json_success(
        self, harmonica_hole_mapping, temp_test_dir, sample_tabs
    ):
        """Test successful saving of tabs to JSON."""
        mapper = TabMapper(harmonica_hole_mapping, str(temp_test_dir))
        filename = "test_tabs.json"

        with patch("builtins.print") as mock_print:
            mapper.save_tabs_to_json(sample_tabs, filename)

        # Check file was created
        json_file = temp_test_dir / filename
        assert json_file.exists()

        # Check file contents
        with json_file.open() as f:
            data = json.load(f)

        assert len(data) == len(sample_tabs.tabs)

        # Check first entry structure
        first_entry = data[0]
        expected_keys = {"tab", "time", "duration", "confidence"}
        assert set(first_entry.keys()) == expected_keys

        # Check success message
        expected_msg = f"💾 Saved {len(sample_tabs.tabs)} tabs to {json_file}"
        mock_print.assert_called_with(expected_msg)

    def test_save_tabs_json_structure(self, harmonica_hole_mapping, temp_test_dir):
        """Test the structure of saved JSON data."""
        mapper = TabMapper(harmonica_hole_mapping, str(temp_test_dir))

        # Create specific tabs for testing
        test_tabs = Tabs(
            [
                TabEntry(tab=1, time=0.5, duration=1.0, confidence=0.8),
                TabEntry(tab=-2, time=1.5, duration=0.7, confidence=0.9),
            ]
        )

        filename = "structure_test.json"
        with patch("builtins.print"):
            mapper.save_tabs_to_json(test_tabs, filename)

        # Load and verify structure
        json_file = temp_test_dir / filename
        with json_file.open() as f:
            data = json.load(f)

        assert len(data) == 2

        # Check first entry
        assert data[0]["tab"] == 1
        assert data[0]["time"] == 0.5
        assert data[0]["duration"] == 1.0
        assert data[0]["confidence"] == 0.8

        # Check second entry (draw note)
        assert data[1]["tab"] == -2
        assert data[1]["time"] == 1.5
        assert data[1]["duration"] == 0.7
        assert data[1]["confidence"] == 0.9

    def test_save_tabs_json_write_error(
        self, harmonica_hole_mapping, sample_tabs, temp_test_dir
    ):
        """Test handling of JSON write errors."""
        mapper = TabMapper(harmonica_hole_mapping, str(temp_test_dir))

        # Mock json.dump to raise an exception
        with (
            patch("json.dump", side_effect=IOError("Mocked write error")),
            patch("builtins.print") as mock_print,
        ):
            mapper.save_tabs_to_json(sample_tabs, "test.json")

        # Should print warning message
        assert any(
            "Could not save tabs to JSON" in str(call)
            for call in mock_print.call_args_list
        )


class TestMappingInfo:
    """Test harmonica mapping information methods."""

    def test_get_mapping_info_basic(self, harmonica_hole_mapping, temp_test_dir):
        """Test basic mapping info functionality."""
        mapper = TabMapper(harmonica_hole_mapping, str(temp_test_dir))
        info = mapper.get_mapping_info()

        expected_keys = {
            "total_mapped_pitches",
            "pitch_range_min",
            "pitch_range_max",
            "blow_holes",
            "draw_holes",
        }
        assert set(info.keys()) == expected_keys

        assert info["total_mapped_pitches"] == len(harmonica_hole_mapping)
        assert info["pitch_range_min"] == min(harmonica_hole_mapping.keys())
        assert info["pitch_range_max"] == max(harmonica_hole_mapping.keys())

    def test_get_mapping_info_blow_draw_count(self, temp_test_dir):
        """Test counting of blow vs draw holes."""
        test_mapping = {
            60: 1,  # Blow
            64: -1,  # Draw
            67: 2,  # Blow
            71: -2,  # Draw
            72: 3,  # Blow
        }

        mapper = TabMapper(test_mapping, str(temp_test_dir))
        info = mapper.get_mapping_info()

        assert info["blow_holes"] == 3  # Positive values
        assert info["draw_holes"] == 2  # Negative values
        assert info["total_mapped_pitches"] == 5

    def test_get_mapping_info_c_harmonica(self, temp_test_dir):
        """Test mapping info with actual C harmonica mapping."""
        mapper = TabMapper(C_HARMONICA_MAPPING, str(temp_test_dir))
        info = mapper.get_mapping_info()

        # C_HARMONICA_MAPPING should have specific characteristics
        # Note: Mapping now includes octave expansions (+/- 12 semitones)
        assert info["total_mapped_pitches"] == len(C_HARMONICA_MAPPING)
        assert info["pitch_range_min"] == 48  # C3 (octave below C4)
        assert info["pitch_range_max"] == 108  # C8 (octave above C7)

        # Count blow vs draw from actual mapping
        expected_blow = len([v for v in C_HARMONICA_MAPPING.values() if v > 0])
        expected_draw = len([v for v in C_HARMONICA_MAPPING.values() if v < 0])

        assert info["blow_holes"] == expected_blow
        assert info["draw_holes"] == expected_draw


class TestTabMapperIntegration:
    """Integration tests combining multiple TabMapper features."""

    def test_full_pipeline_with_c_mapping(self, temp_test_dir):
        """Test complete pipeline using C harmonica mapping."""
        mapper = TabMapper(C_HARMONICA_MAPPING, str(temp_test_dir))

        # Create events using actual C harmonica pitches
        events = [
            (0.0, 1.0, 60, 0.9, [0.5]),  # C4 -> Blow 1
            (1.0, 2.0, 62, 0.85, [0.5]),  # D4 -> Draw 1
            (2.0, 3.0, 64, 0.95, [0.5]),  # E4 -> Blow 2
            (3.0, 4.0, 67, 0.88, [0.5]),  # G4 -> Blow 3
            (4.0, 5.0, 72, 0.75, [0.5]),  # C5 -> Blow 4
        ]

        with patch("builtins.print"):
            tabs = mapper.note_events_to_tabs(events)
            mapper.save_tabs_to_json(tabs, "integration_test.json")

        # Check results
        assert len(tabs.tabs) == 5
        assert tabs.tabs[0].tab == 1  # Blow 1
        assert tabs.tabs[1].tab == -1  # Draw 1
        assert tabs.tabs[2].tab == 2  # Blow 2
        assert tabs.tabs[3].tab == 3  # Blow 3
        assert tabs.tabs[4].tab == 4  # Blow 4

        # Check JSON file was created
        json_file = temp_test_dir / "integration_test.json"
        assert json_file.exists()

        # Verify mapping info
        info = mapper.get_mapping_info()
        assert info["total_mapped_pitches"] == len(C_HARMONICA_MAPPING)

    def test_edge_cases_combined(self, harmonica_hole_mapping, temp_test_dir):
        """Test multiple edge cases in combination."""
        mapper = TabMapper(harmonica_hole_mapping, str(temp_test_dir))

        # Mix of valid, invalid timing, unmapped, and malformed events
        events = [
            (0.0, 1.0, 60, 0.9, [0.5]),  # Valid
            (1.0, 1.0, 64, 0.85, [0.5]),  # Invalid timing (zero duration)
            (2.0, 3.0, 999, 0.95, [0.5]),  # Unmapped pitch
            (3.0, 2.0, 67, 0.88, [0.5]),  # Invalid timing (negative duration)
            (4.0, 5.0, 72, 0.75, [0.5]),  # Valid
            (5.0,),  # Malformed tuple
        ]

        with patch("builtins.print"):
            tabs = mapper.note_events_to_tabs(events)

        # Should only get 2 valid tabs
        assert len(tabs.tabs) == 2
        assert tabs.tabs[0].time == 0.0  # First valid event
        assert tabs.tabs[1].time == 4.0  # Second valid event


class TestBendMapping:
    """Test bend note mapping functionality."""

    def test_bend_mapping_single_bend(self, temp_test_dir):
        """Test that bend notes are properly detected and marked."""
        from tab_converter.consts import C_HARMONICA_BENDS

        # Use C harmonica mapping with bends
        harmonica_mapping = {60: 1, 62: -1, 64: 2, 67: 3}  # Simple mapping
        bend_mapping = C_HARMONICA_BENDS

        mapper = TabMapper(harmonica_mapping, str(temp_test_dir), bend_mapping)

        # MIDI 61 is -1' (draw 1 half-step bend) in C harmonica
        events = [
            (0.0, 1.0, 61, 0.9, [0.5]),  # Db4 -> -1' bend
        ]

        with patch("builtins.print"):
            tabs = mapper.note_events_to_tabs(events)

        assert len(tabs.tabs) == 1
        assert tabs.tabs[0].tab == -1  # Draw hole 1
        assert tabs.tabs[0].is_bend is True
        assert tabs.tabs[0].bend_notation == "'"

    def test_bend_mapping_double_bend(self, temp_test_dir):
        """Test double bend notation."""
        from tab_converter.consts import C_HARMONICA_BENDS

        harmonica_mapping = {60: 1, 62: -1, 64: 2, 67: 3}
        bend_mapping = C_HARMONICA_BENDS

        mapper = TabMapper(harmonica_mapping, str(temp_test_dir), bend_mapping)

        # MIDI 65 is -2'' (draw 2 full-step bend) in C harmonica
        events = [
            (0.0, 1.0, 65, 0.9, [0.5]),  # F4 -> -2'' bend
        ]

        with patch("builtins.print"):
            tabs = mapper.note_events_to_tabs(events)

        assert len(tabs.tabs) == 1
        assert tabs.tabs[0].tab == -2
        assert tabs.tabs[0].is_bend is True
        assert tabs.tabs[0].bend_notation == "''"

    def test_bend_mapping_triple_bend(self, temp_test_dir):
        """Test triple bend notation on hole 3."""
        from tab_converter.consts import C_HARMONICA_BENDS

        harmonica_mapping = {60: 1, 62: -1, 64: 2, 67: 3, 71: -3}
        bend_mapping = C_HARMONICA_BENDS

        mapper = TabMapper(harmonica_mapping, str(temp_test_dir), bend_mapping)

        # MIDI 68 is -3''' (draw 3 triple bend) in C harmonica
        events = [
            (0.0, 1.0, 68, 0.9, [0.5]),  # Ab4 -> -3''' bend
        ]

        with patch("builtins.print"):
            tabs = mapper.note_events_to_tabs(events)

        assert len(tabs.tabs) == 1
        assert tabs.tabs[0].tab == -3
        assert tabs.tabs[0].is_bend is True
        assert tabs.tabs[0].bend_notation == "'''"

    def test_pure_note_priority_over_bend(self, temp_test_dir):
        """Test that pure notes take priority over bend mappings."""
        # Create overlapping mappings to test priority
        harmonica_mapping = {61: 99}  # Pure note mapping for pitch 61
        bend_mapping = {61: (-1, "'")}  # Bend mapping for same pitch

        mapper = TabMapper(harmonica_mapping, str(temp_test_dir), bend_mapping)

        events = [
            (0.0, 1.0, 61, 0.9, [0.5]),
        ]

        with patch("builtins.print"):
            tabs = mapper.note_events_to_tabs(events)

        # Pure note should take priority over bend
        assert tabs.tabs[0].tab == 99
        assert tabs.tabs[0].is_bend is False
        assert tabs.tabs[0].bend_notation == ""

    def test_bend_mapping_with_regular_notes(self, temp_test_dir):
        """Test mixing bend and regular notes."""
        from tab_converter.consts import C_HARMONICA_BENDS

        harmonica_mapping = {60: 1, 62: -1, 64: 2, 67: 3}
        bend_mapping = C_HARMONICA_BENDS

        mapper = TabMapper(harmonica_mapping, str(temp_test_dir), bend_mapping)

        events = [
            (0.0, 1.0, 60, 0.9, [0.5]),  # Regular: C4 -> Blow 1
            (1.0, 2.0, 61, 0.9, [0.5]),  # Bend: Db4 -> -1'
            (2.0, 3.0, 62, 0.9, [0.5]),  # Regular: D4 -> Draw 1
        ]

        with patch("builtins.print"):
            tabs = mapper.note_events_to_tabs(events)

        assert len(tabs.tabs) == 3

        # First note: regular blow 1
        assert tabs.tabs[0].tab == 1
        assert tabs.tabs[0].is_bend is False
        assert tabs.tabs[0].bend_notation == ""

        # Second note: bend -1'
        assert tabs.tabs[1].tab == -1
        assert tabs.tabs[1].is_bend is True
        assert tabs.tabs[1].bend_notation == "'"

        # Third note: regular draw 1
        assert tabs.tabs[2].tab == -1
        assert tabs.tabs[2].is_bend is False
        assert tabs.tabs[2].bend_notation == ""

    def test_g_harmonica_bends(self, temp_test_dir):
        """Test G harmonica bend mappings."""
        from tab_converter.consts import G_HARMONICA_BENDS

        harmonica_mapping = {55: 1, 57: -1}
        bend_mapping = G_HARMONICA_BENDS

        mapper = TabMapper(harmonica_mapping, str(temp_test_dir), bend_mapping)

        # MIDI 56 is -1' (Ab3) in G harmonica
        events = [
            (0.0, 1.0, 56, 0.9, [0.5]),
        ]

        with patch("builtins.print"):
            tabs = mapper.note_events_to_tabs(events)

        assert len(tabs.tabs) == 1
        assert tabs.tabs[0].tab == -1
        assert tabs.tabs[0].is_bend is True
        assert tabs.tabs[0].bend_notation == "'"

    def test_bend_mapping_octave_expansion(self, temp_test_dir):
        """Test that bend mappings include octave expansions."""
        from tab_converter.consts import C_HARMONICA_BENDS

        harmonica_mapping = {60: 1, 62: -1}

        mapper = TabMapper(harmonica_mapping, str(temp_test_dir), C_HARMONICA_BENDS)

        # MIDI 61 is the base -1' bend, MIDI 73 is one octave up
        # (but 73 is also -4' in C harmonica, so test with 49 which is 61-12)
        events = [
            (0.0, 1.0, 49, 0.9, [0.5]),  # One octave below -1' bend
        ]

        with patch("builtins.print"):
            tabs = mapper.note_events_to_tabs(events)

        assert len(tabs.tabs) == 1
        assert tabs.tabs[0].is_bend is True
        assert tabs.tabs[0].bend_notation == "'"


class TestCreateTabMapperFactory:
    """Test the create_tab_mapper factory function."""

    def test_factory_creates_valid_mapper_for_c(self, temp_test_dir):
        """Test factory creates valid TabMapper for C key."""
        from tab_converter.tab_mapper import create_tab_mapper

        mapper = create_tab_mapper("C", output_path=str(temp_test_dir))

        assert isinstance(mapper, TabMapper)
        # C harmonica should have MIDI 60 -> hole 1
        assert 60 in mapper._mapping
        assert mapper._mapping[60] == 1

    def test_factory_creates_valid_mapper_for_g(self, temp_test_dir):
        """Test factory creates valid TabMapper for G key."""
        from tab_converter.tab_mapper import create_tab_mapper

        mapper = create_tab_mapper("G", output_path=str(temp_test_dir))

        assert isinstance(mapper, TabMapper)
        # G harmonica should have MIDI 55 -> hole 1 (G3)
        assert 55 in mapper._mapping
        assert mapper._mapping[55] == 1

    def test_factory_includes_bend_mapping(self, temp_test_dir):
        """Test factory includes bend mappings."""
        from tab_converter.tab_mapper import create_tab_mapper

        mapper = create_tab_mapper("C", output_path=str(temp_test_dir))

        # C harmonica should have bend for MIDI 61 (-1')
        assert 61 in mapper._bend_mapping
        assert mapper._bend_mapping[61] == (-1, "'")

    def test_factory_invalid_key_raises_error(self, temp_test_dir):
        """Test factory raises error for invalid key."""
        from tab_converter.tab_mapper import create_tab_mapper

        with pytest.raises(ValueError):
            create_tab_mapper("X", output_path=str(temp_test_dir))

    def test_factory_case_insensitive_key(self, temp_test_dir):
        """Test factory accepts lowercase key names."""
        from tab_converter.tab_mapper import create_tab_mapper

        # Should work with lowercase
        mapper = create_tab_mapper("c", output_path=str(temp_test_dir))
        assert isinstance(mapper, TabMapper)

        # Should work with mixed case
        mapper = create_tab_mapper("Bb", output_path=str(temp_test_dir))
        assert isinstance(mapper, TabMapper)

    def test_factory_all_keys_work(self, temp_test_dir):
        """Test factory works for all 12 harmonica keys."""
        from tab_converter.tab_mapper import create_tab_mapper

        keys = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"]

        for key in keys:
            mapper = create_tab_mapper(key, output_path=str(temp_test_dir))
            assert isinstance(mapper, TabMapper), f"Failed for key {key}"
            # Each key should have at least some mappings
            assert len(mapper._mapping) > 0, f"No mappings for key {key}"
