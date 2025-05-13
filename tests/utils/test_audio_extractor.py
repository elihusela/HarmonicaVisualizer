from unittest.mock import patch, MagicMock


def test_extract_audio_from_video_calls_correctly(dummy_audio_paths):
    extractor, video_path, audio_path = dummy_audio_paths

    with patch("utils.audio_extractor.VideoFileClip") as mock_clip:
        mock_audio = MagicMock()
        mock_clip.return_value.audio = mock_audio

        result = extractor.extract_audio_from_video()

        mock_clip.assert_called_once_with(str(video_path))
        mock_audio.write_audiofile.assert_called_once_with(str(audio_path))
        assert result == str(audio_path)
