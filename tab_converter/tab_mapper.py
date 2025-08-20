import json
from pathlib import Path
from typing import Dict, List, Tuple

from tab_converter.models import TabEntry, Tabs, NoteEvent


class TabMapper:
    def __init__(self, harmonica_mapping: Dict[int, int], json_outputs_path: str):
        self._mapping = harmonica_mapping
        self._json_outputs_path = json_outputs_path

    def note_events_to_tabs(self, raw_events: List[Tuple]) -> Tabs:
        tab_entries = []

        for event_tuple in raw_events:
            event = NoteEvent(*event_tuple)
            if event.pitch in self._mapping:
                tab = self._mapping[event.pitch]
                start = round(event.start_time, 5)
                duration = round(event.end_time - event.start_time, 5)
                confidence = round(event.confidence, 5)
                tab_entries.append(
                    TabEntry(
                        tab=tab, time=start, duration=duration, confidence=confidence
                    )
                )

        tabs = Tabs(tab_entries)
        tabs.tabs.sort(key=lambda e: e.time)

        return tabs

    def save_tabs_to_json(self, tabs: Tabs, filename: str) -> None:
        path = Path(self._json_outputs_path) / filename
        with path.open("w") as f:
            json.dump(str([tab.__dict__ for tab in tabs.tabs]), f, indent=2)
