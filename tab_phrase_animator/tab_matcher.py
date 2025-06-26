# tab_matcher.py
from typing import Dict, List, Optional
from tab_converter.models import TabEntry, Tabs


class TabMatcher:
    """
    Matches parsed tab chords (from text file) against MIDI-derived Tabs model.
    Ensures each note in parsed tabs receives a timing from closest MIDI-derived TabEntry.
    If no match is found, the note is kept but assigned the time of the closest remaining MIDI TabEntry.

    Returns:
    Dict[str, List[List[Optional[List[TabEntry]]]]]  # page -> lines -> chords -> matched TabEntries or None
    """

    @staticmethod
    def match(
        midi_tabs: Tabs, parsed_pages: Dict[str, List[List[List[int]]]]
    ) -> Dict[str, List[List[Optional[List[TabEntry]]]]]:
        midi_entries: List[TabEntry] = sorted(midi_tabs.tabs, key=lambda e: e.time)
        result: Dict[str, List[List[Optional[List[TabEntry]]]]] = {}

        for page, lines in parsed_pages.items():
            page_result: List[List[Optional[List[TabEntry]]]] = []
            for line in lines:
                line_result: List[Optional[List[TabEntry]]] = []
                for chord in line:
                    matched_entries: List[TabEntry] = []

                    for note in chord:
                        match_found = False
                        for idx, entry in enumerate(midi_entries):
                            if entry.tab == note:
                                matched_entries.append(
                                    TabEntry(
                                        tab=note,
                                        time=entry.time,
                                        duration=entry.duration,
                                        confidence=entry.confidence,
                                    )
                                )
                                midi_entries.pop(idx)
                                match_found = True
                                break

                        if not match_found:
                            if midi_entries:
                                closest_entry = midi_entries.pop(0)
                                print(
                                    f"Replacing note {note} with closest available MIDI timing {closest_entry.tab}"
                                )
                                matched_entries.append(
                                    TabEntry(
                                        tab=note,
                                        time=closest_entry.time,
                                        duration=closest_entry.duration,
                                        confidence=closest_entry.confidence,
                                    )
                                )
                            else:
                                print(f"No MIDI entries left to match note {note}")

                    line_result.append(matched_entries)
                page_result.append(line_result)
            result[page] = page_result

        return result
