"""Analyze animation timing to detect static/animated segments for optimization."""

from typing import List, Tuple

from tab_converter.models import TabEntry


class AnimationAnalyzer:
    """Analyzes note timing to detect animated segment boundaries.

    Identifies regions where animation actually occurs (notes are playing) vs
    regions that are static (no notes). This enables optimization by rendering
    only the animated segment and reusing static frames.

    Example:
        >>> entries = [TabEntry(time=5.0, duration=1.0, ...)]  # First note at 5s
        >>> analyzer = AnimationAnalyzer(entries, buffer=0.5)
        >>> has_anim, start, end = analyzer.analyze_animation_range()
        >>> print(start, end)  # 4.5, 6.5 (with buffer)
    """

    def __init__(
        self,
        flat_entries: List[TabEntry],
        fps: int = 15,
        buffer: float = 0.5,
    ):
        """Initialize analyzer with note entries.

        Args:
            flat_entries: Flattened list of all TabEntry objects
            fps: Frames per second (used for calculations)
            buffer: Time buffer (seconds) to add before first and after last note
        """
        self._entries = flat_entries
        self._fps = fps
        self._buffer = buffer

    def analyze_animation_range(self) -> Tuple[bool, float, float]:
        """Analyze entries to find animated segment boundaries.

        Returns:
            Tuple of (has_animation, start_time, end_time):
            - has_animation (bool): True if there are any notes
            - start_time (float): Start of animated region (with buffer)
            - end_time (float): End of animated region (with buffer)

        Examples:
            >>> analyzer = AnimationAnalyzer([])
            >>> has_anim, start, end = analyzer.analyze_animation_range()
            >>> print((has_anim, start, end))
            (False, 0.0, 0.0)

            >>> entry = TabEntry(time=2.0, duration=1.0, ...)
            >>> analyzer = AnimationAnalyzer([entry], buffer=0.5)
            >>> has_anim, start, end = analyzer.analyze_animation_range()
            >>> print((has_anim, start, end))
            (True, 1.5, 3.5)
        """
        if not self._entries:
            return False, 0.0, 0.0

        # Find first and last note times
        first_note_time = min(entry.time for entry in self._entries)
        last_note_time = max(entry.time + entry.duration for entry in self._entries)

        # Apply buffer (clamp start to >= 0)
        start_time = max(0.0, first_note_time - self._buffer)
        end_time = last_note_time + self._buffer

        return True, start_time, end_time

    def get_animation_statistics(self, total_duration: float) -> dict:
        """Calculate animation statistics for logging/debugging.

        Args:
            total_duration: Total video duration in seconds

        Returns:
            Dictionary with animation stats:
            - total_duration (float): Total video length
            - animated_duration (float): Length of animated segment
            - static_start_duration (float): Length of static start
            - static_end_duration (float): Length of static end
            - speed_improvement_estimate (float): Percentage speedup estimate
            - has_animation (bool): Whether there are notes
            - notes_count (int): Number of notes in video
        """
        if not self._entries:
            return {
                "total_duration": total_duration,
                "animated_duration": 0.0,
                "static_start_duration": total_duration,
                "static_end_duration": 0.0,
                "speed_improvement_estimate": 0.0,
                "has_animation": False,
                "notes_count": 0,
            }

        has_animation, start_time, end_time = self.analyze_animation_range()

        animated_duration = end_time - start_time
        static_start = start_time
        static_end = max(0.0, total_duration - end_time)

        # Estimate speedup: rendering only animated segment + static frame reuse
        # Full render: total_duration frames
        # Optimized: animated_duration frames + 2 static frames (negligible)
        # Speedup = 1 - (animated_duration / total_duration)
        speedup_estimate = (
            (1.0 - animated_duration / total_duration) * 100
            if total_duration > 0
            else 0.0
        )

        return {
            "total_duration": total_duration,
            "animated_duration": animated_duration,
            "static_start_duration": static_start,
            "static_end_duration": static_end,
            "speed_improvement_estimate": speedup_estimate,
            "has_animation": has_animation,
            "notes_count": len(self._entries),
        }

    def should_optimize(
        self,
        total_duration: float,
        min_speedup_percent: float = 10.0,
    ) -> bool:
        """Determine if static optimization is worth applying.

        Args:
            total_duration: Total video duration
            min_speedup_percent: Minimum speedup threshold to enable optimization

        Returns:
            True if optimization would provide enough speedup to be worthwhile
        """
        if not self._entries:
            return False

        stats = self.get_animation_statistics(total_duration)
        return stats["speed_improvement_estimate"] >= min_speedup_percent
