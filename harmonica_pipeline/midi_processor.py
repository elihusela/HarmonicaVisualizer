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

    def fix_overlapping_notes(
        self,
        note_events: List[Tuple[float, float, int, float, float]],
        chord_threshold_ms: float = 50.0,
    ) -> List[Tuple[float, float, int, float, float]]:
        """
        Fix overlapping notes while preserving intentional chords.

        Logic:
        - If notes start within chord_threshold of each other → chord, leave alone
        - If notes start at different times but overlap → truncate earlier note

        Args:
            note_events: List of (start, end, pitch, velocity, confidence) tuples
            chord_threshold_ms: Notes starting within this threshold (ms) are chords

        Returns:
            List of note events with overlaps fixed
        """
        if not note_events:
            return note_events

        chord_threshold_sec = chord_threshold_ms / 1000.0

        # Sort by start time, then by pitch for consistent ordering
        sorted_events = sorted(note_events, key=lambda x: (x[0], x[2]))

        fixed_events = []
        truncated_count = 0

        for i, (start, end, pitch, velocity, confidence) in enumerate(sorted_events):
            new_end = end

            # Check against all subsequent notes
            for j in range(i + 1, len(sorted_events)):
                next_start, next_end, next_pitch, _, _ = sorted_events[j]

                # If next note starts after this note ends, no overlap possible
                if next_start >= end:
                    break

                # Check if this is a chord (notes start at ~same time)
                if abs(next_start - start) <= chord_threshold_sec:
                    # Chord - leave both notes alone
                    continue

                # Different start times but overlap - truncate this note
                if next_start < new_end:
                    new_end = next_start
                    truncated_count += 1

            fixed_events.append((start, new_end, pitch, velocity, confidence))

        if truncated_count > 0:
            print(f"✂️  Truncated {truncated_count} overlapping note(s)")

        return fixed_events

    def load_note_events_fixed(
        self, chord_threshold_ms: float = 50.0
    ) -> List[Tuple[float, float, int, float, float]]:
        """
        Load note events and automatically fix overlapping notes.

        Convenience method that combines load_note_events() and fix_overlapping_notes().

        Args:
            chord_threshold_ms: Notes starting within this threshold (ms) are chords

        Returns:
            List of note events with overlaps fixed
        """
        events = self.load_note_events()
        return self.fix_overlapping_notes(events, chord_threshold_ms)
