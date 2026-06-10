"""Video splicing utilities for partial re-render feature.

Splices a re-rendered video segment back into the original video using
FFmpeg concat demuxer for frame-accurate editing without re-encoding.
"""

import os
import subprocess
import tempfile
from typing import Optional


class VideoSplicerError(Exception):
    """Custom exception for video splicing errors."""

    pass


def splice_video_segment(
    original_video: str,
    replacement_segment: str,
    start_time: float,
    end_time: float,
    output_path: str,
) -> None:
    """
    Splice a replacement video segment into the original video.

    Uses FFmpeg concat demuxer to join:
    [original[0:start_time]] + [replacement_segment] + [original[end_time:]]

    Args:
        original_video: Path to original video file
        replacement_segment: Path to replacement video segment
        start_time: Start time of segment to replace (in seconds)
        end_time: End time of segment to replace (in seconds)
        output_path: Path to output spliced video

    Raises:
        VideoSplicerError: If splicing fails
    """
    if not os.path.exists(original_video):
        raise VideoSplicerError(f"Original video not found: {original_video}")

    if not os.path.exists(replacement_segment):
        raise VideoSplicerError(f"Replacement segment not found: {replacement_segment}")

    if start_time >= end_time:
        raise VideoSplicerError(f"Invalid time range: {start_time} >= {end_time}")

    temp_dir = tempfile.gettempdir()
    concat_file = os.path.join(temp_dir, "concat_list.txt")
    segment1_path_full = os.path.join(temp_dir, "segment1_trim.mov")
    segment3_path_full = os.path.join(temp_dir, "segment3_trim.mov")

    try:
        # Segment 1: Original[0 : start_time]
        segment1_path: Optional[str] = None
        if start_time > 0.01:  # Only trim if significant
            print(f"📹 Extracting original[0:{start_time:.2f}s]...")
            _trim_video(original_video, 0, start_time, segment1_path_full)
            segment1_path = segment1_path_full

        # Segment 2: Replacement (already trimmed)
        print("📹 Using replacement segment...")
        segment2_path = replacement_segment

        # Segment 3: Original[end_time : end]
        print(f"📹 Extracting original[{end_time:.2f}s:end]...")
        _trim_video(original_video, end_time, None, segment3_path_full)

        # Build concat file
        segments = [
            seg for seg in [segment1_path, segment2_path, segment3_path_full] if seg
        ]

        if not segments:
            raise VideoSplicerError("No valid segments to splice")

        print(f"🔗 Concatenating {len(segments)} segments...")
        _write_concat_file(concat_file, segments)

        # Use FFmpeg concat demuxer
        cmd = [
            "ffmpeg",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            concat_file,
            "-c",
            "copy",  # Copy codec (no re-encoding)
            "-y",
            output_path,
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise VideoSplicerError(f"FFmpeg concat failed: {result.stderr}")

        print(f"✅ Spliced video saved: {output_path}")

    except VideoSplicerError:
        raise
    except Exception as e:
        raise VideoSplicerError(f"Splicing failed: {e}") from e
    finally:
        # Cleanup temp files
        for path in [concat_file, segment1_path_full, segment3_path_full]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass


def _trim_video(
    input_path: str, start_time: float, end_time: Optional[float], output_path: str
) -> None:
    """Trim video to specified time range using FFmpeg."""
    cmd = [
        "ffmpeg",
        "-i",
        input_path,
        "-ss",
        str(start_time),
    ]

    if end_time is not None:
        cmd.extend(["-to", str(end_time)])

    cmd.extend(["-c", "copy", "-y", output_path])

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        raise VideoSplicerError(f"FFmpeg trim failed: {result.stderr}")


def _write_concat_file(filepath: str, video_paths: list) -> None:
    """Write FFmpeg concat demuxer file."""
    with open(filepath, "w") as f:
        for video_path in video_paths:
            # Escape single quotes in path
            safe_path = video_path.replace("'", "'\\''")
            f.write(f"file '{safe_path}'\n")
