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


def adjust_consecutive_identical_notes(
    flat_entries: List[TabEntry], gap: float = 0.05
) -> List[TabEntry]:
    """Force visual gap between consecutive identical notes for clarity."""
    for i in range(len(flat_entries) - 1):
        current = flat_entries[i]
        next_entry = flat_entries[i + 1]

        if current.tab == next_entry.tab:
            # ALWAYS create gap for consecutive identical notes (not just overlaps)
            current.duration = max(0, next_entry.time - current.time - gap)
    return flat_entries


class Animator:
    def __init__(
        self, harmonica_layout: HarmonicaLayout, figure_factory: FigureFactory
    ):
        self._frame_timings: List[float] = []
        self._harmonica_layout = harmonica_layout
        self._figure_factory = figure_factory
        self._text_objects: List[Text] = []
        self._arrows: List[Text] = []
        self._temp_video_path: str = TEMP_DIR + "temp_video.mp4"
        self._ax: Optional[Axes] = None
        self._squares: List[Rectangle] = []
        self._flat_entries: List[TabEntry] = []
        self._audio_duration: Optional[float] = None
        self._video_processor = VideoProcessor(TEMP_DIR)

    def create_animation(
        self,
        all_pages: Dict[str, List[List[Optional[List[TabEntry]]]]],
        extracted_audio_path: str,
        output_path: str,
        fps: int = 15,
        audio_duration: Optional[float] = None,
    ) -> None:
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
        total_frames = self._get_total_frames(fps, total_duration)

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
        print(f"🎥 Intermediate video saved to {self._temp_video_path}")

        if self._frame_timings:
            avg_frame_time = sum(self._frame_timings) / len(self._frame_timings)
            print(
                f"⏱ Average frame update time: {avg_frame_time:.4f}s over {len(self._frame_timings)} samples"
            )

        # Use VideoProcessor for post-processing
        try:
            self._video_processor.process_animation_to_video(
                self._temp_video_path,
                extracted_audio_path,
                output_path,
                cleanup_temp=True,
            )

            # Log video information
            self._log_video_info(output_path, total_duration, fps, total_frames)

        except VideoProcessorError as e:
            print(f"❌ Video processing failed: {e}")
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
