import os
from typing import List, Optional, Dict

import matplotlib.animation as animation
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.patches import FancyBboxPatch

from image_converter.consts import IN_COLOR, OUT_COLOR
from image_converter.figure_factory import FigureFactory
from image_converter.harmonica_layout import HarmonicaLayout
from tab_converter.models import TabEntry
from utils.utils import TEMP_DIR


class TabPhraseAnimator:
    def __init__(
        self, harmonica_layout: HarmonicaLayout, figure_factory: FigureFactory
    ):
        self._harmonica_layout = harmonica_layout
        self._figure_factory = figure_factory
        self._flat_entries: List[TabEntry] = []
        self._text_lines: List[List[str]] = []
        self._line_entries: List[List[TabEntry]] = []

    def create_animations(
        self,
        all_pages: Dict[str, List[List[Optional[List[TabEntry]]]]],
        extracted_audio_path: str,
        output_path_text: str,
        fps: int = 30,
    ) -> None:
        # Build text lines
        self._text_lines = []
        self._line_entries = []
        for page in all_pages.values():
            for line in page:
                line_texts = []
                line_tab_entries = []
                for chord in line:
                    if chord:
                        for entry in chord:
                            line_texts.append(self._tab_to_str(entry.tab))
                            line_tab_entries.append(entry)
                if line_texts:
                    self._text_lines.append(line_texts)
                    self._line_entries.append(line_tab_entries)

        total_duration = max(
            e.time + (e.duration or 0.5) for line in self._line_entries for e in line
        )
        total_frames = int(float(total_duration) * fps)

        # === Figure ===
        fig, ax = plt.subplots(figsize=(16, 9))
        fm.fontManager.addfont("ploni-round-bold-aaa.ttf")
        ax.axis("off")

        ani = animation.FuncAnimation(
            fig,
            lambda frame: self._update_text_frame(frame, ax, fps),
            frames=total_frames,
            interval=1000 / fps,
            blit=False,
        )
        text_temp_path = TEMP_DIR + "temp_text.mp4"
        ani.save(text_temp_path, fps=fps, writer="ffmpeg")

        transparent_path = TEMP_DIR + "text_transparent.mov"
        os.system(
            f"ffmpeg -y -i {text_temp_path} "
            f"-vf colorkey=0x000000:0.3:0.0,format=yuva444p10le "
            f"-c:v prores_ks -profile:v 4 -pix_fmt yuva444p10le {transparent_path}"
        )
        os.system(
            f"ffmpeg -y -i {transparent_path} -i {extracted_audio_path} "
            f"-c:v copy -c:a aac -shortest {output_path_text}"
        )

        os.remove(text_temp_path)
        os.remove(transparent_path)

    def _update_text_frame(self, frame: int, ax: Axes, fps: int) -> List:
        current_time = frame / fps
        elements = []
        ax.clear()
        ax.axis("off")

        # Layout settings
        char_spacing = 0.08
        line_spacing = 0.12
        total_height = (len(self._text_lines) - 1) * line_spacing
        y_start = 0.5 + total_height / 2

        # Compute bounding box dimensions
        max_line_len = max((len(line) for line in self._text_lines), default=0)
        box_width = 0.06 * max_line_len + 0.04
        box_height = 0.12 * len(self._text_lines) + 0.04
        box_x = 0.5 - box_width / 2
        box_y = 0.5 - box_height / 2

        # Draw rounded box first
        bbox = FancyBboxPatch(
            (box_x, box_y),
            box_width,
            box_height,
            boxstyle="round,pad=0.05, rounding_size=0.2",
            linewidth=0,
            facecolor="#888888",
            edgecolor=None,
            transform=ax.transAxes,
            alpha=0.5,
        )
        ax.add_patch(bbox)
        elements.append(bbox)

        # Then add the text lines
        for i, (line_texts, line_tab_entries) in enumerate(
            zip(self._text_lines, self._line_entries)
        ):
            ypos = y_start - i * line_spacing
            line_len = len(line_texts)
            for j, (char, entry) in enumerate(zip(line_texts, line_tab_entries)):
                xpos = 0.5 + (j - (line_len - 1) / 2) * char_spacing
                color = "white"
                if entry.time <= current_time <= entry.time + (entry.duration or 0.5):
                    color = OUT_COLOR if entry.tab > 0 else IN_COLOR
                txt = ax.text(
                    xpos,
                    ypos,
                    char,
                    transform=ax.transAxes,
                    ha="center",
                    va="center",
                    fontsize=32,
                    fontname="Ploni Round AAA",
                    color=color,
                    weight="bold",
                )
                elements.append(txt)
        return elements

    @staticmethod
    def _tab_to_str(tab: int) -> str:
        return f"{'-' if tab < 0 else ''}{abs(tab)}"
