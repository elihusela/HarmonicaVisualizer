import os
import time
from typing import List, Optional, Dict

import matplotlib.animation as animation
from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from matplotlib.patches import Rectangle
from matplotlib.text import Text

from image_converter.consts import IN_COLOR, OUT_COLOR
from image_converter.figure_factory import FigureFactory
from image_converter.harmonica_layout import HarmonicaLayout
from tab_converter.models import TabEntry
from utils.utils import TEMP_DIR


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

    def create_animation(
        self,
        all_pages: Dict[str, List[List[Optional[List[TabEntry]]]]],
        extracted_audio_path: str,
        output_path: str,
        fps: int = 15,
    ) -> None:
        self._flat_entries = [
            entry
            for page in all_pages.values()
            for line in page
            for chord in line
            if chord
            for entry in chord
        ]

        total_duration = self._get_total_duration()
        total_frames = self._get_total_frames(fps, total_duration)

        fig, self._ax = self._figure_factory.create()

        ani = animation.FuncAnimation(
            fig,
            lambda frame: self._timed_update_frame(frame, fps),
            frames=total_frames,
            blit=False,
            interval=1000 / fps,
        )

        ani.save(self._temp_video_path, fps=fps, writer="ffmpeg")
        print(f"🎥 Intermediate video saved to {self._temp_video_path}")

        if self._frame_timings:
            avg_frame_time = sum(self._frame_timings) / len(self._frame_timings)
            print(
                f"⏱ Average frame update time: {avg_frame_time:.4f}s over {len(self._frame_timings)} samples"
            )

        transparent_video_path = TEMP_DIR + "temp_transparent.mov"
        os.system(
            f"ffmpeg -y -i {self._temp_video_path} "
            f"-vf colorkey=0xFF00FF:0.4:0.0,format=yuva444p10le "
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

    def _timed_update_frame(self, frame: int, fps: int) -> List:
        start = time.perf_counter()
        output = self._update_frame(frame, fps)
        elapsed = time.perf_counter() - start
        if frame % 30 == 0:  # log every 30th frame
            self._frame_timings.append(elapsed)
        return output

    def _update_frame(self, frame: int, fps: int) -> List:
        current_time = frame / fps

        for obj in self._text_objects + self._arrows:
            obj.remove()
        self._text_objects.clear()
        self._arrows.clear()

        assert self._ax is not None

        for tab_entry in self._flat_entries:
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
                    center_y + 20,
                    direction,
                    color="black",
                    fontsize=18,
                    ha="center",
                    va="center",
                )

                self._text_objects.append(txt)
                self._arrows.append(arr)
                self._text_objects.append(rect)

        return self._text_objects + self._arrows

    @staticmethod
    def _get_color(tab_entry: TabEntry) -> str:
        return OUT_COLOR if tab_entry.tab > 0 else IN_COLOR

    @staticmethod
    def _calc_direction(tab_entry: TabEntry) -> str:
        return "↑" if tab_entry.tab > 0 else "↓"

    def _get_total_duration(self) -> float:
        return max(tab.time + (tab.duration or 0.5) for tab in self._flat_entries)

    @staticmethod
    def _get_total_frames(fps: int, total_duration: float) -> int:
        return int(total_duration * fps)
