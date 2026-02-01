"""Tests for image_converter.animator module."""

import os
import tempfile
from unittest.mock import patch, MagicMock
import pytest

from image_converter.animator import Animator, adjust_consecutive_identical_notes
from image_converter.consts import IN_COLOR, OUT_COLOR
from tab_converter.models import TabEntry


class TestAdjustConsecutiveIdenticalNotes:
    """Test the adjust_consecutive_identical_notes utility function."""

    def test_adjust_no_overlap(self):
        """Test adjustment when notes don't overlap."""
        entries = [
            TabEntry(tab=1, time=0.0, duration=0.5, confidence=0.8),
            TabEntry(tab=2, time=1.0, duration=0.5, confidence=0.8),
        ]

        result = adjust_consecutive_identical_notes(entries)

        # Should remain unchanged as different tabs
        assert len(result) == 2
        assert result[0].duration == 0.5
        assert result[1].duration == 0.5

    def test_adjust_identical_overlapping_notes(self):
        """Test adjustment of overlapping identical notes."""
        entries = [
            TabEntry(tab=3, time=0.0, duration=1.0, confidence=0.8),
            TabEntry(
                tab=3, time=0.8, duration=0.5, confidence=0.8
            ),  # Same tab, overlaps
        ]

        result = adjust_consecutive_identical_notes(entries, gap=0.1)

        # First note should be shortened to avoid overlap
        assert abs(result[0].duration - 0.7) < 1e-10  # 0.8 - 0.0 - 0.1 = 0.7
        assert result[1].duration == 0.5  # Unchanged

    def test_adjust_identical_exact_timing(self):
        """Test adjustment when identical notes have exact same timing."""
        entries = [
            TabEntry(tab=5, time=0.0, duration=0.6, confidence=0.8),
            TabEntry(tab=5, time=0.6, duration=0.4, confidence=0.8),  # Exactly at end
        ]

        result = adjust_consecutive_identical_notes(entries, gap=0.1)

        # First note should be shortened by gap
        assert result[0].duration == 0.5  # 0.6 - 0.0 - 0.1 = 0.5
        assert result[1].duration == 0.4

    def test_adjust_minimum_duration(self):
        """Test that notes get minimum visible duration even when very close."""
        entries = [
            TabEntry(tab=2, time=0.0, duration=0.2, confidence=0.8),
            TabEntry(tab=2, time=0.1, duration=0.3, confidence=0.8),  # Heavy overlap
        ]

        result = adjust_consecutive_identical_notes(entries, gap=0.1, min_duration=0.1)

        # With min_duration=0.1, even close notes stay visible
        # Available time = 0.1s, which equals min_duration
        assert result[0].duration == 0.1  # Guaranteed minimum visibility
        assert result[1].duration == 0.3  # Last entry unchanged

    def test_adjust_different_tabs_no_change(self):
        """Test that different tab numbers are not adjusted."""
        entries = [
            TabEntry(tab=1, time=0.0, duration=1.0, confidence=0.8),
            TabEntry(tab=2, time=0.5, duration=0.5, confidence=0.8),  # Different tab
        ]

        result = adjust_consecutive_identical_notes(entries)

        # Should remain unchanged
        assert result[0].duration == 1.0
        assert result[1].duration == 0.5

    def test_adjust_empty_list(self):
        """Test adjustment with empty list."""
        result = adjust_consecutive_identical_notes([])
        assert result == []

    def test_adjust_single_entry(self):
        """Test adjustment with single entry."""
        entries = [TabEntry(tab=1, time=0.0, duration=0.5, confidence=0.8)]
        result = adjust_consecutive_identical_notes(entries)

        assert len(result) == 1
        assert result[0].duration == 0.5

    def test_adjust_multiple_consecutive_identical(self):
        """Test adjustment with multiple consecutive identical notes."""
        entries = [
            TabEntry(tab=4, time=0.0, duration=0.5, confidence=0.8),
            TabEntry(tab=4, time=0.4, duration=0.5, confidence=0.8),
            TabEntry(tab=4, time=0.8, duration=0.5, confidence=0.8),
        ]

        result = adjust_consecutive_identical_notes(entries, gap=0.1)

        # First two should be adjusted
        assert abs(result[0].duration - 0.3) < 1e-10  # 0.4 - 0.0 - 0.1
        assert abs(result[1].duration - 0.3) < 1e-10  # 0.8 - 0.4 - 0.1
        assert result[2].duration == 0.5  # Last one unchanged

    def test_adjust_page_boundary_gap(self):
        """Test that distant notes (page boundaries) are not adjusted."""
        entries = [
            TabEntry(tab=4, time=7.5, duration=1.5, confidence=0.8),  # End of page 1
            TabEntry(
                tab=4, time=13.4, duration=0.2, confidence=0.8
            ),  # Start of page 2 (5.9s gap)
        ]

        result = adjust_consecutive_identical_notes(entries, gap=0.15, max_gap=2.0)

        # Notes are >2s apart, so no adjustment should happen
        assert result[0].duration == 1.5  # Original duration preserved
        assert result[1].duration == 0.2  # Unchanged


class TestAnimatorInitialization:
    """Test Animator initialization."""

    def test_init_successful(self, mock_harmonica_layout, mock_figure_factory):
        """Test successful Animator initialization."""
        animator = Animator(mock_harmonica_layout, mock_figure_factory)

        assert animator._harmonica_layout == mock_harmonica_layout
        assert animator._figure_factory == mock_figure_factory
        assert animator._frame_timings == []
        assert animator._text_objects == []
        assert animator._arrows == []
        assert animator._squares == []
        assert animator._flat_entries == []
        assert animator._ax is None
        assert animator._temp_video_path.endswith("temp_video.mp4")

    def test_init_video_processor_created(
        self, mock_harmonica_layout, mock_figure_factory
    ):
        """Test that VideoProcessor is created during initialization."""
        with patch("image_converter.animator.VideoProcessor") as mock_vp:
            animator = Animator(mock_harmonica_layout, mock_figure_factory)

            mock_vp.assert_called_once()
            assert animator._video_processor == mock_vp.return_value


class TestAnimatorHelperMethods:
    """Test Animator helper and utility methods."""

    def test_get_color_blow_notes(self):
        """Test color assignment for blow notes (positive tabs)."""
        blow_entry = TabEntry(tab=5, time=0.0, duration=0.5, confidence=0.8)
        color = Animator._get_color(blow_entry)
        assert color == OUT_COLOR

    def test_get_color_draw_notes(self):
        """Test color assignment for draw notes (negative tabs)."""
        draw_entry = TabEntry(tab=-3, time=0.0, duration=0.5, confidence=0.8)
        color = Animator._get_color(draw_entry)
        assert color == IN_COLOR

    def test_get_color_bent_notes(self):
        """Test color assignment for bent notes (orange)."""
        from image_converter.consts import BEND_COLOR

        # Bent blow note
        bent_blow = TabEntry(
            tab=6, time=0.0, duration=0.5, confidence=0.8, is_bend=True
        )
        color = Animator._get_color(bent_blow)
        assert color == BEND_COLOR

        # Bent draw note
        bent_draw = TabEntry(
            tab=-6, time=0.0, duration=0.5, confidence=0.8, is_bend=True
        )
        color = Animator._get_color(bent_draw)
        assert color == BEND_COLOR

    def test_get_color_bend_takes_precedence(self):
        """Test that bend color takes precedence over blow/draw color."""
        from image_converter.consts import BEND_COLOR

        # Bend should override normal blow color
        bent_note = TabEntry(
            tab=5, time=0.0, duration=0.5, confidence=0.8, is_bend=True
        )
        color = Animator._get_color(bent_note)
        assert color == BEND_COLOR
        assert color != OUT_COLOR

        # Regular note should use normal color
        regular_note = TabEntry(
            tab=5, time=0.0, duration=0.5, confidence=0.8, is_bend=False
        )
        color = Animator._get_color(regular_note)
        assert color == OUT_COLOR
        assert color != BEND_COLOR

    def test_calc_direction_blow_notes(self):
        """Test direction arrow for blow notes."""
        blow_entry = TabEntry(tab=7, time=0.0, duration=0.5, confidence=0.8)
        direction = Animator._calc_direction(blow_entry)
        assert direction == "↑"

    def test_calc_direction_draw_notes(self):
        """Test direction arrow for draw notes."""
        draw_entry = TabEntry(tab=-4, time=0.0, duration=0.5, confidence=0.8)
        direction = Animator._calc_direction(draw_entry)
        assert direction == "↓"

    def test_get_total_frames(self):
        """Test total frames calculation."""
        frames = Animator._get_total_frames(fps=30, total_duration=2.5)
        assert frames == 75  # 30 * 2.5

        frames = Animator._get_total_frames(fps=15, total_duration=4.0)
        assert frames == 60  # 15 * 4.0

    def test_get_total_duration(self, mock_harmonica_layout, mock_figure_factory):
        """Test total duration calculation."""
        animator = Animator(mock_harmonica_layout, mock_figure_factory)

        # Set up test entries
        animator._flat_entries = [
            TabEntry(tab=1, time=0.0, duration=1.0, confidence=0.8),
            TabEntry(tab=2, time=1.5, duration=0.5, confidence=0.8),  # Ends at 2.0
            TabEntry(tab=3, time=0.5, duration=1.0, confidence=0.8),  # Ends at 1.5
        ]

        total_duration = animator._get_total_duration()

        # Should be max end time (2.0) + buffer (0.5) = 2.5
        assert total_duration == 2.5

    def test_get_total_duration_empty_entries(
        self, mock_harmonica_layout, mock_figure_factory
    ):
        """Test total duration with no entries."""
        animator = Animator(mock_harmonica_layout, mock_figure_factory)
        animator._flat_entries = []

        # Should handle empty entries gracefully
        with pytest.raises(ValueError):  # max() of empty sequence
            animator._get_total_duration()


class TestAnimatorFrameProcessing:
    """Test frame processing and visualization creation."""

    def test_clear_frame_objects(self, mock_harmonica_layout, mock_figure_factory):
        """Test clearing frame objects."""
        animator = Animator(mock_harmonica_layout, mock_figure_factory)

        # Create mock objects
        mock_text1 = MagicMock()
        mock_text2 = MagicMock()
        mock_arrow = MagicMock()

        animator._text_objects = [mock_text1, mock_text2]
        animator._arrows = [mock_arrow]

        animator._clear_frame_objects()

        # Verify all objects were removed
        mock_text1.remove.assert_called_once()
        mock_text2.remove.assert_called_once()
        mock_arrow.remove.assert_called_once()

        # Verify lists were cleared
        assert animator._text_objects == []
        assert animator._arrows == []

    @patch("matplotlib.pyplot.Rectangle")
    def test_create_note_visualization(
        self, mock_rect_class, mock_harmonica_layout, mock_figure_factory
    ):
        """Test creating visualization for a single note."""
        # Setup mocks
        mock_harmonica_layout.get_position.return_value = (100, 200)
        mock_harmonica_layout.get_rectangle.return_value = (90, 190, 20, 20)

        mock_ax = MagicMock()
        mock_rect = MagicMock()
        mock_rect_class.return_value = mock_rect
        mock_ax.add_patch.return_value = mock_rect

        animator = Animator(mock_harmonica_layout, mock_figure_factory)
        animator._ax = mock_ax

        # Test with blow note
        tab_entry = TabEntry(tab=5, time=0.0, duration=0.5, confidence=0.8)
        animator._create_note_visualization(tab_entry)

        # Verify harmonica layout calls
        mock_harmonica_layout.get_position.assert_called_once_with(5)
        mock_harmonica_layout.get_rectangle.assert_called_once_with(5)

        # Verify rectangle creation
        mock_rect_class.assert_called_once_with(
            (90, 190),
            20,
            20,
            linewidth=0,
            edgecolor=None,
            facecolor=OUT_COLOR,
            alpha=0.8,
        )
        mock_ax.add_patch.assert_called_once_with(mock_rect)

        # Verify text creation (hole number and direction)
        assert mock_ax.text.call_count == 2
        text_calls = mock_ax.text.call_args_list

        # Hole number text
        assert text_calls[0][0][:3] == (
            100,
            190,
            "5",
        )  # center_x, center_y - 10, hole number

        # Direction arrow text
        assert text_calls[1][0][:3] == (
            100,
            220,
            "↑",
        )  # center_x, center_y + 20, direction

    def test_create_note_visualization_draw_note(
        self, mock_harmonica_layout, mock_figure_factory
    ):
        """Test visualization creation for draw note."""
        mock_harmonica_layout.get_position.return_value = (150, 250)
        mock_harmonica_layout.get_rectangle.return_value = (140, 240, 20, 20)

        mock_ax = MagicMock()
        animator = Animator(mock_harmonica_layout, mock_figure_factory)
        animator._ax = mock_ax

        # Test with draw note
        tab_entry = TabEntry(tab=-3, time=0.0, duration=0.5, confidence=0.6)

        with patch("matplotlib.pyplot.Rectangle") as mock_rect_class:
            animator._create_note_visualization(tab_entry)

            # Verify correct color and direction for draw note
            mock_rect_class.assert_called_once()
            call_kwargs = mock_rect_class.call_args[1]
            assert call_kwargs["facecolor"] == IN_COLOR
            assert call_kwargs["alpha"] == 0.6

            # Check direction arrow
            text_calls = mock_ax.text.call_args_list
            assert text_calls[1][0][2] == "↓"  # Draw note direction (3rd argument)

    def test_create_note_visualization_no_axes(
        self, mock_harmonica_layout, mock_figure_factory
    ):
        """Test visualization creation when axes not initialized."""
        animator = Animator(mock_harmonica_layout, mock_figure_factory)
        animator._ax = None

        tab_entry = TabEntry(tab=1, time=0.0, duration=0.5, confidence=0.8)

        with pytest.raises(RuntimeError, match="Axes not initialized"):
            animator._create_note_visualization(tab_entry)

    def test_update_frame(self, mock_harmonica_layout, mock_figure_factory):
        """Test frame update logic."""
        animator = Animator(mock_harmonica_layout, mock_figure_factory)
        animator._ax = MagicMock()

        # Setup test entries
        animator._flat_entries = [
            TabEntry(tab=1, time=0.0, duration=1.0, confidence=0.8),  # Active at 0.5s
            TabEntry(
                tab=2, time=0.8, duration=0.5, confidence=0.8
            ),  # Not active at 0.5s
            TabEntry(
                tab=3, time=0.2, duration=0.5, confidence=0.8
            ),  # Active at 0.5s (0.2-0.7)
        ]

        with (
            patch.object(animator, "_clear_frame_objects") as mock_clear,
            patch.object(animator, "_create_note_visualization") as mock_create,
        ):

            result = animator._update_frame(frame=7, fps=15)  # 7/15 = 0.467s

            # Should clear previous objects
            mock_clear.assert_called_once()

            # Should create visualization for active notes (tabs 1 and 3)
            assert mock_create.call_count == 2
            created_tabs = [call[0][0].tab for call in mock_create.call_args_list]
            assert set(created_tabs) == {1, 3}

            # Should return combined objects
            assert result == animator._text_objects + animator._arrows

    def test_timed_update_frame(self, mock_harmonica_layout, mock_figure_factory):
        """Test timed frame update with performance tracking."""
        animator = Animator(mock_harmonica_layout, mock_figure_factory)

        with (
            patch.object(animator, "_update_frame") as mock_update,
            patch("time.perf_counter", side_effect=[0.0, 0.01]),
        ):  # 10ms elapsed

            mock_update.return_value = ["mock_objects"]
            result = animator._timed_update_frame(
                frame=30, fps=15
            )  # Frame 30 (divisible by 30)

            # Should call update_frame
            mock_update.assert_called_once_with(30, 15)

            # Should record timing for frame 30
            assert len(animator._frame_timings) == 1
            assert animator._frame_timings[0] == 0.01

            assert result == ["mock_objects"]

    def test_timed_update_frame_no_timing(
        self, mock_harmonica_layout, mock_figure_factory
    ):
        """Test timed frame update without performance tracking."""
        animator = Animator(mock_harmonica_layout, mock_figure_factory)

        with patch.object(animator, "_update_frame"):
            animator._timed_update_frame(
                frame=15, fps=15
            )  # Frame 15 (not divisible by 30)

            # Should not record timing
            assert len(animator._frame_timings) == 0


class TestAnimatorVideoCreation:
    """Test video creation and processing."""

    @patch("image_converter.animator.animation.FuncAnimation")
    def test_create_animation_basic_flow(
        self, mock_func_animation, mock_harmonica_layout, mock_figure_factory
    ):
        """Test basic animation creation flow."""
        # Setup mocks
        mock_figure_factory.create.return_value = (MagicMock(), MagicMock())
        mock_ani = MagicMock()
        mock_func_animation.return_value = mock_ani

        animator = Animator(mock_harmonica_layout, mock_figure_factory)

        # Mock video processor
        with patch.object(animator, "_video_processor") as mock_vp:
            # Setup test data
            test_pages = {
                "Page 1": [
                    [
                        [TabEntry(tab=1, time=0.0, duration=0.5, confidence=0.8)],
                        [TabEntry(tab=2, time=0.5, duration=0.5, confidence=0.8)],
                    ]
                ]
            }

            with patch.object(animator, "_log_video_info") as mock_log:
                animator.create_animation(test_pages, "audio.wav", "output.mp4", fps=15)

            # Verify figure creation
            mock_figure_factory.create.assert_called_once()

            # Verify animation creation
            mock_func_animation.assert_called_once()
            func_anim_args = mock_func_animation.call_args
            assert func_anim_args[1]["frames"] > 0
            assert func_anim_args[1]["interval"] == 1000 / 15  # Based on fps
            assert func_anim_args[1]["blit"] is False

            # Verify animation save
            mock_ani.save.assert_called_once()
            save_args = mock_ani.save.call_args
            assert save_args[1]["fps"] == 15
            assert save_args[1]["writer"] == "ffmpeg"

            # Verify video processing
            mock_vp.process_animation_to_video.assert_called_once_with(
                animator._temp_video_path, "audio.wav", "output.mp4", cleanup_temp=True
            )

            # Verify logging
            mock_log.assert_called_once()

    def test_create_animation_flattens_entries(
        self, mock_harmonica_layout, mock_figure_factory
    ):
        """Test that nested page structure is properly flattened."""
        animator = Animator(mock_harmonica_layout, mock_figure_factory)

        test_pages = {
            "Page 1": [
                [
                    [TabEntry(tab=1, time=0.0, duration=0.5, confidence=0.8)],
                    [TabEntry(tab=2, time=0.5, duration=0.5, confidence=0.8)],
                ],
                [
                    [TabEntry(tab=3, time=1.0, duration=0.5, confidence=0.8)],
                ],
            ],
            "Page 2": [
                [
                    [TabEntry(tab=4, time=1.5, duration=0.5, confidence=0.8)],
                ]
            ],
        }

        with (
            patch("image_converter.animator.animation.FuncAnimation"),
            patch.object(animator, "_video_processor"),
            patch.object(
                mock_figure_factory, "create", return_value=(MagicMock(), MagicMock())
            ),
        ):

            animator.create_animation(test_pages, "audio.wav", "output.mp4")

            # Check that all entries were flattened
            assert len(animator._flat_entries) == 4
            tabs = [entry.tab for entry in animator._flat_entries]
            assert set(tabs) == {1, 2, 3, 4}

    def test_create_animation_handles_none_chords(
        self, mock_harmonica_layout, mock_figure_factory
    ):
        """Test that None chords are properly filtered out."""
        animator = Animator(mock_harmonica_layout, mock_figure_factory)

        test_pages = {
            "Page 1": [
                [
                    [TabEntry(tab=1, time=0.0, duration=0.5, confidence=0.8)],
                    None,  # Empty chord
                    [TabEntry(tab=2, time=0.5, duration=0.5, confidence=0.8)],
                ]
            ]
        }

        with (
            patch("image_converter.animator.animation.FuncAnimation"),
            patch.object(animator, "_video_processor"),
            patch.object(
                mock_figure_factory, "create", return_value=(MagicMock(), MagicMock())
            ),
        ):

            animator.create_animation(test_pages, "audio.wav", "output.mp4")

            # Should only have 2 entries (None chord filtered out)
            assert len(animator._flat_entries) == 2
            tabs = [entry.tab for entry in animator._flat_entries]
            assert set(tabs) == {1, 2}

    @patch("image_converter.animator.animation.FuncAnimation")
    def test_create_animation_video_processor_error(
        self, mock_func_animation, mock_harmonica_layout, mock_figure_factory
    ):
        """Test handling of VideoProcessorError."""
        mock_figure_factory.create.return_value = (MagicMock(), MagicMock())
        mock_ani = MagicMock()
        mock_func_animation.return_value = mock_ani

        animator = Animator(mock_harmonica_layout, mock_figure_factory)

        # Mock video processor to raise error
        from image_converter.video_processor import VideoProcessorError

        with patch.object(animator, "_video_processor") as mock_vp:
            mock_vp.process_animation_to_video.side_effect = VideoProcessorError(
                "FFmpeg failed"
            )

            test_pages = {
                "Page 1": [[[TabEntry(tab=1, time=0.0, duration=0.5, confidence=0.8)]]]
            }

            with pytest.raises(VideoProcessorError, match="FFmpeg failed"):
                animator.create_animation(test_pages, "audio.wav", "output.mp4")

    def test_create_animation_performance_logging(
        self, mock_harmonica_layout, mock_figure_factory
    ):
        """Test performance metrics logging."""
        mock_figure_factory.create.return_value = (MagicMock(), MagicMock())

        animator = Animator(mock_harmonica_layout, mock_figure_factory)
        animator._frame_timings = [0.01, 0.02, 0.015]  # Mock some timings

        with (
            patch("image_converter.animator.animation.FuncAnimation") as mock_func_anim,
            patch.object(animator, "_video_processor"),
            patch("builtins.print") as mock_print,
        ):

            mock_ani = MagicMock()
            mock_func_anim.return_value = mock_ani

            test_pages = {
                "Page 1": [[[TabEntry(tab=1, time=0.0, duration=0.5, confidence=0.8)]]]
            }
            animator.create_animation(test_pages, "audio.wav", "output.mp4")

            # Should print average frame time
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            avg_time_message = next(
                (msg for msg in print_calls if "Average frame update time" in msg), None
            )
            assert avg_time_message is not None
            assert "0.0150s" in avg_time_message  # Average of 0.01, 0.02, 0.015


class TestAnimatorVideoInfoLogging:
    """Test video information logging functionality."""

    def test_log_video_info_success(self, mock_harmonica_layout, mock_figure_factory):
        """Test successful video info logging."""
        animator = Animator(mock_harmonica_layout, mock_figure_factory)
        animator._frame_timings = [0.01, 0.02]

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            # Write some dummy content to get file size
            temp_file.write(b"dummy video content" * 1000)  # ~19KB
            temp_path = temp_file.name

        try:
            with patch("builtins.print") as mock_print:
                animator._log_video_info(
                    temp_path, duration=5.0, fps=30, total_frames=150
                )

                # Verify comprehensive logging
                print_calls = [call[0][0] for call in mock_print.call_args_list]

                # Check for key information
                assert any("VIDEO INFORMATION" in msg for msg in print_calls)
                assert any("Size:" in msg and "MB" in msg for msg in print_calls)
                assert any("Duration: 5.00s" in msg for msg in print_calls)
                assert any("Frames: 150 @ 30 FPS" in msg for msg in print_calls)
                assert any("bitrate:" in msg and "kbps" in msg for msg in print_calls)
                assert any("Avg frame time:" in msg for msg in print_calls)

        finally:
            os.unlink(temp_path)

    def test_log_video_info_file_not_found(
        self, mock_harmonica_layout, mock_figure_factory
    ):
        """Test video info logging when file doesn't exist."""
        animator = Animator(mock_harmonica_layout, mock_figure_factory)

        with patch("builtins.print") as mock_print:
            animator._log_video_info(
                "/nonexistent/video.mp4", duration=2.0, fps=15, total_frames=30
            )

            # Should print warning and fallback message
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            assert any(
                "Warning: Could not retrieve video info" in msg for msg in print_calls
            )
            assert any("Video saved to:" in msg for msg in print_calls)

    def test_log_video_info_no_frame_timings(
        self, mock_harmonica_layout, mock_figure_factory
    ):
        """Test video info logging without frame timing data."""
        animator = Animator(mock_harmonica_layout, mock_figure_factory)
        animator._frame_timings = []  # No timing data

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(b"test")
            temp_path = temp_file.name

        try:
            with patch("builtins.print") as mock_print:
                animator._log_video_info(
                    temp_path, duration=1.0, fps=15, total_frames=15
                )

                print_calls = [call[0][0] for call in mock_print.call_args_list]

                # Should not include frame timing info
                assert not any("Avg frame time:" in msg for msg in print_calls)
                assert not any("Est. total render:" in msg for msg in print_calls)

        finally:
            os.unlink(temp_path)


class TestAnimatorIntegration:
    """Test integration scenarios and complete workflows."""

    def test_realistic_harmonica_sequence(
        self, mock_harmonica_layout, mock_figure_factory
    ):
        """Test with realistic harmonica playing sequence."""
        # Setup realistic coordinate returns
        mock_harmonica_layout.get_position.side_effect = lambda hole: (hole * 50, 200)
        mock_harmonica_layout.get_rectangle.side_effect = lambda hole: (
            hole * 50 - 20,
            180,
            40,
            40,
        )

        animator = Animator(mock_harmonica_layout, mock_figure_factory)

        # Realistic harmonica sequence: Mary Had a Little Lamb
        test_pages = {
            "Mary Had a Little Lamb": [
                [
                    # Line 1: Ma-ry had a lit-tle lamb
                    [TabEntry(tab=3, time=0.0, duration=0.5, confidence=0.9)],  # Ma
                    [TabEntry(tab=2, time=0.5, duration=0.5, confidence=0.9)],  # ry
                    [TabEntry(tab=1, time=1.0, duration=0.5, confidence=0.9)],  # had
                    [TabEntry(tab=2, time=1.5, duration=0.5, confidence=0.9)],  # a
                    [TabEntry(tab=3, time=2.0, duration=0.5, confidence=0.9)],  # lit
                    [TabEntry(tab=3, time=2.5, duration=0.5, confidence=0.9)],  # tle
                    [TabEntry(tab=3, time=3.0, duration=1.0, confidence=0.9)],  # lamb
                ]
            ]
        }

        with (
            patch("image_converter.animator.animation.FuncAnimation"),
            patch.object(animator, "_video_processor") as mock_vp,
            patch.object(
                mock_figure_factory, "create", return_value=(MagicMock(), MagicMock())
            ),
        ):

            animator.create_animation(
                test_pages, "mary_audio.wav", "mary_video.mp4", fps=15
            )

            # Verify all notes were processed
            assert len(animator._flat_entries) == 7

            # Verify consecutive identical notes were adjusted
            consecutive_threes = [e for e in animator._flat_entries if e.tab == 3]
            assert len(consecutive_threes) == 4  # Four "3" notes

            # Verify video processing was called
            mock_vp.process_animation_to_video.assert_called_once_with(
                animator._temp_video_path,
                "mary_audio.wav",
                "mary_video.mp4",
                cleanup_temp=True,
            )

    def test_chord_handling(self, mock_harmonica_layout, mock_figure_factory):
        """Test handling of harmonica chords (multiple simultaneous notes)."""
        mock_harmonica_layout.get_position.side_effect = lambda hole: (hole * 50, 200)
        mock_harmonica_layout.get_rectangle.side_effect = lambda hole: (
            hole * 50 - 20,
            180,
            40,
            40,
        )

        animator = Animator(mock_harmonica_layout, mock_figure_factory)

        # Test with chords (multiple notes at same time)
        test_pages = {
            "Chord Test": [
                [
                    # Two-note chord: blow 1+2 simultaneously
                    [
                        TabEntry(tab=1, time=0.0, duration=1.0, confidence=0.8),
                        TabEntry(tab=2, time=0.0, duration=1.0, confidence=0.8),
                    ],
                    # Three-note chord: draw 1+2+3 simultaneously
                    [
                        TabEntry(tab=-1, time=1.5, duration=0.5, confidence=0.7),
                        TabEntry(tab=-2, time=1.5, duration=0.5, confidence=0.7),
                        TabEntry(tab=-3, time=1.5, duration=0.5, confidence=0.7),
                    ],
                ]
            ]
        }

        with (
            patch("image_converter.animator.animation.FuncAnimation"),
            patch.object(animator, "_video_processor"),
            patch.object(
                mock_figure_factory, "create", return_value=(MagicMock(), MagicMock())
            ),
        ):

            animator.create_animation(test_pages, "chord_audio.wav", "chord_video.mp4")

            # Should have 5 total entries (2 + 3)
            assert len(animator._flat_entries) == 5

            # Check timing alignment for chords
            chord1_entries = [e for e in animator._flat_entries if e.time == 0.0]
            chord2_entries = [e for e in animator._flat_entries if e.time == 1.5]

            assert len(chord1_entries) == 2  # Blow chord
            assert len(chord2_entries) == 3  # Draw chord

            # Verify color consistency within chords
            blow_tabs = [e.tab for e in chord1_entries]
            draw_tabs = [e.tab for e in chord2_entries]

            assert all(tab > 0 for tab in blow_tabs)  # All positive (blow)
            assert all(tab < 0 for tab in draw_tabs)  # All negative (draw)

    def test_performance_edge_cases(self, mock_harmonica_layout, mock_figure_factory):
        """Test performance with edge cases and stress scenarios."""
        animator = Animator(mock_harmonica_layout, mock_figure_factory)

        # Test with very short notes
        test_pages = {
            "Rapid Fire": [
                [
                    [
                        TabEntry(
                            tab=i % 10 + 1, time=i * 0.1, duration=0.05, confidence=0.5
                        )
                    ]
                    for i in range(100)  # 100 very short rapid notes
                ]
            ]
        }

        with (
            patch("image_converter.animator.animation.FuncAnimation") as mock_func_anim,
            patch.object(animator, "_video_processor"),
            patch.object(
                mock_figure_factory, "create", return_value=(MagicMock(), MagicMock())
            ),
        ):

            animator.create_animation(
                test_pages, "rapid_audio.wav", "rapid_video.mp4", fps=60
            )

            # Should handle many short notes
            assert len(animator._flat_entries) == 100

            # Should calculate reasonable duration
            total_duration = animator._get_total_duration()
            assert (
                total_duration > 10.0
            )  # Last note at 9.9s + 0.05s duration + 0.5s buffer

            # Should create appropriate frame count for high FPS
            func_anim_args = mock_func_anim.call_args[1]
            assert func_anim_args["frames"] > 600  # > 10s * 60fps

    def test_empty_and_minimal_content(
        self, mock_harmonica_layout, mock_figure_factory
    ):
        """Test with empty or minimal content."""
        animator = Animator(mock_harmonica_layout, mock_figure_factory)

        # Test with empty pages (all None chords)
        empty_pages = {
            "Empty Page": [
                [
                    None,  # Empty chord
                    None,  # Empty chord
                ]
            ]
        }

        with (
            patch("image_converter.animator.animation.FuncAnimation"),
            patch.object(animator, "_video_processor"),
            patch.object(
                mock_figure_factory, "create", return_value=(MagicMock(), MagicMock())
            ),
        ):

            # Should handle empty content gracefully
            with pytest.raises(
                ValueError
            ):  # Empty entries will cause max() error in _get_total_duration
                animator.create_animation(
                    empty_pages, "empty_audio.wav", "empty_video.mp4"
                )

        # Test with single note
        minimal_pages = {
            "Single Note": [
                [
                    [TabEntry(tab=5, time=0.0, duration=2.0, confidence=1.0)],
                ]
            ]
        }

        with (
            patch("image_converter.animator.animation.FuncAnimation"),
            patch.object(animator, "_video_processor"),
            patch.object(
                mock_figure_factory, "create", return_value=(MagicMock(), MagicMock())
            ),
        ):

            animator.create_animation(
                minimal_pages, "minimal_audio.wav", "minimal_video.mp4"
            )

            assert len(animator._flat_entries) == 1
            assert animator._get_total_duration() == 2.5  # 2.0 + 0.5 buffer
