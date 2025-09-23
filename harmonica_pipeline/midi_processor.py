"""
MIDI Processor - Handles MIDI file loading and processing for Phase 2.

Extracts MIDI processing logic from VideoCreator to follow Phase 1 OOP patterns.
"""

import os
from typing import List, Tuple
import pretty_midi


class MidiProcessorError(Exception):
    """Custom exception for MIDI processing errors."""

    pass


class MidiProcessor:
    """Handles loading and processing of fixed MIDI files for video creation."""

    def __init__(self, midi_path: str):
        """
        Initialize MIDI processor.

        Args:
            midi_path: Path to the fixed MIDI file

        Raises:
            MidiProcessorError: If MIDI file doesn't exist or is invalid
        """
        if not os.path.exists(midi_path):
            raise MidiProcessorError(f"MIDI file not found: {midi_path}")

        if not midi_path.lower().endswith((".mid", ".midi")):
            raise MidiProcessorError(f"Invalid MIDI file extension: {midi_path}")

        self.midi_path = midi_path

    def load_note_events(self) -> List[Tuple[float, float, int, float, float]]:
        """
        Load note events from the MIDI file.

        Returns:
            List of note events as tuples: (start, end, pitch, velocity, confidence)

        Raises:
            MidiProcessorError: If MIDI file cannot be loaded or parsed
        """
        print(f"🎹 Loading MIDI file: {self.midi_path}")

        try:
            midi_data = pretty_midi.PrettyMIDI(self.midi_path)
        except Exception as e:
            raise MidiProcessorError(f"Failed to load MIDI file {self.midi_path}: {e}")

        if not midi_data.instruments:
            raise MidiProcessorError(
                f"MIDI file contains no instruments: {self.midi_path}"
            )

        # Remove pitch bends (as done in original pipeline)
        for instrument in midi_data.instruments:
            instrument.pitch_bends = []

        note_events = []
        for instrument in midi_data.instruments:
            for note in instrument.notes:
                # Validate note data
                if note.start < 0 or note.end <= note.start:
                    continue  # Skip invalid notes
                if not (0 <= note.pitch <= 127):
                    continue  # Skip invalid pitch values

                note_events.append(
                    (note.start, note.end, note.pitch, note.velocity / 127.0, 1.0)
                )

        if not note_events:
            raise MidiProcessorError(
                f"No valid note events found in MIDI file: {self.midi_path}"
            )

        print(f"🎵 Loaded {len(note_events)} note events from MIDI")
        return note_events
