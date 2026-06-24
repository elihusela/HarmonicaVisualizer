import os
import time
from typing import List, Optional, Dict

import matplotlib.animation as animation
from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from matplotlib.patches import Rectangle
from matplotlib.text import Text

from image_converter.consts import IN_COLOR, OUT_COLOR, BEND_COLOR
from image_converter.figure_factory import FigureFactory
from image_converter.harmonica_layout import HarmonicaLayout
from image_converter.video_processor import VideoProcessor, VideoProcessorError
from image_converter.animation_analyzer import AnimationAnalyzer
from tab_converter.models import TabEntry
from utils.utils import TEMP_DIR
from typing import Optional as OptionalType


def adjust_consecutive_identical_notes(
    flat_entries: List[TabEntry],
    gap: float = 0.15,
    min_duration: float = 0.1,
    max_gap: float = 2.0,
) -> List[TabEntry]:
    """
    Force visual gap between consecutive identical notes for clarity.

    Only applies to notes that are reasonably close together (within max_gap).
    Ensures every note has minimum visible duration even when notes are very close.

    Args:
        flat_entries: List of tab entries to adjust
        gap: Desired gap between consecutive identical notes (default 0.15s)
        min_duration: Minimum visible duration for any note (default 0.1s)
        max_gap: Only adjust notes within this time distance (default 2.0s)
    """
    for i in range(len(flat_entries) - 1):
        current = flat_entries[i]
        next_entry = flat_entries[i + 1]

        if current.tab == next_entry.tab:
            time_available = next_entry.time - current.time

            # Only adjust if notes are reasonably close (avoid page boundaries)
            if time_available > max_gap:
                continue  # Skip adjustment for distant notes

            # If we have room for min_duration + gap, use it
            if time_available >= (min_duration + gap):
                current.duration = time_available - gap
            # If notes are very close, prioritize visibility over gap
            elif time_available >= min_duration:
                current.duration = min_duration
            # If impossibly close, use what we have with minimal gap
            else:
                current.duration = max(0.05, time_available - 0.05)
    return flat_entries


class Animator:
    def __init__(
        self,
        harmonica_layout: HarmonicaLayout,
        figure_factory: FigureFactory,
        temp_dir: OptionalType[str] = None,
        use_alpha: bool = False,
        chroma_key_config=None,
        enable_static_optimization: bool = True,
    ):
        self._frame_timings: List[float] = []
        self._harmonica_layout = harmonica_layout
        self._figure_factory = figure_factory
        self._text_objects: List[Text] = []
        self._arrows: List[Text] = []
        self._temp_dir = temp_dir or TEMP_DIR
        self._temp_video_path: str = self._temp_dir + "temp_video.mp4"
        self._ax: Optional[Axes] = None
        self._squares: List[Rectangle] = []
        self._flat_entries: List[TabEntry] = []
        self._audio_duration: Optional[float] = None
        self._video_processor = VideoProcessor(self._temp_dir)
        self._use_alpha = use_alpha
        self._chroma_key_config = chroma_key_config
        self._enable_static_optimization = enable_static_optimization

    def create_animation(
        self,
        all_pages: Dict[str, List[List[Optional[List[TabEntry]]]]],
        extracted_audio_path: str,
        output_path: str,
        fps: int = 15,
        audio_duration: Optional[float] = None,
        use_alpha: Optional[bool] = None,
        chroma_key_config=None,
        time_range: Optional[tuple[float, float]] = None,
        force_full_render: bool = False,
    ) -> None:
        # Allow per-call override; fall back to instance defaults
        effective_use_alpha = use_alpha if use_alpha is not None else self._use_alpha
        effective_chroma_cfg = chroma_key_config or self._chroma_key_config

        self._flat_entries = [
            entry
            for page in all_pages.values()
            for line in page
            for chord in line
            if chord
            for entry in chord
        ]

        # Store original time range for splicing if partial render
        self._time_range = time_range
        self._time_offset = 0.0

        # Filter entries to time range if specified
        if time_range:
            start_time, end_time = time_range
            self._time_offset = start_time
            # Keep entries that overlap with the time range
            self._flat_entries = [
                entry
                for entry in self._flat_entries
                if entry.time < end_time and (entry.time + entry.duration) > start_time
            ]
            # Adjust times to start from 0
            for entry in self._flat_entries:
                entry.time = max(0, entry.time - start_time)

        self._flat_entries = adjust_consecutive_identical_notes(self._flat_entries)
        self._audio_duration = audio_duration

        total_duration = self._get_total_duration()
        total_frames = self._get_total_frames(fps, total_duration)

        # Check if static optimization should apply
        # Note: Static optimization is incompatible with alpha/ProRes mode due to codec
        # mismatch in concat. For alpha mode, always do full render.
        if (
            self._enable_static_optimization
            and not force_full_render
            and not effective_use_alpha
            and self._flat_entries
        ):
            analyzer = AnimationAnalyzer(self._flat_entries, fps=fps)
            if analyzer.should_optimize(total_duration, min_speedup_percent=10.0):
                stats = analyzer.get_animation_statistics(total_duration)
                speedup = stats["speed_improvement_estimate"]
                print(
                    f"⚡ Static optimization enabled: ~{speedup:.0f}% speedup "
                    f"({stats['animated_duration']:.1f}s of {total_duration:.1f}s)"
                )
                self._render_with_static_optimization(
                    analyzer=analyzer,
                    extracted_audio_path=extracted_audio_path,
                    output_path=output_path,
                    total_duration=total_duration,
                    fps=fps,
                    effective_use_alpha=effective_use_alpha,
                    effective_chroma_cfg=effective_chroma_cfg,
                )
                return

        # Set background color based on mode
        if not effective_use_alpha:
            from harmonica_pipeline.video_creator_config import ChromaKeyConfig

            cfg = effective_chroma_cfg or ChromaKeyConfig()
            try:
                self._figure_factory._config.background_color = cfg.bg_color
            except AttributeError:
                pass  # figure_factory may be mocked or not have _config

        fig, self._ax = self._figure_factory.create()

        ani = animation.FuncAnimation(
            fig,
            lambda frame: self._timed_update_frame(frame, fps),
            frames=total_frames,
            blit=False,
            interval=1000 / fps,
            cache_frame_data=False,
        )

        ani.save(self._temp_video_path, fps=fps, writer="ffmpeg")
        print(f"Intermediate video saved to {self._temp_video_path}")

        if self._frame_timings:
            avg_frame_time = sum(self._frame_timings) / len(self._frame_timings)
            print(
                f"Average frame update time: {avg_frame_time:.4f}s over {len(self._frame_timings)} samples"
            )

        # Use VideoProcessor for post-processing
        try:
            if effective_use_alpha:
                # ProRes alpha path (archived mode)
                self._video_processor.process_animation_to_video(
                    self._temp_video_path,
                    extracted_audio_path,
                    output_path,
                    cleanup_temp=True,
                )
            else:
                # Chroma key H.265 path (default)
                from harmonica_pipeline.video_creator_config import ChromaKeyConfig

                cfg = effective_chroma_cfg or ChromaKeyConfig()
                self._video_processor.process_animation_to_chromakey_video(
                    self._temp_video_path,
                    extracted_audio_path,
                    output_path,
                    chroma_key_config=cfg,
                    cleanup_temp=True,
                )

            # Log video information
            self._log_video_info(output_path, total_duration, fps, total_frames)

        except VideoProcessorError as e:
            print(f"Video processing failed: {e}")
            raise

    def _timed_update_frame(self, frame: int, fps: int) -> List:
        start = time.perf_counter()
        output = self._update_frame(frame, fps)
        elapsed = time.perf_counter() - start
        if frame % 30 == 0:  # log every 30th frame
            self._frame_timings.append(elapsed)
        return output

    def _update_frame(self, frame: int, fps: int) -> List:
        current_time = frame / fps

        # Clear previous frame objects more efficiently
        self._clear_frame_objects()

        assert self._ax is not None

        # Only process notes that should be visible at current time
        active_entries = [
            entry
            for entry in self._flat_entries
            if entry.time <= current_time <= entry.time + entry.duration
        ]

        # Create objects for active notes
        for tab_entry in active_entries:
            self._create_note_visualization(tab_entry)

        return self._text_objects + self._arrows

    def _clear_frame_objects(self) -> None:
        """Efficiently clear frame objects."""
        for obj in self._text_objects + self._arrows:
            obj.remove()
        self._text_objects.clear()
        self._arrows.clear()

    def _create_note_visualization(self, tab_entry: TabEntry) -> None:
        """
        Create visualization objects for a single note.

        Args:
            tab_entry: The tab entry to visualize
        """
        hole = abs(tab_entry.tab)
        center_x, center_y = self._harmonica_layout.get_position(hole)
        rect_x, rect_y, rect_width, rect_height = self._harmonica_layout.get_rectangle(
            hole
        )
        direction = self._calc_direction(tab_entry)
        color = self._get_color(tab_entry)

        # Create rectangle
        if self._ax is None:
            raise RuntimeError("Axes not initialized")
        rect = self._ax.add_patch(
            plt.Rectangle(
                (rect_x, rect_y),
                rect_width,
                rect_height,
                linewidth=0,
                edgecolor=None,
                facecolor=color,
                alpha=tab_entry.confidence,
            )
        )

        # Create hole number text
        txt = self._ax.text(
            center_x,
            center_y - 10,
            f"{hole}",
            color="black",
            fontsize=26,
            ha="center",
            va="center",
            weight="bold",
        )

        # Create direction arrow
        arr = self._ax.text(
            center_x,
            center_y + 20,
            direction,
            color="black",
            fontsize=26,
            ha="center",
            va="center",
        )

        # Store objects for cleanup
        self._text_objects.extend([txt, rect])
        self._arrows.append(arr)

    @staticmethod
    def _get_color(tab_entry: TabEntry) -> str:
        """
        Get the color for a tab entry.

        Returns:
            BEND_COLOR (orange) if the note is bent,
            OUT_COLOR (green) if blow note,
            IN_COLOR (red) if draw note
        """
        if tab_entry.is_bend:
            return BEND_COLOR
        return OUT_COLOR if tab_entry.tab > 0 else IN_COLOR

    @staticmethod
    def _calc_direction(tab_entry: TabEntry) -> str:
        return "↑" if tab_entry.tab > 0 else "↓"

    def _get_total_duration(self) -> float:
        # Use provided audio duration if available (shows harmonica for full video)
        if self._audio_duration is not None:
            return self._audio_duration

        # Fallback: Calculate from notes (backwards compatibility)
        max_end_time = max(
            tab.time + (tab.duration or 0.5) for tab in self._flat_entries
        )
        # Add a small buffer to ensure the last note fades out properly
        return max_end_time + 0.5

    @staticmethod
    def _get_total_frames(fps: int, total_duration: float) -> int:
        return int(total_duration * fps)

    def _log_video_info(
        self, video_path: str, duration: float, fps: int, total_frames: int
    ) -> None:
        """
        Log comprehensive video information after creation.

        Args:
            video_path: Path to the final video file
            duration: Video duration in seconds
            fps: Frames per second
            total_frames: Total number of frames
        """
        try:
            # Get file size
            file_size_bytes = os.path.getsize(video_path)
            file_size_mb = file_size_bytes / (1024 * 1024)

            # Calculate video metrics
            bitrate_kbps = (
                (file_size_bytes * 8) / (duration * 1000) if duration > 0 else 0
            )

            print("\n" + "=" * 50)
            print("📹 VIDEO INFORMATION")
            print("=" * 50)
            print(f"📁 File: {os.path.basename(video_path)}")
            print(f"📏 Size: {file_size_mb:.2f} MB ({file_size_bytes:,} bytes)")
            print(f"⏱️  Duration: {duration:.2f}s")
            print(f"🎬 Frames: {total_frames} @ {fps} FPS")
            print(f"📊 Estimated bitrate: {bitrate_kbps:.0f} kbps")
            print(f"💾 Path: {video_path}")

            # Performance metrics
            if self._frame_timings:
                avg_frame_time = sum(self._frame_timings) / len(self._frame_timings)
                total_render_time = avg_frame_time * total_frames
                print(f"⚡ Avg frame time: {avg_frame_time:.4f}s")
                print(f"🏃 Est. total render: {total_render_time:.2f}s")

            print("=" * 50 + "\n")

        except Exception as e:
            print(f"⚠️  Warning: Could not retrieve video info: {e}")
            print(f"✅ Video saved to: {video_path}\n")

    def _render_with_static_optimization(
        self,
        analyzer: AnimationAnalyzer,
        extracted_audio_path: str,
        output_path: str,
        total_duration: float,
        fps: int,
        effective_use_alpha: bool,
        effective_chroma_cfg,
    ) -> None:
        """Render only animated segment and compose with static frames.

        Splits video into [static_start] + [animated] + [static_end] and only
        renders the middle segment, dramatically speeding up render time for
        videos with sparse notes.

        Args:
            analyzer: AnimationAnalyzer with animation boundaries
            extracted_audio_path: Path to audio file
            output_path: Final output video path
            total_duration: Total video duration
            fps: Frames per second
            effective_use_alpha: Whether to use alpha channel output
            effective_chroma_cfg: Chroma key config if applicable
        """
        _, anim_start, anim_end = analyzer.analyze_animation_range()
        anim_duration = anim_end - anim_start

        # Create empty harmonica frame (no notes)
        empty_frame_path = self._create_empty_harmonica_frame(fps)

        # Render only the animated segment
        try:
            # Temporarily update flat_entries to only animated range
            original_entries = self._flat_entries.copy()
            self._flat_entries = [
                entry
                for entry in original_entries
                if entry.time < anim_end and (entry.time + entry.duration) > anim_start
            ]
            # Adjust times to segment start
            for entry in self._flat_entries:
                entry.time = max(0, entry.time - anim_start)

            # Render animated segment (use .mov for alpha, .mp4 for chromakey)
            ext = ".mov" if effective_use_alpha else ".mp4"
            segment_path = (
                self._temp_dir + f"segment_{anim_start:.2f}_{anim_end:.2f}{ext}"
            )
            self._render_segment_video(
                extracted_audio_path,
                segment_path,
                anim_duration,
                fps,
                effective_use_alpha,
                effective_chroma_cfg,
            )

            # Compose segments: static_start + animated + static_end
            self._compose_optimized_video(
                empty_frame_path,
                segment_path,
                anim_start,
                anim_end,
                total_duration,
                extracted_audio_path,
                output_path,
                fps,
                effective_use_alpha,
                effective_chroma_cfg,
            )

            # Log video info
            self._log_video_info(
                output_path,
                total_duration,
                fps,
                int(total_duration * fps),
            )

        finally:
            # Restore original entries
            self._flat_entries = original_entries

    def _create_empty_harmonica_frame(self, fps: int) -> str:
        """Create a video of empty harmonica (no notes).

        Returns:
            Path to the empty frame video file
        """
        import subprocess

        empty_frame_path = self._temp_dir + "empty_harmonica_frame.png"

        # Render one frame with empty harmonica
        self._clear_frame_objects()
        assert self._ax is not None

        # Create figure with just empty harmonica (no notes)
        fig, ax = self._figure_factory.create()
        # Note: just the background, no notes added

        # Save as image
        fig.savefig(empty_frame_path, dpi=100, bbox_inches="tight")
        plt.close(fig)

        # Convert to video using ffmpeg image2pipe
        video_path = self._temp_dir + "empty_harmonica.mp4"

        # Use image2 demuxer with loop filter for duration
        cmd = [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            empty_frame_path,
            "-c:v",
            "libx264",
            "-t",
            "1",  # 1 second duration (will be extended via tpad)
            "-pix_fmt",
            "yuv420p",
            video_path,
        ]

        subprocess.run(cmd, check=True, capture_output=True)
        return video_path

    def _render_segment_video(
        self,
        extracted_audio_path: str,
        output_path: str,
        segment_duration: float,
        fps: int,
        effective_use_alpha: bool,
        effective_chroma_cfg,
    ) -> None:
        """Render only the animated segment video.

        Args:
            extracted_audio_path: Path to audio
            output_path: Output video path
            segment_duration: Duration of segment
            fps: Frames per second
            effective_use_alpha: Whether to use alpha
            effective_chroma_cfg: Chroma config
        """
        # Set background color
        if not effective_use_alpha:
            from harmonica_pipeline.video_creator_config import ChromaKeyConfig

            cfg = effective_chroma_cfg or ChromaKeyConfig()
            try:
                self._figure_factory._config.background_color = cfg.bg_color
            except AttributeError:
                pass

        fig, self._ax = self._figure_factory.create()

        total_frames = int(segment_duration * fps)

        ani = animation.FuncAnimation(
            fig,
            lambda frame: self._timed_update_frame(frame, fps),
            frames=total_frames,
            blit=False,
            interval=1000 / fps,
            cache_frame_data=False,
        )

        ani.save(self._temp_video_path, fps=fps, writer="ffmpeg")

        # Post-process video
        try:
            if effective_use_alpha:
                self._video_processor.process_animation_to_video(
                    self._temp_video_path,
                    extracted_audio_path,
                    output_path,
                    cleanup_temp=True,
                )
            else:
                from harmonica_pipeline.video_creator_config import ChromaKeyConfig

                cfg = effective_chroma_cfg or ChromaKeyConfig()
                self._video_processor.process_animation_to_chromakey_video(
                    self._temp_video_path,
                    extracted_audio_path,
                    output_path,
                    chroma_key_config=cfg,
                    cleanup_temp=True,
                )
        except VideoProcessorError as e:
            print(f"Video processing failed: {e}")
            raise

    def _compose_optimized_video(
        self,
        empty_frame_video: str,
        segment_video: str,
        anim_start: float,
        anim_end: float,
        total_duration: float,
        extracted_audio_path: str,
        output_path: str,
        fps: int,
        effective_use_alpha: bool,
        effective_chroma_cfg,
    ) -> None:
        """Compose three segments into final video using ffmpeg concat.

        Concatenates: [static_start] + [animated] + [static_end]

        Args:
            empty_frame_video: Path to empty harmonica frame video
            segment_video: Path to animated segment video
            anim_start: Start time of animation
            anim_end: End time of animation
            total_duration: Total video duration
            extracted_audio_path: Path to audio file
            output_path: Final output path
            fps: Frames per second
            effective_use_alpha: Whether to use alpha
            effective_chroma_cfg: Chroma config
        """
        import subprocess

        # Calculate segment durations
        static_start_duration = anim_start
        static_end_duration = max(0.0, total_duration - anim_end)

        # Create concat demuxer file
        concat_file = self._temp_dir + "concat_list.txt"
        with open(concat_file, "w") as f:
            # Static start (if any)
            if static_start_duration > 0.01:
                # Extend empty frame to start duration using tpad
                start_video = self._temp_dir + "static_start.mp4"
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    empty_frame_video,
                    "-vf",
                    f"tpad=stop_mode=clone:stop_duration={static_start_duration}",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    start_video,
                ]
                subprocess.run(cmd, check=True, capture_output=True)
                f.write(f"file '{start_video}'\n")

            # Animated segment
            f.write(f"file '{segment_video}'\n")

            # Static end (if any)
            if static_end_duration > 0.01:
                end_video = self._temp_dir + "static_end.mp4"
                cmd = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    empty_frame_video,
                    "-vf",
                    f"tpad=stop_mode=clone:stop_duration={static_end_duration}",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    end_video,
                ]
                subprocess.run(cmd, check=True, capture_output=True)
                f.write(f"file '{end_video}'\n")

        # Use concat demuxer to stitch videos
        concat_output = self._temp_dir + "concat_output.mp4"
        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            concat_file,
            "-c",
            "copy",
            concat_output,
        ]
        subprocess.run(cmd, check=True, capture_output=True)

        # Add audio and final processing
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            concat_output,
            "-i",
            extracted_audio_path,
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-shortest",
            output_path,
        ]
        subprocess.run(cmd, check=True, capture_output=True)

        print(f"✅ Optimized video composed: {output_path}")
