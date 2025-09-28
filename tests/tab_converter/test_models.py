"""
Tests for tab_converter.models module.

Tests the core data structures: TabEntry, Tabs, and NoteEvent.
"""

import pytest
from tab_converter.models import TabEntry, Tabs, NoteEvent


class TestTabEntry:
    """Test TabEntry dataclass functionality."""

    def test_tab_entry_creation_with_all_parameters(self):
        """Test TabEntry creation with all required parameters."""
        entry = TabEntry(tab=5, time=1.0, duration=0.5, confidence=0.8)

        assert entry.tab == 5
        assert entry.time == 1.0
        assert entry.duration == 0.5
        assert entry.confidence == 0.8

    def test_tab_entry_negative_tab_value(self):
        """Test TabEntry with negative tab value (draw notes)."""
        entry = TabEntry(tab=-4, time=2.0, duration=0.3, confidence=0.9)

        assert entry.tab == -4
        assert entry.time == 2.0
        assert entry.duration == 0.3
        assert entry.confidence == 0.9

    def test_tab_entry_zero_values(self):
        """Test TabEntry with zero values."""
        entry = TabEntry(tab=0, time=0.0, duration=0.0, confidence=0.0)

        assert entry.tab == 0
        assert entry.time == 0.0
        assert entry.duration == 0.0
        assert entry.confidence == 0.0

    def test_tab_entry_high_confidence(self):
        """Test TabEntry with maximum confidence."""
        entry = TabEntry(tab=7, time=1.5, duration=1.0, confidence=1.0)

        assert entry.confidence == 1.0

    def test_tab_entry_equality(self):
        """Test TabEntry equality comparison."""
        entry1 = TabEntry(tab=5, time=1.0, duration=0.5, confidence=0.8)
        entry2 = TabEntry(tab=5, time=1.0, duration=0.5, confidence=0.8)
        entry3 = TabEntry(tab=6, time=1.0, duration=0.5, confidence=0.8)

        assert entry1 == entry2
        assert entry1 != entry3

    def test_tab_entry_string_representation(self):
        """Test TabEntry string representation."""
        entry = TabEntry(tab=5, time=1.0, duration=0.5, confidence=0.8)
        str_repr = str(entry)

        assert "TabEntry" in str_repr
        assert "tab=5" in str_repr
        assert "time=1.0" in str_repr
        assert "duration=0.5" in str_repr
        assert "confidence=0.8" in str_repr


class TestTabs:
    """Test Tabs collection functionality."""

    def test_tabs_creation_empty(self):
        """Test Tabs creation with empty list."""
        tabs = Tabs(tabs=[])

        assert tabs.tabs == []
        assert len(tabs.tabs) == 0

    def test_tabs_creation_with_entries(self):
        """Test Tabs creation with TabEntry list."""
        entry1 = TabEntry(tab=5, time=1.0, duration=0.5, confidence=0.8)
        entry2 = TabEntry(tab=-4, time=2.0, duration=0.3, confidence=0.9)
        tabs = Tabs(tabs=[entry1, entry2])

        assert len(tabs.tabs) == 2
        assert tabs.tabs[0] == entry1
        assert tabs.tabs[1] == entry2

    def test_tabs_single_entry(self):
        """Test Tabs with single entry."""
        entry = TabEntry(tab=3, time=0.5, duration=0.25, confidence=0.7)
        tabs = Tabs(tabs=[entry])

        assert len(tabs.tabs) == 1
        assert tabs.tabs[0] == entry

    def test_tabs_equality(self):
        """Test Tabs equality comparison."""
        entry1 = TabEntry(tab=5, time=1.0, duration=0.5, confidence=0.8)
        entry2 = TabEntry(tab=-4, time=2.0, duration=0.3, confidence=0.9)

        tabs1 = Tabs(tabs=[entry1, entry2])
        tabs2 = Tabs(tabs=[entry1, entry2])
        tabs3 = Tabs(tabs=[entry1])

        assert tabs1 == tabs2
        assert tabs1 != tabs3

    def test_tabs_modification(self):
        """Test Tabs list modification."""
        entry1 = TabEntry(tab=5, time=1.0, duration=0.5, confidence=0.8)
        tabs = Tabs(tabs=[entry1])

        # Add another entry
        entry2 = TabEntry(tab=-4, time=2.0, duration=0.3, confidence=0.9)
        tabs.tabs.append(entry2)

        assert len(tabs.tabs) == 2
        assert tabs.tabs[1] == entry2


class TestNoteEvent:
    """Test NoteEvent namedtuple functionality."""

    def test_note_event_creation(self):
        """Test NoteEvent creation with all parameters."""
        activation = [0.1, 0.8, 0.9, 0.7, 0.2]
        note = NoteEvent(
            start_time=1.0,
            end_time=2.5,
            pitch=60,
            confidence=0.85,
            activation=activation
        )

        assert note.start_time == 1.0
        assert note.end_time == 2.5
        assert note.pitch == 60
        assert note.confidence == 0.85
        assert note.activation == activation

    def test_note_event_duration_calculation(self):
        """Test calculating duration from NoteEvent."""
        note = NoteEvent(
            start_time=1.0,
            end_time=3.5,
            pitch=72,
            confidence=0.9,
            activation=[]
        )

        duration = note.end_time - note.start_time
        assert duration == 2.5

    def test_note_event_immutability(self):
        """Test NoteEvent immutability (namedtuple property)."""
        note = NoteEvent(
            start_time=1.0,
            end_time=2.0,
            pitch=60,
            confidence=0.8,
            activation=[0.5]
        )

        # Should not be able to modify fields
        with pytest.raises(AttributeError):
            note.start_time = 2.0

    def test_note_event_equality(self):
        """Test NoteEvent equality comparison."""
        activation = [0.1, 0.8, 0.9]

        note1 = NoteEvent(
            start_time=1.0,
            end_time=2.0,
            pitch=60,
            confidence=0.8,
            activation=activation
        )

        note2 = NoteEvent(
            start_time=1.0,
            end_time=2.0,
            pitch=60,
            confidence=0.8,
            activation=activation
        )

        note3 = NoteEvent(
            start_time=1.0,
            end_time=2.0,
            pitch=61,  # Different pitch
            confidence=0.8,
            activation=activation
        )

        assert note1 == note2
        assert note1 != note3

    def test_note_event_field_access(self):
        """Test NoteEvent field access by name and index."""
        note = NoteEvent(
            start_time=1.5,
            end_time=3.0,
            pitch=67,
            confidence=0.75,
            activation=[0.2, 0.9, 0.6]
        )

        # Access by name
        assert note.start_time == 1.5
        assert note.pitch == 67

        # Access by index (namedtuple feature)
        assert note[0] == 1.5  # start_time
        assert note[2] == 67   # pitch

    def test_note_event_with_empty_activation(self):
        """Test NoteEvent with empty activation list."""
        note = NoteEvent(
            start_time=0.0,
            end_time=1.0,
            pitch=48,
            confidence=0.6,
            activation=[]
        )

        assert note.activation == []
        assert len(note.activation) == 0

    def test_note_event_extreme_values(self):
        """Test NoteEvent with extreme values."""
        note = NoteEvent(
            start_time=0.0,
            end_time=1000.0,
            pitch=0,
            confidence=1.0,
            activation=[1.0] * 100
        )

        assert note.start_time == 0.0
        assert note.end_time == 1000.0
        assert note.pitch == 0
        assert note.confidence == 1.0
        assert len(note.activation) == 100