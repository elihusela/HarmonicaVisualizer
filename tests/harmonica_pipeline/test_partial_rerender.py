"""Tests for partial re-render functionality (Feature 2).

These tests verify that the partial re-render infrastructure is in place:
- Methods exist on VideoCreator
- Method signatures are correct
- time_range parameter is supported in animators
"""

from inspect import signature

from harmonica_pipeline.video_creator import VideoCreator
from image_converter.animator import Animator
from tab_phrase_animator.tab_phrase_animator import TabPhraseAnimator


class TestPartialRerenderMethodsExist:
    """Verify partial re-render methods exist on VideoCreator."""

    def test_render_harmonica_segment_exists(self):
        """Test that render_harmonica_segment method exists."""
        assert hasattr(VideoCreator, "render_harmonica_segment")
        assert callable(getattr(VideoCreator, "render_harmonica_segment"))

    def test_render_tab_segment_exists(self):
        """Test that render_tab_segment method exists."""
        assert hasattr(VideoCreator, "render_tab_segment")
        assert callable(getattr(VideoCreator, "render_tab_segment"))

    def test_splice_harmonica_fix_exists(self):
        """Test that splice_harmonica_fix method exists."""
        assert hasattr(VideoCreator, "splice_harmonica_fix")
        assert callable(getattr(VideoCreator, "splice_harmonica_fix"))

    def test_splice_tab_fix_exists(self):
        """Test that splice_tab_fix method exists."""
        assert hasattr(VideoCreator, "splice_tab_fix")
        assert callable(getattr(VideoCreator, "splice_tab_fix"))


class TestPartialRerenderSignatures:
    """Verify method signatures support partial re-render."""

    def test_render_harmonica_segment_signature(self):
        """Test render_harmonica_segment has correct parameters."""
        sig = signature(VideoCreator.render_harmonica_segment)
        params = list(sig.parameters.keys())

        # Should accept start_time, end_time, output_path
        assert "start_time" in params
        assert "end_time" in params
        assert "output_path" in params

    def test_render_tab_segment_signature(self):
        """Test render_tab_segment has correct parameters."""
        sig = signature(VideoCreator.render_tab_segment)
        params = list(sig.parameters.keys())

        assert "start_time" in params
        assert "end_time" in params
        assert "output_path" in params

    def test_splice_harmonica_fix_signature(self):
        """Test splice_harmonica_fix has correct parameters."""
        sig = signature(VideoCreator.splice_harmonica_fix)
        params = list(sig.parameters.keys())

        assert "original_video_path" in params
        assert "start_time" in params
        assert "end_time" in params
        assert "output_path" in params

    def test_splice_tab_fix_signature(self):
        """Test splice_tab_fix has correct parameters."""
        sig = signature(VideoCreator.splice_tab_fix)
        params = list(sig.parameters.keys())

        assert "original_video_path" in params
        assert "start_time" in params
        assert "end_time" in params
        assert "output_path" in params


class TestAnimatorTimeRangeSupport:
    """Verify animators support time_range parameter."""

    def test_animator_create_animation_has_time_range(self):
        """Test that Animator.create_animation accepts time_range."""
        sig = signature(Animator.create_animation)
        assert "time_range" in sig.parameters

    def test_animator_create_animation_has_force_full_render(self):
        """Test that Animator.create_animation accepts force_full_render."""
        sig = signature(Animator.create_animation)
        assert "force_full_render" in sig.parameters

    def test_tab_animator_create_animations_has_time_range(self):
        """Test that TabPhraseAnimator.create_animations accepts time_range."""
        sig = signature(TabPhraseAnimator.create_animations)
        assert "time_range" in sig.parameters


class TestPartialRerenderDocumentation:
    """Document the partial re-render workflow."""

    def test_partial_rerender_workflow_documented(self):
        """Document intended use case for partial re-render.

        Workflow:
        1. User generates full video: creator.create(create_harmonica=True)
           Output: song_harmonica.mp4

        2. User notices mistake at 5.0-6.0 seconds
           User fixes MIDI in DAW

        3. Render only the affected segment:
           segment = creator.render_harmonica_segment(4.5, 6.5, "segment.mp4")

        4. Splice fixed segment back into original:
           result = creator.splice_harmonica_fix(
               "song_harmonica.mp4",
               start_time=4.5,
               end_time=6.5,
               output_path="song_harmonica_fixed.mp4"
           )

        Result: song_harmonica_fixed.mp4 with segment at 4.5-6.5s re-rendered
        - Rest of video unchanged (saves ~70-90% render time for sparse fixes)
        - FFmpeg concat ensures frame-accurate splicing
        """
        pass  # This is a documentation test

    def test_video_splicer_available(self):
        """Test that video_splicer is available for splice operations."""
        from utils.video_splicer import splice_video_segment, VideoSplicerError

        assert callable(splice_video_segment)
        assert issubclass(VideoSplicerError, Exception)
