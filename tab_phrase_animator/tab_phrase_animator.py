import os
from typing import List, Optional, Dict

import matplotlib.animation as animation
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.patches import FancyBboxPatch
from matplotlib.text import Text

from image_converter.consts import OUT_COLOR, IN_COLOR
from tab_converter.models import TabEntry
from utils.utils import TEMP_DIR
import matplotlib.font_manager as fm


class TabPhraseAnimator:
    def __init__(self):
        self._ax: Optional[Axes] = None
        self._temp_video_path: str = TEMP_DIR + "temp_phrase.mp4"

    def create_animation(
        self,
        tabs: Dict[str, List[List[Optional[List[TabEntry]]]]],
        audio_path: str,
        output_path: str,
        fps: int = 30,
        font_color: str = "white",
        box_alpha: float = 0.4,
        line_limit: int = 4,
    ) -> None:
        fm.fontManager.addfont("ploni-round-bold-aaa.ttf")
        fig, self._ax = plt.subplots(figsize=(16, 9))
        self._ax.axis("off")

        # Flatten all TabEntry instances and sort
        tab_entries: List[TabEntry] = [
            entry
            for page in tabs.values()
            for line in page
            for chord in line
            if chord
            for entry in chord
        ]
        tab_entries.sort(key=lambda t: t.time)

        # Extract tab text
        tab_text = [self._tab_to_str(t.tab) for t in tab_entries]
        lines = [
            tab_text[i : i + line_limit] for i in range(0, len(tab_text), line_limit)
        ]
        num_lines = len(lines)

        text_objects: List[Text] = []
        bbox: Optional[FancyBboxPatch] = None

        def init():
            nonlocal bbox
            if self._ax is None:
                return

            longest_line_len = max(len(line) for line in lines)
            text_width = 0.06 * longest_line_len
            text_height = 0.12 * num_lines

            x = 0.5 - text_width / 2
            y = 0.5 - text_height / 2

            bbox = FancyBboxPatch(
                (x, y),
                text_width,
                text_height,
                boxstyle="round,pad=0.05",
                linewidth=0,
                facecolor="white",
                edgecolor=None,
                alpha=box_alpha,
                transform=self._ax.transAxes,
            )
            self._ax.add_patch(bbox)

            for i, line in enumerate(lines):
                for j, char in enumerate(line):
                    xpos = x + j * 0.06
                    ypos = y + text_height - (i + 1) * 0.12
                    text = self._ax.text(
                        xpos,
                        ypos,
                        char,
                        transform=self._ax.transAxes,
                        ha="center",
                        va="center",
                        fontsize=32,
                        fontname="Ploni Round AAA",
                        color=font_color,
                        weight="bold",
                    )
                    text_objects.append(text)

        def update(frame: int):
            current_time = frame / fps
            for obj in text_objects:
                obj.set_color(font_color)

            for tab_entry, text_obj in zip(tab_entries, text_objects):
                if (
                    tab_entry.time
                    <= current_time
                    <= tab_entry.time + (tab_entry.duration or 0.5)
                ):
                    if tab_entry.tab > 0:
                        text_obj.set_color(OUT_COLOR)
                    else:
                        text_obj.set_color(IN_COLOR)

            return text_objects

        total_duration = max(tab.time + (tab.duration or 0.5) for tab in tab_entries)
        total_frames = int(total_duration * fps)

        ani = animation.FuncAnimation(
            fig,
            update,
            init_func=init,
            frames=total_frames,
            interval=1000 / fps,
            blit=False,
        )

        ani.save(self._temp_video_path, fps=fps, writer="ffmpeg")
        print(f"🎥 Intermediate video saved to {self._temp_video_path}")

        transparent_path = TEMP_DIR + "temp_phrase_transparent.mov"
        os.system(
            f"ffmpeg -y -i {self._temp_video_path} "
            f"-vf colorkey=0xFFFFFF:0.3:0.0,format=yuva444p10le "
            f"-c:v prores_ks -profile:v 4 -pix_fmt yuva444p10le "
            f"{transparent_path}"
        )
        print(f"🕓 Background removed, transparent video saved to {transparent_path}")

        os.system(
            f"ffmpeg -y -i {transparent_path} -i {audio_path} "
            f"-c:v copy -c:a aac {output_path}"
        )
        print(f"✅ Final video with transparency + audio saved to {output_path}")

        os.remove(self._temp_video_path)
        os.remove(transparent_path)

    @staticmethod
    def _tab_to_str(tab: int) -> str:
        return f"{'-' if tab < 0 else ''}{abs(tab)}"
