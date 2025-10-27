"""Global test fixtures for HarmonicaTabs project."""

# Configure matplotlib to use non-interactive backend for testing
# Must be done before any matplotlib imports
import matplotlib

matplotlib.use("Agg")

import pytest  # noqa: E402
from pathlib import Path  # noqa: E402

from tab_converter.models import TabEntry, Tabs, NoteEvent  # noqa: E402

# Import pipeline modules early to avoid pkg_resources initialization issues
# when running CLI tests in isolation
from harmonica_pipeline.midi_generator import MidiGenerator  # noqa: F401, E402
from harmonica_pipeline.video_creator import VideoCreator  # noqa: F401, E402


@pytest.fixture
def sample_tab_entry():
    """Basic TabEntry with confidence parameter."""
    return TabEntry(tab=3, time=1.5, duration=0.8, confidence=0.9)


@pytest.fixture
def sample_tab_entry_negative():
    """TabEntry with negative tab (draw note)."""
    return TabEntry(tab=-4, time=2.0, duration=1.2, confidence=0.7)


@pytest.fixture
def sample_tab_entries():
    """List of sample TabEntry objects."""
    return [
        TabEntry(tab=1, time=0.0, duration=0.5, confidence=0.8),
        TabEntry(tab=-2, time=0.5, duration=0.7, confidence=0.9),
        TabEntry(tab=3, time=1.2, duration=0.6, confidence=0.85),
        TabEntry(tab=-4, time=1.8, duration=0.9, confidence=0.75),
        TabEntry(tab=5, time=2.7, duration=0.4, confidence=0.95),
    ]


@pytest.fixture
def sample_tabs(sample_tab_entries):
    """Tabs container with sample TabEntry objects."""
    return Tabs(tabs=sample_tab_entries)


@pytest.fixture
def sample_note_event():
    """Basic NoteEvent with MIDI pitch."""
    return NoteEvent(
        start_time=1.0,
        end_time=1.8,
        pitch=60,  # C4
        confidence=0.85,
        activation=[0.1, 0.3, 0.8, 0.6, 0.2],
    )


@pytest.fixture
def sample_note_events():
    """List of sample NoteEvent objects covering harmonica range."""
    return [
        NoteEvent(
            start_time=0.0,
            end_time=0.5,
            pitch=60,
            confidence=0.8,
            activation=[0.2, 0.5, 0.7],
        ),
        NoteEvent(
            start_time=0.5,
            end_time=1.2,
            pitch=64,
            confidence=0.9,
            activation=[0.3, 0.8, 0.6],
        ),
        NoteEvent(
            start_time=1.2,
            end_time=1.8,
            pitch=67,
            confidence=0.75,
            activation=[0.4, 0.7, 0.5],
        ),
        NoteEvent(
            start_time=1.8,
            end_time=2.5,
            pitch=72,
            confidence=0.85,
            activation=[0.5, 0.9, 0.4],
        ),
        NoteEvent(
            start_time=2.5,
            end_time=3.0,
            pitch=76,
            confidence=0.95,
            activation=[0.6, 0.8, 0.3],
        ),
    ]


@pytest.fixture
def empty_tabs():
    """Empty Tabs container for edge case testing."""
    return Tabs(tabs=[])


@pytest.fixture
def test_data_dir():
    """Path to test data directory."""
    return Path(__file__).parent / "data"


@pytest.fixture
def temp_test_dir(tmp_path):
    """Temporary directory for test files."""
    return tmp_path


@pytest.fixture
def sample_midi_pitches():
    """Common MIDI pitches used in harmonica testing."""
    return {
        "C4": 60,
        "E4": 64,
        "G4": 67,
        "C5": 72,
        "E5": 76,
        "G5": 79,
        "C6": 84,
    }


@pytest.fixture
def harmonica_hole_mapping():
    """Sample harmonica hole mappings for testing."""
    return {
        60: 1,  # C4 -> Hole 1 blow
        64: -1,  # E4 -> Hole 1 draw
        67: 2,  # G4 -> Hole 2 blow
        72: 3,  # C5 -> Hole 3 blow
        76: -3,  # E5 -> Hole 3 draw
        79: 4,  # G5 -> Hole 4 blow
        84: 5,  # C6 -> Hole 5 blow
    }
