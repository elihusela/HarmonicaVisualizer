# tab_matcher.py
from typing import Dict, List, Optional
from tab_converter.models import TabEntry, Tabs


class TabMatcher:
    """
    Matches parsed tab chords (from text file) against MIDI-derived Tabs model.
    Instead of returning a filtered list, this injects timing (TabEntry) into the parsed tab structure.

    Returns:
    Dict[str, List[List[Optional[List[TabEntry]]]]]  # page -> lines -> chords -> matched TabEntries or None
    """

    @staticmethod
    def match(
        midi_tabs: Tabs, parsed_pages: Dict[str, List[List[List[int]]]]
    ) -> Dict[str, List[List[Optional[List[TabEntry]]]]]:
        entries: List[TabEntry] = sorted(midi_tabs.tabs, key=lambda e: e.time)
        result: Dict[str, List[List[Optional[List[TabEntry]]]]] = {}

        for page, lines in parsed_pages.items():
            page_result: List[List[Optional[List[TabEntry]]]] = []
            for line in lines:
                line_result: List[Optional[List[TabEntry]]] = []
                for chord in line:
                    matched_entries: List[TabEntry] = []
                    chord_note_index: int = 0

                    for entry in entries:
                        if entry.tab == chord[chord_note_index]:
                            matched_entries.append(entry)
                            chord_note_index += 1
                        if chord_note_index == len(chord):
                            break

                    if chord_note_index == len(chord):
                        line_result.append(matched_entries)
                    else:
                        line_result.append(None)
                page_result.append(line_result)
            result[page] = page_result

        return result
