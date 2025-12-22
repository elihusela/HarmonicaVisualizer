"""Tests for FullTabVideoCompositor."""

import subprocess

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from tab_phrase_animator.full_tab_video_compositor import (
    FullTabVideoCompositor,
    FullTabVideoCompositorError,
    CompositorConfig,
)
from tab_phrase_animator.tab_phrase_animator import PageStatistics


# Fixtures


@pytest.fixture
def default_compositor():
    """Create compositor with default configuration."""
    return FullTabVideoCompositor()


@pytest.fixture
def custom_compositor():
    """Create compositor with custom configuration."""
    config = CompositorConfig(
        transition_gap=0.2,
        background_color=(255, 0, 255, 0),
        cleanup_temp_files=False,
    )
    return FullTabVideoCompositor(config)


@pytest.fixture
def sample_page_statistics(temp_test_dir):
    """Sample page statistics for testing."""
    return [
        PageStatistics(
            page_name="Page 1",
            total_entries=5,
            start_time=0.5,
            end_time=5.5,
            duration=5.0,
            total_frames=150,
            lines_count=2,
            chords_count=5,
            output_file=str(temp_test_dir / "page1_tabs.mov"),
        ),
        PageStatistics(
            page_name="Page 2",
            total_entries=8,
            start_time=6.0,
            end_time=12.0,
            duration=6.0,
            total_frames=180,
            lines_count=3,
            chords_count=8,
            output_file=str(temp_test_dir / "page2_tabs.mov"),
        ),
        PageStatistics(
            page_name="Page 3",
            total_entries=3,
            start_time=13.0,
            end_time=16.0,
            duration=3.0,
            total_frames=90,
            lines_count=1,
            chords_count=3,
            output_file=str(temp_test_dir / "page3_tabs.mov"),
        ),
    ]


@pytest.fixture
def create_dummy_video_files(temp_test_dir, sample_page_statistics):
    """Create dummy video files for page statistics."""
    for stat in sample_page_statistics:
        Path(stat.output_file).write_text("dummy video content")
    return sample_page_statistics


# Configuration Tests


def test_compositor_default_config(default_compositor):
    """Test compositor initialization with default config."""
    assert default_compositor._config.transition_gap == 0.1
    assert default_compositor._config.background_color == (0, 0, 0, 0)
    assert default_compositor._config.cleanup_temp_files is True
    assert default_compositor._page_windows == []


def test_compositor_custom_config(custom_compositor):
    """Test compositor initialization with custom config."""
    assert custom_compositor._config.transition_gap == 0.2
    assert custom_compositor._config.background_color == (255, 0, 255, 0)
    assert custom_compositor._config.cleanup_temp_files is False


# Page Window Calculation Tests


def test_calculate_page_windows_basic(default_compositor, sample_page_statistics):
    """Test basic page window calculation."""
    windows = default_compositor._calculate_page_windows(sample_page_statistics)

    assert len(windows) == 3

    # Verify Page 1
    assert windows[0].page_idx == 1
    assert windows[0].page_name == "Page 1"
    assert windows[0].start_time == 0.5
    assert windows[0].end_time == 5.5
    assert windows[0].duration == 5.0
    assert windows[0].video_path == sample_page_statistics[0].output_file

    # Verify Page 2
    assert windows[1].page_idx == 2
    assert windows[1].page_name == "Page 2"
    assert windows[1].start_time == 6.0
    assert windows[1].end_time == 12.0
    assert windows[1].duration == 6.0

    # Verify Page 3
    assert windows[2].page_idx == 3
    assert windows[2].page_name == "Page 3"
    assert windows[2].start_time == 13.0
    assert windows[2].end_time == 16.0
    assert windows[2].duration == 3.0


def test_calculate_page_windows_empty(default_compositor):
    """Test page window calculation with empty statistics."""
    windows = default_compositor._calculate_page_windows([])
    assert windows == []


def test_calculate_page_windows_single_page(default_compositor, temp_test_dir):
    """Test page window calculation with single page."""
    single_stat = [
        PageStatistics(
            page_name="Only Page",
            total_entries=10,
            start_time=1.0,
            end_time=10.0,
            duration=9.0,
            total_frames=270,
            lines_count=4,
            chords_count=10,
            output_file=str(temp_test_dir / "page1_tabs.mov"),
        )
    ]

    windows = default_compositor._calculate_page_windows(single_stat)

    assert len(windows) == 1
    assert windows[0].page_idx == 1
    assert windows[0].page_name == "Only Page"
    assert windows[0].start_time == 1.0
    assert windows[0].end_time == 10.0
    assert windows[0].duration == 9.0


# Video Validation Tests


def test_validate_page_videos_success(default_compositor, create_dummy_video_files):
    """Test validation passes when all videos exist."""
    default_compositor._page_windows = default_compositor._calculate_page_windows(
        create_dummy_video_files
    )

    # Should not raise any exception
    default_compositor._validate_page_videos()


def test_validate_page_videos_missing_file(default_compositor, sample_page_statistics):
    """Test validation fails when video file is missing."""
    default_compositor._page_windows = default_compositor._calculate_page_windows(
        sample_page_statistics
    )

    with pytest.raises(FullTabVideoCompositorError, match="Page video not found"):
        default_compositor._validate_page_videos()


def test_validate_page_videos_empty_windows(default_compositor):
    """Test validation with no page windows."""
    default_compositor._page_windows = []

    # Should not raise exception with empty windows
    default_compositor._validate_page_videos()


# Video Stitching Tests


@patch("tab_phrase_animator.full_tab_video_compositor.subprocess.run")
@patch.object(FullTabVideoCompositor, "_get_video_dimensions")
@patch.object(FullTabVideoCompositor, "_create_blank_video")
def test_stitch_videos_basic(
    mock_create_blank,
    mock_get_dimensions,
    mock_subprocess,
    default_compositor,
    create_dummy_video_files,
    temp_test_dir,
):
    """Test basic video stitching with ffmpeg."""
    default_compositor._page_windows = default_compositor._calculate_page_windows(
        create_dummy_video_files
    )

    # Mock video dimensions
    mock_get_dimensions.return_value = (1920, 1080)

    # Mock blank video creation
    mock_create_blank.side_effect = lambda dur, size: str(
        temp_test_dir / f"blank_{dur}.mov"
    )

    # Mock ffmpeg subprocess calls (successful)
    mock_subprocess.return_value = MagicMock(returncode=0, stdout="", stderr="")

    output_path = str(temp_test_dir / "full_tabs.mov")
    audio_duration = 17.0

    result = default_compositor._stitch_videos(audio_duration, output_path)

    # _stitch_videos now returns temp video-only path (for audio addition)
    expected_temp_path = str(temp_test_dir / "full_tabs_noaudio.mov")
    assert result == expected_temp_path
    # Should call ffmpeg subprocess for concatenation
    assert any("ffmpeg" in str(call) for call in mock_subprocess.call_args_list)


@patch("tab_phrase_animator.full_tab_video_compositor.subprocess.run")
@patch.object(FullTabVideoCompositor, "_get_video_dimensions")
@patch.object(FullTabVideoCompositor, "_extend_video_with_last_frame")
def test_stitch_videos_with_gaps(
    mock_create_static,
    mock_get_dimensions,
    mock_subprocess,
    default_compositor,
    create_dummy_video_files,
    temp_test_dir,
):
    """Test video stitching with gaps - static frame videos should be inserted."""
    # Modify statistics to have gaps in timing
    stats = create_dummy_video_files
    stats[0].start_time = 0.0
    stats[0].end_time = 5.0
    stats[1].start_time = 7.0  # 2.0s gap after page 1
    stats[1].end_time = 12.0
    stats[2].start_time = 15.0  # 3.0s gap after page 2
    stats[2].end_time = 18.0

    default_compositor._page_windows = default_compositor._calculate_page_windows(stats)

    # Mock video dimensions
    mock_get_dimensions.return_value = (1920, 1080)

    # Mock static frame video creation - should be called for each gap
    static_counter = [0]

    def create_static_side_effect(source, dur, size):
        static_counter[0] += 1
        return str(temp_test_dir / f"static_{static_counter[0]}.mov")

    mock_create_static.side_effect = create_static_side_effect

    # Mock ffmpeg subprocess
    mock_subprocess.return_value = MagicMock(returncode=0)

    output_path = str(temp_test_dir / "full_tabs.mov")
    audio_duration = 20.0

    default_compositor._stitch_videos(audio_duration, output_path)

    # Verify static frame videos were created for both gaps (2.0s and 3.0s)
    assert mock_create_static.call_count == 2
    # First gap: 2.0s between page 1 and 2 (holding page 1's last frame)
    assert mock_create_static.call_args_list[0][0][1] == 2.0  # duration
    assert mock_create_static.call_args_list[0][0][2] == (1920, 1080)  # size
    # Second gap: 3.0s between page 2 and 3 (holding page 2's last frame)
    assert mock_create_static.call_args_list[1][0][1] == 3.0  # duration
    assert mock_create_static.call_args_list[1][0][2] == (1920, 1080)  # size


@patch("tab_phrase_animator.full_tab_video_compositor.subprocess.run")
@patch.object(FullTabVideoCompositor, "_get_video_dimensions")
def test_stitch_videos_exception_handling(
    mock_get_dimensions,
    mock_subprocess,
    default_compositor,
    create_dummy_video_files,
    temp_test_dir,
):
    """Test error handling during video stitching."""
    default_compositor._page_windows = default_compositor._calculate_page_windows(
        create_dummy_video_files
    )

    # Mock video dimensions
    mock_get_dimensions.return_value = (1920, 1080)

    # Simulate error during ffmpeg concatenation
    mock_subprocess.side_effect = Exception("FFmpeg failed")

    output_path = str(temp_test_dir / "full_tabs.mov")
    audio_duration = 17.0

    with pytest.raises(FullTabVideoCompositorError, match="Video stitching failed"):
        default_compositor._stitch_videos(audio_duration, output_path)


# Video Dimensions Tests


@patch("tab_phrase_animator.full_tab_video_compositor.subprocess.run")
def test_get_video_dimensions_success(mock_subprocess, default_compositor):
    """Test getting video dimensions with ffprobe."""
    # Mock ffprobe output
    mock_result = MagicMock()
    mock_result.stdout = '{"streams": [{"width": 1280, "height": 720}]}'
    mock_subprocess.return_value = mock_result

    dimensions = default_compositor._get_video_dimensions("/path/to/video.mov")

    assert dimensions == (1280, 720)
    mock_subprocess.assert_called_once()


@patch("tab_phrase_animator.full_tab_video_compositor.subprocess.run")
def test_get_video_dimensions_fallback(mock_subprocess, default_compositor):
    """Test fallback to default dimensions when ffprobe fails."""
    # Mock ffprobe failure
    mock_subprocess.side_effect = Exception("ffprobe failed")

    dimensions = default_compositor._get_video_dimensions("/path/to/video.mov")

    # Should return default dimensions
    assert dimensions == (1920, 1080)


# Blank Video Creation Tests


@patch("tab_phrase_animator.full_tab_video_compositor.subprocess.run")
def test_create_blank_video_success(mock_subprocess, default_compositor, temp_test_dir):
    """Test blank video creation with ffmpeg."""
    # Mock successful ffmpeg call
    mock_subprocess.return_value = MagicMock(returncode=0)

    blank_path = default_compositor._create_blank_video(2.5, (1920, 1080))

    assert "blank_" in blank_path
    assert blank_path.endswith(".mov")
    mock_subprocess.assert_called_once()

    # Verify ffmpeg command includes duration and size
    call_args = mock_subprocess.call_args[0][0]
    assert "ffmpeg" in call_args
    assert any("1920x1080" in arg for arg in call_args)


@patch("tab_phrase_animator.full_tab_video_compositor.subprocess.run")
def test_create_blank_video_failure(mock_subprocess, default_compositor):
    """Test error handling when blank video creation fails."""
    # Mock ffmpeg failure
    mock_error = subprocess.CalledProcessError(1, "ffmpeg")
    mock_error.stderr = "FFmpeg error"
    mock_subprocess.side_effect = mock_error

    with pytest.raises(
        FullTabVideoCompositorError, match="Failed to create blank video"
    ):
        default_compositor._create_blank_video(2.5, (1920, 1080))


# Static Frame Video Tests


@patch("tab_phrase_animator.full_tab_video_compositor.subprocess.run")
def test_extend_video_with_last_frame_success(
    mock_subprocess, default_compositor, temp_test_dir
):
    """Test successful video extension using tpad filter."""
    # Create dummy source video
    source_video = temp_test_dir / "source.mov"
    source_video.touch()

    # Mock successful ffmpeg call
    mock_subprocess.return_value = MagicMock(returncode=0)

    result = default_compositor._extend_video_with_last_frame(
        str(source_video), 2.5, (1920, 1080)
    )

    # Should return path to extended video
    assert result.endswith(".mov")
    assert "extended_" in result

    # Should call ffmpeg once with tpad filter
    assert mock_subprocess.call_count == 1
    cmd = mock_subprocess.call_args[0][0]
    assert "ffmpeg" in cmd
    assert str(source_video) in cmd
    assert "tpad" in " ".join(cmd)
    assert "2.5" in " ".join(cmd)  # Duration


@patch("tab_phrase_animator.full_tab_video_compositor.subprocess.run")
def test_extend_video_with_last_frame_failure(
    mock_subprocess, default_compositor, temp_test_dir
):
    """Test error handling when video extension fails."""
    # Create dummy source video
    source_video = temp_test_dir / "source.mov"
    source_video.touch()

    # Mock ffmpeg failure
    mock_error = subprocess.CalledProcessError(1, "ffmpeg")
    mock_error.stderr = "Extension failed"
    mock_subprocess.side_effect = mock_error

    with pytest.raises(FullTabVideoCompositorError, match="Failed to extend video"):
        default_compositor._extend_video_with_last_frame(
            str(source_video), 2.5, (1920, 1080)
        )


# FFmpeg Concatenation Tests


@patch("tab_phrase_animator.full_tab_video_compositor.subprocess.run")
def test_concatenate_with_ffmpeg_success(
    mock_subprocess, default_compositor, temp_test_dir
):
    """Test successful video concatenation with ffmpeg."""
    # Mock successful ffmpeg call
    mock_subprocess.return_value = MagicMock(returncode=0)

    concat_file = str(temp_test_dir / "concat.txt")
    output_path = str(temp_test_dir / "output.mov")

    # Should not raise exception
    default_compositor._concatenate_with_ffmpeg(concat_file, output_path)

    mock_subprocess.assert_called_once()
    call_args = mock_subprocess.call_args[0][0]
    assert "ffmpeg" in call_args
    assert concat_file in call_args
    assert output_path in call_args


@patch("tab_phrase_animator.full_tab_video_compositor.subprocess.run")
def test_concatenate_with_ffmpeg_failure(
    mock_subprocess, default_compositor, temp_test_dir
):
    """Test error handling when concatenation fails."""
    # Mock ffmpeg failure
    mock_error = subprocess.CalledProcessError(1, "ffmpeg")
    mock_error.stderr = "Concatenation error"
    mock_subprocess.side_effect = mock_error

    concat_file = str(temp_test_dir / "concat.txt")
    output_path = str(temp_test_dir / "output.mov")

    with pytest.raises(FullTabVideoCompositorError, match="Video concatenation failed"):
        default_compositor._concatenate_with_ffmpeg(concat_file, output_path)


# Full Generate Method Tests


@patch.object(FullTabVideoCompositor, "_stitch_videos")
@patch.object(FullTabVideoCompositor, "_validate_page_videos")
@patch.object(FullTabVideoCompositor, "_calculate_page_windows")
def test_generate_success(
    mock_calc_windows,
    mock_validate,
    mock_stitch,
    default_compositor,
    sample_page_statistics,
    temp_test_dir,
):
    """Test successful full video generation."""
    output_path = str(temp_test_dir / "full_tabs.mov")
    mock_calc_windows.return_value = []
    mock_stitch.return_value = output_path

    result = default_compositor.generate(sample_page_statistics, 17.0, output_path)

    assert result == output_path
    mock_calc_windows.assert_called_once_with(sample_page_statistics)
    mock_validate.assert_called_once()
    mock_stitch.assert_called_once_with(17.0, output_path)


def test_generate_empty_statistics(default_compositor, temp_test_dir):
    """Test generation fails with empty page statistics."""
    output_path = str(temp_test_dir / "full_tabs.mov")

    with pytest.raises(
        FullTabVideoCompositorError, match="No page statistics provided"
    ):
        default_compositor.generate([], 10.0, output_path)


@patch.object(FullTabVideoCompositor, "_calculate_page_windows")
def test_generate_calculation_failure(
    mock_calc_windows,
    default_compositor,
    sample_page_statistics,
    temp_test_dir,
):
    """Test generation handles calculation failures."""
    mock_calc_windows.side_effect = Exception("Calculation failed")
    output_path = str(temp_test_dir / "full_tabs.mov")

    with pytest.raises(Exception, match="Calculation failed"):
        default_compositor.generate(sample_page_statistics, 17.0, output_path)


# Get Page Windows Tests


def test_get_page_windows_empty(default_compositor):
    """Test getting page windows when none exist."""
    windows = default_compositor.get_page_windows()
    assert windows == []


def test_get_page_windows_after_calculation(default_compositor, sample_page_statistics):
    """Test getting page windows after calculation."""
    default_compositor._page_windows = default_compositor._calculate_page_windows(
        sample_page_statistics
    )

    windows = default_compositor.get_page_windows()

    assert len(windows) == 3
    assert windows[0].page_name == "Page 1"
    assert windows[1].page_name == "Page 2"
    assert windows[2].page_name == "Page 3"


def test_get_page_windows_returns_copy(default_compositor, sample_page_statistics):
    """Test that get_page_windows returns a copy, not reference."""
    default_compositor._page_windows = default_compositor._calculate_page_windows(
        sample_page_statistics
    )

    windows1 = default_compositor.get_page_windows()
    windows2 = default_compositor.get_page_windows()

    assert windows1 is not windows2
    assert windows1 == windows2


# Edge Cases


def test_zero_duration_audio(default_compositor, sample_page_statistics, temp_test_dir):
    """Test handling of zero duration audio."""
    # This should be handled gracefully or raise appropriate error
    # Depending on implementation choice
    # Placeholder test - no assertions yet
    pass


def test_overlapping_pages(default_compositor, temp_test_dir):
    """Test handling of overlapping page timings."""
    overlapping_stats = [
        PageStatistics(
            page_name="Page 1",
            total_entries=5,
            start_time=0.0,
            end_time=5.0,
            duration=5.0,
            total_frames=150,
            lines_count=2,
            chords_count=5,
            output_file=str(temp_test_dir / "page1_tabs.mov"),
        ),
        PageStatistics(
            page_name="Page 2",
            total_entries=8,
            start_time=3.0,  # Overlaps with Page 1
            end_time=8.0,
            duration=5.0,
            total_frames=150,
            lines_count=3,
            chords_count=8,
            output_file=str(temp_test_dir / "page2_tabs.mov"),
        ),
    ]

    # Should still calculate windows, behavior depends on implementation
    windows = default_compositor._calculate_page_windows(overlapping_stats)
    assert len(windows) == 2


def test_very_short_gaps(default_compositor, temp_test_dir):
    """Test handling of very short gaps between pages."""
    close_stats = [
        PageStatistics(
            page_name="Page 1",
            total_entries=5,
            start_time=0.0,
            end_time=5.0,
            duration=5.0,
            total_frames=150,
            lines_count=2,
            chords_count=5,
            output_file=str(temp_test_dir / "page1_tabs.mov"),
        ),
        PageStatistics(
            page_name="Page 2",
            total_entries=8,
            start_time=5.005,  # 5ms gap (below 10ms threshold)
            end_time=10.0,
            duration=4.995,
            total_frames=149,
            lines_count=3,
            chords_count=8,
            output_file=str(temp_test_dir / "page2_tabs.mov"),
        ),
    ]

    windows = default_compositor._calculate_page_windows(close_stats)
    assert len(windows) == 2
