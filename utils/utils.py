import os
import shutil
from pathlib import Path

import mido
from mido import MidiFile

from tab_converter.consts import SET_TEMPO_MSG

TEMP_DIR = str(Path(__file__).parent.parent / "temp") + "/"
VIDEO_FILES_DIR = str(Path(__file__).parent.parent / "video-files") + "/"
TAB_FILES_DIR = str(Path(__file__).parent.parent / "tab-files") + "/"
OUTPUTS_DIR = str(Path(__file__).parent.parent / "outputs") + "/"


def clean_temp_folder(path=TEMP_DIR):
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)
    print(f"🧹 Cleaned and recreated '{path}' folder.")


def get_tempo(mid: MidiFile) -> int:
    for track in mid.tracks:
        for msg in track:
            if msg.type == SET_TEMPO_MSG:
                return msg.tempo
    return mido.bpm2tempo(120)
