"""
TabPhraseAnimator - Creates animated text-based harmonica tab phrase videos.

Handles page-based tab animation with proper timing, visual formatting,
and video processing with transparency support.
"""

import os
import subprocess
from dataclasses import dataclass
from typing import List, Optional, Dict

import matplotlib.animation as animation
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.patches import FancyBboxPatch

from image_converter.consts import IN_COLOR, OUT_COLOR, BEND_COLOR
from image_converter.figure_factory import FigureFactory
from image_converter.harmonica_layout import HarmonicaLayout
from tab_converter.models import TabEntry
from utils.utils import TEMP_DIR


@dataclass
class AnimationConfig:
    """Configuration for tab phrase animation."""

    fps: int = 30
    figure_size: tuple[float, float] = (16, 9)
    background_color: str = "#FF00FF"  # Magenta for chroma key
    font_family: str = "Ploni Round AAA"
    font_file: str = "ploni-round-bold-aaa.ttf"
    font_size: int = 32
    char_spacing: float = 0.08
    line_spacing: float = 0.12
    box_padding: float = 0.05
    box_rounding: float = 0.2
    box_color: str = "#888888"
    box_alpha: float = 0.5
    time_buffer: float = 0.5  # Buffer time before/after notes
    cleanup_temp_files: bool = True


@dataclass
class PageStatistics:
    """Statistics for a single animated page."""

    page_name: str
    total_entries: int
    start_time: float
    end_time: float
    duration: float
    total_frames: int
    lines_count: int
    chords_count: int
    output_file: str


class TabPhraseAnimatorError(Exception):
    """Custom exception for tab phrase animation errors."""

    pass


class TabPhraseAnimator:
    """
    Creates animated text-based harmonica tab phrase videos.

    Generates page-by-page animations with proper timing synchronization,
    visual highlighting, and transparent video output for compositing.
    """

    def __init__(
        self,
        harmonica_layout: HarmonicaLayout,
        figure_factory: FigureFactory,
        config: Optional[AnimationConfig] = None,
    ):
        """
        Initialize tab phrase animator.

        Args:
            harmonica_layout: Harmonica layout for positioning (not used in text mode)
            figure_factory: Figure factory for creating plots (not used in text mode)
            config: Optional animation configuration
        """
        self._harmonica_layout = harmonica_layout
        self._figure_factory = figure_factory
        self._config = config or AnimationConfig()
        self._page_statistics: List[PageStatistics] = []

        # Load custom font
        self._load_font()

    def create_animations(
        self,
        all_pages: Dict[str, List[List[Optional[List[TabEntry]]]]],
        extracted_audio_path: str,
        output_path_base: str,
        fps: Optional[int] = None,
    ) -> List[PageStatistics]:
        """
        Create animated tab phrase videos for all pages.

        Args:
            all_pages: Dictionary mapping page names to tab content
            extracted_audio_path: Path to the source audio file
            output_path_base: Base path for output files (without extension)
            fps: Optional FPS override (uses config default if None)

        Returns:
            List of PageStatistics for each created page

        Raises:
            TabPhraseAnimatorError: If animation creation fails
        """
        if not all_pages:
            raise TabPhraseAnimatorError("No pages provided for animation")

        if not os.path.exists(extracted_audio_path):
            raise TabPhraseAnimatorError(
                f"Audio file not found: {extracted_audio_path}"
            )

        actual_fps = fps or self._config.fps
        self._page_statistics.clear()

        print(f"🎬 Creating tab phrase animations for {len(all_pages)} pages")
        print(f"🎵 Audio source: {extracted_audio_path}")
        print(f"📹 Output base: {output_path_base}")

        for page_idx, (page_name, page) in enumerate(all_pages.items(), start=1):
            try:
                stats = self._create_single_page_animation(
                    page_idx,
                    page_name,
                    page,
                    extracted_audio_path,
                    output_path_base,
                    actual_fps,
                )
                self._page_statistics.append(stats)
                print(f"✅ Page {page_idx}/{len(all_pages)}: {stats.output_file}")

            except Exception as e:
                error_msg = (
                    f"Failed to create animation for page {page_idx} ({page_name}): {e}"
                )
                print(f"❌ {error_msg}")
                if not isinstance(e, TabPhraseAnimatorError):
                    raise TabPhraseAnimatorError(error_msg) from e
                raise

        print(f"🎉 Successfully created {len(self._page_statistics)} page animations")
        return self._page_statistics.copy()

    def get_statistics(self) -> List[PageStatistics]:
        """
        Get animation statistics for all created pages.

        Returns:
            List of PageStatistics for each animated page
        """
        return self._page_statistics.copy()

    def get_animation_info(self) -> dict:
        """
        Get comprehensive animation information.

        Returns:
            Dict with animation properties and statistics
        """
        if not self._page_statistics:
            return {
                "total_pages": 0,
                "total_duration": 0,
                "config": self._config.__dict__,
            }

        total_duration = sum(stat.duration for stat in self._page_statistics)
        total_frames = sum(stat.total_frames for stat in self._page_statistics)
        total_entries = sum(stat.total_entries for stat in self._page_statistics)

        return {
            "total_pages": len(self._page_statistics),
            "total_duration": total_duration,
            "total_frames": total_frames,
            "total_entries": total_entries,
            "average_page_duration": total_duration / len(self._page_statistics),
            "pages": [
                {
                    "name": stat.page_name,
                    "duration": stat.duration,
                    "entries": stat.total_entries,
                    "lines": stat.lines_count,
                    "chords": stat.chords_count,
                    "output": stat.output_file,
                }
                for stat in self._page_statistics
            ],
            "config": self._config.__dict__,
        }

    def _load_font(self) -> None:
        """
        Load the custom font for tab rendering.

        Raises:
            TabPhraseAnimatorError: If font loading fails
        """
        try:
            if os.path.exists(self._config.font_file):
                fm.fontManager.addfont(self._config.font_file)
                print(f"📝 Loaded font: {self._config.font_file}")
            else:
                print(
                    f"⚠️  Font file not found: {self._config.font_file}, using system default"
                )
        except Exception as e:
            print(f"⚠️  Warning: Could not load font {self._config.font_file}: {e}")

    def _create_single_page_animation(
        self,
        page_idx: int,
        page_name: str,
        page: List[List[Optional[List[TabEntry]]]],
        extracted_audio_path: str,
        output_path_base: str,
        fps: int,
    ) -> PageStatistics:
        """
        Create animation for a single page.

        Args:
            page_idx: Page index (1-based)
            page_name: Name of the page
            page: Page content with tab entries
            extracted_audio_path: Path to source audio
            output_path_base: Base output path
            fps: Frames per second

        Returns:
            PageStatistics for the created animation

        Raises:
            TabPhraseAnimatorError: If page animation creation fails
        """
        # Extract and validate entries
        all_entries = [
            entry for line in page for chord in line if chord for entry in chord
        ]

        if not all_entries:
            raise TabPhraseAnimatorError(f"Page {page_name} has no valid entries")

        # Calculate timing
        raw_start = min(entry.time for entry in all_entries)
        raw_end = max(entry.time + (entry.duration or 0.5) for entry in all_entries)
        start_time = max(0.0, raw_start - self._config.time_buffer)
        end_time = raw_end + self._config.time_buffer
        duration = end_time - start_time
        total_frames = int(duration * fps)

        # Prepare text data
        text_lines, line_entries = self._prepare_text_data(page)

        if not text_lines:
            raise TabPhraseAnimatorError(
                f"No valid text lines found for page {page_name}"
            )

        # Create animation
        fig, ax = plt.subplots(figsize=self._config.figure_size)
        ax.axis("off")
        fig.patch.set_facecolor(self._config.background_color)
        ax.set_facecolor(self._config.background_color)

        ani = animation.FuncAnimation(
            fig,
            lambda frame: self._update_text_frame(
                frame, ax, fps, text_lines, line_entries, start_time
            ),
            frames=total_frames,
            interval=1000 / fps,
            blit=False,
        )

        # Save and process video
        final_output = self._process_animation_video(
            ani,
            page_idx,
            fps,
            start_time,
            end_time,
            extracted_audio_path,
            output_path_base,
        )

        # Create and return statistics
        return PageStatistics(
            page_name=page_name,
            total_entries=len(all_entries),
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            total_frames=total_frames,
            lines_count=len(text_lines),
            chords_count=sum(len(line) for line in text_lines),
            output_file=final_output,
        )

    def _prepare_text_data(
        self, page: List[List[Optional[List[TabEntry]]]]
    ) -> tuple[List[List[str]], List[List[TabEntry]]]:
        """
        Prepare text data for animation rendering.

        Args:
            page: Page content with tab entries

        Returns:
            Tuple of (text_lines, line_entries) for rendering
        """
        text_lines: List[List[str]] = []
        line_entries: List[List[TabEntry]] = []

        for line in page:
            line_texts = []
            line_tab_entries = []

            for chord in line:
                if chord:
                    # Format chord visually
                    tabs = [entry.tab for entry in chord]
                    if all(n < 0 for n in tabs):
                        chord_str = "-" + "".join(str(abs(n)) for n in tabs)
                    else:
                        chord_str = "".join(str(abs(n)) for n in tabs)

                    # Add bend notation if the first note (anchor) is bent
                    if chord[0].is_bend:
                        chord_str += "'"

                    line_texts.append(chord_str)
                    line_tab_entries.append(chord[0])  # Anchor on first note

            if line_texts:
                text_lines.append(line_texts)
                line_entries.append(line_tab_entries)

        return text_lines, line_entries

    def _process_animation_video(
        self,
        ani: animation.FuncAnimation,
        page_idx: int,
        fps: int,
        start_time: float,
        end_time: float,
        extracted_audio_path: str,
        output_path_base: str,
    ) -> str:
        """
        Process and save the animation video with transparency and audio.

        Args:
            ani: Matplotlib animation object
            page_idx: Page index for file naming
            fps: Frames per second
            start_time: Start time for audio extraction
            end_time: End time for audio extraction
            extracted_audio_path: Source audio file
            output_path_base: Base output path

        Returns:
            Path to the final output file

        Raises:
            TabPhraseAnimatorError: If video processing fails
        """
        temp_files = []
        try:
            # Save raw animation
            temp_path = os.path.join(TEMP_DIR, f"temp_page_{page_idx}.mp4")
            temp_files.append(temp_path)
            ani.save(temp_path, fps=fps, writer="ffmpeg")

            # Create transparent video
            transparent_path = os.path.join(
                TEMP_DIR, f"page_{page_idx}_transparent.mov"
            )
            temp_files.append(transparent_path)
            self._create_transparent_video(temp_path, transparent_path)

            # Extract audio slice
            audio_trimmed = os.path.join(TEMP_DIR, f"audio_page_{page_idx}.m4a")
            temp_files.append(audio_trimmed)
            self._extract_audio_slice(
                extracted_audio_path, audio_trimmed, start_time, end_time
            )

            # Combine video and audio
            final_output = f"{output_path_base}_page{page_idx}.mov"
            self._combine_video_audio(transparent_path, audio_trimmed, final_output)

            return final_output

        except Exception as e:
            raise TabPhraseAnimatorError(
                f"Video processing failed for page {page_idx}: {e}"
            )
        finally:
            # Cleanup temporary files
            if self._config.cleanup_temp_files:
                for temp_file in temp_files:
                    try:
                        if os.path.exists(temp_file):
                            os.remove(temp_file)
                    except OSError:
                        pass  # Ignore cleanup errors

    def _create_transparent_video(self, input_path: str, output_path: str) -> None:
        """
        Create transparent video using FFmpeg colorkey filter.

        Args:
            input_path: Input video file
            output_path: Output transparent video file

        Raises:
            TabPhraseAnimatorError: If FFmpeg processing fails
        """
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            input_path,
            "-vf",
            "colorkey=0xFF00FF:0.3:0.0,format=yuva444p10le",
            "-c:v",
            "prores_ks",
            "-profile:v",
            "4",
            "-pix_fmt",
            "yuva444p10le",
            output_path,
        ]

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            raise TabPhraseAnimatorError(f"Transparency processing failed: {e.stderr}")

    def _extract_audio_slice(
        self, input_audio: str, output_audio: str, start_time: float, end_time: float
    ) -> None:
        """
        Extract audio slice for the current page timing.

        Args:
            input_audio: Source audio file
            output_audio: Output audio file
            start_time: Start time in seconds
            end_time: End time in seconds

        Raises:
            TabPhraseAnimatorError: If audio extraction fails
        """
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            input_audio,
            "-ss",
            f"{start_time:.3f}",
            "-to",
            f"{end_time:.3f}",
            "-c:a",
            "aac",
            output_audio,
        ]

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            raise TabPhraseAnimatorError(f"Audio extraction failed: {e.stderr}")

    def _combine_video_audio(
        self, video_path: str, audio_path: str, output_path: str
    ) -> None:
        """
        Combine transparent video with audio.

        Args:
            video_path: Input video file
            audio_path: Input audio file
            output_path: Final output file

        Raises:
            TabPhraseAnimatorError: If video/audio combination fails
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
            "-shortest",
            output_path,
        ]

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            raise TabPhraseAnimatorError(f"Video/audio combination failed: {e.stderr}")

    def _update_text_frame(
        self,
        frame: int,
        ax: Axes,
        fps: int,
        text_lines: List[List[str]],
        line_entries: List[List[TabEntry]],
        offset: float,
    ) -> List:
        """
        Update a single animation frame with highlighted text.

        Args:
            frame: Current frame number
            ax: Matplotlib axes
            fps: Frames per second
            text_lines: Text content to render
            line_entries: Corresponding tab entries for timing
            offset: Time offset for the animation

        Returns:
            List of matplotlib elements for the frame
        """
        current_time = offset + (frame / fps)
        elements = []
        ax.clear()
        ax.axis("off")
        ax.set_facecolor(self._config.background_color)

        # Calculate layout
        total_height = (len(text_lines) - 1) * self._config.line_spacing
        y_start = 0.5 + total_height / 2

        # Create background box
        if text_lines:
            bbox = self._create_background_box(text_lines, ax)
            elements.append(bbox)

        # Render text with highlighting
        for i, (line_texts, line_tab_entries) in enumerate(
            zip(text_lines, line_entries)
        ):
            ypos = y_start - i * self._config.line_spacing
            line_len = len(line_texts)

            for j, (char, entry) in enumerate(zip(line_texts, line_tab_entries)):
                xpos = 0.5 + (j - (line_len - 1) / 2) * self._config.char_spacing

                # Determine color based on timing, bend status, and tab direction
                color = "white"
                if entry.time <= current_time <= entry.time + (entry.duration or 0.5):
                    if entry.is_bend:
                        color = BEND_COLOR  # Orange for bent notes
                    else:
                        color = OUT_COLOR if entry.tab > 0 else IN_COLOR

                txt = ax.text(
                    xpos,
                    ypos,
                    char,
                    transform=ax.transAxes,
                    ha="center",
                    va="center",
                    fontsize=self._config.font_size,
                    fontname=self._config.font_family,
                    color=color,
                    weight="bold",
                )
                elements.append(txt)

        return elements

    def _create_background_box(
        self, text_lines: List[List[str]], ax: Axes
    ) -> FancyBboxPatch:
        """
        Create background box for text rendering.

        Args:
            text_lines: Text content for sizing
            ax: Matplotlib axes

        Returns:
            FancyBboxPatch for the background
        """
        max_line_len = max((len(line) for line in text_lines), default=0)
        box_width = 0.06 * max_line_len + 0.04
        box_height = 0.12 * len(text_lines) + 0.04
        box_x = 0.5 - box_width / 2
        box_y = 0.5 - box_height / 2

        return FancyBboxPatch(
            (box_x, box_y),
            box_width,
            box_height,
            boxstyle=f"round,pad={self._config.box_padding},rounding_size={self._config.box_rounding}",
            linewidth=0,
            facecolor=self._config.box_color,
            edgecolor=None,
            transform=ax.transAxes,
            alpha=self._config.box_alpha,
        )
