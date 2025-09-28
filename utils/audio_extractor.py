"""
AudioExtractor - Extracts audio from video files with fallback methods.

Provides robust audio extraction using MoviePy and FFmpeg with comprehensive
error handling, format detection, and audio quality validation.
"""

import os
import subprocess
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Callable

try:
    from moviepy import VideoFileClip

    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False


@dataclass
class AudioConfig:
    """Configuration for audio extraction."""

    sample_rate: int = 44100
    channels: int = 2  # Stereo
    audio_codec: str = "pcm_s16le"
    prefer_moviepy: bool = True
    validate_output: bool = True
    cleanup_on_error: bool = True


@dataclass
class ExtractionResult:
    """Result of audio extraction operation."""

    success: bool
    output_path: str
    method_used: str
    file_size_bytes: int
    duration_seconds: Optional[float]
    sample_rate: Optional[int]
    channels: Optional[int]
    error_message: Optional[str] = None


class AudioExtractionError(Exception):
    """Custom exception for audio extraction errors."""

    pass


class AudioExtractor:
    """
    Extracts audio from video files with multiple fallback methods.

    Supports both MoviePy and FFmpeg extraction with comprehensive error
    handling, format validation, and quality assessment.
    """

    def __init__(
        self,
        video_path: str,
        audio_result_path: str,
        config: Optional[AudioConfig] = None,
    ):
        """
        Initialize audio extractor.

        Args:
            video_path: Path to input video file
            audio_result_path: Path for output audio file
            config: Optional extraction configuration

        Raises:
            AudioExtractionError: If initialization fails
        """
        self._video_path = video_path
        self._audio_result_path = audio_result_path
        self._config = config or AudioConfig()

        # Validate inputs
        self._validate_inputs()

    def extract_audio_from_video(self) -> str:
        """
        Extract audio from video with automatic fallback.

        Returns:
            Path to the extracted audio file

        Raises:
            AudioExtractionError: If all extraction methods fail
        """
        # If input is already an audio file, return it
        if self._is_audio_file(self._video_path):
            print(f"📄 Input is already an audio file: {self._video_path}")
            return self._video_path

        print(f"🎧 Extracting audio from: {self._video_path}")
        print(f"📁 Output: {self._audio_result_path}")

        extraction_methods = self._get_extraction_methods()
        last_error = None

        for method_name, method_func in extraction_methods:
            try:
                print(f"🔄 Trying {method_name}...")
                result = method_func()
                self._validate_extraction(result)
                print(f"✅ {method_name} extraction successful")
                return result.output_path

            except Exception as e:
                last_error = e
                print(f"⚠️  {method_name} failed: {e}")

                # Cleanup partial files on error
                if self._config.cleanup_on_error and os.path.exists(
                    self._audio_result_path
                ):
                    try:
                        os.remove(self._audio_result_path)
                    except OSError:
                        pass

        # All methods failed
        error_msg = f"All extraction methods failed. Last error: {last_error}"
        raise AudioExtractionError(error_msg)

    def get_extraction_info(self) -> Dict[str, Any]:
        """
        Get information about extraction capabilities and configuration.

        Returns:
            Dict with extraction information
        """
        return {
            "video_path": self._video_path,
            "output_path": self._audio_result_path,
            "config": {
                "sample_rate": self._config.sample_rate,
                "channels": self._config.channels,
                "audio_codec": self._config.audio_codec,
                "prefer_moviepy": self._config.prefer_moviepy,
                "validate_output": self._config.validate_output,
            },
            "capabilities": {
                "moviepy_available": MOVIEPY_AVAILABLE,
                "ffmpeg_available": self._check_ffmpeg_available(),
            },
            "input_file": {
                "exists": os.path.exists(self._video_path),
                "is_audio": self._is_audio_file(self._video_path),
                "size_mb": (
                    os.path.getsize(self._video_path) / (1024 * 1024)
                    if os.path.exists(self._video_path)
                    else 0
                ),
            },
        }

    def _validate_inputs(self) -> None:
        """
        Validate input parameters.

        Raises:
            AudioExtractionError: If validation fails
        """
        if not self._video_path:
            raise AudioExtractionError("Video path cannot be empty")

        if not self._audio_result_path:
            raise AudioExtractionError("Audio result path cannot be empty")

        if not os.path.exists(self._video_path):
            raise AudioExtractionError(f"Video file not found: {self._video_path}")

        # Ensure output directory exists
        output_dir = os.path.dirname(self._audio_result_path)
        if output_dir and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except OSError as e:
                raise AudioExtractionError(f"Cannot create output directory: {e}")

    def _is_audio_file(self, file_path: str) -> bool:
        """
        Check if file is already an audio file.

        Args:
            file_path: Path to check

        Returns:
            True if file appears to be audio
        """
        audio_extensions = {".wav", ".mp3", ".aac", ".m4a", ".flac", ".ogg"}
        return os.path.splitext(file_path)[1].lower() in audio_extensions

    def _get_extraction_methods(self) -> List[tuple[str, Callable]]:
        """
        Get list of available extraction methods in order of preference.

        Returns:
            List of (method_name, method_function) tuples
        """
        methods = []

        if self._config.prefer_moviepy and MOVIEPY_AVAILABLE:
            methods.append(("MoviePy", self._extract_with_moviepy))
            methods.append(("FFmpeg", self._extract_with_ffmpeg))
        else:
            methods.append(("FFmpeg", self._extract_with_ffmpeg))
            if MOVIEPY_AVAILABLE:
                methods.append(("MoviePy", self._extract_with_moviepy))

        return methods

    def _extract_with_moviepy(self) -> ExtractionResult:
        """
        Extract audio using MoviePy.

        Returns:
            ExtractionResult with extraction details

        Raises:
            AudioExtractionError: If MoviePy extraction fails
        """
        if not MOVIEPY_AVAILABLE:
            raise AudioExtractionError("MoviePy not available")

        try:
            video_clip = VideoFileClip(self._video_path)

            if video_clip.audio is None:
                raise AudioExtractionError("Video file has no audio track")

            audio = video_clip.audio
            audio.write_audiofile(
                self._audio_result_path,
                logger=None,  # Suppress moviepy logs
                verbose=False,
            )

            # Get audio properties
            duration = audio.duration

            # Cleanup
            video_clip.close()

            file_size = os.path.getsize(self._audio_result_path)

            return ExtractionResult(
                success=True,
                output_path=self._audio_result_path,
                method_used="MoviePy",
                file_size_bytes=file_size,
                duration_seconds=duration,
                sample_rate=self._config.sample_rate,
                channels=self._config.channels,
            )

        except Exception as e:
            raise AudioExtractionError(f"MoviePy extraction failed: {e}")

    def _extract_with_ffmpeg(self) -> ExtractionResult:
        """
        Extract audio using FFmpeg.

        Returns:
            ExtractionResult with extraction details

        Raises:
            AudioExtractionError: If FFmpeg extraction fails
        """
        if not self._check_ffmpeg_available():
            raise AudioExtractionError("FFmpeg not found on system")

        cmd = [
            "ffmpeg",
            "-y",  # Overwrite output
            "-i",
            self._video_path,
            "-map",
            "0:a:0",  # Select first audio stream
            "-acodec",
            self._config.audio_codec,
            "-ar",
            str(self._config.sample_rate),
            "-ac",
            str(self._config.channels),
            self._audio_result_path,
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            # Get file properties
            file_size = os.path.getsize(self._audio_result_path)

            # Extract duration from ffmpeg output if possible
            duration = self._extract_duration_from_ffmpeg_output(result.stderr)

            return ExtractionResult(
                success=True,
                output_path=self._audio_result_path,
                method_used="FFmpeg",
                file_size_bytes=file_size,
                duration_seconds=duration,
                sample_rate=self._config.sample_rate,
                channels=self._config.channels,
            )

        except subprocess.CalledProcessError as e:
            error_msg = f"FFmpeg failed with code {e.returncode}"
            if e.stderr:
                error_msg += f": {e.stderr.strip()}"
            raise AudioExtractionError(error_msg)
        except FileNotFoundError:
            raise AudioExtractionError("FFmpeg executable not found")

    def _check_ffmpeg_available(self) -> bool:
        """
        Check if FFmpeg is available on the system.

        Returns:
            True if FFmpeg is available
        """
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            return False

    def _extract_duration_from_ffmpeg_output(
        self, stderr_output: str
    ) -> Optional[float]:
        """
        Extract duration from FFmpeg stderr output.

        Args:
            stderr_output: FFmpeg stderr text

        Returns:
            Duration in seconds, or None if not found
        """
        try:
            # Look for duration in format "Duration: HH:MM:SS.ss"
            import re

            match = re.search(
                r"Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})", stderr_output
            )
            if match:
                hours, minutes, seconds, centiseconds = match.groups()
                total_seconds = (
                    int(hours) * 3600
                    + int(minutes) * 60
                    + int(seconds)
                    + int(centiseconds) / 100
                )
                return total_seconds
        except Exception:
            pass  # Ignore parsing errors

        return None

    def _validate_extraction(self, result: ExtractionResult) -> None:
        """
        Validate the extraction result.

        Args:
            result: Extraction result to validate

        Raises:
            AudioExtractionError: If validation fails
        """
        if not self._config.validate_output:
            return

        if not result.success:
            raise AudioExtractionError(
                f"Extraction reported failure: {result.error_message}"
            )

        if not os.path.exists(result.output_path):
            raise AudioExtractionError(f"Output file not created: {result.output_path}")

        if result.file_size_bytes == 0:
            raise AudioExtractionError("Output file is empty")

        # Basic size sanity check (audio should be at least 1KB)
        if result.file_size_bytes < 1024:
            raise AudioExtractionError(
                f"Output file suspiciously small: {result.file_size_bytes} bytes"
            )

    # Backwards compatibility properties
    @property
    def _vid_path(self) -> str:
        """Legacy property for backwards compatibility."""
        return self._video_path
