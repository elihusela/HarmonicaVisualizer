"""Tests for image_converter.figure_factory module."""

import os
import tempfile
from unittest.mock import patch, MagicMock
import pytest

from image_converter.figure_factory import (
    FigureFactory,
    FigureFactoryError,
    FigureConfig,
)


class TestFigureConfig:
    """Test FigureConfig dataclass."""

    def test_figure_config_defaults(self):
        """Test FigureConfig default values."""
        config = FigureConfig()

        assert config.background_color == "#FF00FF"  # Magenta for chroma key
        assert config.default_dpi == 100
        assert config.tight_layout is True
        assert config.transparent is False

    def test_figure_config_custom_values(self):
        """Test FigureConfig with custom values."""
        config = FigureConfig(
            background_color="#00FF00",
            default_dpi=150,
            tight_layout=False,
            transparent=True,
        )

        assert config.background_color == "#00FF00"
        assert config.default_dpi == 150
        assert config.tight_layout is False
        assert config.transparent is True


class TestFigureFactoryInitialization:
    """Test FigureFactory initialization."""

    def test_init_successful(self, temp_image_file, figure_config):
        """Test successful initialization."""
        factory = FigureFactory(temp_image_file, figure_config)

        assert factory._image_path == temp_image_file
        assert factory._config == figure_config
        assert factory._img is not None
        assert factory._dpi > 0
        assert len(factory._figsize) == 2

    def test_init_default_config(self, temp_image_file):
        """Test initialization with default config."""
        factory = FigureFactory(temp_image_file)

        assert isinstance(factory._config, FigureConfig)
        assert factory._config.background_color == "#FF00FF"
        assert factory._config.default_dpi == 100

    def test_init_missing_image_file(self):
        """Test initialization with missing image file."""
        with pytest.raises(FigureFactoryError, match="Harmonica image not found"):
            FigureFactory("/nonexistent/image.png")

    def test_init_directory_path(self):
        """Test initialization with directory path instead of file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with pytest.raises(FigureFactoryError, match="Path is not a file"):
                FigureFactory(temp_dir)

    def test_init_empty_image(self):
        """Test initialization with invalid image file."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            # Write invalid image data
            temp_file.write(b"invalid image data")
            temp_path = temp_file.name

        try:
            with pytest.raises(
                FigureFactoryError, match="Failed to load harmonica image"
            ):
                FigureFactory(temp_path)
        finally:
            os.unlink(temp_path)

    def test_init_zero_size_image(self):
        """Test initialization with zero-size image."""
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            # Create zero-size image (this is tricky with PIL, so we'll mock it)
            temp_path = temp_file.name

        try:
            with patch("PIL.Image.open") as mock_open:
                mock_img = MagicMock()
                mock_img.size = (0, 100)  # Zero width
                mock_open.return_value = mock_img

                with pytest.raises(
                    FigureFactoryError, match="Image has zero width or height"
                ):
                    FigureFactory(temp_path)
        finally:
            os.unlink(temp_path)


class TestFigureFactoryImageProcessing:
    """Test image loading and DPI processing."""

    def test_image_loading(self, temp_image_file):
        """Test image loading functionality."""
        factory = FigureFactory(temp_image_file)

        assert factory._img is not None
        assert factory._img.size == (100, 100)  # From temp_image_file fixture
        assert factory._img.mode in ["RGB", "RGBA"]

    def test_dpi_extraction_with_dpi_info(self, temp_image_file):
        """Test DPI extraction when image has DPI info."""
        with patch("PIL.Image.open") as mock_open:
            mock_img = MagicMock()
            mock_img.size = (100, 100)
            mock_img.info = {"dpi": (150, 150)}
            mock_open.return_value = mock_img

            factory = FigureFactory(temp_image_file)
            assert factory._dpi == 150

    def test_dpi_extraction_single_value(self, temp_image_file):
        """Test DPI extraction with single DPI value."""
        with patch("PIL.Image.open") as mock_open:
            mock_img = MagicMock()
            mock_img.size = (100, 100)
            mock_img.info = {"dpi": 200}
            mock_open.return_value = mock_img

            factory = FigureFactory(temp_image_file)
            assert factory._dpi == 200

    def test_dpi_extraction_no_dpi_info(self, temp_image_file, capsys):
        """Test DPI extraction fallback when no DPI info."""
        with patch("PIL.Image.open") as mock_open:
            mock_img = MagicMock()
            mock_img.size = (100, 100)
            mock_img.info = {}  # No DPI info
            mock_open.return_value = mock_img

            config = FigureConfig(default_dpi=120)
            factory = FigureFactory(temp_image_file, config)

            assert factory._dpi == 120
            captured = capsys.readouterr()
            assert "DPI not found" in captured.out

    def test_dpi_extraction_invalid_range(self, temp_image_file, capsys):
        """Test DPI extraction with invalid DPI values."""
        with patch("PIL.Image.open") as mock_open:
            mock_img = MagicMock()
            mock_img.size = (100, 100)
            mock_img.info = {"dpi": (1000, 1000)}  # Too high
            mock_open.return_value = mock_img

            config = FigureConfig(default_dpi=90)
            factory = FigureFactory(temp_image_file, config)

            assert factory._dpi == 90
            captured = capsys.readouterr()
            assert "Unusual DPI value" in captured.out

    def test_dpi_extraction_error_handling(self, temp_image_file, capsys):
        """Test DPI extraction error handling."""
        with patch("PIL.Image.open") as mock_open:
            mock_img = MagicMock()
            mock_img.size = (100, 100)
            mock_img.info = {"dpi": "invalid"}  # Invalid DPI type
            mock_open.return_value = mock_img

            factory = FigureFactory(temp_image_file)

            assert factory._dpi == 100  # Default fallback
            captured = capsys.readouterr()
            assert "Error reading DPI" in captured.out

    def test_figsize_calculation(self, temp_image_file):
        """Test figure size calculation."""
        with patch("PIL.Image.open") as mock_open:
            mock_img = MagicMock()
            mock_img.size = (300, 200)  # 300x200 pixels
            mock_img.info = {"dpi": (100, 100)}
            mock_open.return_value = mock_img

            factory = FigureFactory(temp_image_file)

            # 300px / 100dpi = 3 inches, 200px / 100dpi = 2 inches
            assert factory._figsize == (3.0, 2.0)

    def test_figsize_large_warning(self, temp_image_file, capsys):
        """Test warning for very large figure sizes."""
        with patch("PIL.Image.open") as mock_open:
            mock_img = MagicMock()
            mock_img.size = (6000, 4000)  # Very large image
            mock_img.info = {"dpi": (100, 100)}
            mock_open.return_value = mock_img

            factory = FigureFactory(temp_image_file)

            # 6000px / 100dpi = 60 inches (> 50 inch threshold)
            assert factory._figsize == (60.0, 40.0)
            captured = capsys.readouterr()
            assert "Very large figure size" in captured.out


class TestFigureFactoryCreation:
    """Test figure creation functionality."""

    @patch("matplotlib.pyplot.subplots")
    def test_create_figure_successful(self, mock_subplots, temp_image_file):
        """Test successful figure creation."""
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_subplots.return_value = (mock_fig, mock_ax)

        factory = FigureFactory(temp_image_file)
        fig, ax = factory.create()

        assert fig == mock_fig
        assert ax == mock_ax

        # Verify matplotlib calls
        mock_subplots.assert_called_once()
        call_args = mock_subplots.call_args
        assert "figsize" in call_args.kwargs
        assert "dpi" in call_args.kwargs
        assert "facecolor" in call_args.kwargs

        # Verify figure configuration
        mock_fig.patch.set_facecolor.assert_called_once()
        mock_fig.tight_layout.assert_called_once_with(pad=0)
        mock_ax.imshow.assert_called_once()
        mock_ax.axis.assert_called_once_with("off")
        mock_ax.set_xlim.assert_called_once()
        mock_ax.set_ylim.assert_called_once()

    @patch("matplotlib.pyplot.subplots")
    def test_create_figure_custom_config(self, mock_subplots, temp_image_file):
        """Test figure creation with custom configuration."""
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_subplots.return_value = (mock_fig, mock_ax)

        config = FigureConfig(background_color="#00FF00", tight_layout=False)
        factory = FigureFactory(temp_image_file, config)
        factory.create()

        # Verify custom background color
        call_args = mock_subplots.call_args
        assert call_args.kwargs["facecolor"] == "#00FF00"
        mock_fig.patch.set_facecolor.assert_called_with("#00FF00")

        # Verify tight_layout not called when disabled
        mock_fig.tight_layout.assert_not_called()

    @patch("matplotlib.pyplot.subplots")
    def test_create_figure_error_handling(self, mock_subplots, temp_image_file):
        """Test figure creation error handling."""
        mock_subplots.side_effect = Exception("Matplotlib error")

        factory = FigureFactory(temp_image_file)

        with pytest.raises(FigureFactoryError, match="Failed to create figure"):
            factory.create()

    def test_create_figure_axis_limits(self, temp_image_file):
        """Test axis limits are set correctly."""
        with patch("matplotlib.pyplot.subplots") as mock_subplots:
            mock_fig = MagicMock()
            mock_ax = MagicMock()
            mock_subplots.return_value = (mock_fig, mock_ax)

            with patch("PIL.Image.open") as mock_open:
                mock_img = MagicMock()
                mock_img.size = (400, 300)
                mock_img.width = 400
                mock_img.height = 300
                mock_open.return_value = mock_img

                factory = FigureFactory(temp_image_file)
                factory.create()

                # Verify axis limits match image dimensions
                mock_ax.set_xlim.assert_called_once_with(0, 400)
                mock_ax.set_ylim.assert_called_once_with(300, 0)  # Inverted Y


class TestFigureFactoryInfo:
    """Test information retrieval methods."""

    def test_get_image_info(self, temp_image_file):
        """Test getting image information."""
        factory = FigureFactory(temp_image_file)
        info = factory.get_image_info()

        assert isinstance(info, dict)
        assert "path" in info
        assert "size" in info
        assert "dpi" in info
        assert "figsize" in info
        assert "mode" in info
        assert "format" in info

        assert info["path"] == temp_image_file
        assert info["size"] == (100, 100)  # From fixture
        assert info["dpi"] > 0
        assert len(info["figsize"]) == 2

    def test_get_image_info_detailed(self, temp_image_file):
        """Test detailed image information."""
        with patch("PIL.Image.open") as mock_open:
            mock_img = MagicMock()
            mock_img.size = (800, 600)
            mock_img.mode = "RGB"
            mock_img.format = "PNG"
            mock_img.info = {"dpi": (150, 150)}
            mock_open.return_value = mock_img

            factory = FigureFactory(temp_image_file)
            info = factory.get_image_info()

            assert info["size"] == (800, 600)
            assert info["mode"] == "RGB"
            assert info["format"] == "PNG"
            assert info["dpi"] == 150
            assert info["figsize"] == (800 / 150, 600 / 150)


class TestFigureFactoryIntegration:
    """Test integration scenarios and real-world usage."""

    def test_complete_workflow(self, temp_image_file):
        """Test complete figure creation workflow."""
        # Create factory
        config = FigureConfig(background_color="#123456", default_dpi=120)
        factory = FigureFactory(temp_image_file, config)

        # Get info
        info = factory.get_image_info()
        assert info["path"] == temp_image_file

        # Create figure with mocked matplotlib
        with patch("matplotlib.pyplot.subplots") as mock_subplots:
            mock_fig = MagicMock()
            mock_ax = MagicMock()
            mock_subplots.return_value = (mock_fig, mock_ax)

            fig, ax = factory.create()

            assert fig is not None
            assert ax is not None

    def test_multiple_figure_creation(self, temp_image_file):
        """Test creating multiple figures from same factory."""
        factory = FigureFactory(temp_image_file)

        with patch("matplotlib.pyplot.subplots") as mock_subplots:
            mock_fig = MagicMock()
            mock_ax = MagicMock()
            mock_subplots.return_value = (mock_fig, mock_ax)

            # Create multiple figures
            fig1, ax1 = factory.create()
            fig2, ax2 = factory.create()

            assert fig1 == fig2  # Same mock object
            assert ax1 == ax2  # Same mock object
            assert mock_subplots.call_count == 2

    def test_resource_cleanup(self, temp_image_file):
        """Test resource cleanup on destruction."""
        factory = FigureFactory(temp_image_file)
        mock_img = factory._img

        # Mock the close method
        mock_img.close = MagicMock()

        # Trigger cleanup - this test mainly ensures the __del__ method doesn't crash
        del factory

    def test_error_scenarios_and_recovery(self, temp_image_file):
        """Test various error scenarios."""
        # Test with different error conditions
        with patch("os.path.exists", return_value=False):
            with pytest.raises(FigureFactoryError, match="Harmonica image not found"):
                FigureFactory("/fake/path.png")

        # Test with image loading error
        with patch("PIL.Image.open", side_effect=Exception("PIL error")):
            with pytest.raises(
                FigureFactoryError, match="Failed to load harmonica image"
            ):
                FigureFactory(temp_image_file)

    def test_realistic_image_sizes(self, temp_image_file):
        """Test with realistic harmonica image dimensions."""
        realistic_sizes = [
            (1536, 512),  # Common harmonica image size
            (800, 300),  # Smaller size
            (2048, 768),  # Larger size
        ]

        for width, height in realistic_sizes:
            with patch("PIL.Image.open") as mock_open:
                mock_img = MagicMock()
                mock_img.size = (width, height)
                mock_img.width = width
                mock_img.height = height
                mock_img.info = {"dpi": (100, 100)}
                mock_open.return_value = mock_img

                factory = FigureFactory(temp_image_file)

                assert factory._figsize == (width / 100, height / 100)

                # Test figure creation
                with patch("matplotlib.pyplot.subplots") as mock_subplots:
                    mock_fig = MagicMock()
                    mock_ax = MagicMock()
                    mock_subplots.return_value = (mock_fig, mock_ax)

                    factory.create()

                    # Verify axis limits
                    mock_ax.set_xlim.assert_called_with(0, width)
                    mock_ax.set_ylim.assert_called_with(height, 0)
