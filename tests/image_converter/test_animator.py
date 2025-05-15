from unittest.mock import patch, MagicMock

from tab_converter.models import TabEntry
from utils.utils import TEMP_DIR


class TestAnimator:

    @patch("image_converter.animator.os.remove")
    @patch("image_converter.animator.os.system")
    @patch("image_converter.animator.animation.FuncAnimation")
    def test_create_animation_pipeline_runs(
        self,
        mock_anim,
        mock_system,
        mock_remove,
        dummy_figure_factory,
        dummy_harmonica_layout,
        dummy_animator,
        dummy_tabs,
        tmp_path,
    ):
        fig_mock = MagicMock()
        ax_mock = MagicMock()
        dummy_figure_factory.create.return_value = (fig_mock, ax_mock)

        dummy_audio_path = tmp_path / "fake.wav"
        dummy_audio_path.write_bytes(b"FAKEAUDIO")
        output_path = str(tmp_path / "final.mp4")

        dummy_animator.create_animation(dummy_tabs, str(dummy_audio_path), output_path)

        mock_anim.return_value.save.assert_called_once()
        assert mock_system.call_count == 2
        called_args = [call.args[0] for call in mock_system.call_args_list]
        assert any(
            "colorkey" in cmd for cmd in called_args
        ), "Missing chroma key ffmpeg call"
        assert any(
            "aac" in cmd and "-shortest" in cmd for cmd in called_args
        ), "Missing audio merge ffmpeg call"
        assert mock_remove.call_count == 2
        mock_remove.assert_any_call(dummy_animator._temp_video_path)
        mock_remove.assert_any_call(TEMP_DIR + "temp_transparent.mov")

    def test_update_frame_blows_and_draws(
        self, dummy_animator, dummy_harmonica_layout, dummy_tabs
    ):
        dummy_animator._ax = MagicMock()
        dummy_harmonica_layout.hole_positions = {
            i: {
                "x": 100 + (i - 1) * 30,
                "y": 200,
                "width": 100,
                "height": 100,
            }
            for i in range(1, 3)
        }
        dummy_animator._text_objects = []
        dummy_animator._arrows = []

        # simulate a moment where both 1 and -2 are active
        result = dummy_animator._update_frame(frame=15, tabs=dummy_tabs, fps=30)

        assert len(result) == 4  # two text + two arrows
        assert all(call.remove.called is False for call in result)

    def test_update_frame_inactive_time(self, dummy_animator, dummy_tabs):
        dummy_animator._ax = MagicMock()
        dummy_animator._hole_positions = {1: (100, 200), 2: (130, 200), 3: (160, 200)}
        dummy_animator._text_objects = []
        dummy_animator._arrows = []

        # at a time with no active notes
        result = dummy_animator._update_frame(frame=100, tabs=dummy_tabs, fps=30)

        assert result == []

    def test_calc_direction_and_color(self, dummy_animator):
        assert dummy_animator._calc_direction(TabEntry(4, 0, 1)) == "↓"
        assert dummy_animator._calc_direction(TabEntry(-4, 0, 1)) == "↑"

        assert dummy_animator._get_color(TabEntry(5, 0, 1)) == "#41dd65"
        assert dummy_animator._get_color(TabEntry(-5, 0, 1)) == "#fd4444"
