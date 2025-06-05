from typing import List
from matplotlib.axes import Axes
from matplotlib.text import Text

from image_converter.color_scheme import ColorScheme
from image_converter.harmonica_layout import HarmonicaLayout
from tab_converter.models import TabEntry


class TabVisualizer:
    def __init__(self, ax: Axes, layout: HarmonicaLayout, color_scheme: ColorScheme):
        self._ax = ax
        self._layout = layout
        self._color_scheme = color_scheme
        self._text_objects: List[Text] = []
        self._arrows: List[Text] = []

    def clear(self) -> None:
        for obj in self._text_objects + self._arrows:
            obj.remove()
        self._text_objects.clear()
        self._arrows.clear()

    def draw_tab(self, tab_entry: TabEntry) -> None:
        hole = abs(tab_entry.tab)
        x, y = self._layout.get_position(hole)
        color = self._color_scheme.get_color(tab_entry)
        direction = "↓" if tab_entry.tab > 0 else "↑"

        txt = self._ax.text(
            x,
            y - 10,
            f"{hole}",
            color=color,
            fontsize=18,
            fontname="Fredoka",
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
            fontname="Fredoka",
            ha="center",
            va="center",
        )

        self._text_objects.append(txt)
        self._arrows.append(arr)

    def get_objects(self) -> List[Text]:
        return self._text_objects + self._arrows
