"""Tests for tab_phrase_animator.tab_phrase_animator module."""

import subprocess
from unittest.mock import MagicMock, patch
import pytest

from tab_phrase_animator.tab_phrase_animator import (
    TabPhraseAnimator,
    TabPhraseAnimatorError,
    AnimationConfig,
    PageStatistics,
)
from tab_converter.models import TabEntry


class TestAnimationConfig:
    """Test AnimationConfig dataclass functionality."""

    def test_default_config(self):
        """Test default AnimationConfig values."""
        config = AnimationConfig()
        assert config.fps == 30
        assert config.figure_size == (16, 9)
        assert config.background_color == "#FF00FF"
        assert config.font_family == "Ploni Round AAA"
        assert config.font_file == "ploni-round-bold-aaa.ttf"
        assert config.font_size == 32
        assert config.char_spacing == 0.08
        assert config.line_spacing == 0.12
        assert config.box_padding == 0.05
        assert config.box_rounding == 0.2
        assert config.box_color == "#888888"
        assert config.box_alpha == 0.5
        assert config.time_buffer == 0.5
        assert config.cleanup_temp_files is True

    def test_custom_config(self):
        """Test custom AnimationConfig values."""
        config = AnimationConfig(
            fps=60,
            figure_size=(20, 12),
            background_color="#00FF00",
            font_family="Arial",
            font_file="arial.ttf",
            font_size=24,
            char_spacing=0.1,
            line_spacing=0.15,
            box_padding=0.08,
            box_rounding=0.3,
            box_color="#FFFFFF",
            box_alpha=0.8,
            time_buffer=1.0,
            cleanup_temp_files=False,
        )
        assert config.fps == 60
        assert config.figure_size == (20, 12)
        assert config.background_color == "#00FF00"
        assert config.font_family == "Arial"
        assert config.font_file == "arial.ttf"
        assert config.font_size == 24
        assert config.char_spacing == 0.1
        assert config.line_spacing == 0.15
        assert config.box_padding == 0.08
        assert config.box_rounding == 0.3
        assert config.box_color == "#FFFFFF"
        assert config.box_alpha == 0.8
        assert config.time_buffer == 1.0
        assert config.cleanup_temp_files is False


class TestPageStatistics:
    """Test PageStatistics dataclass functionality."""

    def test_page_statistics_creation(self):
        """Test creating PageStatistics."""
        stats = PageStatistics(
            page_name="Page 1",
            total_entries=12,
            start_time=0.5,
            end_time=5.2,
            duration=4.7,
            total_frames=141,
            lines_count=3,
            chords_count=8,
            output_file="/output/page1.mov",
        )
        assert stats.page_name == "Page 1"
        assert stats.total_entries == 12
        assert stats.start_time == 0.5
        assert stats.end_time == 5.2
        assert stats.duration == 4.7
        assert stats.total_frames == 141
        assert stats.lines_count == 3
        assert stats.chords_count == 8
        assert stats.output_file == "/output/page1.mov"


class TestTabPhraseAnimatorInitialization:
    """Test TabPhraseAnimator initialization."""

    def test_init_with_default_config(self, mock_harmonica_layout, mock_figure_factory):
        """Test initialization with default configuration."""
        with patch.object(TabPhraseAnimator, "_load_font"):
            animator = TabPhraseAnimator(mock_harmonica_layout, mock_figure_factory)

        assert animator._harmonica_layout == mock_harmonica_layout
        assert animator._figure_factory == mock_figure_factory
        assert isinstance(animator._config, AnimationConfig)
        assert animator._config.fps == 30  # Default value
        assert animator._page_statistics == []

    def test_init_with_custom_config(self, mock_harmonica_layout, mock_figure_factory):
        """Test initialization with custom configuration."""
        custom_config = AnimationConfig(fps=60, font_size=48)

        with patch.object(TabPhraseAnimator, "_load_font"):
            animator = TabPhraseAnimator(
                mock_harmonica_layout, mock_figure_factory, custom_config
            )

        assert animator._config == custom_config
        assert animator._config.fps == 60
        assert animator._config.font_size == 48

    def test_font_loading_success(self, mock_harmonica_layout, mock_figure_factory):
        """Test successful font loading."""
        config = AnimationConfig(font_file="test.ttf")

        with patch("os.path.exists", return_value=True):
            with patch("matplotlib.font_manager.fontManager.addfont") as mock_add:
                TabPhraseAnimator(mock_harmonica_layout, mock_figure_factory, config)

        mock_add.assert_called_once_with("test.ttf")

    def test_font_loading_file_not_found(
        self, mock_harmonica_layout, mock_figure_factory
    ):
        """Test font loading when file doesn't exist."""
        config = AnimationConfig(font_file="missing.ttf")

        with patch("os.path.exists", return_value=False):
            # Should not raise exception, just print warning
            animator = TabPhraseAnimator(
                mock_harmonica_layout, mock_figure_factory, config
            )

        assert isinstance(animator, TabPhraseAnimator)

    def test_font_loading_exception(self, mock_harmonica_layout, mock_figure_factory):
        """Test font loading with exception."""
        config = AnimationConfig(font_file="problematic.ttf")

        with patch("os.path.exists", return_value=True):
            with patch(
                "matplotlib.font_manager.fontManager.addfont",
                side_effect=Exception("Font error"),
            ):
                # Should not raise exception, just print warning
                animator = TabPhraseAnimator(
                    mock_harmonica_layout, mock_figure_factory, config
                )

        assert isinstance(animator, TabPhraseAnimator)


class TestTabPhraseAnimatorValidation:
    """Test input validation and error handling."""

    def test_create_animations_empty_pages(self, basic_animator, temp_audio_file):
        """Test animation creation with empty pages."""
        with pytest.raises(TabPhraseAnimatorError, match="No pages provided"):
            basic_animator.create_animations({}, str(temp_audio_file), "/output/base")

    def test_create_animations_missing_audio(self, basic_animator, sample_pages):
        """Test animation creation with missing audio file."""
        with pytest.raises(TabPhraseAnimatorError, match="Audio file not found"):
            basic_animator.create_animations(
                sample_pages, "/nonexistent/audio.wav", "/output/base"
            )

    def test_create_animations_page_no_entries(self, basic_animator, temp_audio_file):
        """Test animation creation with page containing no valid entries."""
        empty_pages = {"Page 1": [[[]]]}  # Empty chord

        with pytest.raises(TabPhraseAnimatorError, match="has no valid entries"):
            basic_animator.create_animations(
                empty_pages, str(temp_audio_file), "/output/base"
            )

    def test_create_animations_page_no_text_lines(
        self, basic_animator, temp_audio_file
    ):
        """Test animation creation with page that produces no text lines."""
        # Mock _prepare_text_data to return empty results
        with patch.object(basic_animator, "_prepare_text_data", return_value=([], [])):
            pages_with_entries = {
                "Page 1": [[[TabEntry(tab=1, time=1.0, duration=0.5, confidence=0.8)]]]
            }

            with pytest.raises(
                TabPhraseAnimatorError, match="No valid text lines found"
            ):
                basic_animator.create_animations(
                    pages_with_entries, str(temp_audio_file), "/output/base"
                )


class TestTabPhraseAnimatorTextProcessing:
    """Test text data preparation and formatting."""

    def test_prepare_text_data_simple(self, basic_animator):
        """Test text data preparation with simple tabs."""
        page = [
            [[TabEntry(tab=1, time=1.0, duration=0.5, confidence=0.8)]],
            [[TabEntry(tab=-2, time=2.0, duration=0.5, confidence=0.8)]],
        ]

        text_lines, line_entries = basic_animator._prepare_text_data(page)

        assert len(text_lines) == 2
        assert text_lines[0] == ["1"]
        assert text_lines[1] == ["-2"]
        assert len(line_entries) == 2
        assert line_entries[0][0].tab == 1
        assert line_entries[1][0].tab == -2

    def test_prepare_text_data_chords(self, basic_animator):
        """Test text data preparation with chord combinations."""
        page = [
            [
                [
                    TabEntry(tab=1, time=1.0, duration=0.5, confidence=0.8),
                    TabEntry(tab=2, time=1.0, duration=0.5, confidence=0.8),
                ]
            ],
            [
                [
                    TabEntry(tab=-4, time=2.0, duration=0.5, confidence=0.8),
                    TabEntry(tab=-5, time=2.0, duration=0.5, confidence=0.8),
                ]
            ],
        ]

        text_lines, line_entries = basic_animator._prepare_text_data(page)

        assert len(text_lines) == 2
        assert text_lines[0] == ["12"]  # Positive tabs combined
        assert text_lines[1] == ["-45"]  # Negative tabs with dash prefix
        assert line_entries[0][0].tab == 1  # Anchored on first note
        assert line_entries[1][0].tab == -4  # Anchored on first note

    def test_prepare_text_data_mixed_line(self, basic_animator):
        """Test text data preparation with multiple chords per line."""
        page = [
            [
                [TabEntry(tab=1, time=1.0, duration=0.5, confidence=0.8)],
                [TabEntry(tab=2, time=1.5, duration=0.5, confidence=0.8)],
                [TabEntry(tab=-3, time=2.0, duration=0.5, confidence=0.8)],
            ]
        ]

        text_lines, line_entries = basic_animator._prepare_text_data(page)

        assert len(text_lines) == 1
        assert text_lines[0] == ["1", "2", "-3"]
        assert len(line_entries[0]) == 3
        assert line_entries[0][0].tab == 1
        assert line_entries[0][1].tab == 2
        assert line_entries[0][2].tab == -3

    def test_prepare_text_data_empty_chords(self, basic_animator):
        """Test text data preparation with empty chords."""
        page = [
            [
                [TabEntry(tab=1, time=1.0, duration=0.5, confidence=0.8)],
                None,  # Empty chord
                [TabEntry(tab=2, time=2.0, duration=0.5, confidence=0.8)],
            ]
        ]

        text_lines, line_entries = basic_animator._prepare_text_data(page)

        assert len(text_lines) == 1
        assert text_lines[0] == ["1", "2"]  # Empty chord skipped
        assert len(line_entries[0]) == 2

    def test_prepare_text_data_empty_lines(self, basic_animator):
        """Test text data preparation with completely empty lines."""
        page = [
            [[TabEntry(tab=1, time=1.0, duration=0.5, confidence=0.8)]],
            [None, None],  # Line with only empty chords
            [[TabEntry(tab=2, time=2.0, duration=0.5, confidence=0.8)]],
        ]

        text_lines, line_entries = basic_animator._prepare_text_data(page)

        assert len(text_lines) == 2  # Empty line should be skipped
        assert text_lines[0] == ["1"]
        assert text_lines[1] == ["2"]

    def test_prepare_text_data_bent_notes(self, basic_animator):
        """Test text data preparation with bent notes (apostrophe appended)."""
        page = [
            [
                [
                    TabEntry(
                        tab=1, time=1.0, duration=0.5, confidence=0.8, is_bend=False
                    )
                ],
                [TabEntry(tab=2, time=1.5, duration=0.5, confidence=0.8, is_bend=True)],
                [
                    TabEntry(
                        tab=-6, time=2.0, duration=0.5, confidence=0.8, is_bend=True
                    )
                ],
            ]
        ]

        text_lines, line_entries = basic_animator._prepare_text_data(page)

        # Bent notes should have apostrophe appended
        assert len(text_lines) == 1
        assert text_lines[0] == ["1", "2'", "-6'"]

    def test_prepare_text_data_bent_chords(self, basic_animator):
        """Test that only single note bends get apostrophe (chords shouldn't have bends)."""
        # In practice, chords shouldn't have bends (validation prevents this)
        # But we test the rendering logic anyway
        page = [
            [
                [
                    TabEntry(
                        tab=1, time=1.0, duration=0.5, confidence=0.8, is_bend=False
                    ),
                    TabEntry(
                        tab=2, time=1.0, duration=0.5, confidence=0.8, is_bend=False
                    ),
                ],
                [TabEntry(tab=6, time=1.5, duration=0.5, confidence=0.8, is_bend=True)],
            ]
        ]

        text_lines, line_entries = basic_animator._prepare_text_data(page)

        assert len(text_lines) == 1
        assert text_lines[0] == [
            "12",
            "6'",
        ]  # Chord is normal, single bent note has apostrophe


class TestTabPhraseAnimatorVideoProcessing:
    """Test video processing functionality."""

    def test_create_transparent_video_success(self, basic_animator):
        """Test successful transparent video creation."""
        with patch(
            "tab_phrase_animator.tab_phrase_animator.subprocess.run"
        ) as mock_run:
            mock_run.return_value = None

            basic_animator._create_transparent_video("input.mp4", "output.mov")

            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert args[0] == "ffmpeg"
            assert "input.mp4" in args
            assert "output.mov" in args
            # Check for colorkey in the -vf argument
            vf_index = args.index("-vf")
            assert "colorkey=0xFF00FF:0.3:0.0" in args[vf_index + 1]

    def test_create_transparent_video_failure(self, basic_animator):
        """Test transparent video creation failure."""
        with patch(
            "subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "ffmpeg", stderr="Error"),
        ):
            with pytest.raises(
                TabPhraseAnimatorError, match="Transparency processing failed"
            ):
                basic_animator._create_transparent_video("input.mp4", "output.mov")

    def test_extract_audio_slice_success(self, basic_animator):
        """Test successful audio slice extraction."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = None

            basic_animator._extract_audio_slice("input.wav", "output.m4a", 1.5, 4.2)

            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert args[0] == "ffmpeg"
            assert "input.wav" in args
            assert "output.m4a" in args
            assert "1.500" in args  # Start time
            assert "4.200" in args  # End time

    def test_extract_audio_slice_failure(self, basic_animator):
        """Test audio slice extraction failure."""
        with patch(
            "subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "ffmpeg", stderr="Error"),
        ):
            with pytest.raises(TabPhraseAnimatorError, match="Audio extraction failed"):
                basic_animator._extract_audio_slice("input.wav", "output.m4a", 1.0, 2.0)

    def test_combine_video_audio_success(self, basic_animator):
        """Test successful video/audio combination."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = None

            basic_animator._combine_video_audio("video.mov", "audio.m4a", "output.mov")

            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert args[0] == "ffmpeg"
            assert "video.mov" in args
            assert "audio.m4a" in args
            assert "output.mov" in args
            assert "-shortest" in args

    def test_combine_video_audio_failure(self, basic_animator):
        """Test video/audio combination failure."""
        with patch(
            "subprocess.run",
            side_effect=subprocess.CalledProcessError(1, "ffmpeg", stderr="Error"),
        ):
            with pytest.raises(
                TabPhraseAnimatorError, match="Video/audio combination failed"
            ):
                basic_animator._combine_video_audio(
                    "video.mov", "audio.m4a", "output.mov"
                )


class TestTabPhraseAnimatorMatplotlib:
    """Test matplotlib animation functionality."""

    @patch("matplotlib.pyplot.subplots")
    @patch("matplotlib.animation.FuncAnimation")
    def test_animation_creation_setup(
        self, mock_animation, mock_subplots, basic_animator
    ):
        """Test matplotlib animation setup."""
        mock_fig = MagicMock()
        mock_ax = MagicMock()
        mock_subplots.return_value = (mock_fig, mock_ax)
        mock_ani = MagicMock()
        mock_animation.return_value = mock_ani

        # Mock other dependencies
        with patch.object(basic_animator, "_process_animation_video") as mock_process:
            mock_process.return_value = "/output/page1.mov"

            page = [[[TabEntry(tab=1, time=1.0, duration=0.5, confidence=0.8)]]]
            result = basic_animator._create_single_page_animation(
                1, "Page 1", page, "/audio.wav", "/output/base", 30
            )

        # Verify matplotlib setup
        mock_subplots.assert_called_once_with(figsize=(16, 9))  # Default figure size
        mock_ax.axis.assert_called_with("off")
        mock_fig.patch.set_facecolor.assert_called_with("#FF00FF")  # Background color

        # Verify animation creation
        mock_animation.assert_called_once()
        animation_args = mock_animation.call_args

        assert animation_args[0][0] == mock_fig  # Figure passed correctly
        assert "frames" in animation_args[1]
        assert "interval" in animation_args[1]
        assert animation_args[1]["interval"] == 1000 / 30  # FPS conversion

        # Verify result
        assert isinstance(result, PageStatistics)
        assert result.page_name == "Page 1"

    def test_update_text_frame_timing(self, basic_animator):
        """Test text frame update with timing-based highlighting."""
        mock_ax = MagicMock()
        text_lines = [["1", "2"], ["-3"]]
        line_entries = [
            [
                TabEntry(tab=1, time=1.0, duration=0.5, confidence=0.8),
                TabEntry(tab=2, time=2.0, duration=0.5, confidence=0.8),
            ],
            [TabEntry(tab=-3, time=3.0, duration=0.5, confidence=0.8)],
        ]

        # Test frame at time 1.2 (within first note's duration)
        with patch.object(basic_animator, "_create_background_box") as mock_box:
            mock_box.return_value = MagicMock()

            basic_animator._update_text_frame(
                6, mock_ax, 30, text_lines, line_entries, 1.0  # frame 6 = time 1.2
            )

        # Verify ax setup
        mock_ax.clear.assert_called_once()
        mock_ax.axis.assert_called_with("off")

        # Verify text elements were created
        assert mock_ax.text.call_count == 3  # Three notes total
        text_calls = mock_ax.text.call_args_list

        # First note should be highlighted (current time within its duration)
        first_call = text_calls[0]
        assert first_call[0][2] == "1"  # Text content
        # Color should be for positive tab (blow note)

        # Second note should be white (not active yet)
        second_call = text_calls[1]
        assert second_call[0][2] == "2"

    def test_create_background_box(self, basic_animator):
        """Test background box creation."""
        mock_ax = MagicMock()
        text_lines = [["123"], ["45"]]

        with patch(
            "tab_phrase_animator.tab_phrase_animator.FancyBboxPatch"
        ) as mock_patch:
            mock_bbox = MagicMock()
            mock_patch.return_value = mock_bbox

            result = basic_animator._create_background_box(text_lines, mock_ax)

            assert result == mock_bbox
            mock_patch.assert_called_once()

            # Verify box sizing based on text content
            call_args = mock_patch.call_args
            box_position = call_args[0][0]  # (x, y)

            # Box should be sized appropriately for the content
            assert isinstance(box_position[0], float)  # x position
            assert isinstance(box_position[1], float)  # y position


class TestTabPhraseAnimatorIntegration:
    """Test full integration workflows."""

    def test_create_animations_full_workflow(
        self, basic_animator, sample_pages, temp_audio_file
    ):
        """Test complete animation creation workflow."""
        # Mock all the complex external dependencies
        with patch("matplotlib.pyplot.subplots") as mock_subplots:
            with patch("matplotlib.animation.FuncAnimation") as mock_animation:
                with patch("subprocess.run") as mock_subprocess:
                    with patch("os.path.exists", return_value=True):
                        with patch("os.remove"):

                            # Setup mocks
                            mock_fig = MagicMock()
                            mock_ax = MagicMock()
                            mock_subplots.return_value = (mock_fig, mock_ax)
                            mock_ani = MagicMock()
                            mock_animation.return_value = mock_ani
                            mock_subprocess.return_value = None

                            # Execute
                            result = basic_animator.create_animations(
                                sample_pages, str(temp_audio_file), "/output/base"
                            )

        # Verify results
        assert len(result) == len(sample_pages)
        assert all(isinstance(stat, PageStatistics) for stat in result)

        # Verify matplotlib was called appropriately
        assert mock_subplots.call_count == len(sample_pages)
        assert mock_animation.call_count == len(sample_pages)

        # Verify FFmpeg processing was called
        assert (
            mock_subprocess.call_count >= len(sample_pages) * 3
        )  # Each page needs multiple ffmpeg calls

    def test_create_animations_with_fps_override(
        self, basic_animator, sample_pages, temp_audio_file
    ):
        """Test animation creation with FPS override."""
        with patch("matplotlib.pyplot.subplots") as mock_subplots:
            with patch("matplotlib.animation.FuncAnimation") as mock_animation:
                with patch("tab_phrase_animator.tab_phrase_animator.subprocess.run"):
                    with patch("os.path.exists", return_value=True):
                        with patch("os.remove"):

                            # Mock matplotlib components
                            mock_fig = MagicMock()
                            mock_ax = MagicMock()
                            mock_subplots.return_value = (mock_fig, mock_ax)
                            mock_animation.return_value = MagicMock()

                            basic_animator.create_animations(
                                sample_pages,
                                str(temp_audio_file),
                                "/output/base",
                                fps=60,
                            )

        # Verify FPS was used in animation
        animation_calls = mock_animation.call_args_list
        for call in animation_calls:
            interval = call[1]["interval"]
            assert interval == 1000 / 60  # 60 FPS

    def test_create_animations_cleanup_disabled(
        self, temp_audio_file, mock_harmonica_layout, mock_figure_factory, sample_pages
    ):
        """Test animation creation with cleanup disabled."""
        config = AnimationConfig(cleanup_temp_files=False)
        with patch.object(TabPhraseAnimator, "_load_font"):
            animator = TabPhraseAnimator(
                mock_harmonica_layout, mock_figure_factory, config
            )

        with patch("matplotlib.pyplot.subplots") as mock_subplots:
            with patch("matplotlib.animation.FuncAnimation"):
                with patch("tab_phrase_animator.tab_phrase_animator.subprocess.run"):
                    with patch("os.path.exists", return_value=True):
                        with patch("os.remove") as mock_remove:

                            # Mock matplotlib components
                            mock_fig = MagicMock()
                            mock_ax = MagicMock()
                            mock_subplots.return_value = (mock_fig, mock_ax)

                            animator.create_animations(
                                sample_pages, str(temp_audio_file), "/output/base"
                            )

        # Verify no cleanup occurred
        mock_remove.assert_not_called()

    def test_error_handling_during_page_creation(self, basic_animator, temp_audio_file):
        """Test error handling when page creation fails."""
        problematic_pages = {
            "Page 1": [[[TabEntry(tab=1, time=1.0, duration=0.5, confidence=0.8)]]],
            "Page 2": [[[TabEntry(tab=2, time=2.0, duration=0.5, confidence=0.8)]]],
        }

        # Mock matplotlib and subprocess first
        with patch("matplotlib.pyplot.subplots") as mock_subplots:
            with patch("matplotlib.animation.FuncAnimation"):
                with patch("tab_phrase_animator.tab_phrase_animator.subprocess.run"):

                    # Setup matplotlib mocks
                    mock_fig = MagicMock()
                    mock_ax = MagicMock()
                    mock_subplots.return_value = (mock_fig, mock_ax)

                    # Mock the single page creation to fail on second page
                    def side_effect(*args, **kwargs):
                        if args[1] == "Page 2":  # page_name
                            raise Exception("Simulated failure")
                        # For Page 1, return a mock PageStatistics
                        return PageStatistics(
                            page_name="Page 1",
                            total_entries=1,
                            start_time=1.0,
                            end_time=1.5,
                            duration=0.5,
                            total_frames=15,
                            lines_count=1,
                            chords_count=1,
                            output_file="/output/page1.mov",
                        )

                    with patch.object(
                        basic_animator,
                        "_create_single_page_animation",
                        side_effect=side_effect,
                    ):
                        with pytest.raises(
                            TabPhraseAnimatorError, match="Failed to create animation"
                        ):
                            basic_animator.create_animations(
                                problematic_pages, str(temp_audio_file), "/output/base"
                            )


class TestTabPhraseAnimatorStatistics:
    """Test statistics and information gathering."""

    def test_get_statistics_empty(self, basic_animator):
        """Test getting statistics with no animations created."""
        stats = basic_animator.get_statistics()
        assert stats == []

    def test_get_animation_info_empty(self, basic_animator):
        """Test getting animation info with no animations created."""
        info = basic_animator.get_animation_info()

        assert info["total_pages"] == 0
        assert info["total_duration"] == 0
        assert "config" in info
        assert isinstance(info["config"], dict)

    def test_get_animation_info_with_data(self, basic_animator):
        """Test getting animation info with existing statistics."""
        # Manually add statistics
        basic_animator._page_statistics = [
            PageStatistics(
                page_name="Page 1",
                total_entries=5,
                start_time=0.0,
                end_time=3.0,
                duration=3.0,
                total_frames=90,
                lines_count=2,
                chords_count=4,
                output_file="/output/page1.mov",
            ),
            PageStatistics(
                page_name="Page 2",
                total_entries=8,
                start_time=3.0,
                end_time=7.0,
                duration=4.0,
                total_frames=120,
                lines_count=3,
                chords_count=6,
                output_file="/output/page2.mov",
            ),
        ]

        info = basic_animator.get_animation_info()

        assert info["total_pages"] == 2
        assert info["total_duration"] == 7.0
        assert info["total_frames"] == 210
        assert info["total_entries"] == 13
        assert info["average_page_duration"] == 3.5
        assert len(info["pages"]) == 2
        assert info["pages"][0]["name"] == "Page 1"
        assert info["pages"][1]["name"] == "Page 2"

    def test_statistics_copying(self, basic_animator):
        """Test that statistics are properly copied and isolated."""
        # Add initial statistics
        initial_stats = [
            PageStatistics(
                page_name="Page 1",
                total_entries=5,
                start_time=0.0,
                end_time=3.0,
                duration=3.0,
                total_frames=90,
                lines_count=2,
                chords_count=4,
                output_file="/output/page1.mov",
            )
        ]
        basic_animator._page_statistics = initial_stats

        # Get statistics copy
        stats_copy = basic_animator.get_statistics()

        # Modify original
        basic_animator._page_statistics.clear()

        # Verify copy is unaffected
        assert len(stats_copy) == 1
        assert stats_copy[0].page_name == "Page 1"
        assert len(basic_animator.get_statistics()) == 0  # Original is cleared
