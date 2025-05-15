from PIL import Image
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from typing import Tuple

REMOVABLE_BACKGROUND_COLOR = "#FF00FF"


class FigureFactory:
    def __init__(self, harmonica_image_path: str):
        self._image_path = harmonica_image_path
        self._img = Image.open(harmonica_image_path)
        self._dpi = self._get_image_dpi()
        self._figsize = self._calculate_figsize()

    def create(self) -> Tuple[plt.Figure, Axes]:
        fig, ax = plt.subplots(figsize=self._figsize, dpi=self._dpi)
        fig.patch.set_facecolor(REMOVABLE_BACKGROUND_COLOR)
        ax.imshow(self._img)
        ax.axis("off")
        return fig, ax

    def _get_image_dpi(self) -> int:
        dpi_info = self._img.info.get("dpi")
        if dpi_info is None:
            print("⚠️ DPI not found in image. Using default of 100.")
            return 100
        if isinstance(dpi_info, tuple):
            return int(dpi_info[0])
        return int(dpi_info)

    def _calculate_figsize(self) -> Tuple[float, float]:
        width_px, height_px = self._img.size
        width_in = width_px / self._dpi
        height_in = height_px / self._dpi
        return width_in, height_in
