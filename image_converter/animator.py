import os
from typing import List, Tuple, Optional

import matplotlib.animation as animation
import matplotlib.pyplot as plt
from PIL import Image
from matplotlib.axes import Axes
from matplotlib.text import Text

from image_converter.consts import DISTANCE, FIRST_X, Y, IN_COLOR, OUT_COLOR
from tab_converter.models import Tabs, TabEntry
from utils.utils import TEMP_DIR


class Animator:
    def __init__(self, harmonica_image_path: str, outputs_path: str):
        self._harmonica_image_path = harmonica_image_path
        self._outputs_path = outputs_path
        self._hole_positions = self._calc_hole_positions()
        self._text_objects: List[Text] = []
        self._arrows: List[str] = []
        self._temp_video_path: str = TEMP_DIR + "temp_video.mp4"
        self._ax: Optional[Axes] = None

    def create_animation(
        self, tabs: Tabs, extracted_audio_path: str, fps: int = 30
    ) -> None:
        img = Image.open(self._harmonica_image_path)
        fig, self._ax = plt.subplots(figsize=(12, 2))
        self._ax.imshow(img)
        self._ax.axis("off")

        total_duration = self._get_total_duration(tabs)
        total_frames = self._get_total_frames(fps, total_duration)

        ani = animation.FuncAnimation(
            fig,
            lambda frame: self._update_frame(frame, tabs, fps),
            frames=total_frames,
            blit=False,
            interval=1000 / fps,
        )

        ani.save(self._temp_video_path, fps=fps, writer="ffmpeg")

        os.system(
            f"ffmpeg -y -i {self._temp_video_path} -i "
            f"{extracted_audio_path} -c:v copy -c:a aac -shortest "
            f"{self._outputs_path}"
        )
        print(f"✅ Final video saved to {self._outputs_path}")
        os.remove(self._temp_video_path)

    def _update_frame(self, frame: int, tabs: Tabs, fps: int) -> List:
        current_time = frame / fps

        # Clear previous text/arrows
        for obj in self._text_objects + self._arrows:
            obj.remove()
        self._text_objects.clear()
        self._arrows.clear()

        assert self._ax is not None

        # Draw each tab currently active
        for tab_entry in tabs.tabs:
            start = tab_entry.time
            end = start + tab_entry.duration
            if start <= current_time <= end:
                hole = abs(tab_entry.tab)
                x, y = self._hole_positions.get(hole, (0, 0))
                direction = self._calc_direction(tab_entry)
                color = self._get_color(tab_entry)

                txt = self._ax.text(
                    x,
                    y - 10,
                    f"{hole}",
                    color=color,
                    fontsize=18,
                    ha="center",
                    va="center",
                    weight="bold",
                )
                arr = self._ax.text(
                    x,
                    y + 15,
                    direction,
                    color=color,
                    fontsize=20,
                    ha="center",
                    va="center",
                )

                self._text_objects.append(txt)
                self._arrows.append(arr)

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

    @staticmethod
    def _calc_hole_positions() -> dict[int, Tuple[int, int]]:
        return {i: (FIRST_X + (i - 1) * DISTANCE, Y) for i in range(1, 11)}
