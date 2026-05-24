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

        self._flat_entries = adjust_consecutive_identical_notes(self._flat_entries)
        self._audio_duration = audio_duration

        total_duration = self._get_total_duration()

        # Handle time_range rendering (for segmented animation)
        if time_range is not None:
            start_time, end_time = time_range
            frames: int | range = range(int(start_time * fps), int(end_time * fps))
            duration_for_output = end_time - start_time
        else:
            frames = self._get_total_frames(fps, total_duration)
            duration_for_output = total_duration

        total_frames = len(frames) if isinstance(frames, range) else frames

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
            frames=frames,
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
            self._log_video_info(output_path, duration_for_output, fps, total_frames)

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

    def _detect_segments(
        self, entries: List[TabEntry], duration: float, merge_threshold: float = 0.05
    ) -> List[tuple[float, float, bool]]:
        """
        Detect static (no notes) and animated (notes playing) segments.

        Analyzes timeline to find contiguous periods where no notes are active.
        Adjacent segments of same type are merged if gap < merge_threshold.

        Args:
            entries: List of TabEntry objects (already flat and adjusted)
            duration: Total video duration in seconds
            merge_threshold: Merge segments if gap between them is < this (seconds)

        Returns:
            List of (start_time, end_time, is_static) tuples, sorted by time.
            Example: [(0.0, 2.5, True), (2.5, 5.0, False), (5.0, 7.0, True)]
        """
        if not entries:
            # No entries = entire video is static
            return [(0.0, duration, True)]

        # Find all time boundaries (note starts and ends)
        boundaries_set: set[float] = {0.0, duration}
        for entry in entries:
            boundaries_set.add(entry.time)
            boundaries_set.add(entry.time + entry.duration)

        # Sort boundaries
        boundaries = sorted(boundaries_set)

        # Determine if each interval is static or animated
        segments = []
        for i in range(len(boundaries) - 1):
            start_t = boundaries[i]
            end_t = boundaries[i + 1]
            mid_t = (start_t + end_t) / 2

            # Check if any note is active at midpoint
            is_active = any(
                entry.time <= mid_t <= entry.time + entry.duration for entry in entries
            )
            segments.append((start_t, end_t, not is_active))

        # Merge adjacent segments of same type if gap is small
        merged: list[tuple[float, float, bool]] = []
        for start, end, is_static in segments:
            if merged and merged[-1][2] == is_static:
                # Same type as previous; check if we should merge
                prev_start, prev_end, prev_static = merged[-1]
                if start - prev_end < merge_threshold:
                    # Merge by extending previous segment
                    merged[-1] = (prev_start, end, is_static)
                else:
                    merged.append((start, end, is_static))
            else:
                merged.append((start, end, is_static))

        return merged

    def animate_with_segmentation(
        self,
        all_pages: Dict[str, List[List[Optional[List[TabEntry]]]]],
        extracted_audio_path: str,
        output_path: str,
        fps: int = 15,
        audio_duration: Optional[float] = None,
        use_alpha: Optional[bool] = None,
        chroma_key_config=None,
    ) -> None:
        """
        Generate animation using segment-based compositing for speed optimization.

        Detects static vs animated segments, renders only what's needed, then
        concatenates the results. Expected 2-3x speedup for videos with rests.

        Args:
            all_pages: Page structure
            extracted_audio_path: Audio file path
            output_path: Output video path
            fps: Frames per second
            audio_duration: Total duration
            use_alpha: Use ProRes alpha mode
            chroma_key_config: Chroma key configuration
        """
        import os

        self._flat_entries = [
            entry
            for page in all_pages.values()
            for line in page
            for chord in line
            if chord
            for entry in chord
        ]
        self._flat_entries = adjust_consecutive_identical_notes(self._flat_entries)
        self._audio_duration = audio_duration
        total_duration = self._get_total_duration()

        # Detect segments
        segments = self._detect_segments(self._flat_entries, total_duration)

        # Check if segmentation is worth it (>50% static)
        static_duration = sum(
            end - start for start, end, is_static in segments if is_static
        )
        if static_duration / total_duration < 0.5:
            # Not worth segmenting, use standard rendering
            self.create_animation(
                all_pages,
                extracted_audio_path,
                output_path,
                fps=fps,
                audio_duration=audio_duration,
                use_alpha=use_alpha,
                chroma_key_config=chroma_key_config,
            )
            return

        # Create segment output directory
        seg_dir = os.path.join(self._temp_dir, "segments")
        os.makedirs(seg_dir, exist_ok=True)

        segment_videos = []
        segment_durations = []

        try:
            for i, (start_time, end_time, is_static) in enumerate(segments):
                duration = end_time - start_time

                if is_static:
                    # Extract single frame for static segment
                    frame_path = self._extract_static_frame(
                        all_pages, start_time, fps, seg_dir, i
                    )
                    segment_videos.append(frame_path)
                else:
                    # Render animated segment
                    seg_video = os.path.join(seg_dir, f"seg_{i}.mov")
                    self.create_animation(
                        all_pages,
                        extracted_audio_path,
                        seg_video,
                        fps=fps,
                        audio_duration=duration,
                        use_alpha=use_alpha,
                        chroma_key_config=chroma_key_config,
                        time_range=(start_time, end_time),
                    )
                    segment_videos.append(seg_video)

                segment_durations.append(duration)

            # Concatenate all segments
            self._video_processor.concatenate_segments(
                segment_videos,
                output_path,
                fps=fps,
                segment_durations=segment_durations,
            )

            print(f"✅ Segmented animation saved to {output_path}")
            print(
                f"   Rendered {len(segments)} segments ({sum(1 for _, _, s in segments if s)} static)"
            )

        finally:
            # Cleanup segment directory
            import shutil

            try:
                shutil.rmtree(seg_dir)
            except Exception:
                pass

    def _extract_static_frame(
        self,
        all_pages: Dict[str, List[List[Optional[List[TabEntry]]]]],
        time: float,
        fps: int,
        output_dir: str,
        frame_idx: int,
    ) -> str:
        """
        Extract a single frame from a static segment as a representative image.

        Renders one frame at the given time and saves it as PNG for later reuse.

        Args:
            all_pages: Page structure (used by create_animation)
            time: Time to extract frame from (seconds)
            fps: Frames per second
            output_dir: Directory to save PNG frame
            frame_idx: Index for naming (e.g., frame_0.png)

        Returns:
            Path to extracted PNG frame file
        """
        import os

        # Create a tiny time range to render just one frame
        time_range = (time, time + (1 / fps) * 1.5)  # 1.5 frames to ensure coverage

        # Render the frame (saves to temp video path)
        temp_frame_video = os.path.join(output_dir, f"_temp_frame_{frame_idx}.mp4")
        original_temp = self._temp_video_path
        self._temp_video_path = temp_frame_video

        try:
            # Create dummy audio path (won't be used since we're just extracting video)
            dummy_audio = os.path.join(output_dir, "_dummy.wav")
            if not os.path.exists(dummy_audio):
                # Create a minimal silence WAV (just for video rendering)
                import wave

                with wave.open(dummy_audio, "wb") as wav_file:
                    wav_file.setnchannels(1)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(44100)
                    wav_file.writeframes(b"\x00\x00" * 44100)  # 1 second of silence

            self.create_animation(
                all_pages,
                dummy_audio,
                temp_frame_video,
                fps=fps,
                audio_duration=1.0,
                time_range=time_range,
            )

            # Extract first frame from the rendered video using ffmpeg
            frame_png = os.path.join(output_dir, f"frame_{frame_idx}.png")
            import subprocess

            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                temp_frame_video,
                "-vframes",
                "1",
                "-f",
                "image2",
                frame_png,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise ValueError(f"Failed to extract frame: {result.stderr}")

            return frame_png

        finally:
            self._temp_video_path = original_temp
            # Cleanup temp files
            for f in [temp_frame_video, dummy_audio]:
                if os.path.exists(f):
                    try:
                        os.remove(f)
                    except Exception:
                        pass

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
