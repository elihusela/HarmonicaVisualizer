import wave
from pathlib import Path

import numpy as np
from PIL import Image

import pytest

TESTS_DIR = Path(__file__).parent
RESOURCES_PATH = str(TESTS_DIR / "resources") + "/"


@pytest.fixture
def dummy_video():
    path = Path(RESOURCES_PATH + "dummy_video.mp4")
    path.write_bytes(b"FAKE")  # minimal fake file
    return str(path)


@pytest.fixture
def dummy_image():
    path = RESOURCES_PATH + "dummy_image.png"
    Image.new('RGB', (600, 100)).save(path)
    return str(path)


@pytest.fixture
def dummy_output():
    return str(RESOURCES_PATH + "final.mp4")


@pytest.fixture
def dummy_wav_file():
    path = Path(RESOURCES_PATH + "extracted_audio.wav")
    path.parent.mkdir(parents=True, exist_ok=True)

    # Create 1 second of silence (16-bit mono, 22050 Hz)
    duration_sec = 1
    sample_rate = 22050
    n_frames = int(duration_sec * sample_rate)
    audio = np.zeros(n_frames, dtype=np.int16)

    with wave.open(str(path), 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio.tobytes())

    return path