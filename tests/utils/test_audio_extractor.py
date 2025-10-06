"""Tests for utils.audio_extractor module."""

import os
import subprocess
from unittest.mock import MagicMock, patch
import pytest

from utils.audio_extractor import (
    AudioExtractor,
    AudioConfig,
    ExtractionResult,
    AudioExtractionError,
    MOVIEPY_AVAILABLE,
)


class TestAudioConfig:
    """Test AudioConfig dataclass functionality."""

    def test_default_config(self):
        """Test default AudioConfig values."""
        config = AudioConfig()
        assert config.sample_rate == 44100
        assert config.channels == 2
        assert config.audio_codec == "pcm_s16le"
        assert config.prefer_moviepy is True
        assert config.validate_output is True
        assert config.cleanup_on_error is True

    def test_custom_config(self):
        """Test custom AudioConfig values."""
        config = AudioConfig(
            sample_rate=48000,
            channels=1,
            audio_codec="aac",
            prefer_moviepy=False,
            validate_output=False,
            cleanup_on_error=False,
        )
        assert config.sample_rate == 48000
        assert config.channels == 1
        assert config.audio_codec == "aac"
        assert config.prefer_moviepy is False
        assert config.validate_output is False
        assert config.cleanup_on_error is False


class TestExtractionResult:
    """Test ExtractionResult dataclass functionality."""

    def test_extraction_result_creation(self):
        """Test creating ExtractionResult."""
        result = ExtractionResult(
            success=True,
            output_path="/path/to/audio.wav",
            method_used="MoviePy",
            file_size_bytes=1024000,
            duration_seconds=60.5,
            sample_rate=44100,
            channels=2,
        )
        assert result.success is True
        assert result.output_path == "/path/to/audio.wav"
        assert result.method_used == "MoviePy"
        assert result.file_size_bytes == 1024000
        assert result.duration_seconds == 60.5
        assert result.sample_rate == 44100
        assert result.channels == 2
        assert result.error_message is None

    def test_extraction_result_with_error(self):
        """Test ExtractionResult with error."""
        result = ExtractionResult(
            success=False,
            output_path="",
            method_used="FFmpeg",
            file_size_bytes=0,
            duration_seconds=None,
            sample_rate=None,
            channels=None,
            error_message="Extraction failed",
        )
        assert result.success is False
        assert result.error_message == "Extraction failed"


class TestAudioExtractorInitialization:
    """Test AudioExtractor initialization."""

    def test_init_with_valid_paths(self, temp_test_dir):
        """Test initialization with valid paths."""
        video_path = temp_test_dir / "test.mp4"
        audio_path = temp_test_dir / "output.wav"
        video_path.write_text("dummy video")

        extractor = AudioExtractor(str(video_path), str(audio_path))
        assert extractor._video_path == str(video_path)
        assert extractor._audio_result_path == str(audio_path)
        assert isinstance(extractor._config, AudioConfig)

    def test_init_with_custom_config(self, temp_test_dir):
        """Test initialization with custom config."""
        video_path = temp_test_dir / "test.mp4"
        audio_path = temp_test_dir / "output.wav"
        video_path.write_text("dummy video")

        config = AudioConfig(sample_rate=48000, channels=1)
        extractor = AudioExtractor(str(video_path), str(audio_path), config)
        assert extractor._config.sample_rate == 48000
        assert extractor._config.channels == 1

    def test_init_with_missing_video_file(self, temp_test_dir):
        """Test initialization fails with missing video file."""
        video_path = temp_test_dir / "nonexistent.mp4"
        audio_path = temp_test_dir / "output.wav"

        with pytest.raises(AudioExtractionError, match="Video file not found"):
            AudioExtractor(str(video_path), str(audio_path))

    def test_init_with_empty_paths(self):
        """Test initialization fails with empty paths."""
        with pytest.raises(AudioExtractionError, match="Video path cannot be empty"):
            AudioExtractor("", "/output.wav")

        with pytest.raises(
            AudioExtractionError, match="Audio result path cannot be empty"
        ):
            AudioExtractor("/video.mp4", "")

    def test_init_creates_output_directory(self, temp_test_dir):
        """Test initialization creates output directory if needed."""
        video_path = temp_test_dir / "test.mp4"
        audio_path = temp_test_dir / "subdir" / "output.wav"
        video_path.write_text("dummy video")

        AudioExtractor(str(video_path), str(audio_path))
        assert os.path.exists(temp_test_dir / "subdir")

    def test_init_output_directory_creation_fails(self, temp_test_dir):
        """Test initialization fails when output directory cannot be created."""
        video_path = temp_test_dir / "test.mp4"
        video_path.write_text("dummy video")

        # Try to create directory in a read-only location (simulate permission error)
        with patch("os.makedirs", side_effect=OSError("Permission denied")):
            with pytest.raises(
                AudioExtractionError, match="Cannot create output directory"
            ):
                AudioExtractor(str(video_path), "/root/restricted/output.wav")


class TestAudioExtractorFileDetection:
    """Test audio file detection functionality."""

    @pytest.mark.parametrize(
        "extension,expected",
        [
            (".wav", True),
            (".mp3", True),
            (".aac", True),
            (".m4a", True),
            (".flac", True),
            (".ogg", True),
            (".WAV", True),  # Case insensitive
            (".MP3", True),
            (".mp4", False),
            (".mov", False),
            (".avi", False),
            (".txt", False),
            ("", False),
        ],
    )
    def test_is_audio_file(self, temp_test_dir, extension, expected):
        """Test audio file detection by extension."""
        video_path = temp_test_dir / "dummy.mp4"
        audio_path = temp_test_dir / "output.wav"
        video_path.write_text("dummy")

        extractor = AudioExtractor(str(video_path), str(audio_path))

        test_file = f"test{extension}"
        result = extractor._is_audio_file(test_file)
        assert result == expected

    def test_extract_audio_returns_input_for_audio_files(self, temp_test_dir):
        """Test that audio files are returned as-is without extraction."""
        audio_path = temp_test_dir / "input.wav"
        output_path = temp_test_dir / "output.wav"
        audio_path.write_text("dummy audio content")

        extractor = AudioExtractor(str(audio_path), str(output_path))
        result = extractor.extract_audio_from_video()
        assert result == str(audio_path)


class TestAudioExtractorExtractionMethods:
    """Test audio extraction method selection and execution."""

    def test_get_extraction_methods_moviepy_preferred(self, temp_test_dir):
        """Test extraction method order when MoviePy is preferred."""
        video_path = temp_test_dir / "test.mp4"
        audio_path = temp_test_dir / "output.wav"
        video_path.write_text("dummy")

        config = AudioConfig(prefer_moviepy=True)
        extractor = AudioExtractor(str(video_path), str(audio_path), config)

        with patch.object(extractor, "_check_ffmpeg_available", return_value=True):
            methods = extractor._get_extraction_methods()

        if MOVIEPY_AVAILABLE:
            assert methods[0][0] == "MoviePy"
            assert methods[1][0] == "FFmpeg"
        else:
            assert methods[0][0] == "FFmpeg"

    def test_get_extraction_methods_ffmpeg_preferred(self, temp_test_dir):
        """Test extraction method order when FFmpeg is preferred."""
        video_path = temp_test_dir / "test.mp4"
        audio_path = temp_test_dir / "output.wav"
        video_path.write_text("dummy")

        config = AudioConfig(prefer_moviepy=False)
        extractor = AudioExtractor(str(video_path), str(audio_path), config)

        methods = extractor._get_extraction_methods()
        assert methods[0][0] == "FFmpeg"

    def test_check_ffmpeg_available(self, temp_test_dir):
        """Test FFmpeg availability check."""
        video_path = temp_test_dir / "test.mp4"
        audio_path = temp_test_dir / "output.wav"
        video_path.write_text("dummy")

        extractor = AudioExtractor(str(video_path), str(audio_path))

        # Mock successful ffmpeg check
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock()
            assert extractor._check_ffmpeg_available() is True

        # Mock failed ffmpeg check
        with patch("subprocess.run", side_effect=FileNotFoundError):
            assert extractor._check_ffmpeg_available() is False

        # Mock ffmpeg error
        with patch(
            "subprocess.run", side_effect=subprocess.CalledProcessError(1, "ffmpeg")
        ):
            assert extractor._check_ffmpeg_available() is False


class TestAudioExtractorMoviePyExtraction:
    """Test MoviePy extraction functionality."""

    @pytest.mark.skipif(not MOVIEPY_AVAILABLE, reason="MoviePy not available")
    def test_extract_with_moviepy_success(self, temp_test_dir):
        """Test successful MoviePy extraction."""
        video_path = temp_test_dir / "test.mp4"
        audio_path = temp_test_dir / "output.wav"
        video_path.write_text("dummy")

        extractor = AudioExtractor(str(video_path), str(audio_path))

        # Mock VideoFileClip and audio extraction
        mock_video_clip = MagicMock()
        mock_audio = MagicMock()
        mock_audio.duration = 60.5
        mock_video_clip.audio = mock_audio

        with patch("utils.audio_extractor.VideoFileClip", return_value=mock_video_clip):
            with patch("os.path.getsize", return_value=1024000):
                result = extractor._extract_with_moviepy()

        assert result.success is True
        assert result.method_used == "MoviePy"
        assert result.duration_seconds == 60.5
        assert result.file_size_bytes == 1024000
        mock_audio.write_audiofile.assert_called_once()
        mock_video_clip.close.assert_called_once()

    def test_extract_with_moviepy_no_audio_track(self, temp_test_dir):
        """Test MoviePy extraction with video file that has no audio."""
        video_path = temp_test_dir / "test.mp4"
        audio_path = temp_test_dir / "output.wav"
        video_path.write_text("dummy")

        extractor = AudioExtractor(str(video_path), str(audio_path))

        # Mock VideoFileClip with no audio
        mock_video_clip = MagicMock()
        mock_video_clip.audio = None

        with patch("utils.audio_extractor.VideoFileClip", return_value=mock_video_clip):
            with pytest.raises(
                AudioExtractionError, match="Video file has no audio track"
            ):
                extractor._extract_with_moviepy()

    def test_extract_with_moviepy_not_available(self, temp_test_dir):
        """Test MoviePy extraction when MoviePy is not available."""
        video_path = temp_test_dir / "test.mp4"
        audio_path = temp_test_dir / "output.wav"
        video_path.write_text("dummy")

        extractor = AudioExtractor(str(video_path), str(audio_path))

        # Temporarily disable MoviePy
        with patch("utils.audio_extractor.MOVIEPY_AVAILABLE", False):
            with pytest.raises(AudioExtractionError, match="MoviePy not available"):
                extractor._extract_with_moviepy()

    def test_extract_with_moviepy_exception(self, temp_test_dir):
        """Test MoviePy extraction with exception during processing."""
        video_path = temp_test_dir / "test.mp4"
        audio_path = temp_test_dir / "output.wav"
        video_path.write_text("dummy")

        extractor = AudioExtractor(str(video_path), str(audio_path))

        with patch(
            "utils.audio_extractor.VideoFileClip",
            side_effect=Exception("VideoClip error"),
        ):
            with pytest.raises(AudioExtractionError, match="MoviePy extraction failed"):
                extractor._extract_with_moviepy()


class TestAudioExtractorFFmpegExtraction:
    """Test FFmpeg extraction functionality."""

    def test_extract_with_ffmpeg_success(self, temp_test_dir):
        """Test successful FFmpeg extraction."""
        video_path = temp_test_dir / "test.mp4"
        audio_path = temp_test_dir / "output.wav"
        video_path.write_text("dummy")

        extractor = AudioExtractor(str(video_path), str(audio_path))

        # Mock successful ffmpeg run
        mock_result = MagicMock()
        mock_result.stderr = "Duration: 01:02:30.50"

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            with patch("os.path.getsize", return_value=2048000):
                with patch.object(
                    extractor, "_check_ffmpeg_available", return_value=True
                ):
                    result = extractor._extract_with_ffmpeg()

        assert result.success is True
        assert result.method_used == "FFmpeg"
        assert result.file_size_bytes == 2048000
        assert result.duration_seconds == 3750.5  # 1:02:30.50 in seconds

        # Verify ffmpeg command
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "ffmpeg"
        assert "-i" in args
        assert str(video_path) in args
        assert str(audio_path) in args

    def test_extract_with_ffmpeg_not_available(self, temp_test_dir):
        """Test FFmpeg extraction when FFmpeg is not available."""
        video_path = temp_test_dir / "test.mp4"
        audio_path = temp_test_dir / "output.wav"
        video_path.write_text("dummy")

        extractor = AudioExtractor(str(video_path), str(audio_path))

        with patch.object(extractor, "_check_ffmpeg_available", return_value=False):
            with pytest.raises(
                AudioExtractionError, match="FFmpeg not found on system"
            ):
                extractor._extract_with_ffmpeg()

    def test_extract_with_ffmpeg_command_failure(self, temp_test_dir):
        """Test FFmpeg extraction with command failure."""
        video_path = temp_test_dir / "test.mp4"
        audio_path = temp_test_dir / "output.wav"
        video_path.write_text("dummy")

        extractor = AudioExtractor(str(video_path), str(audio_path))

        # Mock ffmpeg command failure
        with patch.object(extractor, "_check_ffmpeg_available", return_value=True):
            with patch(
                "subprocess.run",
                side_effect=subprocess.CalledProcessError(
                    1, "ffmpeg", stderr="Error message"
                ),
            ):
                with pytest.raises(
                    AudioExtractionError, match="FFmpeg failed with code 1"
                ):
                    extractor._extract_with_ffmpeg()

    def test_extract_with_ffmpeg_not_found(self, temp_test_dir):
        """Test FFmpeg extraction when executable is not found."""
        video_path = temp_test_dir / "test.mp4"
        audio_path = temp_test_dir / "output.wav"
        video_path.write_text("dummy")

        extractor = AudioExtractor(str(video_path), str(audio_path))

        with patch.object(extractor, "_check_ffmpeg_available", return_value=True):
            with patch("subprocess.run", side_effect=FileNotFoundError):
                with pytest.raises(
                    AudioExtractionError, match="FFmpeg executable not found"
                ):
                    extractor._extract_with_ffmpeg()

    @pytest.mark.parametrize(
        "ffmpeg_output,expected_duration",
        [
            ("Duration: 01:23:45.67", 5025.67),
            ("Duration: 00:01:30.00", 90.0),
            ("Duration: 02:00:00.50", 7200.5),
            ("No duration info", None),
            ("Duration: invalid", None),
            ("", None),
        ],
    )
    def test_extract_duration_from_ffmpeg_output(
        self, temp_test_dir, ffmpeg_output, expected_duration
    ):
        """Test duration extraction from FFmpeg output."""
        video_path = temp_test_dir / "test.mp4"
        audio_path = temp_test_dir / "output.wav"
        video_path.write_text("dummy")

        extractor = AudioExtractor(str(video_path), str(audio_path))
        duration = extractor._extract_duration_from_ffmpeg_output(ffmpeg_output)
        assert duration == expected_duration


class TestAudioExtractorValidation:
    """Test extraction result validation."""

    def test_validate_extraction_success(self, temp_test_dir):
        """Test validation of successful extraction."""
        video_path = temp_test_dir / "test.mp4"
        audio_path = temp_test_dir / "output.wav"
        video_path.write_text("dummy")
        # Create a file larger than 1KB to pass validation
        dummy_audio = "x" * 2048  # 2KB of dummy content
        audio_path.write_text(dummy_audio)

        extractor = AudioExtractor(str(video_path), str(audio_path))

        result = ExtractionResult(
            success=True,
            output_path=str(audio_path),
            method_used="MoviePy",
            file_size_bytes=len(dummy_audio),
            duration_seconds=60.0,
            sample_rate=44100,
            channels=2,
        )

        # Should not raise any exception
        extractor._validate_extraction(result)

    def test_validate_extraction_disabled(self, temp_test_dir):
        """Test validation when disabled in config."""
        video_path = temp_test_dir / "test.mp4"
        audio_path = temp_test_dir / "output.wav"
        video_path.write_text("dummy")

        config = AudioConfig(validate_output=False)
        extractor = AudioExtractor(str(video_path), str(audio_path), config)

        result = ExtractionResult(
            success=False,  # Even with failure, should not validate
            output_path=str(audio_path),
            method_used="MoviePy",
            file_size_bytes=0,
            duration_seconds=None,
            sample_rate=None,
            channels=None,
            error_message="Some error",
        )

        # Should not raise any exception when validation is disabled
        extractor._validate_extraction(result)

    def test_validate_extraction_failure_reported(self, temp_test_dir):
        """Test validation when extraction reports failure."""
        video_path = temp_test_dir / "test.mp4"
        audio_path = temp_test_dir / "output.wav"
        video_path.write_text("dummy")

        extractor = AudioExtractor(str(video_path), str(audio_path))

        result = ExtractionResult(
            success=False,
            output_path=str(audio_path),
            method_used="MoviePy",
            file_size_bytes=0,
            duration_seconds=None,
            sample_rate=None,
            channels=None,
            error_message="Extraction failed",
        )

        with pytest.raises(AudioExtractionError, match="Extraction reported failure"):
            extractor._validate_extraction(result)

    def test_validate_extraction_missing_output_file(self, temp_test_dir):
        """Test validation when output file is missing."""
        video_path = temp_test_dir / "test.mp4"
        audio_path = temp_test_dir / "output.wav"
        video_path.write_text("dummy")

        extractor = AudioExtractor(str(video_path), str(audio_path))

        result = ExtractionResult(
            success=True,
            output_path=str(audio_path),  # File doesn't exist
            method_used="MoviePy",
            file_size_bytes=1024,
            duration_seconds=60.0,
            sample_rate=44100,
            channels=2,
        )

        with pytest.raises(AudioExtractionError, match="Output file not created"):
            extractor._validate_extraction(result)

    def test_validate_extraction_empty_file(self, temp_test_dir):
        """Test validation when output file is empty."""
        video_path = temp_test_dir / "test.mp4"
        audio_path = temp_test_dir / "output.wav"
        video_path.write_text("dummy")
        audio_path.write_text("")  # Empty file

        extractor = AudioExtractor(str(video_path), str(audio_path))

        result = ExtractionResult(
            success=True,
            output_path=str(audio_path),
            method_used="MoviePy",
            file_size_bytes=0,
            duration_seconds=60.0,
            sample_rate=44100,
            channels=2,
        )

        with pytest.raises(AudioExtractionError, match="Output file is empty"):
            extractor._validate_extraction(result)

    def test_validate_extraction_suspiciously_small(self, temp_test_dir):
        """Test validation when output file is suspiciously small."""
        video_path = temp_test_dir / "test.mp4"
        audio_path = temp_test_dir / "output.wav"
        video_path.write_text("dummy")
        audio_path.write_text("x")  # Very small file

        extractor = AudioExtractor(str(video_path), str(audio_path))

        result = ExtractionResult(
            success=True,
            output_path=str(audio_path),
            method_used="MoviePy",
            file_size_bytes=1,  # Less than 1KB
            duration_seconds=60.0,
            sample_rate=44100,
            channels=2,
        )

        with pytest.raises(
            AudioExtractionError, match="Output file suspiciously small"
        ):
            extractor._validate_extraction(result)


class TestAudioExtractorIntegration:
    """Test full extraction workflow and integration."""

    def test_extract_audio_with_moviepy_success(self, temp_test_dir):
        """Test full extraction workflow with MoviePy success."""
        video_path = temp_test_dir / "test.mp4"
        audio_path = temp_test_dir / "output.wav"
        video_path.write_text("dummy video")

        config = AudioConfig(prefer_moviepy=True, validate_output=False)
        extractor = AudioExtractor(str(video_path), str(audio_path), config)

        # Mock successful MoviePy extraction
        with patch.object(extractor, "_extract_with_moviepy") as mock_moviepy:
            mock_moviepy.return_value = ExtractionResult(
                success=True,
                output_path=str(audio_path),
                method_used="MoviePy",
                file_size_bytes=1024000,
                duration_seconds=60.0,
                sample_rate=44100,
                channels=2,
            )

            result_path = extractor.extract_audio_from_video()
            assert result_path == str(audio_path)
            mock_moviepy.assert_called_once()

    def test_extract_audio_with_fallback_to_ffmpeg(self, temp_test_dir):
        """Test extraction workflow with fallback from MoviePy to FFmpeg."""
        video_path = temp_test_dir / "test.mp4"
        audio_path = temp_test_dir / "output.wav"
        video_path.write_text("dummy video")

        config = AudioConfig(prefer_moviepy=True, validate_output=False)
        extractor = AudioExtractor(str(video_path), str(audio_path), config)

        # Mock MoviePy failure and FFmpeg success
        with patch.object(
            extractor,
            "_extract_with_moviepy",
            side_effect=AudioExtractionError("MoviePy failed"),
        ):
            with patch.object(extractor, "_extract_with_ffmpeg") as mock_ffmpeg:
                mock_ffmpeg.return_value = ExtractionResult(
                    success=True,
                    output_path=str(audio_path),
                    method_used="FFmpeg",
                    file_size_bytes=2048000,
                    duration_seconds=65.0,
                    sample_rate=44100,
                    channels=2,
                )

                result_path = extractor.extract_audio_from_video()
                assert result_path == str(audio_path)
                mock_ffmpeg.assert_called_once()

    def test_extract_audio_all_methods_fail(self, temp_test_dir):
        """Test extraction when all methods fail."""
        video_path = temp_test_dir / "test.mp4"
        audio_path = temp_test_dir / "output.wav"
        video_path.write_text("dummy video")

        extractor = AudioExtractor(str(video_path), str(audio_path))

        # Mock both methods failing
        with patch.object(
            extractor,
            "_extract_with_moviepy",
            side_effect=AudioExtractionError("MoviePy failed"),
        ):
            with patch.object(
                extractor,
                "_extract_with_ffmpeg",
                side_effect=AudioExtractionError("FFmpeg failed"),
            ):
                with pytest.raises(
                    AudioExtractionError, match="All extraction methods failed"
                ):
                    extractor.extract_audio_from_video()

    def test_extract_audio_cleanup_on_error(self, temp_test_dir):
        """Test cleanup of partial files when extraction fails."""
        video_path = temp_test_dir / "test.mp4"
        audio_path = temp_test_dir / "output.wav"
        video_path.write_text("dummy video")

        config = AudioConfig(cleanup_on_error=True)
        extractor = AudioExtractor(str(video_path), str(audio_path), config)

        # Create partial output file
        audio_path.write_text("partial content")
        assert audio_path.exists()

        # Mock extraction failure
        with patch.object(
            extractor,
            "_extract_with_moviepy",
            side_effect=AudioExtractionError("Failed"),
        ):
            with patch.object(
                extractor,
                "_extract_with_ffmpeg",
                side_effect=AudioExtractionError("Failed"),
            ):
                with pytest.raises(AudioExtractionError):
                    extractor.extract_audio_from_video()

        # File should be cleaned up
        assert not audio_path.exists()

    def test_extract_audio_no_cleanup_on_error(self, temp_test_dir):
        """Test no cleanup when cleanup_on_error is disabled."""
        video_path = temp_test_dir / "test.mp4"
        audio_path = temp_test_dir / "output.wav"
        video_path.write_text("dummy video")

        config = AudioConfig(cleanup_on_error=False)
        extractor = AudioExtractor(str(video_path), str(audio_path), config)

        # Create partial output file
        audio_path.write_text("partial content")
        assert audio_path.exists()

        # Mock extraction failure
        with patch.object(
            extractor,
            "_extract_with_moviepy",
            side_effect=AudioExtractionError("Failed"),
        ):
            with patch.object(
                extractor,
                "_extract_with_ffmpeg",
                side_effect=AudioExtractionError("Failed"),
            ):
                with pytest.raises(AudioExtractionError):
                    extractor.extract_audio_from_video()

        # File should still exist
        assert audio_path.exists()


class TestAudioExtractorUtilities:
    """Test utility methods and properties."""

    def test_get_extraction_info(self, temp_test_dir):
        """Test extraction information gathering."""
        video_path = temp_test_dir / "test.mp4"
        audio_path = temp_test_dir / "output.wav"
        video_content = "dummy video content"
        video_path.write_text(video_content)

        config = AudioConfig(sample_rate=48000, channels=1)
        extractor = AudioExtractor(str(video_path), str(audio_path), config)

        with patch.object(extractor, "_check_ffmpeg_available", return_value=True):
            info = extractor.get_extraction_info()

        assert info["video_path"] == str(video_path)
        assert info["output_path"] == str(audio_path)
        assert info["config"]["sample_rate"] == 48000
        assert info["config"]["channels"] == 1
        assert info["capabilities"]["moviepy_available"] == MOVIEPY_AVAILABLE
        assert info["capabilities"]["ffmpeg_available"] is True
        assert info["input_file"]["exists"] is True
        assert info["input_file"]["is_audio"] is False
        assert info["input_file"]["size_mb"] == len(video_content) / (1024 * 1024)

    def test_legacy_vid_path_property(self, temp_test_dir):
        """Test backwards compatibility property."""
        video_path = temp_test_dir / "test.mp4"
        audio_path = temp_test_dir / "output.wav"
        video_path.write_text("dummy")

        extractor = AudioExtractor(str(video_path), str(audio_path))
        assert extractor._vid_path == str(video_path)

    def test_extraction_info_with_missing_file(self, temp_test_dir):
        """Test extraction info when video file is missing after creation."""
        video_path = temp_test_dir / "test.mp4"
        audio_path = temp_test_dir / "output.wav"
        video_path.write_text("dummy")

        extractor = AudioExtractor(str(video_path), str(audio_path))

        # Remove file after initialization
        os.remove(video_path)

        with patch.object(extractor, "_check_ffmpeg_available", return_value=False):
            info = extractor.get_extraction_info()

        assert info["input_file"]["exists"] is False
        assert info["input_file"]["size_mb"] == 0
        assert info["capabilities"]["ffmpeg_available"] is False


class TestAudioExtractorCoverageGaps:
    """Test cases to achieve higher coverage for AudioExtractor."""

    def test_cleanup_file_removal_error(self, temp_test_dir):
        """Test OSError handling during file cleanup - Lines 124-125."""
        video_path = temp_test_dir / "test.mp4"
        audio_path = temp_test_dir / "output.wav"
        video_path.write_text("dummy")

        # Create the audio file so it exists for removal attempt
        audio_path.write_text("dummy audio")

        config = AudioConfig(cleanup_on_error=True)
        extractor = AudioExtractor(str(video_path), str(audio_path), config)

        # Mock extraction methods to fail and os.remove to raise OSError
        with patch.object(
            extractor, "_extract_with_moviepy", side_effect=Exception("MoviePy failed")
        ):
            with patch.object(
                extractor,
                "_extract_with_ffmpeg",
                side_effect=Exception("FFmpeg failed"),
            ):
                with patch("os.remove", side_effect=OSError("Permission denied")):
                    with pytest.raises(
                        AudioExtractionError, match="All extraction methods failed"
                    ):
                        extractor.extract_audio_from_video()

                    # File should still exist despite removal error
                    assert audio_path.exists()

    def test_duration_parsing_exception(self, temp_test_dir):
        """Test Exception handling in duration parsing - Lines 363-364."""
        video_path = temp_test_dir / "test.mp4"
        audio_path = temp_test_dir / "output.wav"
        video_path.write_text("dummy")

        config = AudioConfig(prefer_moviepy=False)
        extractor = AudioExtractor(str(video_path), str(audio_path), config)

        # Mock re.search to raise an exception during parsing
        with patch("re.search", side_effect=Exception("Regex processing error")):
            # This should trigger the exception handling in _extract_duration_from_ffmpeg_output
            duration = extractor._extract_duration_from_ffmpeg_output(
                "Duration: 01:02:30.50"
            )

            # Should return None when parsing fails due to exception
            assert duration is None
