from utils.audio_extractor import extract_audio_from_video
from unittest.mock import MagicMock, patch

def test_extract_audio_from_video_mocks():
    with patch("utils.media_utils.VideoFileClip") as mock_clip:
        mock_audio = MagicMock()
        mock_clip.return_value.audio = mock_audio

        path = extract_audio_from_video("dummy.mp4", "temp/out.wav")

        mock_audio.write_audiofile.assert_called_once_with("temp/out.wav")
        assert path == "temp/out.wav"
