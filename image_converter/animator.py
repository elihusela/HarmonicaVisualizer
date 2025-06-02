import os
from typing import List, Optional

import matplotlib.animation as animation
from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from matplotlib.text import Text
from matplotlib.patches import Rectangle

from image_converter.consts import IN_COLOR, OUT_COLOR
from image_converter.figure_factory import FigureFactory
from image_converter.harmonica_layout import HarmonicaLayout
from tab_converter.models import Tabs, TabEntry
from utils.utils import TEMP_DIR


class Animator:
    def __init__(
        self, harmonica_layoout: HarmonicaLayout, figure_factory: FigureFactory
    ):
        self._harmonica_layout = harmonica_layoout
        self._figure_factory = figure_factory
        self._text_objects: List[Text] = []
        self._arrows: List[Text] = []
        self._temp_video_path: str = TEMP_DIR + "temp_video.mp4"
        self._ax: Optional[Axes] = None
        self._squares: List[Rectangle] = []

    def create_animation(
        self,
        tabs: Tabs,
        extracted_audio_path: str,
        output_path: str,
        fps: int = 30,
    ) -> None:
        total_duration = self._get_total_duration(tabs)
        total_frames = self._get_total_frames(fps, total_duration)

        fig, self._ax = self._figure_factory.create()

        ani = animation.FuncAnimation(
            fig,
            lambda frame: self._update_frame(frame, tabs, fps),
            frames=total_frames,
            blit=False,
            interval=1000 / fps,
        )

        ani.save(self._temp_video_path, fps=fps, writer="ffmpeg")
        print(f"🎥 Intermediate video saved to {self._temp_video_path}")

        transparent_video_path = TEMP_DIR + "temp_transparent.mov"
        os.system(
            f"ffmpeg -y -i {self._temp_video_path} "
            f"-vf colorkey=0xFF00FF:0.3:0.0,format=yuva444p10le "
            f"-c:v prores_ks -profile:v 4 -pix_fmt yuva444p10le "
            f"{transparent_video_path}"
        )
        print(
            f"🟣 Background removed, transparent video saved to {transparent_video_path}"
        )

        os.system(
            f"ffmpeg -y -i {transparent_video_path} -i {extracted_audio_path} "
            f"-c:v copy -c:a aac -shortest {output_path}"
        )
        print(f"✅ Final video with transparency + audio saved to {output_path}")

        os.remove(self._temp_video_path)
        os.remove(transparent_video_path)

    def _update_frame(self, frame: int, tabs: Tabs, fps: int) -> List:
        current_time = frame / fps

        for obj in self._text_objects + self._arrows:
            obj.remove()
        self._text_objects.clear()
        self._arrows.clear()

        assert self._ax is not None

        for tab_entry in tabs.tabs:
            start = tab_entry.time
            end = start + tab_entry.duration
            if start <= current_time <= end:
                hole = abs(tab_entry.tab)
                center_x, center_y = self._harmonica_layout.get_position(hole)
                rect_x, rect_y, rect_width, rect_height = (
                    self._harmonica_layout.get_rectangle(hole)
                )
                direction = self._calc_direction(tab_entry)
                color = self._get_color(tab_entry)

                # Draw the colored rectangle
                rect = self._ax.add_patch(
                    plt.Rectangle(
                        (rect_x, rect_y),
                        rect_width,
                        rect_height,
                        linewidth=0,
                        edgecolor=None,
                        facecolor=color,
                        alpha=0.85,
                    )
                )

                txt = self._ax.text(
                    center_x,
                    center_y - 10,
                    f"{hole}",
                    color="black",
                    fontsize=18,
                    ha="center",
                    va="center",
                    weight="bold",
                )
                arr = self._ax.text(
                    center_x,
                    center_y + 15,
                    direction,
                    color="black",
                    fontsize=20,
                    ha="center",
                    va="center",
                )

                self._text_objects.append(txt)
                self._arrows.append(arr)
                self._text_objects.append(rect)  # include rectangle in the cleanup

        return self._text_objects + self._arrows

    @staticmethod
    def _get_color(tab_entry: TabEntry) -> str:
        return OUT_COLOR if tab_entry.tab > 0 else IN_COLOR

    @staticmethod
    def _calc_direction(tab_entry: TabEntry) -> str:
        return "↓" if tab_entry.tab > 0 else "↑"

    @staticmethod
    def _get_total_duration(tabs: Tabs) -> float:
        return max(tab.time + (tab.duration or 0.5) for tab in tabs.tabs)

    @staticmethod
    def _get_total_frames(fps: int, total_duration: float) -> int:
        return int(total_duration * fps)
