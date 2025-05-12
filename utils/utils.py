import json
import os
import shutil
from pathlib import Path
from typing import Union

import mido
from mido import MidiFile

from tab_converter.consts import SET_TEMPO_MSG
from tab_converter.models import Tabs

TEMP_DIR = str(Path(__file__).parent.parent / "temp") + "/"


def clean_temp_folder(path=TEMP_DIR):
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)
    print(f"🧹 Cleaned and recreated '{path}' folder.")


def save_tabs_to_json(tabs: Tabs, output_path: Union[str, Path]) -> None:
    path = Path(output_path)
    with path.open("w") as f:
        json.dump([tab.__dict__ for tab in tabs.tabs], f, indent=2)


def get_tempo(mid: MidiFile) -> int:
    for track in mid.tracks:
        for msg in track:
            if msg.type == SET_TEMPO_MSG:
                return msg.tempo
    return mido.bpm2tempo(120)
