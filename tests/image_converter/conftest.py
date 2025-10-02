"""Shared fixtures for image_converter tests."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from PIL import Image

from image_converter.harmonica_layout import HarmonicaLayout, LayoutConfig
from image_converter.figure_factory import FigureFactory, FigureConfig
from image_converter.video_processor import VideoProcessor
from image_converter.color_scheme import ColorScheme
from tab_converter.models import TabEntry


@pytest.fixture
def temp_image_file():
    """Create a temporary test image file."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
        # Create a simple 100x100 RGB image
        img = Image.new("RGB", (100, 100), color="white")
        img.save(temp_file.name, "PNG")
        yield temp_file.name

    # Cleanup
    Path(temp_file.name).unlink(missing_ok=True)


@pytest.fixture
def sample_hole_mapping():
    """Create a simple hole mapping for testing."""
    return {
        1: {"top_left": {"x": 10, "y": 10}, "bottom_right": {"x": 50, "y": 50}},
        2: {"top_left": {"x": 60, "y": 10}, "bottom_right": {"x": 100, "y": 50}},
        3: {"top_left": {"x": 110, "y": 10}, "bottom_right": {"x": 150, "y": 50}},
    }


@pytest.fixture
def layout_config():
    """Create a basic layout configuration."""
    return LayoutConfig(
        min_coordinate=0,
        max_coordinate=1000,
        validate_coordinates=True
    )


@pytest.fixture
def figure_config():
    """Create a basic figure configuration."""
    return FigureConfig(
        background_color="#FF00FF",
        default_dpi=100,
        tight_layout=True,
        transparent=False
    )


@pytest.fixture
def harmonica_layout(temp_image_file, sample_hole_mapping, layout_config):
    """Create a HarmonicaLayout instance for testing."""
    return HarmonicaLayout(temp_image_file, sample_hole_mapping, layout_config)


@pytest.fixture
def figure_factory(temp_image_file, figure_config):
    """Create a FigureFactory instance for testing."""
    return FigureFactory(temp_image_file, figure_config)


@pytest.fixture
def mock_figure_factory():
    """Create a mock FigureFactory for testing."""
    factory = MagicMock(spec=FigureFactory)
    mock_fig = MagicMock()
    mock_ax = MagicMock()
    factory.create.return_value = (mock_fig, mock_ax)
    return factory


@pytest.fixture
def mock_harmonica_layout():
    """Create a mock HarmonicaLayout for testing."""
    layout = MagicMock(spec=HarmonicaLayout)
    layout.get_hole_coordinates.return_value = MagicMock()
    layout.get_hole_rectangle.return_value = MagicMock()
    layout.get_all_hole_numbers.return_value = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    return layout


@pytest.fixture
def video_processor():
    """Create a VideoProcessor instance for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield VideoProcessor(temp_dir)


@pytest.fixture
def color_scheme():
    """Create a ColorScheme instance for testing."""
    return ColorScheme()


@pytest.fixture
def sample_tab_entries():
    """Create sample TabEntry objects for testing."""
    return [
        TabEntry(tab=1, time=0.0, duration=0.5, confidence=0.8),    # Blow
        TabEntry(tab=-2, time=0.5, duration=0.5, confidence=0.8),   # Draw
        TabEntry(tab=3, time=1.0, duration=0.5, confidence=0.8),    # Blow
        TabEntry(tab=-4, time=1.5, duration=0.5, confidence=0.8),   # Draw
    ]


@pytest.fixture
def sample_animation_pages(sample_tab_entries):
    """Create sample animation page structure."""
    return {
        "Page 1": [
            [
                [sample_tab_entries[0]],  # Single note chord
                [sample_tab_entries[1], sample_tab_entries[2]],  # Two-note chord
            ],
            [
                [sample_tab_entries[3]],  # Single note chord
            ]
        ]
    }


@pytest.fixture
def temp_audio_file():
    """Create a temporary audio file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
        temp_file.write(b"dummy audio content")
        yield temp_file.name

    # Cleanup
    Path(temp_file.name).unlink(missing_ok=True)


@pytest.fixture
def temp_video_file():
    """Create a temporary video file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
        temp_file.write(b"dummy video content")
        yield temp_file.name

    # Cleanup
    Path(temp_file.name).unlink(missing_ok=True)


@pytest.fixture
def mock_subprocess_run():
    """Mock subprocess.run for FFmpeg operations."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock()
        yield mock_run


@pytest.fixture
def mock_matplotlib():
    """Mock matplotlib components for animation testing."""
    with patch("matplotlib.pyplot.subplots") as mock_subplots:
        with patch("matplotlib.animation.FuncAnimation") as mock_animation:
            mock_fig = MagicMock()
            mock_ax = MagicMock()
            mock_subplots.return_value = (mock_fig, mock_ax)

            mock_ani = MagicMock()
            mock_animation.return_value = mock_ani

            yield {
                "subplots": mock_subplots,
                "animation": mock_animation,
                "fig": mock_fig,
                "ax": mock_ax,
                "ani": mock_ani
            }