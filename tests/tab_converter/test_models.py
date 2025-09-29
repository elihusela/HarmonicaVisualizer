"""Tests for tab_converter.models data structures."""

import pytest

from tab_converter.models import TabEntry, Tabs, NoteEvent


class TestTabEntry:
    """Test TabEntry dataclass with confidence parameter."""

    def test_tab_entry_creation_basic(self, sample_tab_entry):
        """Test basic TabEntry creation with all parameters."""
        assert sample_tab_entry.tab == 3
        assert sample_tab_entry.time == 1.5
        assert sample_tab_entry.duration == 0.8
        assert sample_tab_entry.confidence == 0.9

    def test_tab_entry_creation_negative_tab(self, sample_tab_entry_negative):
        """Test TabEntry with negative tab number (draw note)."""
        assert sample_tab_entry_negative.tab == -4
        assert sample_tab_entry_negative.time == 2.0
        assert sample_tab_entry_negative.duration == 1.2
        assert sample_tab_entry_negative.confidence == 0.7

    def test_tab_entry_confidence_parameter_required(self):
        """Test that confidence parameter is required (recent fix)."""
        # This should work with confidence parameter
        entry = TabEntry(tab=1, time=0.0, duration=0.5, confidence=0.8)
        assert entry.confidence == 0.8

        # Missing confidence should raise TypeError
        with pytest.raises(TypeError):
            TabEntry(tab=1, time=0.0, duration=0.5)  # Missing confidence

    def test_tab_entry_edge_cases(self):
        """Test TabEntry with edge case values."""
        # Zero values
        entry_zero = TabEntry(tab=0, time=0.0, duration=0.0, confidence=0.0)
        assert entry_zero.tab == 0
        assert entry_zero.time == 0.0
        assert entry_zero.duration == 0.0
        assert entry_zero.confidence == 0.0

        # High confidence
        entry_high_conf = TabEntry(tab=10, time=5.5, duration=2.0, confidence=1.0)
        assert entry_high_conf.confidence == 1.0

        # Negative time (edge case)
        entry_neg_time = TabEntry(tab=2, time=-1.0, duration=0.5, confidence=0.5)
        assert entry_neg_time.time == -1.0

    def test_tab_entry_equality(self):
        """Test TabEntry equality comparison."""
        entry1 = TabEntry(tab=3, time=1.5, duration=0.8, confidence=0.9)
        entry2 = TabEntry(tab=3, time=1.5, duration=0.8, confidence=0.9)
        entry3 = TabEntry(tab=4, time=1.5, duration=0.8, confidence=0.9)

        assert entry1 == entry2
        assert entry1 != entry3

    def test_tab_entry_dataclass_fields(self):
        """Test that TabEntry has expected dataclass behavior."""
        entry = TabEntry(tab=1, time=2.0, duration=1.0, confidence=0.8)

        # Test field access
        assert hasattr(entry, "tab")
        assert hasattr(entry, "time")
        assert hasattr(entry, "duration")
        assert hasattr(entry, "confidence")

        # Test repr
        repr_str = repr(entry)
        assert "TabEntry" in repr_str
        assert "tab=1" in repr_str
        assert "confidence=0.8" in repr_str


class TestTabs:
    """Test Tabs container class."""

    def test_tabs_creation(self, sample_tabs, sample_tab_entries):
        """Test Tabs container creation."""
        assert isinstance(sample_tabs.tabs, list)
        assert len(sample_tabs.tabs) == 5
        assert sample_tabs.tabs == sample_tab_entries

    def test_tabs_empty(self, empty_tabs):
        """Test empty Tabs container."""
        assert isinstance(empty_tabs.tabs, list)
        assert len(empty_tabs.tabs) == 0

    def test_tabs_single_entry(self, sample_tab_entry):
        """Test Tabs with single entry."""
        single_tabs = Tabs(tabs=[sample_tab_entry])
        assert len(single_tabs.tabs) == 1
        assert single_tabs.tabs[0] == sample_tab_entry

    def test_tabs_dataclass_behavior(self, sample_tab_entries):
        """Test Tabs dataclass behavior."""
        tabs = Tabs(tabs=sample_tab_entries)

        # Test equality
        tabs2 = Tabs(tabs=sample_tab_entries)
        assert tabs == tabs2

        # Test field access
        assert hasattr(tabs, "tabs")

        # Test repr
        repr_str = repr(tabs)
        assert "Tabs" in repr_str


class TestNoteEvent:
    """Test NoteEvent NamedTuple."""

    def test_note_event_creation(self, sample_note_event):
        """Test basic NoteEvent creation."""
        assert sample_note_event.start_time == 1.0
        assert sample_note_event.end_time == 1.8
        assert sample_note_event.pitch == 60
        assert sample_note_event.confidence == 0.85
        assert sample_note_event.activation == [0.1, 0.3, 0.8, 0.6, 0.2]

    def test_note_event_namedtuple_behavior(self):
        """Test NoteEvent NamedTuple specific behavior."""
        event = NoteEvent(
            start_time=0.5,
            end_time=1.0,
            pitch=64,
            confidence=0.9,
            activation=[0.2, 0.8],
        )

        # Test field access by name
        assert event.start_time == 0.5
        assert event.end_time == 1.0
        assert event.pitch == 64
        assert event.confidence == 0.9
        assert event.activation == [0.2, 0.8]

        # Test field access by index
        assert event[0] == 0.5  # start_time
        assert event[1] == 1.0  # end_time
        assert event[2] == 64  # pitch
        assert event[3] == 0.9  # confidence
        assert event[4] == [0.2, 0.8]  # activation

        # Test immutability (NamedTuple characteristic)
        with pytest.raises(AttributeError):
            event.start_time = 2.0

    def test_note_event_equality(self):
        """Test NoteEvent equality."""
        event1 = NoteEvent(
            start_time=1.0, end_time=2.0, pitch=60, confidence=0.8, activation=[0.5]
        )
        event2 = NoteEvent(
            start_time=1.0, end_time=2.0, pitch=60, confidence=0.8, activation=[0.5]
        )
        event3 = NoteEvent(
            start_time=1.0, end_time=2.0, pitch=61, confidence=0.8, activation=[0.5]
        )

        assert event1 == event2
        assert event1 != event3

    def test_note_event_duration_calculation(self, sample_note_events):
        """Test derived duration calculation."""
        for event in sample_note_events:
            duration = event.end_time - event.start_time
            assert duration > 0, f"Event should have positive duration: {event}"

    def test_note_event_midi_pitch_range(self, sample_note_events):
        """Test MIDI pitch values are in valid range."""
        for event in sample_note_events:
            assert 0 <= event.pitch <= 127, f"MIDI pitch out of range: {event.pitch}"

    def test_note_event_confidence_range(self, sample_note_events):
        """Test confidence values are in expected range."""
        for event in sample_note_events:
            assert (
                0.0 <= event.confidence <= 1.0
            ), f"Confidence out of range: {event.confidence}"

    def test_note_event_activation_list(self, sample_note_event):
        """Test activation is a list of floats."""
        assert isinstance(sample_note_event.activation, list)
        assert len(sample_note_event.activation) > 0
        for activation_val in sample_note_event.activation:
            assert isinstance(activation_val, (int, float))
