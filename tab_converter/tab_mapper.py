import json
from pathlib import Path
from typing import Dict

import mido
from mido import MidiFile, Message

from tab_converter.consts import NOTE_ON_MSG, NOTE_OFF_MSG
from tab_converter.models import TabEntry, Tabs
from utils.utils import get_tempo


class TabMapper:
    def __init__(self, harmonica_mapping: Dict[int, int], json_outputs_path: str):
        self._mapping = harmonica_mapping
        self._json_outputs_path = json_outputs_path
        return

    def midi_to_tabs_with_timing(self, midi_path: str) -> Tabs:
        mid = MidiFile(midi_path)
        ticks_per_beat = mid.ticks_per_beat
        tempo = get_tempo(mid)

        time = 0
        note_start_times = {}
        tab_sequence = Tabs([])

        for msg in mid.merged_track:
            time += mido.tick2second(msg.time, ticks_per_beat, tempo)
            self._handle_message(msg, note_start_times, tab_sequence, time)

        return tab_sequence

    def _handle_message(self, msg: Message, note_start_times: Dict[str, float], tab_sequence: Tabs,
                        time: float) -> None:
        if msg.type == NOTE_ON_MSG and msg.velocity > 0:
            note_start_times[msg.note] = time
        elif (msg.type == NOTE_OFF_MSG) or (msg.type == NOTE_ON_MSG and msg.velocity == 0):
            if msg.note in note_start_times:
                start_time = note_start_times.pop(msg.note)
                duration = round(time - start_time, 3)
                if msg.note in self._mapping:
                    tab = self._mapping[msg.note]
                    tab_sequence.tabs.append(TabEntry(tab=tab, time=round(start_time, 3), duration=duration))

    def save_tabs_to_json(self, tabs: Tabs, filename: str) -> None:
        path = Path(self._json_outputs_path + filename)
        with path.open("w") as f:
            json.dump([tab.__dict__ for tab in tabs.tabs], f, indent=2)
