"""
FullTabVideoCompositor - Creates a single continuous tab video from page videos.

Stitches together individual page animations into one continuous video where
pages appear/disappear in sync with audio timing, with individual notes lighting
up precisely as they play.
"""

import json
import os
import subprocess
from dataclasses import dataclass
from typing import List, Optional

from tab_phrase_animator.tab_phrase_animator import PageStatistics
from utils.utils import TEMP_DIR


@dataclass
class PageWindow:
    """Timing window for a single page in the full video."""

    page_idx: int
    page_name: str
    start_time: float  # When page appears
    end_time: float  # When page disappears
    duration: float  # Page visibility duration
    video_path: str  # Path to the page video file


@dataclass
class CompositorConfig:
    """Configuration for full tab video compositor."""

    transition_gap: float = 0.1  # Gap between pages (transparent frames)
    background_color: tuple = (0, 0, 0, 0)  # RGBA for transparent background
    cleanup_temp_files: bool = True


class FullTabVideoCompositorError(Exception):
    """Custom exception for compositor errors."""

    pass


class FullTabVideoCompositor:
    """
    Creates a single continuous tab video from individual page videos.

    Stitches page videos together with transparent gaps, maintaining proper
    timing synchronization with the audio.
    """

    def __init__(self, config: Optional[CompositorConfig] = None):
        """
        Initialize the full tab video compositor.

        Args:
            config: Optional compositor configuration
        """
        self._config = config or CompositorConfig()
        self._page_windows: List[PageWindow] = []

    def generate(
        self,
        page_statistics: List[PageStatistics],
        audio_duration: float,
        output_path: str,
        audio_path: Optional[str] = None,
    ) -> str:
        """
        Generate the full tab video from individual page videos.

        Args:
            page_statistics: List of PageStatistics from TabPhraseAnimator
            audio_duration: Total duration of the audio file
            output_path: Path for the output video file
            audio_path: Optional path to audio file to add to video

        Returns:
            Path to the generated full tab video

        Raises:
            FullTabVideoCompositorError: If video generation fails
        """
        if not page_statistics:
            raise FullTabVideoCompositorError("No page statistics provided")

        print(f"🎬 Creating full tab video from {len(page_statistics)} pages")
        print(f"🎵 Total audio duration: {audio_duration:.3f}s")

        # Calculate page windows
        self._page_windows = self._calculate_page_windows(page_statistics)

        # Validate page videos exist
        self._validate_page_videos()

        # Stitch videos together
        video_only_path = self._stitch_videos(audio_duration, output_path)

        # Add audio track if provided
        if audio_path:
            final_path = self._add_audio_track(video_only_path, audio_path, output_path)
        else:
            final_path = video_only_path

        print(f"✅ Full tab video created: {final_path}")
        return final_path

    def _calculate_page_windows(
        self, page_statistics: List[PageStatistics]
    ) -> List[PageWindow]:
        """
        Calculate timing windows for each page.

        Each page window determines when the page appears and disappears
        in the final video based on the first and last note timings.

        Args:
            page_statistics: List of PageStatistics from TabPhraseAnimator

        Returns:
            List of PageWindow objects with timing information
        """
        windows = []

        for idx, stats in enumerate(page_statistics, start=1):
            # Page timing already includes the time_buffer from TabPhraseAnimator
            # So start_time and end_time are already padded
            window = PageWindow(
                page_idx=idx,
                page_name=stats.page_name,
                start_time=stats.start_time,
                end_time=stats.end_time,
                duration=stats.duration,
                video_path=stats.output_file,
            )
            windows.append(window)

            print(
                f"   📄 Page {idx} ({stats.page_name}): "
                f"{window.start_time:.3f}s -> {window.end_time:.3f}s "
                f"(duration: {window.duration:.3f}s)"
            )

        return windows

    def _validate_page_videos(self) -> None:
        """
        Validate that all page video files exist.

        Raises:
            FullTabVideoCompositorError: If any page video is missing
        """
        for window in self._page_windows:
            if not os.path.exists(window.video_path):
                raise FullTabVideoCompositorError(
                    f"Page video not found: {window.video_path}"
                )

    def _stitch_videos(self, audio_duration: float, final_output_path: str) -> str:
        """
        Stitch page videos together with transparent gaps using ffmpeg.

        Args:
            audio_duration: Total audio duration
            final_output_path: Path for the final output video

        Returns:
            Path to the video-only stitched video (without audio)

        Raises:
            FullTabVideoCompositorError: If video stitching fails
        """
        # Create temporary video-only output path
        output_path = final_output_path.replace(".mov", "_noaudio.mov")
        try:
            # Get video dimensions from first page
            video_size = self._get_video_dimensions(self._page_windows[0].video_path)

            # Create concat file for ffmpeg
            concat_file_path = os.path.join(TEMP_DIR, "full_tab_concat.txt")
            temp_files = []
            current_time = 0.0

            # Build list of video segments placing each at absolute timestamp
            video_segments = []
            video_durations = []  # Track duration for each segment

            for window in self._page_windows:
                # Calculate where this page should appear in the final timeline
                if current_time < window.start_time:
                    # Add blank gap before this page
                    gap_before = window.start_time - current_time
                    print(
                        f"   🔲 Adding {gap_before:.3f}s blank before page {window.page_idx}"
                    )
                    blank_video = self._create_blank_video(gap_before, video_size)
                    video_segments.append(blank_video)
                    video_durations.append(gap_before)
                    temp_files.append(blank_video)
                    current_time = window.start_time

                elif current_time > window.start_time:
                    # Page overlaps with previous - need to truncate the previous segment
                    overlap = current_time - window.start_time
                    print(
                        f"   ⚠️  Page {window.page_idx} overlaps previous by {overlap:.3f}s"
                    )
                    # Trim overlap from the last segment that was added
                    if video_segments and video_durations:
                        prev_duration = video_durations[-1]
                        new_duration = prev_duration - overlap
                        if new_duration > 0.01:
                            # Re-add the previous segment with trimmed duration
                            prev_segment = video_segments.pop()
                            prev_duration_val = video_durations.pop()
                            trimmed_video = self._trim_video(
                                prev_segment, 0, new_duration, video_size
                            )
                            video_segments.append(trimmed_video)
                            video_durations.append(new_duration)
                            temp_files.append(trimmed_video)
                            print(
                                f"   ✂️  Trimmed previous segment from {prev_duration_val:.3f}s to {new_duration:.3f}s"
                            )
                        current_time = window.start_time

                # Add page video at correct position
                video_segments.append(window.video_path)
                video_durations.append(window.duration)
                print(
                    f"   🎬 Added page {window.page_idx} at {current_time:.3f}s (duration: {window.duration:.3f}s)"
                )
                current_time = window.end_time

            # Add final blank gap if needed to match audio duration
            final_gap = audio_duration - current_time
            if final_gap > 0.01:
                blank_video = self._create_blank_video(final_gap, video_size)
                video_segments.append(blank_video)
                temp_files.append(blank_video)
                print(f"   🔲 Added {final_gap:.3f}s blank at end")

            # Create concat file
            with open(concat_file_path, "w") as f:
                for segment in video_segments:
                    # Escape single quotes in path
                    escaped_path = segment.replace("'", "'\\''")
                    f.write(f"file '{escaped_path}'\n")
            temp_files.append(concat_file_path)

            # Concatenate videos using ffmpeg
            print("🔗 Concatenating clips with ffmpeg...")
            self._concatenate_with_ffmpeg(concat_file_path, output_path)

            # Cleanup temporary files
            if self._config.cleanup_temp_files:
                for temp_file in temp_files:
                    try:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                    except OSError:
                        pass  # Ignore cleanup errors

            return output_path

        except Exception as e:
            raise FullTabVideoCompositorError(f"Video stitching failed: {e}") from e

    def _get_video_dimensions(self, video_path: str) -> tuple[int, int]:
        """
        Get video dimensions using ffprobe.

        Args:
            video_path: Path to video file

        Returns:
            Tuple of (width, height)

        Raises:
            FullTabVideoCompositorError: If dimensions cannot be determined
        """
        try:
            cmd = [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_streams",
                "-select_streams",
                "v:0",
                video_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            stream = data["streams"][0]
            width = int(stream["width"])
            height = int(stream["height"])
            return (width, height)
        except Exception as e:
            # Default to 1920x1080 if detection fails
            print(
                f"⚠️  Warning: Could not detect video dimensions, using default 1920x1080: {e}"
            )
            return (1920, 1080)

    def _trim_video(
        self, video_path: str, start_time: float, end_time: float, size: tuple[int, int]
    ) -> str:
        """
        Trim a video to a specific time range.

        Args:
            video_path: Path to source video
            start_time: Start time in seconds
            end_time: End time in seconds
            size: Video dimensions (width, height)

        Returns:
            Path to trimmed video file

        Raises:
            FullTabVideoCompositorError: If trimming fails
        """
        import time

        timestamp = str(int(time.time() * 1000000))
        trimmed_path = os.path.join(TEMP_DIR, f"trimmed_{timestamp}.mov")

        try:
            duration = end_time - start_time
            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                video_path,
                "-ss",
                f"{start_time:.3f}",
                "-t",
                f"{duration:.3f}",
                "-c:v",
                "prores_ks",
                "-profile:v",
                "4",
                "-pix_fmt",
                "yuva444p10le",
                trimmed_path,
            ]

            subprocess.run(cmd, capture_output=True, text=True, check=True)
            return trimmed_path

        except subprocess.CalledProcessError as e:
            raise FullTabVideoCompositorError(
                f"Failed to trim video: {e.stderr}"
            ) from e

    def _create_blank_video(self, duration: float, size: tuple[int, int]) -> str:
        """
        Create a blank (transparent) video file using ffmpeg.

        Args:
            duration: Duration of the blank video in seconds
            size: Tuple of (width, height)

        Returns:
            Path to the created blank video file

        Raises:
            FullTabVideoCompositorError: If blank video creation fails
        """
        import time

        # Create unique temporary file
        timestamp = str(int(time.time() * 1000000))
        blank_path = os.path.join(TEMP_DIR, f"blank_{timestamp}.mov")

        width, height = size

        try:
            # Create transparent video using ffmpeg
            # Use lavfi with color source and set alpha channel
            cmd = [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                f"color=color=#FF00FF:size={width}x{height}:rate=30:duration={duration}",
                "-vf",
                "colorkey=0xFF00FF:0.3:0.0,format=yuva444p10le",
                "-c:v",
                "prores_ks",
                "-profile:v",
                "4",
                "-pix_fmt",
                "yuva444p10le",
                blank_path,
            ]

            subprocess.run(cmd, capture_output=True, text=True, check=True)
            return blank_path

        except subprocess.CalledProcessError as e:
            raise FullTabVideoCompositorError(
                f"Failed to create blank video: {e.stderr}"
            ) from e

    def _concatenate_with_ffmpeg(self, concat_file: str, output_path: str) -> None:
        """
        Concatenate videos using ffmpeg concat demuxer.

        Args:
            concat_file: Path to concat file listing videos
            output_path: Path for output video

        Raises:
            FullTabVideoCompositorError: If concatenation fails
        """
        try:
            # Force re-encoding to ensure precise timing
            # Using ProRes 4444 to preserve alpha channel and quality
            cmd = [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                concat_file,
                "-c:v",
                "prores_ks",
                "-profile:v",
                "4",  # ProRes 4444 profile (supports alpha)
                "-pix_fmt",
                "yuva444p10le",  # Preserve alpha channel
                "-fps_mode",
                "cfr",  # Constant frame rate mode for precise timing
                output_path,
            ]

            subprocess.run(cmd, capture_output=True, text=True, check=True)

        except subprocess.CalledProcessError as e:
            raise FullTabVideoCompositorError(
                f"Video concatenation failed: {e.stderr}"
            ) from e

    def _add_audio_track(
        self, video_path: str, audio_path: str, output_path: str
    ) -> str:
        """
        Add audio track to video using ffmpeg.

        Args:
            video_path: Path to video file (without audio)
            audio_path: Path to audio file
            output_path: Path for output video with audio

        Returns:
            Path to the final video with audio

        Raises:
            FullTabVideoCompositorError: If audio addition fails
        """
        try:
            print(f"   🎵 Adding audio track from {os.path.basename(audio_path)}")

            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                video_path,
                "-i",
                audio_path,
                "-c:v",
                "copy",  # Copy video stream without re-encoding
                "-c:a",
                "aac",  # Encode audio as AAC
                "-map",
                "0:v:0",  # Use video from first input
                "-map",
                "1:a:0",  # Use audio from second input
                "-shortest",  # Match shortest stream duration
                output_path,
            ]

            subprocess.run(cmd, capture_output=True, text=True, check=True)

            # Clean up temporary video-only file
            if os.path.exists(video_path) and video_path != output_path:
                try:
                    os.remove(video_path)
                except OSError:
                    pass  # Ignore cleanup errors

            return output_path

        except subprocess.CalledProcessError as e:
            raise FullTabVideoCompositorError(
                f"Failed to add audio track: {e.stderr}"
            ) from e

    def get_page_windows(self) -> List[PageWindow]:
        """
        Get the calculated page windows.

        Returns:
            List of PageWindow objects
        """
        return self._page_windows.copy()
