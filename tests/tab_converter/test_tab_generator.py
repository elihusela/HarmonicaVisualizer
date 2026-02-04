"""Tests for tab_converter.tab_generator - Tab file generation from TabEntry objects."""

import pytest

from tab_converter.models import TabEntry, Tabs
from tab_converter.tab_generator import (
    TabGenerator,
    TabGeneratorConfig,
    TabGeneratorError,
)


class TestTabGeneratorConfig:
    """Test TabGeneratorConfig defaults and customization."""

    def test_default_config(self):
        """Test default configuration values."""
        config = TabGeneratorConfig()
        assert config.notes_per_line == 6
        assert config.notes_per_page == 24
        assert config.line_gap_threshold == 0.5
        assert config.page_gap_threshold == 2.0
        assert config.chord_time_tolerance == 0.05

    def test_custom_config(self):
        """Test custom configuration values."""
        config = TabGeneratorConfig(
            notes_per_line=4,
            notes_per_page=16,
            line_gap_threshold=1.0,
            page_gap_threshold=3.0,
            chord_time_tolerance=0.1,
        )
        assert config.notes_per_line == 4
        assert config.notes_per_page == 16


class TestTabGeneratorInit:
    """Test TabGenerator initialization."""

    def test_default_init(self):
        """Test initialization with default config."""
        gen = TabGenerator()
        assert gen.config.notes_per_line == 6

    def test_custom_init(self):
        """Test initialization with custom config."""
        config = TabGeneratorConfig(notes_per_line=8)
        gen = TabGenerator(config)
        assert gen.config.notes_per_line == 8


class TestTabGeneratorGenerate:
    """Test TabGenerator.generate() method."""

    def test_generate_empty_tabs_raises_error(self):
        """Test that empty tabs raises error."""
        gen = TabGenerator()
        with pytest.raises(TabGeneratorError, match="No tabs to generate"):
            gen.generate(Tabs([]))

    def test_generate_single_note(self):
        """Test generating a single note."""
        gen = TabGenerator()
        tabs = Tabs([TabEntry(tab=6, time=0.0, duration=0.5, confidence=1.0)])
        result = gen.generate(tabs)

        assert "page 1:" in result
        assert "6" in result

    def test_generate_multiple_notes(self):
        """Test generating multiple notes."""
        gen = TabGenerator()
        tabs = Tabs(
            [
                TabEntry(tab=6, time=0.0, duration=0.5, confidence=1.0),
                TabEntry(tab=-5, time=0.6, duration=0.5, confidence=1.0),
                TabEntry(tab=4, time=1.2, duration=0.5, confidence=1.0),
            ]
        )
        result = gen.generate(tabs)

        assert "page 1:" in result
        assert "6" in result
        assert "-5" in result
        assert "4" in result

    def test_generate_draw_notes(self):
        """Test generating draw notes (negative)."""
        gen = TabGenerator()
        tabs = Tabs(
            [
                TabEntry(tab=-4, time=0.0, duration=0.5, confidence=1.0),
                TabEntry(tab=-5, time=0.6, duration=0.5, confidence=1.0),
            ]
        )
        result = gen.generate(tabs)

        assert "-4" in result
        assert "-5" in result

    def test_generate_with_bend(self):
        """Test generating note with bend notation."""
        gen = TabGenerator()
        tabs = Tabs(
            [
                TabEntry(
                    tab=-6,
                    time=0.0,
                    duration=0.5,
                    confidence=1.0,
                    is_bend=True,
                    bend_notation="'",
                ),
            ]
        )
        result = gen.generate(tabs)

        assert "-6'" in result


class TestChordDetection:
    """Test chord detection (simultaneous notes)."""

    def test_simultaneous_notes_grouped_as_chord(self):
        """Test that simultaneous notes are grouped as a chord."""
        gen = TabGenerator()
        tabs = Tabs(
            [
                TabEntry(tab=5, time=0.0, duration=0.5, confidence=1.0),
                TabEntry(tab=6, time=0.0, duration=0.5, confidence=1.0),
            ]
        )
        result = gen.generate(tabs)

        # Blow chord should be "56"
        assert "56" in result

    def test_draw_chord(self):
        """Test draw chord formatting."""
        gen = TabGenerator()
        tabs = Tabs(
            [
                TabEntry(tab=-4, time=0.0, duration=0.5, confidence=1.0),
                TabEntry(tab=-5, time=0.0, duration=0.5, confidence=1.0),
            ]
        )
        result = gen.generate(tabs)

        # Draw chord should be "-4-5"
        assert "-4-5" in result

    def test_notes_just_outside_tolerance_not_grouped(self):
        """Test that notes just outside tolerance are separate."""
        config = TabGeneratorConfig(chord_time_tolerance=0.05)
        gen = TabGenerator(config)
        tabs = Tabs(
            [
                TabEntry(tab=5, time=0.0, duration=0.5, confidence=1.0),
                TabEntry(tab=6, time=0.1, duration=0.5, confidence=1.0),  # 0.1s apart
            ]
        )
        result = gen.generate(tabs)

        # Should be separate notes, not a chord
        assert "5 6" in result or "5\n" in result


class TestLineBreaks:
    """Test line break detection."""

    def test_line_break_at_max_notes(self):
        """Test line break when max notes per line reached."""
        config = TabGeneratorConfig(notes_per_line=3)
        gen = TabGenerator(config)
        tabs = Tabs(
            [
                TabEntry(tab=i, time=i * 0.1, duration=0.05, confidence=1.0)
                for i in range(1, 7)  # 6 notes
            ]
        )
        result = gen.generate(tabs)

        # Should have at least 2 lines
        lines = [ln for ln in result.split("\n") if ln and not ln.startswith("page")]
        assert len(lines) >= 2


class TestPageBreaks:
    """Test page break detection."""

    def test_page_break_at_long_gap(self):
        """Test page break at long silence gap."""
        config = TabGeneratorConfig(page_gap_threshold=1.0)
        gen = TabGenerator(config)
        tabs = Tabs(
            [
                TabEntry(tab=6, time=0.0, duration=0.5, confidence=1.0),
                TabEntry(tab=5, time=2.0, duration=0.5, confidence=1.0),  # 1.5s gap
            ]
        )
        result = gen.generate(tabs)

        assert "page 1:" in result
        assert "page 2:" in result

    def test_page_break_at_max_notes(self):
        """Test page break when max notes per page reached."""
        config = TabGeneratorConfig(notes_per_page=4, notes_per_line=2)
        gen = TabGenerator(config)
        tabs = Tabs(
            [
                TabEntry(tab=i, time=i * 0.1, duration=0.05, confidence=1.0)
                for i in range(1, 9)  # 8 notes = 2 pages
            ]
        )
        result = gen.generate(tabs)

        assert "page 1:" in result
        assert "page 2:" in result


class TestChordFormatting:
    """Test chord string formatting."""

    def test_single_blow_note(self):
        """Test single blow note formatting."""
        gen = TabGenerator()
        tabs = Tabs([TabEntry(tab=6, time=0.0, duration=0.5, confidence=1.0)])
        result = gen.generate(tabs)
        assert "6" in result

    def test_single_draw_note(self):
        """Test single draw note formatting."""
        gen = TabGenerator()
        tabs = Tabs([TabEntry(tab=-5, time=0.0, duration=0.5, confidence=1.0)])
        result = gen.generate(tabs)
        assert "-5" in result

    def test_two_note_blow_chord(self):
        """Test two-note blow chord formatting."""
        gen = TabGenerator()
        tabs = Tabs(
            [
                TabEntry(tab=4, time=0.0, duration=0.5, confidence=1.0),
                TabEntry(tab=5, time=0.0, duration=0.5, confidence=1.0),
            ]
        )
        result = gen.generate(tabs)
        assert "45" in result

    def test_three_note_blow_chord(self):
        """Test three-note blow chord formatting."""
        gen = TabGenerator()
        tabs = Tabs(
            [
                TabEntry(tab=3, time=0.0, duration=0.5, confidence=1.0),
                TabEntry(tab=4, time=0.0, duration=0.5, confidence=1.0),
                TabEntry(tab=5, time=0.0, duration=0.5, confidence=1.0),
            ]
        )
        result = gen.generate(tabs)
        assert "345" in result

    def test_two_note_draw_chord(self):
        """Test two-note draw chord formatting."""
        gen = TabGenerator()
        tabs = Tabs(
            [
                TabEntry(tab=-5, time=0.0, duration=0.5, confidence=1.0),
                TabEntry(tab=-6, time=0.0, duration=0.5, confidence=1.0),
            ]
        )
        result = gen.generate(tabs)
        assert "-5-6" in result
