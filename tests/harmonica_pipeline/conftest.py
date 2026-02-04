"""Shared fixtures for harmonica_pipeline tests."""

from unittest.mock import MagicMock, patch
import pytest

from harmonica_pipeline.video_creator_config import VideoCreatorConfig
from tab_converter.models import TabEntry
from tab_phrase_animator.tab_text_parser import ParsedNote


@pytest.fixture
def mock_video_creator_dependencies():
    """Mock all VideoCreator dependencies."""
    with patch.multiple(
        "harmonica_pipeline.video_creator",
        AudioExtractor=MagicMock(),
        MidiProcessor=MagicMock(),
        create_tab_mapper=MagicMock(return_value=MagicMock()),
        TabTextParser=MagicMock(),
        TabMatcher=MagicMock(),
        HarmonicaLayout=MagicMock(),
        FigureFactory=MagicMock(),
        Animator=MagicMock(),
        TabPhraseAnimator=MagicMock(),
    ) as mocks:
        yield mocks


@pytest.fixture
def create_test_files():
    """Helper to create test files in a temp directory."""

    def _create_files(temp_dir, file_specs=None):
        """
        Create test files in temp directory.

        Args:
            temp_dir: Path to temp directory
            file_specs: Dict of {filename: content}, defaults to common test files
        """
        if file_specs is None:
            file_specs = {
                "test.mp4": "dummy video",
                "test.txt": "dummy tabs",
                "harmonica.png": "dummy image",
                "test.mid": "dummy midi",
            }

        created_files = {}
        for filename, content in file_specs.items():
            file_path = temp_dir / filename
            file_path.write_text(content)
            created_files[filename.split(".")[0] + "_path"] = file_path

        return created_files

    return _create_files


@pytest.fixture
def basic_config(temp_test_dir, create_test_files):
    """Create a basic VideoCreatorConfig for testing."""
    create_test_files(temp_test_dir)
    return VideoCreatorConfig(
        video_path=str(temp_test_dir / "test.mp4"),
        tabs_path=str(temp_test_dir / "test.txt"),
        harmonica_path=str(temp_test_dir / "harmonica.png"),
        midi_path=str(temp_test_dir / "test.mid"),
        output_video_path=str(temp_test_dir / "output.mp4"),
    )


@pytest.fixture
def config_with_tabs(temp_test_dir, create_test_files):
    """Create VideoCreatorConfig with tabs output enabled."""
    create_test_files(temp_test_dir)
    return VideoCreatorConfig(
        video_path=str(temp_test_dir / "test.mp4"),
        tabs_path=str(temp_test_dir / "test.txt"),
        harmonica_path=str(temp_test_dir / "harmonica.png"),
        midi_path=str(temp_test_dir / "test.mid"),
        output_video_path=str(temp_test_dir / "output.mp4"),
        tabs_output_path=str(temp_test_dir / "tabs_output.mp4"),
        produce_tabs=True,
    )


@pytest.fixture
def config_with_tab_matching(temp_test_dir, create_test_files):
    """Create VideoCreatorConfig with tab matching enabled."""
    create_test_files(temp_test_dir)
    config = VideoCreatorConfig(
        video_path=str(temp_test_dir / "test.mp4"),
        tabs_path=str(temp_test_dir / "test.txt"),
        harmonica_path=str(temp_test_dir / "harmonica.png"),
        midi_path=str(temp_test_dir / "test.mid"),
        output_video_path=str(temp_test_dir / "output.mp4"),
    )
    config.enable_tab_matching = True
    return config


@pytest.fixture
def sample_midi_tabs():
    """Create sample MIDI tab entries for testing."""
    return [
        TabEntry(tab=1, time=0.0, duration=0.5, confidence=0.8),
        TabEntry(tab=2, time=0.5, duration=0.5, confidence=0.8),
        TabEntry(tab=3, time=1.0, duration=0.5, confidence=0.8),
        TabEntry(tab=4, time=1.5, duration=0.5, confidence=0.8),
        TabEntry(tab=-5, time=2.0, duration=0.5, confidence=0.8),
        TabEntry(tab=-6, time=2.5, duration=0.5, confidence=0.8),
    ]


@pytest.fixture
def sample_parsed_pages():
    """Create sample parsed page structure for testing with ParsedNote objects."""
    return {
        "Page 1": [
            [
                [ParsedNote(1, False)],  # Chord 1
                [ParsedNote(2, False), ParsedNote(3, False)],  # Chord 2+3
            ]
        ],
        "Page 2": [
            [[ParsedNote(4, False)]],  # Line 1: chord 4
            [[ParsedNote(-5, False), ParsedNote(-6, False)]],  # Line 2: chord -5+-6
        ],
    }


@pytest.fixture
def mock_tabs_object(sample_midi_tabs):
    """Create a mock tabs object with sample data."""
    mock_tabs = MagicMock()
    mock_tabs.tabs = sample_midi_tabs
    return mock_tabs


@pytest.fixture
def mock_empty_tabs():
    """Create a mock tabs object with empty data."""
    mock_tabs = MagicMock()
    mock_tabs.tabs = []
    return mock_tabs


@pytest.fixture
def create_video_creator_with_mocks(mock_video_creator_dependencies):
    """Factory to create VideoCreator with all dependencies mocked."""

    def _create(config):
        from harmonica_pipeline.video_creator import VideoCreator

        return VideoCreator(config)

    return _create
