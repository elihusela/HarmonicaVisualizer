from pathlib import Path
from unittest.mock import patch

from tab_converter.models import NoteEvent
from tab_converter.models import TabEntry, Tabs


class TestTabMapper:

    def test_note_events_to_tabs_valid(self, tab_mapper):
        note_events = [
            NoteEvent(0.0, 1.0, 60, 0.95, []),
            NoteEvent(1.0, 1.5, 62, 0.85, []),
            NoteEvent(2.0, 2.6, 64, 0.88, []),
        ]

        result = tab_mapper.note_events_to_tabs(note_events)
        assert result.tabs == [
            TabEntry(tab=1, time=0.0, duration=1.0),
            TabEntry(tab=-1, time=1.0, duration=0.5),
            TabEntry(tab=2, time=2.0, duration=0.6),
        ]

    def test_ignores_unmapped_pitches(self, tab_mapper):
        note_events = [
            NoteEvent(0.0, 1.0, 999, 0.9, []),
            NoteEvent(0.0, 1.0, 60, 0.9, []),
        ]
        result = tab_mapper.note_events_to_tabs(note_events)
        assert result.tabs == [TabEntry(tab=1, time=0.0, duration=1.0)]

    def test_empty_input(self, tab_mapper):
        result = tab_mapper.note_events_to_tabs([])
        assert isinstance(result, Tabs)
        assert result.tabs == []

    def test_zero_duration(self, tab_mapper):
        note_events = [NoteEvent(1.0, 1.0, 60, 0.9, [])]
        result = tab_mapper.note_events_to_tabs(note_events)
        assert result.tabs == [TabEntry(tab=1, time=1.0, duration=0.0)]

    def test_negative_duration(self, tab_mapper):
        note_events = [NoteEvent(2.0, 1.5, 60, 0.9, [])]
        result = tab_mapper.note_events_to_tabs(note_events)
        assert result.tabs == [TabEntry(tab=1, time=2.0, duration=-0.5)]

    def test_rounding_precision(self, tab_mapper):
        note_events = [NoteEvent(0.00001, 0.99999, 60, 0.9, [])]
        result = tab_mapper.note_events_to_tabs(note_events)
        assert result.tabs == [TabEntry(tab=1, time=0.0, duration=1.0)]

    def test_save_tabs_to_json_calls_open(self, tab_mapper):
        tabs = Tabs(
            [
                TabEntry(tab=1, time=0.0, duration=1.0),
                TabEntry(tab=-1, time=1.0, duration=0.5),
            ]
        )
        filename = "mocked_tabs.json"
        expected_path = Path(tab_mapper._json_outputs_path) / filename

        with patch.object(Path, "open", autospec=True) as mock_open:
            tab_mapper.save_tabs_to_json(tabs, filename)

        mock_open.assert_called_once_with(expected_path, "w")
