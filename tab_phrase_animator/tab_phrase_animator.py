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

    def create_animations(
        self,
        all_pages: Dict[str, List[List[Optional[List[TabEntry]]]]],
        extracted_audio_path: str,
        output_path_base: str,
        fps: int = 30,
    ) -> None:
        all_entries = [
            entry
            for page in all_pages.values()
            for line in page
            for chord in line
            if chord
            for entry in chord
        ]
        total_duration = max(
            entry.time + (entry.duration or 0.5) for entry in all_entries
        )
        total_frames = int(float(total_duration) * fps)

        fm.fontManager.addfont("ploni-round-bold-aaa.ttf")

        for page_idx, (page_name, page) in enumerate(all_pages.items(), start=1):
            text_lines: List[List[str]] = []
            line_entries: List[List[TabEntry]] = []

            for line in page:
                line_texts = []
                line_tab_entries = []
                for chord in line:
                    if chord:
                        # Format the entire chord visually
                        tabs = [entry.tab for entry in chord]
                        if all(n < 0 for n in tabs):
                            chord_str = "-" + "".join(str(abs(n)) for n in tabs)
                        else:
                            chord_str = "".join(str(abs(n)) for n in tabs)

                        line_texts.append(chord_str)
                        line_tab_entries.append(chord[0])  # one timing anchor per chord

                if line_texts:
                    text_lines.append(line_texts)
                    line_entries.append(line_tab_entries)

            fig, ax = plt.subplots(figsize=(16, 9))
            ax.axis("off")
            fig.patch.set_facecolor("#FF00FF")
            ax.set_facecolor("#FF00FF")

            ani = animation.FuncAnimation(
                fig,
                lambda frame: self._update_text_frame(
                    frame, ax, fps, text_lines, line_entries
                ),
                frames=total_frames,
                interval=1000 / fps,
                blit=False,
            )

            temp_path = os.path.join(TEMP_DIR, f"temp_page_{page_idx}.mp4")
            ani.save(temp_path, fps=fps, writer="ffmpeg")

            transparent_path = os.path.join(
                TEMP_DIR, f"page_{page_idx}_transparent.mov"
            )
            os.system(
                f"ffmpeg -y -i {temp_path} "
                f"-vf colorkey=0xFF00FF:0.3:0.0,format=yuva444p10le "
                f"-c:v prores_ks -profile:v 4 -pix_fmt yuva444p10le {transparent_path}"
            )
            final_output = f"{output_path_base}_page{page_idx}.mov"
            os.system(
                f"ffmpeg -y -i {transparent_path} -i {extracted_audio_path} "
                f"-c:v copy -c:a aac -shortest {final_output}"
            )

            os.remove(temp_path)
            os.remove(transparent_path)

            print(f"✅ Saved page {page_idx} video to {final_output}")

    def _update_text_frame(
        self,
        frame: int,
        ax: Axes,
        fps: int,
        text_lines: List[List[str]],
        line_entries: List[List[TabEntry]],
    ) -> List:
        current_time = frame / fps
        elements = []
        ax.clear()
        ax.axis("off")
        ax.set_facecolor("#FF00FF")

        char_spacing = 0.08
        line_spacing = 0.12
        total_height = (len(text_lines) - 1) * line_spacing
        y_start = 0.5 + total_height / 2

        max_line_len = max((len(line) for line in text_lines), default=0)
        box_width = 0.06 * max_line_len + 0.04
        box_height = 0.12 * len(text_lines) + 0.04
        box_x = 0.5 - box_width / 2
        box_y = 0.5 - box_height / 2

        if text_lines:
            bbox = FancyBboxPatch(
                (box_x, box_y),
                box_width,
                box_height,
                boxstyle="round,pad=0.05,rounding_size=0.2",
                linewidth=0,
                facecolor="#888888",
                edgecolor=None,
                transform=ax.transAxes,
                alpha=0.5,
            )
            ax.add_patch(bbox)
            elements.append(bbox)

        for i, (line_texts, line_tab_entries) in enumerate(
            zip(text_lines, line_entries)
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
