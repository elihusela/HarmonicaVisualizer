"""
Figure Factory - Creates matplotlib figures with harmonica background images.

Handles image loading, DPI detection, and figure creation with proper error handling
and configuration options.
"""

import os
from dataclasses import dataclass
from typing import Tuple, Optional

from PIL import Image
import matplotlib.pyplot as plt
from matplotlib.axes import Axes


@dataclass
class FigureConfig:
    """Configuration for figure creation."""
    background_color: str = "#FF00FF"  # Magenta for chroma key removal
    default_dpi: int = 100
    tight_layout: bool = True
    transparent: bool = False


class FigureFactoryError(Exception):
    """Custom exception for figure creation errors."""
    pass


class FigureFactory:
    """
    Creates matplotlib figures with harmonica background images.

    Handles image loading, DPI detection, and figure sizing with proper
    error handling and resource management.
    """

    def __init__(self, harmonica_image_path: str, config: Optional[FigureConfig] = None):
        """
        Initialize figure factory.

        Args:
            harmonica_image_path: Path to harmonica background image
            config: Optional configuration for figure creation

        Raises:
            FigureFactoryError: If image cannot be loaded or is invalid
        """
        self._image_path = harmonica_image_path
        self._config = config or FigureConfig()

        # Validate and load image
        self._validate_image_path()
        self._img = self._load_image()

        # Calculate figure properties
        self._dpi = self._get_image_dpi()
        self._figsize = self._calculate_figsize()

    def create(self) -> Tuple[plt.Figure, Axes]:
        """
        Create a matplotlib figure with harmonica background.

        Returns:
            Tuple of (figure, axes) ready for harmonica animation

        Raises:
            FigureFactoryError: If figure creation fails
        """
        try:
            fig, ax = plt.subplots(
                figsize=self._figsize,
                dpi=self._dpi,
                facecolor=self._config.background_color
            )

            # Configure figure
            fig.patch.set_facecolor(self._config.background_color)

            if self._config.tight_layout:
                fig.tight_layout(pad=0)

            # Add harmonica image
            ax.imshow(self._img)
            ax.axis("off")

            # Remove margins for precise sizing
            ax.set_xlim(0, self._img.width)
            ax.set_ylim(self._img.height, 0)  # Invert Y-axis for image coordinates

            return fig, ax

        except Exception as e:
            raise FigureFactoryError(f"Failed to create figure: {e}")

    def get_image_info(self) -> dict:
        """
        Get information about the loaded harmonica image.

        Returns:
            Dict with image properties
        """
        return {
            "path": self._image_path,
            "size": self._img.size,
            "dpi": self._dpi,
            "figsize": self._figsize,
            "mode": self._img.mode,
            "format": self._img.format
        }

    def _validate_image_path(self) -> None:
        """Validate that image file exists and is accessible."""
        if not os.path.exists(self._image_path):
            raise FigureFactoryError(f"Harmonica image not found: {self._image_path}")

        if not os.path.isfile(self._image_path):
            raise FigureFactoryError(f"Path is not a file: {self._image_path}")

    def _load_image(self) -> Image.Image:
        """
        Load and validate the harmonica image.

        Returns:
            PIL Image object

        Raises:
            FigureFactoryError: If image cannot be loaded
        """
        try:
            img = Image.open(self._image_path)
            img.load()  # Ensure image is fully loaded

            if img.size[0] == 0 or img.size[1] == 0:
                raise FigureFactoryError("Image has zero width or height")

            return img

        except Exception as e:
            raise FigureFactoryError(f"Failed to load harmonica image {self._image_path}: {e}")

    def _get_image_dpi(self) -> int:
        """
        Extract DPI from image metadata with fallback.

        Returns:
            DPI value for figure creation
        """
        try:
            dpi_info = self._img.info.get("dpi")

            if dpi_info is None:
                print(f"⚠️  DPI not found in {os.path.basename(self._image_path)}. Using default: {self._config.default_dpi}")
                return self._config.default_dpi

            if isinstance(dpi_info, tuple):
                # Use horizontal DPI
                dpi = int(dpi_info[0])
            else:
                dpi = int(dpi_info)

            # Validate DPI range
            if not (50 <= dpi <= 600):
                print(f"⚠️  Unusual DPI value ({dpi}) detected. Using default: {self._config.default_dpi}")
                return self._config.default_dpi

            return dpi

        except (ValueError, TypeError) as e:
            print(f"⚠️  Error reading DPI: {e}. Using default: {self._config.default_dpi}")
            return self._config.default_dpi

    def _calculate_figsize(self) -> Tuple[float, float]:
        """
        Calculate matplotlib figure size in inches.

        Returns:
            Tuple of (width_inches, height_inches)
        """
        width_px, height_px = self._img.size
        width_in = width_px / self._dpi
        height_in = height_px / self._dpi

        # Validate reasonable figure sizes
        if width_in > 50 or height_in > 50:
            print(f"⚠️  Very large figure size: {width_in:.1f}x{height_in:.1f} inches")

        return width_in, height_in

    def __del__(self):
        """Clean up resources when factory is destroyed."""
        if hasattr(self, '_img'):
            self._img.close()
