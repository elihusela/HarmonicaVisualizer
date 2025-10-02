"""Tests for image_converter.video_processor module."""

import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from image_converter.video_processor import VideoProcessor, VideoProcessorError


class TestVideoProcessorInitialization:
    """Test VideoProcessor initialization."""

    def test_init_default_temp_dir(self):
        """Test initialization with default temp directory."""
        with patch("pathlib.Path.mkdir") as mock_mkdir:
            processor = VideoProcessor()

            assert processor.temp_dir == Path("temp/")
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_init_custom_temp_dir(self):
        """Test initialization with custom temp directory."""
        with patch("pathlib.Path.mkdir") as mock_mkdir:
            processor = VideoProcessor("/custom/temp/")

            assert processor.temp_dir == Path("/custom/temp/")
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_init_creates_temp_directory(self):
        """Test that temp directory is actually created."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / "video_temp"
            processor = VideoProcessor(str(temp_path))

            assert temp_path.exists()
            assert temp_path.is_dir()
            assert processor.temp_dir == temp_path


class TestVideoProcessorFFmpegAvailability:
    """Test FFmpeg availability checking."""

    @patch("subprocess.run")
    def test_check_ffmpeg_available_success(self, mock_run):
        """Test FFmpeg availability check when FFmpeg is available."""
        mock_run.return_value = MagicMock(returncode=0)

        processor = VideoProcessor()
        result = processor.check_ffmpeg_available()

        assert result is True
        mock_run.assert_called_once_with(
            ["ffmpeg", "-version"], capture_output=True, text=True, timeout=5
        )

    @patch("subprocess.run")
    def test_check_ffmpeg_available_failure(self, mock_run):
        """Test FFmpeg availability check when FFmpeg fails."""
        mock_run.return_value = MagicMock(returncode=1)

        processor = VideoProcessor()
        result = processor.check_ffmpeg_available()

        assert result is False

    @patch("subprocess.run")
    def test_check_ffmpeg_not_found(self, mock_run):
        """Test FFmpeg availability when command not found."""
        mock_run.side_effect = FileNotFoundError()

        processor = VideoProcessor()
        result = processor.check_ffmpeg_available()

        assert result is False

    @patch("subprocess.run")
    def test_check_ffmpeg_timeout(self, mock_run):
        """Test FFmpeg availability check timeout."""
        import subprocess

        mock_run.side_effect = subprocess.TimeoutExpired("ffmpeg", 5)

        processor = VideoProcessor()
        result = processor.check_ffmpeg_available()

        assert result is False


class TestVideoProcessorTransparencyCreation:
    """Test transparent video creation."""

    @patch("subprocess.run")
    def test_create_transparent_video_success(self, mock_run):
        """Test successful transparent video creation."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        processor = VideoProcessor()
        processor._create_transparent_video("input.mp4", "output.mov")

        # Verify FFmpeg command
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "ffmpeg"
        assert "colorkey=0xFF00FF:0.4:0.0,format=yuva444p10le" in call_args
        assert "prores_ks" in call_args

    @patch("subprocess.run")
    def test_create_transparent_video_failure(self, mock_run):
        """Test transparent video creation failure."""
        mock_run.return_value = MagicMock(returncode=1, stderr="FFmpeg error")

        processor = VideoProcessor()

        with pytest.raises(
            VideoProcessorError, match="Failed to create transparent video"
        ):
            processor._create_transparent_video("input.mp4", "output.mov")

    @patch("subprocess.run")
    def test_create_transparent_video_command_structure(self, mock_run):
        """Test the exact FFmpeg command structure for transparency."""
        mock_run.return_value = MagicMock(returncode=0)

        processor = VideoProcessor()
        processor._create_transparent_video("test_input.mp4", "test_output.mov")

        expected_cmd = [
            "ffmpeg",
            "-y",
            "-i",
            "test_input.mp4",
            "-vf",
            "colorkey=0xFF00FF:0.4:0.0,format=yuva444p10le",
            "-c:v",
            "prores_ks",
            "-profile:v",
            "4",
            "-pix_fmt",
            "yuva444p10le",
            "test_output.mov",
        ]

        mock_run.assert_called_once_with(expected_cmd, capture_output=True, text=True)


class TestVideoProcessorAudioAdding:
    """Test audio addition to video."""

    @patch("subprocess.run")
    def test_add_audio_to_video_success(self, mock_run):
        """Test successful audio addition."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        processor = VideoProcessor()
        processor._add_audio_to_video("video.mov", "audio.wav", "final.mov")

        # Verify FFmpeg command
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "ffmpeg"
        assert "copy" in call_args  # Video codec copy
        assert "aac" in call_args  # Audio codec

    @patch("subprocess.run")
    def test_add_audio_to_video_failure(self, mock_run):
        """Test audio addition failure."""
        mock_run.return_value = MagicMock(returncode=1, stderr="Audio error")

        processor = VideoProcessor()

        with pytest.raises(VideoProcessorError, match="Failed to add audio to video"):
            processor._add_audio_to_video("video.mov", "audio.wav", "final.mov")

    @patch("subprocess.run")
    def test_add_audio_command_structure(self, mock_run):
        """Test exact FFmpeg command for audio addition."""
        mock_run.return_value = MagicMock(returncode=0)

        processor = VideoProcessor()
        processor._add_audio_to_video("test.mov", "test.wav", "output.mov")

        expected_cmd = [
            "ffmpeg",
            "-y",
            "-i",
            "test.mov",
            "-i",
            "test.wav",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "output.mov",
        ]

        mock_run.assert_called_once_with(expected_cmd, capture_output=True, text=True)


class TestVideoProcessorCleanup:
    """Test file cleanup functionality."""

    def test_cleanup_existing_files(self):
        """Test cleanup of existing files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test files
            file1 = Path(temp_dir) / "file1.tmp"
            file2 = Path(temp_dir) / "file2.tmp"
            file1.touch()
            file2.touch()

            processor = VideoProcessor()
            processor._cleanup_temp_files([str(file1), str(file2)])

            assert not file1.exists()
            assert not file2.exists()

    def test_cleanup_nonexistent_files(self, capsys):
        """Test cleanup with nonexistent files (should not crash)."""
        processor = VideoProcessor()
        processor._cleanup_temp_files(["/nonexistent/file.tmp"])

        # Should not raise exception
        # Nonexistent files are silently ignored (no output)

    def test_cleanup_permission_error(self, capsys):
        """Test cleanup with permission errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            test_file = Path(temp_dir) / "readonly.tmp"
            test_file.touch()

            # Mock os.remove to raise permission error
            with patch("os.remove", side_effect=PermissionError("Access denied")):
                processor = VideoProcessor()
                processor._cleanup_temp_files([str(test_file)])

                captured = capsys.readouterr()
                assert "Warning: Could not remove" in captured.out

    def test_cleanup_mixed_scenarios(self):
        """Test cleanup with mix of existing and nonexistent files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            existing_file = Path(temp_dir) / "exists.tmp"
            existing_file.touch()

            processor = VideoProcessor()
            processor._cleanup_temp_files(
                [
                    str(existing_file),
                    "/nonexistent/file.tmp",
                ]
            )

            assert not existing_file.exists()


class TestVideoProcessorCompleteWorkflow:
    """Test complete video processing workflow."""

    @patch("subprocess.run")
    def test_process_animation_to_video_success(self, mock_run):
        """Test successful complete video processing."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        processor = VideoProcessor()

        with patch.object(processor, "_cleanup_temp_files") as mock_cleanup:
            processor.process_animation_to_video(
                "raw.mp4", "audio.wav", "final.mov", cleanup_temp=True
            )

            # Should call FFmpeg twice (transparency + audio)
            assert mock_run.call_count == 2
            mock_cleanup.assert_called_once()

    @patch("subprocess.run")
    def test_process_animation_to_video_no_cleanup(self, mock_run):
        """Test video processing without cleanup."""
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        processor = VideoProcessor()

        with patch.object(processor, "_cleanup_temp_files") as mock_cleanup:
            processor.process_animation_to_video(
                "raw.mp4", "audio.wav", "final.mov", cleanup_temp=False
            )

            mock_cleanup.assert_not_called()

    @patch("subprocess.run")
    def test_process_animation_to_video_failure(self, mock_run):
        """Test video processing failure handling."""
        mock_run.return_value = MagicMock(returncode=1, stderr="FFmpeg failed")

        processor = VideoProcessor()

        with patch.object(processor, "_cleanup_temp_files") as mock_cleanup:
            with pytest.raises(VideoProcessorError, match="Video processing failed"):
                processor.process_animation_to_video(
                    "raw.mp4", "audio.wav", "final.mov"
                )

            # Cleanup should still be called on failure
            mock_cleanup.assert_called_once()

    @patch("subprocess.run")
    def test_process_animation_temp_file_paths(self, mock_run):
        """Test that temporary file paths are constructed correctly."""
        mock_run.return_value = MagicMock(returncode=0)

        processor = VideoProcessor("custom_temp/")

        with patch.object(processor, "_cleanup_temp_files") as mock_cleanup:
            processor.process_animation_to_video("input.mp4", "audio.wav", "output.mov")

            # Check cleanup was called with expected temp file
            cleanup_args = mock_cleanup.call_args[0][0]
            assert "input.mp4" in cleanup_args
            assert any("temp_transparent.mov" in path for path in cleanup_args)


class TestVideoProcessorVideoInfo:
    """Test video information retrieval."""

    @patch.object(VideoProcessor, "check_ffmpeg_available", return_value=False)
    def test_get_video_info_no_ffmpeg(self, mock_check):
        """Test video info when FFmpeg not available."""
        processor = VideoProcessor()

        with pytest.raises(VideoProcessorError, match="FFmpeg not available"):
            processor.get_video_info("test.mp4")

    @patch.object(VideoProcessor, "check_ffmpeg_available", return_value=True)
    @patch("subprocess.run")
    def test_get_video_info_success(self, mock_run, mock_check):
        """Test successful video info retrieval."""
        probe_output = {
            "format": {"duration": "10.5", "size": "1234567"},
            "streams": [
                {
                    "codec_type": "video",
                    "width": 1920,
                    "height": 1080,
                    "r_frame_rate": "30/1",
                    "codec_name": "h264",
                }
            ],
        }

        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(probe_output))

        processor = VideoProcessor()
        info = processor.get_video_info("test.mp4")

        assert info["duration"] == 10.5
        assert info["size_bytes"] == 1234567
        assert info["width"] == 1920
        assert info["height"] == 1080
        assert info["fps"] == 30.0
        assert info["codec"] == "h264"

    @patch.object(VideoProcessor, "check_ffmpeg_available", return_value=True)
    @patch("subprocess.run")
    @patch("os.path.exists", return_value=False)
    def test_get_video_info_ffprobe_failure(self, mock_exists, mock_run, mock_check):
        """Test video info when FFprobe fails (falls back to default values)."""
        mock_run.return_value = MagicMock(returncode=1, stderr="FFprobe error")

        processor = VideoProcessor()
        info = processor.get_video_info("test.mp4")

        # Should return fallback values when FFprobe fails
        assert info["duration"] == 0
        assert info["size_bytes"] == 0  # file doesn't exist
        assert info["width"] == 0
        assert info["height"] == 0
        assert info["fps"] == 0
        assert info["codec"] == "unknown"

    @patch.object(VideoProcessor, "check_ffmpeg_available", return_value=True)
    @patch("subprocess.run")
    @patch("os.path.getsize", return_value=9999)
    @patch("os.path.exists", return_value=True)
    def test_get_video_info_fallback(
        self, mock_exists, mock_getsize, mock_run, mock_check
    ):
        """Test video info fallback when JSON parsing fails."""
        mock_run.return_value = MagicMock(returncode=0, stdout="invalid json")

        processor = VideoProcessor()
        info = processor.get_video_info("test.mp4")

        # Should return fallback values
        assert info["duration"] == 0
        assert info["size_bytes"] == 9999  # From os.path.getsize
        assert info["width"] == 0
        assert info["height"] == 0
        assert info["fps"] == 0
        assert info["codec"] == "unknown"

    @patch.object(VideoProcessor, "check_ffmpeg_available", return_value=True)
    @patch("subprocess.run")
    def test_get_video_info_missing_video_stream(self, mock_run, mock_check):
        """Test video info with no video stream."""
        probe_output = {
            "format": {"duration": "5.0", "size": "999"},
            "streams": [{"codec_type": "audio"}],  # Only audio stream
        }

        mock_run.return_value = MagicMock(returncode=0, stdout=json.dumps(probe_output))

        processor = VideoProcessor()
        info = processor.get_video_info("audio_only.mp4")

        assert info["duration"] == 5.0
        assert info["width"] == 0  # No video stream
        assert info["height"] == 0
        assert info["fps"] == 0
        assert info["codec"] == "unknown"

    @patch.object(VideoProcessor, "check_ffmpeg_available", return_value=True)
    @patch("subprocess.run")
    def test_get_video_info_command_structure(self, mock_run, mock_check):
        """Test FFprobe command structure."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout='{"format": {}, "streams": []}'
        )

        processor = VideoProcessor()
        processor.get_video_info("test.mp4")

        expected_cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            "test.mp4",
        ]

        mock_run.assert_called_once_with(
            expected_cmd, capture_output=True, text=True, timeout=10
        )


class TestVideoProcessorIntegration:
    """Test integration scenarios and edge cases."""

    def test_complete_workflow_integration(self):
        """Test complete workflow with real temp directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            processor = VideoProcessor(temp_dir)

            # Verify temp directory exists
            assert Path(temp_dir).exists()

            # Test FFmpeg availability (will depend on system)
            ffmpeg_available = processor.check_ffmpeg_available()
            assert isinstance(ffmpeg_available, bool)

    @patch("subprocess.run")
    def test_error_propagation(self, mock_run):
        """Test that errors are properly propagated and wrapped."""
        mock_run.side_effect = Exception("Unexpected error")

        processor = VideoProcessor()

        with pytest.raises(VideoProcessorError, match="Video processing failed"):
            processor.process_animation_to_video("a.mp4", "b.wav", "c.mov")

    def test_temp_directory_edge_cases(self):
        """Test temp directory handling edge cases."""
        # Test with relative path
        processor1 = VideoProcessor("./temp_relative")
        assert processor1.temp_dir == Path("./temp_relative")

        # Test with absolute path
        processor2 = VideoProcessor("/tmp/absolute_temp")
        assert processor2.temp_dir == Path("/tmp/absolute_temp")

    @patch("subprocess.run")
    def test_realistic_video_processing_scenario(self, mock_run):
        """Test realistic video processing scenario."""
        # Mock successful FFmpeg calls
        mock_run.return_value = MagicMock(returncode=0, stderr="")

        processor = VideoProcessor("harmonica_temp/")

        # Create some temporary files to simulate real workflow
        with tempfile.TemporaryDirectory() as temp_dir:
            raw_video = Path(temp_dir) / "raw_animation.mp4"
            audio_file = Path(temp_dir) / "harmonica_audio.wav"
            final_output = Path(temp_dir) / "final_harmonica_video.mov"

            # Create placeholder files
            raw_video.touch()
            audio_file.touch()

            # Process video
            processor.process_animation_to_video(
                str(raw_video), str(audio_file), str(final_output), cleanup_temp=True
            )

            # Verify FFmpeg was called twice (transparency + audio)
            assert mock_run.call_count == 2

            # Verify command structures
            calls = mock_run.call_args_list
            transparency_cmd = calls[0][0][0]
            audio_cmd = calls[1][0][0]

            assert transparency_cmd[0] == "ffmpeg"
            assert audio_cmd[0] == "ffmpeg"
            assert "colorkey" in " ".join(transparency_cmd)
            assert "aac" in audio_cmd
