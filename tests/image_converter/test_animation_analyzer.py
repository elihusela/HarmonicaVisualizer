"""Tests for AnimationAnalyzer - detects animated segment boundaries."""

import pytest
from tab_converter.models import TabEntry
from image_converter.animation_analyzer import AnimationAnalyzer


class TestAnimationAnalyzerInitialization:
    """Test AnimationAnalyzer initialization."""

    def test_init_with_entries(self):
        """Test initialization with note entries."""
        entries = [TabEntry(time=1.0, duration=0.5, tab=1, confidence=1.0)]
        analyzer = AnimationAnalyzer(entries, fps=15)
        assert analyzer._entries == entries
        assert analyzer._fps == 15
        assert analyzer._buffer == 0.5

    def test_init_empty_entries(self):
        """Test initialization with empty list."""
        analyzer = AnimationAnalyzer([], fps=20, buffer=0.3)
        assert analyzer._entries == []
        assert analyzer._fps == 20
        assert analyzer._buffer == 0.3

    def test_init_custom_buffer(self):
        """Test custom buffer parameter."""
        entries = [TabEntry(time=2.0, duration=1.0, tab=1, confidence=1.0)]
        analyzer = AnimationAnalyzer(entries, buffer=1.0)
        assert analyzer._buffer == 1.0


class TestAnimationAnalyzerRangeDetection:
    """Test detection of animated segment boundaries."""

    def test_single_note(self):
        """Test with single note."""
        entry = TabEntry(time=5.0, duration=1.0, tab=1, confidence=1.0)
        analyzer = AnimationAnalyzer([entry], buffer=0.5)

        has_anim, start, end = analyzer.analyze_animation_range()

        assert has_anim is True
        assert start == 4.5  # 5.0 - 0.5 buffer
        assert end == 6.5  # (5.0 + 1.0) + 0.5 buffer

    def test_multiple_notes(self):
        """Test with multiple notes."""
        entries = [
            TabEntry(time=1.0, duration=0.5, tab=1, confidence=1.0),
            TabEntry(time=3.0, duration=0.5, tab=2, confidence=1.0),
            TabEntry(time=5.0, duration=0.5, tab=3, confidence=1.0),
        ]
        analyzer = AnimationAnalyzer(entries, buffer=0.5)

        has_anim, start, end = analyzer.analyze_animation_range()

        assert has_anim is True
        assert start == 0.5  # 1.0 - 0.5 buffer
        assert end == 6.0  # (5.0 + 0.5) + 0.5 buffer

    def test_no_notes(self):
        """Test with no notes (all static)."""
        analyzer = AnimationAnalyzer([], buffer=0.5)

        has_anim, start, end = analyzer.analyze_animation_range()

        assert has_anim is False
        assert start == 0.0
        assert end == 0.0

    def test_buffer_clamped_to_zero(self):
        """Test that start time is clamped to >= 0."""
        entry = TabEntry(time=0.2, duration=1.0, tab=1, confidence=1.0)
        analyzer = AnimationAnalyzer([entry], buffer=1.0)

        has_anim, start, end = analyzer.analyze_animation_range()

        assert has_anim is True
        assert start == 0.0  # Clamped from -0.8
        assert end == 2.2  # 0.2 + 1.0 + 1.0

    def test_no_buffer(self):
        """Test with zero buffer."""
        entry = TabEntry(time=2.0, duration=1.0, tab=1, confidence=1.0)
        analyzer = AnimationAnalyzer([entry], buffer=0.0)

        has_anim, start, end = analyzer.analyze_animation_range()

        assert has_anim is True
        assert start == 2.0
        assert end == 3.0

    def test_overlapping_notes(self):
        """Test with overlapping notes."""
        entries = [
            TabEntry(time=1.0, duration=2.0, tab=1, confidence=1.0),
            TabEntry(time=2.0, duration=2.0, tab=2, confidence=1.0),
        ]
        analyzer = AnimationAnalyzer(entries, buffer=0.2)

        has_anim, start, end = analyzer.analyze_animation_range()

        assert has_anim is True
        assert start == 0.8  # 1.0 - 0.2
        assert end == 4.2  # (2.0 + 2.0) + 0.2


class TestAnimationAnalyzerStatistics:
    """Test animation statistics calculation."""

    def test_statistics_with_sparse_notes(self):
        """Test statistics for video with sparse notes."""
        entries = [
            TabEntry(time=2.0, duration=0.5, tab=1, confidence=1.0),
            TabEntry(time=8.0, duration=0.5, tab=2, confidence=1.0),
        ]
        analyzer = AnimationAnalyzer(entries, buffer=1.0)

        stats = analyzer.get_animation_statistics(total_duration=10.0)

        assert stats["has_animation"] is True
        assert stats["total_duration"] == 10.0
        assert stats["notes_count"] == 2
        # First note at 2.0, last note ends at 8.5, with buffer 1.0: 1.0 to 9.5
        assert stats["animated_duration"] == 8.5
        assert stats["static_start_duration"] == 1.0  # 0 to 1.0
        assert stats["static_end_duration"] == 0.5  # 9.5 to 10.0
        # Speedup estimate: (1 - 8.5/10) * 100 = 15%
        assert stats["speed_improvement_estimate"] == pytest.approx(15.0)

    def test_statistics_all_static(self):
        """Test statistics for all-static video."""
        analyzer = AnimationAnalyzer([], buffer=0.5)

        stats = analyzer.get_animation_statistics(total_duration=5.0)

        assert stats["has_animation"] is False
        assert stats["total_duration"] == 5.0
        assert stats["animated_duration"] == 0.0
        assert stats["static_start_duration"] == 5.0
        assert stats["static_end_duration"] == 0.0
        assert stats["speed_improvement_estimate"] == 0.0
        assert stats["notes_count"] == 0

    def test_statistics_dense_notes(self):
        """Test statistics for video with dense notes."""
        entries = [
            TabEntry(time=float(i) * 0.5, duration=0.3, tab=1, confidence=1.0)
            for i in range(10)
        ]
        analyzer = AnimationAnalyzer(entries, buffer=0.2)

        stats = analyzer.get_animation_statistics(total_duration=5.0)

        assert stats["has_animation"] is True
        assert stats["notes_count"] == 10
        # Most of video is animated, small speedup
        assert 0.0 <= stats["speed_improvement_estimate"] < 30.0

    def test_statistics_notes_at_boundaries(self):
        """Test statistics with notes at start and end."""
        entries = [
            TabEntry(time=0.0, duration=1.0, tab=1, confidence=1.0),
            TabEntry(time=9.0, duration=1.0, tab=2, confidence=1.0),
        ]
        analyzer = AnimationAnalyzer(entries, buffer=0.5)

        stats = analyzer.get_animation_statistics(total_duration=10.0)

        # Start: 0.0 - 0.5 = -0.5 (clamped to 0.0)
        # End: 10.0 + 0.5 = 10.5 (beyond total duration)
        assert stats["animated_duration"] == 10.5
        assert stats["static_start_duration"] == 0.0
        assert stats["static_end_duration"] == pytest.approx(0.0)  # 10.5 > 10.0


class TestAnimationAnalyzerOptimizationDecision:
    """Test should_optimize decision logic."""

    def test_optimize_high_speedup(self):
        """Test optimization decision with high speedup potential."""
        entry = TabEntry(time=8.0, duration=1.0, tab=1, confidence=1.0)
        analyzer = AnimationAnalyzer([entry], buffer=0.5)

        # 80% of video is static, should optimize
        assert analyzer.should_optimize(total_duration=10.0, min_speedup_percent=10.0)

    def test_dont_optimize_low_speedup(self):
        """Test optimization decision with low speedup potential."""
        entries = [
            TabEntry(time=float(i) * 0.1, duration=0.08, tab=1, confidence=1.0)
            for i in range(100)
        ]
        analyzer = AnimationAnalyzer(entries, buffer=0.1)

        # Almost entire video has notes, skip optimization
        assert not analyzer.should_optimize(
            total_duration=10.0, min_speedup_percent=20.0
        )

    def test_dont_optimize_no_notes(self):
        """Test optimization decision with no notes."""
        analyzer = AnimationAnalyzer([], buffer=0.5)

        # No notes, can't optimize
        assert not analyzer.should_optimize(total_duration=10.0)

    def test_optimize_threshold_boundary(self):
        """Test optimization at threshold boundary."""
        entry = TabEntry(time=5.0, duration=1.0, tab=1, confidence=1.0)
        analyzer = AnimationAnalyzer([entry], buffer=0.5)

        # With single note at 5.0±0.5 duration, animated region is 2.0s of 10s
        # Speedup: (1 - 2/10) * 100 = 80%
        # Should optimize with 10% threshold
        assert analyzer.should_optimize(total_duration=10.0, min_speedup_percent=10.0)

        # Should optimize with 50% threshold (80% > 50%)
        assert analyzer.should_optimize(total_duration=10.0, min_speedup_percent=50.0)

        # Should not optimize with 90% threshold (80% < 90%)
        assert not analyzer.should_optimize(
            total_duration=10.0, min_speedup_percent=90.0
        )


class TestAnimationAnalyzerEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_duration_video(self):
        """Test with zero-duration video."""
        entry = TabEntry(time=0.0, duration=1.0, tab=1, confidence=1.0)
        analyzer = AnimationAnalyzer([entry], buffer=0.5)

        stats = analyzer.get_animation_statistics(total_duration=0.0)

        assert stats["speed_improvement_estimate"] == 0.0

    def test_very_short_buffer(self):
        """Test with very small buffer."""
        entry = TabEntry(time=5.0, duration=1.0, tab=1, confidence=1.0)
        analyzer = AnimationAnalyzer([entry], buffer=0.01)

        has_anim, start, end = analyzer.analyze_animation_range()

        assert start == pytest.approx(4.99)
        assert end == pytest.approx(6.01)

    def test_many_notes(self):
        """Test with many notes."""
        entries = [
            TabEntry(time=float(i) / 100.0, duration=0.005, tab=i % 10, confidence=1.0)
            for i in range(1000)
        ]
        analyzer = AnimationAnalyzer(entries, buffer=0.1)

        has_anim, start, end = analyzer.analyze_animation_range()

        assert has_anim is True
        assert start == pytest.approx(0.0)  # Clamped from -0.1
        assert end > 10.0

    def test_identical_start_end_times(self):
        """Test with note at exact start time."""
        entry = TabEntry(time=0.0, duration=0.0, tab=1, confidence=1.0)
        analyzer = AnimationAnalyzer([entry], buffer=0.5)

        has_anim, start, end = analyzer.analyze_animation_range()

        assert has_anim is True
        assert start == 0.0  # Clamped
        assert end == 0.5
