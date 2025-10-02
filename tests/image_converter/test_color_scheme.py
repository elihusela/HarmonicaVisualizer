"""Tests for image_converter.color_scheme module."""

import pytest
from image_converter.color_scheme import ColorScheme
from image_converter.consts import IN_COLOR, OUT_COLOR
from tab_converter.models import TabEntry


class TestColorScheme:
    """Test ColorScheme class functionality."""

    def test_initialization(self, color_scheme):
        """Test ColorScheme initializes properly."""
        assert isinstance(color_scheme, ColorScheme)

    def test_blow_note_color(self, color_scheme):
        """Test blow notes (positive tabs) return OUT_COLOR."""
        blow_notes = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

        for tab_value in blow_notes:
            tab_entry = TabEntry(tab=tab_value, time=0.0, duration=0.5, confidence=0.8)
            color = color_scheme.get_color(tab_entry)
            assert color == OUT_COLOR, f"Blow note {tab_value} should be {OUT_COLOR}"

    def test_draw_note_color(self, color_scheme):
        """Test draw notes (negative tabs) return IN_COLOR."""
        draw_notes = [-1, -2, -3, -4, -5, -6, -7, -8, -9, -10]

        for tab_value in draw_notes:
            tab_entry = TabEntry(tab=tab_value, time=0.0, duration=0.5, confidence=0.8)
            color = color_scheme.get_color(tab_entry)
            assert color == IN_COLOR, f"Draw note {tab_value} should be {IN_COLOR}"

    def test_zero_tab_value(self, color_scheme):
        """Test tab value of 0 (edge case)."""
        tab_entry = TabEntry(tab=0, time=0.0, duration=0.5, confidence=0.8)
        color = color_scheme.get_color(tab_entry)
        # Tab 0 should be treated as draw note (not positive)
        assert color == IN_COLOR

    def test_extreme_tab_values(self, color_scheme):
        """Test extreme positive and negative tab values."""
        # Very high positive value
        high_blow = TabEntry(tab=100, time=0.0, duration=0.5, confidence=0.8)
        assert color_scheme.get_color(high_blow) == OUT_COLOR

        # Very low negative value
        low_draw = TabEntry(tab=-100, time=0.0, duration=0.5, confidence=0.8)
        assert color_scheme.get_color(low_draw) == IN_COLOR

    def test_color_consistency(self, color_scheme):
        """Test that same tab values always return same colors."""
        tab_entry = TabEntry(tab=5, time=0.0, duration=0.5, confidence=0.8)

        # Call multiple times
        color1 = color_scheme.get_color(tab_entry)
        color2 = color_scheme.get_color(tab_entry)
        color3 = color_scheme.get_color(tab_entry)

        assert color1 == color2 == color3

    def test_different_tab_entry_properties(self, color_scheme):
        """Test that only tab value affects color, not other properties."""
        tab_value = 3

        # Different time values
        entry1 = TabEntry(tab=tab_value, time=0.0, duration=0.5, confidence=0.8)
        entry2 = TabEntry(tab=tab_value, time=5.0, duration=0.5, confidence=0.8)

        # Different duration values
        entry3 = TabEntry(tab=tab_value, time=0.0, duration=2.0, confidence=0.8)

        # Different confidence values
        entry4 = TabEntry(tab=tab_value, time=0.0, duration=0.5, confidence=0.1)

        colors = [
            color_scheme.get_color(entry1),
            color_scheme.get_color(entry2),
            color_scheme.get_color(entry3),
            color_scheme.get_color(entry4),
        ]

        # All should be the same color since tab value is the same
        assert all(color == colors[0] for color in colors)

    def test_color_values_are_valid_hex(self, color_scheme):
        """Test that returned colors are valid hex color strings."""
        test_entries = [
            TabEntry(tab=1, time=0.0, duration=0.5, confidence=0.8),  # Blow
            TabEntry(tab=-1, time=0.0, duration=0.5, confidence=0.8),  # Draw
        ]

        for entry in test_entries:
            color = color_scheme.get_color(entry)

            # Should be string
            assert isinstance(color, str)

            # Should start with #
            assert color.startswith("#")

            # Should be 7 characters (#RRGGBB)
            assert len(color) == 7

            # Should be valid hex
            try:
                int(color[1:], 16)  # Convert hex to int
            except ValueError:
                pytest.fail(f"Invalid hex color: {color}")

    def test_blow_vs_draw_colors_different(self, color_scheme):
        """Test that blow and draw notes have different colors."""
        blow_entry = TabEntry(tab=1, time=0.0, duration=0.5, confidence=0.8)
        draw_entry = TabEntry(tab=-1, time=0.0, duration=0.5, confidence=0.8)

        blow_color = color_scheme.get_color(blow_entry)
        draw_color = color_scheme.get_color(draw_entry)

        assert blow_color != draw_color

    def test_color_scheme_constants_match(self, color_scheme):
        """Test that ColorScheme uses the same constants as imported."""
        blow_entry = TabEntry(tab=5, time=0.0, duration=0.5, confidence=0.8)
        draw_entry = TabEntry(tab=-5, time=0.0, duration=0.5, confidence=0.8)

        assert color_scheme.get_color(blow_entry) == OUT_COLOR
        assert color_scheme.get_color(draw_entry) == IN_COLOR

    @pytest.mark.parametrize(
        "tab_value,expected_color",
        [
            (1, OUT_COLOR),
            (2, OUT_COLOR),
            (10, OUT_COLOR),
            (-1, IN_COLOR),
            (-2, IN_COLOR),
            (-10, IN_COLOR),
        ],
    )
    def test_parametrized_color_mapping(self, color_scheme, tab_value, expected_color):
        """Test color mapping with parametrized values."""
        tab_entry = TabEntry(tab=tab_value, time=0.0, duration=0.5, confidence=0.8)
        actual_color = color_scheme.get_color(tab_entry)
        assert actual_color == expected_color


class TestColorSchemeIntegration:
    """Test ColorScheme integration scenarios."""

    def test_realistic_harmonica_sequence(self, color_scheme):
        """Test a realistic sequence of harmonica notes."""
        # Typical harmonica phrase: 4 -4 5 -5 6 -6 -7 7
        sequence = [
            TabEntry(tab=4, time=0.0, duration=0.5, confidence=0.8),
            TabEntry(tab=-4, time=0.5, duration=0.5, confidence=0.8),
            TabEntry(tab=5, time=1.0, duration=0.5, confidence=0.8),
            TabEntry(tab=-5, time=1.5, duration=0.5, confidence=0.8),
            TabEntry(tab=6, time=2.0, duration=0.5, confidence=0.8),
            TabEntry(tab=-6, time=2.5, duration=0.5, confidence=0.8),
            TabEntry(tab=-7, time=3.0, duration=0.5, confidence=0.8),
            TabEntry(tab=7, time=3.5, duration=0.5, confidence=0.8),
        ]

        expected_colors = [
            OUT_COLOR,
            IN_COLOR,
            OUT_COLOR,
            IN_COLOR,
            OUT_COLOR,
            IN_COLOR,
            IN_COLOR,
            OUT_COLOR,
        ]

        actual_colors = [color_scheme.get_color(entry) for entry in sequence]
        assert actual_colors == expected_colors

    def test_chord_color_handling(self, color_scheme):
        """Test color scheme with chord entries (multiple notes at same time)."""
        # Harmonica chord: blow 1-2-3 at same time
        chord_entries = [
            TabEntry(tab=1, time=1.0, duration=1.0, confidence=0.8),
            TabEntry(tab=2, time=1.0, duration=1.0, confidence=0.8),
            TabEntry(tab=3, time=1.0, duration=1.0, confidence=0.8),
        ]

        # All should be blow notes (OUT_COLOR)
        for entry in chord_entries:
            assert color_scheme.get_color(entry) == OUT_COLOR

        # Draw chord: -1, -2, -3 at same time
        draw_chord_entries = [
            TabEntry(tab=-1, time=2.0, duration=1.0, confidence=0.8),
            TabEntry(tab=-2, time=2.0, duration=1.0, confidence=0.8),
            TabEntry(tab=-3, time=2.0, duration=1.0, confidence=0.8),
        ]

        # All should be draw notes (IN_COLOR)
        for entry in draw_chord_entries:
            assert color_scheme.get_color(entry) == IN_COLOR
