"""
Video Processor - Handles FFmpeg operations and video file management.

Separated from Animator for better separation of concerns and easier testing.
"""

import os
import subprocess
from pathlib import Path
from typing import Dict, Any


class VideoProcessorError(Exception):
    """Custom exception for video processing errors."""

    pass


class VideoProcessor:
    """
    Handles video encoding, transparency effects, and file management.

    Uses FFmpeg for all video operations with proper error handling.
    """

    def __init__(self, temp_dir: str = "temp/"):
        """
        Initialize video processor.

        Args:
            temp_dir: Directory for temporary files
        """
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def process_animation_to_video(
        self,
        raw_video_path: str,
        audio_path: str,
        final_output_path: str,
        cleanup_temp: bool = True,
    ) -> None:
        """
        Convert raw animation video to final transparent video with audio.

        Args:
            raw_video_path: Path to raw matplotlib animation video
            audio_path: Path to audio file to add
            final_output_path: Final output video path
            cleanup_temp: Whether to clean up temporary files

        Raises:
            VideoProcessorError: If any FFmpeg operation fails
        """
        transparent_video_path = self.temp_dir / "temp_transparent.mov"

        try:
            # Step 1: Create transparent video (remove magenta background)
            self._create_transparent_video(raw_video_path, str(transparent_video_path))

            # Step 2: Add audio to transparent video
            self._add_audio_to_video(
                str(transparent_video_path), audio_path, final_output_path
            )

            print(
                f"✅ Final video with transparency + audio saved to {final_output_path}"
            )

        except Exception as e:
            raise VideoProcessorError(f"Video processing failed: {e}")

        finally:
            # Cleanup temporary files
            if cleanup_temp:
                self._cleanup_temp_files([raw_video_path, str(transparent_video_path)])

    def _create_transparent_video(self, input_path: str, output_path: str) -> None:
        """
        Remove magenta background and create transparent video.

        Args:
            input_path: Input video with magenta background
            output_path: Output transparent video path

        Raises:
            VideoProcessorError: If transparency processing fails
        """
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            input_path,
            "-vf",
            "colorkey=0xFF00FF:0.4:0.0,format=yuva444p10le",
            "-c:v",
            "prores_ks",
            "-profile:v",
            "4",
            "-pix_fmt",
            "yuva444p10le",
            output_path,
        ]

        print("🟣 Creating transparent video...")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise VideoProcessorError(
                f"Failed to create transparent video: {result.stderr}"
            )

        print(f"✅ Transparent video created: {output_path}")

    def _add_audio_to_video(
        self, video_path: str, audio_path: str, output_path: str
    ) -> None:
        """
        Add audio track to video.

        Args:
            video_path: Input video path
            audio_path: Audio file path
            output_path: Final output path

        Raises:
            VideoProcessorError: If audio processing fails
        """
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            video_path,
            "-i",
            audio_path,
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            output_path,
        ]

        print("🎵 Adding audio to video...")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise VideoProcessorError(f"Failed to add audio to video: {result.stderr}")

    def _cleanup_temp_files(self, file_paths: list[str]) -> None:
        """
        Clean up temporary files safely.

        Args:
            file_paths: List of file paths to remove
        """
        for file_path in file_paths:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"🗑️  Cleaned up: {os.path.basename(file_path)}")
            except Exception as e:
                print(f"⚠️  Warning: Could not remove {file_path}: {e}")

    def check_ffmpeg_available(self) -> bool:
        """
        Check if FFmpeg is available on the system.

        Returns:
            True if FFmpeg is available, False otherwise
        """
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"], capture_output=True, text=True, timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def get_video_info(self, video_path: str) -> dict:
        """
        Get detailed video information using FFprobe.

        Args:
            video_path: Path to video file

        Returns:
            Dict with video information (duration, resolution, etc.)

        Raises:
            VideoProcessorError: If video info cannot be retrieved
        """
        if not self.check_ffmpeg_available():
            raise VideoProcessorError("FFmpeg not available for video info")

        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            video_path,
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                raise VideoProcessorError(f"FFprobe failed: {result.stderr}")

            import json

            probe_data = json.loads(result.stdout)

            # Extract basic info
            format_info = probe_data.get("format", {})
            video_stream: Dict[str, Any] = next(
                (
                    s
                    for s in probe_data.get("streams", [])
                    if s.get("codec_type") == "video"
                ),
                {},
            )

            return {
                "duration": float(format_info.get("duration", 0)),
                "size_bytes": int(format_info.get("size", 0)),
                "width": video_stream.get("width", 0),
                "height": video_stream.get("height", 0),
                "fps": eval(
                    video_stream.get("r_frame_rate", "0/1")
                ),  # e.g., "30/1" -> 30.0
                "codec": video_stream.get("codec_name", "unknown"),
            }

        except Exception:
            # Fallback to basic file size info
            return {
                "duration": 0,
                "size_bytes": (
                    os.path.getsize(video_path) if os.path.exists(video_path) else 0
                ),
                "width": 0,
                "height": 0,
                "fps": 0,
                "codec": "unknown",
            }
