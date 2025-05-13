import pytest
from unittest.mock import MagicMock
from harmonica_pipeline.harmonica_pipeline import HarmonicaTabsPipeline
from tab_converter.models import Tabs, TabEntry


# Individual dependency fixtures (fully mocked)
@pytest.fixture
def mock_tab_mapper() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_animator() -> MagicMock:
    return MagicMock()


@pytest.fixture
def mock_audio_extractor() -> MagicMock:
    return MagicMock()


# Combined pipeline fixture
@pytest.fixture
def dummy_pipeline(
    mock_tab_mapper, mock_animator, mock_audio_extractor
) -> HarmonicaTabsPipeline:
    return HarmonicaTabsPipeline(
        tab_mapper=mock_tab_mapper,
        animator=mock_animator,
        audio_extractor=mock_audio_extractor,
        one_note_melody=True,
        save_midi=True,
    )


@pytest.fixture
def configured_pipeline(
    dummy_pipeline, mock_tab_mapper, mock_animator, mock_audio_extractor
):
    fake_tabs = Tabs([TabEntry(tab=1, time=0.0, duration=1.0)])
    fake_note_events = [(0.0, 1.0, 60, 0.9, [])]
    fake_midi = MagicMock()

    mock_audio_extractor.extract_audio_from_video.return_value = "audio.wav"
    mock_tab_mapper.note_events_to_tabs.return_value = fake_tabs

    return {
        "pipeline": dummy_pipeline,
        "tabs": fake_tabs,
        "note_events": fake_note_events,
        "midi_data": fake_midi,
    }
