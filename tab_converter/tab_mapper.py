"""
Tab Mapper - Converts MIDI note events to harmonica tab notation.

Handles the conversion from MIDI pitch values to harmonica hole numbers
using a configurable harmonica mapping.
"""

import json
from pathlib import Path
from typing import Dict, List, Tuple

from tab_converter.models import TabEntry, Tabs, NoteEvent


class TabMapperError(Exception):
    """Custom exception for tab mapping errors."""

    pass


class TabMapper:
    """
    Converts MIDI note events to harmonica tablature format.

    Maps MIDI pitch values to harmonica hole numbers (positive for blow, negative for draw)
    and creates properly timed TabEntry objects.
    """

    def __init__(
        self,
        harmonica_mapping: Dict[int, int],
        json_outputs_path: str,
        bend_mapping: Dict[int, Tuple[int, str]] | None = None,
    ):
        """
        Initialize tab mapper.

        Args:
            harmonica_mapping: Dict mapping MIDI pitch (60-96) to harmonica holes
            json_outputs_path: Directory path for saving JSON debug files
            bend_mapping: Optional dict mapping MIDI pitch to (hole, bend_notation)
        """
        if not harmonica_mapping:
            raise TabMapperError("Harmonica mapping cannot be empty")

        self._mapping = harmonica_mapping
        self._bend_mapping = bend_mapping or {}
        self._json_outputs_path = Path(json_outputs_path)
        self._json_outputs_path.mkdir(parents=True, exist_ok=True)

    def note_events_to_tabs(self, raw_events: List[Tuple]) -> Tabs:
        """
        Convert MIDI note events to harmonica tabs.

        Args:
            raw_events: List of tuples (start, end, pitch, velocity, confidence)

        Returns:
            Tabs object containing sorted TabEntry objects

        Raises:
            TabMapperError: If no valid tabs could be created
        """
        if not raw_events:
            raise TabMapperError("No note events provided")

        tab_entries = []
        skipped_notes = 0

        for event_tuple in raw_events:
            try:
                tab_entry = self._convert_note_event_to_tab(event_tuple)
                if tab_entry:
                    tab_entries.append(tab_entry)
                else:
                    skipped_notes += 1
            except Exception as e:
                print(f"⚠️  Warning: Skipping invalid note event {event_tuple}: {e}")
                skipped_notes += 1

        if not tab_entries:
            raise TabMapperError(
                "No valid harmonica tabs could be created from note events"
            )

        # Create and sort tabs by time
        tabs = Tabs(tab_entries)
        tabs.tabs.sort(key=lambda entry: entry.time)

        print(f"🎼 Mapped {len(tab_entries)} valid tabs, skipped {skipped_notes} notes")
        return tabs

    def _convert_note_event_to_tab(self, event_tuple: Tuple) -> TabEntry | None:
        """
        Convert a single note event to a TabEntry.

        Args:
            event_tuple: (start, end, pitch, velocity, confidence)

        Returns:
            TabEntry if pitch is mappable, None otherwise
        """
        event = NoteEvent(*event_tuple)

        # Check regular mapping first (pure notes take priority over bends)
        # Only use bend if the pitch is NOT available as a pure note
        is_bend = False
        bend_notation = ""
        tab_hole = None

        if event.pitch in self._mapping:
            # Pure note available - use it
            tab_hole = self._mapping[event.pitch]
        elif event.pitch in self._bend_mapping:
            # No pure note, but bend is available
            tab_hole, bend_notation = self._bend_mapping[event.pitch]
            is_bend = True
        else:
            # Pitch not mappable
            return None

        # Validate timing
        if event.end_time <= event.start_time:
            print(f"⚠️  Warning: Invalid timing for pitch {event.pitch}")
            return None

        # Create tab entry with rounded values for precision
        start_time = round(event.start_time, 5)
        duration = round(event.end_time - event.start_time, 5)
        confidence = round(event.confidence, 5)

        return TabEntry(
            tab=tab_hole,
            time=start_time,
            duration=duration,
            confidence=confidence,
            is_bend=is_bend,
            bend_notation=bend_notation,
        )

    def save_tabs_to_json(self, tabs: Tabs, filename: str) -> None:
        """
        Save tabs to JSON file for debugging.

        Args:
            tabs: Tabs object to save
            filename: Name of JSON file to create
        """
        try:
            file_path = self._json_outputs_path / filename

            # Create a more readable JSON format
            tabs_data = [
                {
                    "tab": entry.tab,
                    "time": entry.time,
                    "duration": entry.duration,
                    "confidence": entry.confidence,
                }
                for entry in tabs.tabs
            ]

            with file_path.open("w") as f:
                json.dump(tabs_data, f, indent=2, sort_keys=True)

            print(f"💾 Saved {len(tabs_data)} tabs to {file_path}")

        except Exception as e:
            print(f"⚠️  Warning: Could not save tabs to JSON: {e}")

    def get_mapping_info(self) -> Dict[str, int]:
        """
        Get information about the current harmonica mapping.

        Returns:
            Dict with mapping statistics
        """
        return {
            "total_mapped_pitches": len(self._mapping),
            "pitch_range_min": min(self._mapping.keys()) if self._mapping else 0,
            "pitch_range_max": max(self._mapping.keys()) if self._mapping else 0,
            "blow_holes": len([v for v in self._mapping.values() if v > 0]),
            "draw_holes": len([v for v in self._mapping.values() if v < 0]),
        }
