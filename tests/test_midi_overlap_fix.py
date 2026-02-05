"""Tests for MIDI processor overlap fixing functionality."""

import pytest
from harmonica_pipeline.midi_processor import MidiProcessor


class TestFixOverlappingNotes:
    """Tests for fix_overlapping_notes method."""

    @pytest.fixture
    def processor(self, tmp_path):
        """Create a processor with a dummy MIDI file."""
        # Create a minimal valid MIDI file
        import pretty_midi

        midi = pretty_midi.PrettyMIDI()
        instrument = pretty_midi.Instrument(program=0)
        instrument.notes.append(
            pretty_midi.Note(velocity=100, pitch=60, start=0, end=1)
        )
        midi.instruments.append(instrument)

        midi_path = tmp_path / "test.mid"
        midi.write(str(midi_path))
        return MidiProcessor(str(midi_path))

    def test_no_overlap(self, processor):
        """Notes with no overlap should remain unchanged."""
        events = [
            (0.0, 1.0, 60, 0.8, 1.0),  # C4: 0-1s
            (1.5, 2.5, 62, 0.8, 1.0),  # D4: 1.5-2.5s
            (3.0, 4.0, 64, 0.8, 1.0),  # E4: 3-4s
        ]
        fixed = processor.fix_overlapping_notes(events)
        assert fixed == events

    def test_slight_overlap_truncated(self, processor):
        """Slight overlap between sequential notes should truncate earlier note."""
        events = [
            (0.0, 1.5, 60, 0.8, 1.0),  # C4: ends at 1.5s
            (1.0, 2.0, 62, 0.8, 1.0),  # D4: starts at 1.0s (0.5s overlap)
        ]
        fixed = processor.fix_overlapping_notes(events)
        assert fixed[0] == (0.0, 1.0, 60, 0.8, 1.0)  # Truncated to end at 1.0s
        assert fixed[1] == (1.0, 2.0, 62, 0.8, 1.0)  # Unchanged

    def test_chord_preserved(self, processor):
        """Notes starting at same time (chord) should not be truncated."""
        events = [
            (1.0, 2.0, 60, 0.8, 1.0),  # C4
            (1.0, 2.0, 64, 0.8, 1.0),  # E4 - same start time = chord
            (1.0, 2.0, 67, 0.8, 1.0),  # G4 - same start time = chord
        ]
        fixed = processor.fix_overlapping_notes(events)
        # All notes should be unchanged (chord)
        assert len(fixed) == 3
        for orig, result in zip(events, fixed):
            assert orig == result

    def test_chord_within_threshold(self, processor):
        """Notes starting within threshold should be treated as chord."""
        events = [
            (1.000, 2.0, 60, 0.8, 1.0),  # C4 at 1.000s
            (1.030, 2.0, 64, 0.8, 1.0),  # E4 at 1.030s (30ms later, within 50ms)
            (1.045, 2.0, 67, 0.8, 1.0),  # G4 at 1.045s (45ms later, within 50ms)
        ]
        fixed = processor.fix_overlapping_notes(events, chord_threshold_ms=50.0)
        # All should be unchanged - treated as chord
        assert fixed[0][1] == 2.0
        assert fixed[1][1] == 2.0
        assert fixed[2][1] == 2.0

    def test_chord_outside_threshold(self, processor):
        """Notes starting outside threshold should be truncated."""
        events = [
            (1.000, 2.0, 60, 0.8, 1.0),  # C4 at 1.000s
            (1.100, 2.0, 64, 0.8, 1.0),  # E4 at 1.100s (100ms later, outside 50ms)
        ]
        fixed = processor.fix_overlapping_notes(events, chord_threshold_ms=50.0)
        # First note should be truncated
        assert fixed[0][1] == 1.1  # Truncated to next note start
        assert fixed[1][1] == 2.0  # Unchanged

    def test_mixed_chords_and_overlaps(self, processor):
        """Mixed scenario with both chords and overlapping sequential notes."""
        events = [
            (0.0, 1.5, 60, 0.8, 1.0),  # C4: 0-1.5s
            (0.0, 1.5, 64, 0.8, 1.0),  # E4: chord with C4
            (1.0, 2.0, 67, 0.8, 1.0),  # G4: starts at 1.0s (overlaps C4/E4)
            (2.5, 3.5, 72, 0.8, 1.0),  # C5: no overlap
        ]
        fixed = processor.fix_overlapping_notes(events)
        # C4 and E4 should be truncated to 1.0s (when G4 starts)
        assert fixed[0][1] == 1.0
        assert fixed[1][1] == 1.0
        # G4 and C5 unchanged
        assert fixed[2][1] == 2.0
        assert fixed[3][1] == 3.5

    def test_empty_input(self, processor):
        """Empty input should return empty list."""
        assert processor.fix_overlapping_notes([]) == []

    def test_single_note(self, processor):
        """Single note should remain unchanged."""
        events = [(0.0, 1.0, 60, 0.8, 1.0)]
        fixed = processor.fix_overlapping_notes(events)
        assert fixed == events

    def test_custom_threshold(self, processor):
        """Custom chord threshold should be respected."""
        events = [
            (1.000, 2.0, 60, 0.8, 1.0),
            (1.080, 2.0, 64, 0.8, 1.0),  # 80ms later
        ]
        # With 100ms threshold - should be chord
        fixed_100 = processor.fix_overlapping_notes(events, chord_threshold_ms=100.0)
        assert fixed_100[0][1] == 2.0  # Not truncated

        # With 50ms threshold - should truncate
        fixed_50 = processor.fix_overlapping_notes(events, chord_threshold_ms=50.0)
        assert fixed_50[0][1] == 1.08  # Truncated

    def test_multiple_sequential_overlaps(self, processor):
        """Multiple sequential overlapping notes should all be truncated correctly."""
        events = [
            (0.0, 1.5, 60, 0.8, 1.0),  # Overlaps with next
            (1.0, 2.5, 62, 0.8, 1.0),  # Overlaps with next
            (2.0, 3.5, 64, 0.8, 1.0),  # Overlaps with next
            (3.0, 4.0, 65, 0.8, 1.0),  # No overlap
        ]
        fixed = processor.fix_overlapping_notes(events)
        assert fixed[0][1] == 1.0  # Truncated
        assert fixed[1][1] == 2.0  # Truncated
        assert fixed[2][1] == 3.0  # Truncated
        assert fixed[3][1] == 4.0  # Unchanged
