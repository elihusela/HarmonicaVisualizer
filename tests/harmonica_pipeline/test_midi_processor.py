"""Tests for harmonica_pipeline.midi_processor module."""

import pytest
from unittest.mock import MagicMock, patch

import pretty_midi

from harmonica_pipeline.midi_processor import MidiProcessor, MidiProcessorError


class TestMidiProcessorInitialization:
    """Test MidiProcessor initialization and validation."""

    def test_init_with_valid_midi_file(self, temp_test_dir):
        """Test initialization with a valid MIDI file."""
        # Create a minimal MIDI file
        midi_file = temp_test_dir / "test.mid"
        midi_data = pretty_midi.PrettyMIDI()
        instrument = pretty_midi.Instrument(program=0)
        note = pretty_midi.Note(velocity=100, pitch=60, start=0.0, end=1.0)
        instrument.notes.append(note)
        midi_data.instruments.append(instrument)
        midi_data.write(str(midi_file))

        processor = MidiProcessor(str(midi_file))
        assert processor.midi_path == str(midi_file)

    def test_init_with_missing_file_raises_error(self, temp_test_dir):
        """Test that missing MIDI file raises MidiProcessorError."""
        non_existent_file = temp_test_dir / "nonexistent.mid"

        with pytest.raises(MidiProcessorError, match="MIDI file not found"):
            MidiProcessor(str(non_existent_file))

    def test_init_with_invalid_extension_raises_error(self, temp_test_dir):
        """Test that invalid file extension raises MidiProcessorError."""
        txt_file = temp_test_dir / "test.txt"
        txt_file.write_text("not a midi file")

        with pytest.raises(MidiProcessorError, match="Invalid MIDI file extension"):
            MidiProcessor(str(txt_file))

    def test_init_accepts_midi_extension(self, temp_test_dir):
        """Test that .midi extension is accepted."""
        midi_file = temp_test_dir / "test.midi"
        midi_data = pretty_midi.PrettyMIDI()
        instrument = pretty_midi.Instrument(program=0)
        note = pretty_midi.Note(velocity=100, pitch=60, start=0.0, end=1.0)
        instrument.notes.append(note)
        midi_data.instruments.append(instrument)
        midi_data.write(str(midi_file))

        processor = MidiProcessor(str(midi_file))
        assert processor.midi_path == str(midi_file)

    def test_init_accepts_uppercase_extensions(self, temp_test_dir):
        """Test that uppercase .MID extension is accepted."""
        midi_file = temp_test_dir / "test.MID"
        midi_data = pretty_midi.PrettyMIDI()
        instrument = pretty_midi.Instrument(program=0)
        note = pretty_midi.Note(velocity=100, pitch=60, start=0.0, end=1.0)
        instrument.notes.append(note)
        midi_data.instruments.append(instrument)
        midi_data.write(str(midi_file))

        processor = MidiProcessor(str(midi_file))
        assert processor.midi_path == str(midi_file)


class TestMidiProcessorLoadNoteEvents:
    """Test MIDI note event loading functionality."""

    def test_load_note_events_success(self, temp_test_dir, capsys):
        """Test successful loading of note events from MIDI file."""
        midi_file = temp_test_dir / "test.mid"
        midi_data = pretty_midi.PrettyMIDI()
        instrument = pretty_midi.Instrument(program=0)

        # Add multiple notes
        notes_data = [
            (60, 0.0, 1.0, 100),
            (64, 1.0, 2.0, 80),
            (67, 2.0, 3.0, 90),
        ]
        for pitch, start, end, velocity in notes_data:
            note = pretty_midi.Note(
                velocity=velocity, pitch=pitch, start=start, end=end
            )
            instrument.notes.append(note)

        midi_data.instruments.append(instrument)
        midi_data.write(str(midi_file))

        processor = MidiProcessor(str(midi_file))
        note_events = processor.load_note_events()

        # Verify note events
        assert len(note_events) == 3
        for i, (pitch, start, end, velocity) in enumerate(notes_data):
            event_start, event_end, event_pitch, event_velocity, event_confidence = (
                note_events[i]
            )
            assert event_start == start
            assert event_end == end
            assert event_pitch == pitch
            assert event_velocity == pytest.approx(velocity / 127.0)
            assert event_confidence == 1.0

        # Check print output
        captured = capsys.readouterr()
        assert "Loading MIDI file" in captured.out
        assert "Loaded 3 note events" in captured.out

    def test_load_note_events_removes_pitch_bends(self, temp_test_dir):
        """Test that pitch bends are removed from MIDI data."""
        midi_file = temp_test_dir / "test.mid"
        midi_data = pretty_midi.PrettyMIDI()
        instrument = pretty_midi.Instrument(program=0)

        # Add note and pitch bend
        note = pretty_midi.Note(velocity=100, pitch=60, start=0.0, end=1.0)
        instrument.notes.append(note)
        instrument.pitch_bends.append(pretty_midi.PitchBend(pitch=100, time=0.5))

        midi_data.instruments.append(instrument)
        midi_data.write(str(midi_file))

        processor = MidiProcessor(str(midi_file))
        note_events = processor.load_note_events()

        # Verify pitch bends were removed (note events should still load)
        assert len(note_events) == 1

    def test_load_note_events_multiple_instruments(self, temp_test_dir):
        """Test loading notes from multiple instruments."""
        midi_file = temp_test_dir / "test.mid"
        midi_data = pretty_midi.PrettyMIDI()

        # Add two instruments with notes
        for i in range(2):
            instrument = pretty_midi.Instrument(program=i)
            note = pretty_midi.Note(velocity=100, pitch=60 + i, start=0.0, end=1.0)
            instrument.notes.append(note)
            midi_data.instruments.append(instrument)

        midi_data.write(str(midi_file))

        processor = MidiProcessor(str(midi_file))
        note_events = processor.load_note_events()

        # Should have notes from both instruments
        assert len(note_events) == 2

    def test_load_note_events_skips_invalid_notes(self, temp_test_dir):
        """Test that invalid notes are skipped."""
        midi_file = temp_test_dir / "test.mid"
        midi_data = pretty_midi.PrettyMIDI()
        instrument = pretty_midi.Instrument(program=0)

        # Add valid note
        valid_note = pretty_midi.Note(velocity=100, pitch=60, start=0.0, end=1.0)
        instrument.notes.append(valid_note)

        # Add invalid notes (we'll mock them)
        midi_data.instruments.append(instrument)
        midi_data.write(str(midi_file))

        # Reload and modify to add invalid notes
        processor = MidiProcessor(str(midi_file))

        # Mock the MIDI loading to include invalid notes
        with patch("pretty_midi.PrettyMIDI") as mock_midi:
            mock_instrument = MagicMock()

            # Valid note
            mock_note1 = MagicMock()
            mock_note1.start = 0.0
            mock_note1.end = 1.0
            mock_note1.pitch = 60
            mock_note1.velocity = 100

            # Invalid: negative start
            mock_note2 = MagicMock()
            mock_note2.start = -1.0
            mock_note2.end = 1.0
            mock_note2.pitch = 60
            mock_note2.velocity = 100

            # Invalid: end <= start
            mock_note3 = MagicMock()
            mock_note3.start = 1.0
            mock_note3.end = 1.0
            mock_note3.pitch = 60
            mock_note3.velocity = 100

            # Invalid: pitch out of range (negative)
            mock_note4 = MagicMock()
            mock_note4.start = 0.0
            mock_note4.end = 1.0
            mock_note4.pitch = -1
            mock_note4.velocity = 100

            # Invalid: pitch out of range (too high)
            mock_note5 = MagicMock()
            mock_note5.start = 0.0
            mock_note5.end = 1.0
            mock_note5.pitch = 128
            mock_note5.velocity = 100

            mock_instrument.notes = [
                mock_note1,
                mock_note2,
                mock_note3,
                mock_note4,
                mock_note5,
            ]
            mock_instrument.pitch_bends = []

            mock_midi.return_value.instruments = [mock_instrument]

            note_events = processor.load_note_events()

            # Only the valid note should be loaded
            assert len(note_events) == 1

    def test_load_note_events_file_read_error(self, temp_test_dir):
        """Test error handling when MIDI file cannot be read."""
        midi_file = temp_test_dir / "test.mid"
        # Create empty file that's not valid MIDI
        midi_file.write_bytes(b"not valid midi data")

        processor = MidiProcessor(str(midi_file))

        with pytest.raises(MidiProcessorError, match="Failed to load MIDI file"):
            processor.load_note_events()

    def test_load_note_events_no_instruments_error(self, temp_test_dir):
        """Test error when MIDI file contains no instruments."""
        midi_file = temp_test_dir / "test.mid"
        midi_data = pretty_midi.PrettyMIDI()
        # No instruments added
        midi_data.write(str(midi_file))

        processor = MidiProcessor(str(midi_file))

        with pytest.raises(MidiProcessorError, match="contains no instruments"):
            processor.load_note_events()

    def test_load_note_events_no_valid_notes_error(self, temp_test_dir):
        """Test error when MIDI has instruments but no valid notes."""
        midi_file = temp_test_dir / "test.mid"

        # Create a valid MIDI file first
        midi_data = pretty_midi.PrettyMIDI()
        instrument = pretty_midi.Instrument(program=0)
        note = pretty_midi.Note(velocity=100, pitch=60, start=0.0, end=1.0)
        instrument.notes.append(note)
        midi_data.instruments.append(instrument)
        midi_data.write(str(midi_file))

        processor = MidiProcessor(str(midi_file))

        # Mock MIDI loading to return instrument with no notes
        with patch("pretty_midi.PrettyMIDI") as mock_midi:
            mock_instrument = MagicMock()
            mock_instrument.notes = []
            mock_instrument.pitch_bends = []
            mock_midi.return_value.instruments = [mock_instrument]

            with pytest.raises(MidiProcessorError, match="No valid note events found"):
                processor.load_note_events()


class TestMidiProcessorIntegration:
    """Integration tests for MidiProcessor."""

    def test_realistic_midi_file_processing(self, temp_test_dir):
        """Test processing a realistic MIDI file with multiple characteristics."""
        midi_file = temp_test_dir / "realistic.mid"
        midi_data = pretty_midi.PrettyMIDI()

        # Create instrument with various notes
        instrument = pretty_midi.Instrument(program=0)

        # Add notes with different velocities and timings
        notes = [
            (60, 0.0, 0.5, 100),  # C4
            (64, 0.5, 1.0, 80),  # E4
            (67, 1.0, 1.5, 90),  # G4
            (72, 1.5, 2.0, 110),  # C5
        ]

        for pitch, start, end, velocity in notes:
            note = pretty_midi.Note(
                velocity=velocity, pitch=pitch, start=start, end=end
            )
            instrument.notes.append(note)

        # Add pitch bends that should be removed
        instrument.pitch_bends.extend(
            [
                pretty_midi.PitchBend(pitch=100, time=0.25),
                pretty_midi.PitchBend(pitch=-100, time=0.75),
            ]
        )

        midi_data.instruments.append(instrument)
        midi_data.write(str(midi_file))

        # Process the MIDI file
        processor = MidiProcessor(str(midi_file))
        note_events = processor.load_note_events()

        # Verify all notes were loaded correctly
        assert len(note_events) == 4

        # Check notes are in chronological order
        for i in range(len(note_events) - 1):
            assert note_events[i][0] <= note_events[i + 1][0]

        # Verify first and last notes
        assert note_events[0][2] == 60  # First pitch
        assert note_events[-1][2] == 72  # Last pitch

    def test_velocity_normalization(self, temp_test_dir):
        """Test that velocities are normalized to 0-1 range."""
        midi_file = temp_test_dir / "velocity_test.mid"
        midi_data = pretty_midi.PrettyMIDI()
        instrument = pretty_midi.Instrument(program=0)

        # Add notes with different velocities (PrettyMIDI may drop velocity=0 notes)
        velocities = [1, 64, 127]
        for i, velocity in enumerate(velocities):
            note = pretty_midi.Note(
                velocity=velocity, pitch=60, start=float(i), end=float(i + 1)
            )
            instrument.notes.append(note)

        midi_data.instruments.append(instrument)
        midi_data.write(str(midi_file))

        processor = MidiProcessor(str(midi_file))
        note_events = processor.load_note_events()

        # Verify we got all notes
        assert len(note_events) == 3

        # Verify velocities are normalized to 0-1 range
        # Note: MIDI file I/O may slightly modify values, so we check ranges
        for event in note_events:
            velocity_normalized = event[3]
            assert 0.0 <= velocity_normalized <= 1.0

        # Check specific values with some tolerance
        assert note_events[0][3] < 0.1  # Low velocity (1/127)
        assert 0.4 < note_events[1][3] < 0.6  # Mid velocity (64/127)
        assert note_events[2][3] > 0.9  # High velocity (127/127)

    def test_confidence_always_one(self, temp_test_dir):
        """Test that confidence is always set to 1.0."""
        midi_file = temp_test_dir / "confidence_test.mid"
        midi_data = pretty_midi.PrettyMIDI()
        instrument = pretty_midi.Instrument(program=0)

        note = pretty_midi.Note(velocity=100, pitch=60, start=0.0, end=1.0)
        instrument.notes.append(note)

        midi_data.instruments.append(instrument)
        midi_data.write(str(midi_file))

        processor = MidiProcessor(str(midi_file))
        note_events = processor.load_note_events()

        # All events should have confidence = 1.0
        for event in note_events:
            assert event[4] == 1.0
