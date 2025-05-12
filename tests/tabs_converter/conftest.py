import pytest

from tests.conftest import RESOURCES_PATH


@pytest.fixture
def simple_c4_midi():
    midi_path = RESOURCES_PATH + "/c4.mid"
    mid = MidiFile()
    track = MidiTrack()
    mid.tracks.append(track)
    track.append(Message('note_on', note=60, velocity=64, time=0))
    track.append(Message('note_off', note=60, velocity=64, time=480))
    mid.save(midi_path)
    return midi_path


import pytest
from mido import MidiFile, MidiTrack, Message

@pytest.fixture
def midi_with_unsupported_note():
    path = RESOURCES_PATH + "unsupported_note.mid"
    mid = MidiFile()
    track = MidiTrack()
    mid.tracks.append(track)
    track.append(Message('note_on', note=21, velocity=64, time=0))  # A0
    track.append(Message('note_off', note=21, velocity=64, time=480))
    mid.save(path)
    return path

@pytest.fixture
def midi_with_polyphony():
    path = RESOURCES_PATH + "polyphony.mid"
    mid = MidiFile()
    track = MidiTrack()
    mid.tracks.append(track)
    track.append(Message('note_on', note=60, velocity=64, time=0))  # C4
    track.append(Message('note_on', note=64, velocity=64, time=0))  # E4
    track.append(Message('note_off', note=60, velocity=64, time=480))
    track.append(Message('note_off', note=64, velocity=64, time=480))
    mid.save(path)
    return path

@pytest.fixture
def midi_with_timing_gap():
    path = RESOURCES_PATH + "timing_gap.mid"
    mid = MidiFile()
    track = MidiTrack()
    mid.tracks.append(track)
    # C4 now, then E4 after 960 ticks (longer delay)
    track.append(Message('note_on', note=60, velocity=64, time=0))
    track.append(Message('note_off', note=60, velocity=64, time=480))
    track.append(Message('note_on', note=64, velocity=64, time=960))  # Delay
    track.append(Message('note_off', note=64, velocity=64, time=480))
    mid.save(path)
    return path
