import pytest
from pathlib import Path
from utils.audio_extractor import AudioExtractor


@pytest.fixture
def dummy_audio_paths(tmp_path) -> tuple[AudioExtractor, Path, Path]:
    video_path = tmp_path / "dummy_video.mp4"
    audio_path = tmp_path / "dummy_audio.wav"
    video_path.write_bytes(b"FAKE_VIDEO")  # So it exists

    extractor = AudioExtractor(str(video_path), str(audio_path))
    return extractor, video_path, audio_path
