"""Test fixtures for tab_phrase_animator module tests."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from tab_phrase_animator.tab_text_parser import ParseConfig, ParseStatistics
from tab_phrase_animator.tab_phrase_animator import TabPhraseAnimator, AnimationConfig
from tab_converter.models import TabEntry
from image_converter.harmonica_layout import HarmonicaLayout
from image_converter.figure_factory import FigureFactory


@pytest.fixture
def sample_tab_content():
    """Sample tab file content for testing."""
    return """Page 1:
1 2 3 -4 -5
67 -89

Page 2:
1 -23 45

Page 3:
"""


@pytest.fixture
def complex_tab_content():
    """Complex tab file content with various scenarios."""
    return """Page Intro:
4 -4 5 -5 6

Page Verse 1:
6 6 6 -6 -7 7 -8 8
-8 7 -7 -6 6 -5 5 -4

page chorus:
8 -8 -9 8 -8 -9 8
-8 -9 -10 9 -9 8 -8

Page Bridge:
-3 4 -4 5 -5 6 -6 7

Page Outro:
7 -7 6 -6 5 -5 4 -4 4
"""


@pytest.fixture
def invalid_tab_content():
    """Tab content with various parsing errors."""
    return """Page 1:
1 2 3
1 - invalid
4 5 6

outside page context
Page 2:
7 8 9
"""


@pytest.fixture
def parse_config_permissive():
    """Permissive parse configuration for testing."""
    return ParseConfig(
        allow_empty_pages=True,
        allow_empty_chords=True,
        validate_hole_numbers=False,
        min_hole=1,
        max_hole=15,
        encoding="utf-8",
    )


@pytest.fixture
def parse_config_strict():
    """Strict parse configuration for testing."""
    return ParseConfig(
        allow_empty_pages=False,
        allow_empty_chords=False,
        validate_hole_numbers=True,
        min_hole=1,
        max_hole=10,
        encoding="utf-8",
    )


@pytest.fixture
def parse_config_custom_range():
    """Custom hole range parse configuration."""
    return ParseConfig(
        validate_hole_numbers=True,
        min_hole=3,
        max_hole=7,
    )


@pytest.fixture
def sample_parse_statistics():
    """Sample parse statistics for testing."""
    return ParseStatistics(
        total_pages=3,
        total_lines=5,
        total_chords=12,
        total_notes=28,
        empty_pages=1,
        invalid_lines=2,
        hole_range=(1, 10),
    )


@pytest.fixture
def expected_parsed_structure():
    """Expected structure for sample tab content."""
    return {
        "Page 1": [
            [[1], [2], [3], [-4], [-5]],  # Line 1: 5 single-note chords
            [[6, 7], [-8, -9]],  # Line 2: 2 multi-note chords
        ],
        "Page 2": [
            [[1], [-2, -3], [4, 5]],  # Line 1: 3 chords (no hole 0)
        ],
        "Page 3": [],  # Empty page
    }


@pytest.fixture
def tab_file_paths(temp_test_dir):
    """Common tab file paths for testing."""
    return {
        "simple": temp_test_dir / "simple.txt",
        "complex": temp_test_dir / "complex.txt",
        "invalid": temp_test_dir / "invalid.txt",
        "empty": temp_test_dir / "empty.txt",
        "nonexistent": temp_test_dir / "nonexistent.txt",
    }


@pytest.fixture
def create_tab_file(temp_test_dir):
    """Helper function to create tab files with specific content."""

    def _create_file(filename: str, content: str) -> Path:
        file_path = temp_test_dir / filename
        file_path.write_text(content, encoding="utf-8")
        return file_path

    return _create_file


# TabPhraseAnimator specific fixtures

@pytest.fixture
def mock_harmonica_layout():
    """Mock HarmonicaLayout for testing."""
    return MagicMock(spec=HarmonicaLayout)


@pytest.fixture
def mock_figure_factory():
    """Mock FigureFactory for testing."""
    return MagicMock(spec=FigureFactory)


@pytest.fixture
def basic_animator(mock_harmonica_layout, mock_figure_factory):
    """Basic TabPhraseAnimator with mocked dependencies."""
    from unittest.mock import patch
    with patch.object(TabPhraseAnimator, "_load_font"):
        return TabPhraseAnimator(mock_harmonica_layout, mock_figure_factory)


@pytest.fixture
def temp_audio_file(temp_test_dir):
    """Create a temporary audio file for testing."""
    audio_file = temp_test_dir / "test_audio.wav"
    audio_file.write_text("dummy audio content")
    return audio_file


@pytest.fixture
def sample_pages():
    """Sample page structure for animation testing."""
    return {
        "Page 1": [
            [
                [TabEntry(tab=1, time=1.0, duration=0.5, confidence=0.8)],
                [TabEntry(tab=2, time=1.5, duration=0.5, confidence=0.8)],
            ],
            [
                [TabEntry(tab=-3, time=2.0, duration=0.5, confidence=0.8)],
            ],
        ],
        "Page 2": [
            [
                [
                    TabEntry(tab=4, time=3.0, duration=0.5, confidence=0.8),
                    TabEntry(tab=5, time=3.0, duration=0.5, confidence=0.8),
                ],
            ],
        ],
    }


@pytest.fixture
def sample_midi_tabs():
    """Sample MIDI tabs for testing."""
    from tab_converter.models import Tabs

    return Tabs(tabs=[
        TabEntry(tab=1, time=1.0, duration=0.5, confidence=0.8),
        TabEntry(tab=2, time=1.5, duration=0.5, confidence=0.8),
        TabEntry(tab=-3, time=2.0, duration=0.5, confidence=0.8),
        TabEntry(tab=4, time=2.5, duration=0.5, confidence=0.8),
        TabEntry(tab=-5, time=3.0, duration=0.5, confidence=0.8),
    ])
