from unittest.mock import patch, MagicMock

import pytest


class TestHarmonicaTabsPipeline:

    @pytest.mark.parametrize("save_midi", [True])
    def test_pipeline_saves_midi_when_enabled(self, configured_pipeline, save_midi):
        pipeline = configured_pipeline["pipeline"]
        pipeline._save_midi = save_midi

        with patch("harmonica_pipeline.harmonica_pipeline.clean_temp_folder") as mock_clean, \
                patch("harmonica_pipeline.harmonica_pipeline.predict",
                      return_value=(
                              None, configured_pipeline["midi_data"],
                              configured_pipeline["note_events"])) as mock_predict:
            pipeline.run()

            configured_pipeline["midi_data"].write.assert_called_once_with(pipeline._debug_midi_path)

    @pytest.mark.parametrize("save_midi", [False])
    def test_pipeline_skips_midi_write_when_disabled(self, configured_pipeline, save_midi):
        pipeline = configured_pipeline["pipeline"]
        pipeline._save_midi = save_midi

        with patch("harmonica_pipeline.harmonica_pipeline.clean_temp_folder"), \
                patch("harmonica_pipeline.harmonica_pipeline.predict",
                      return_value=(None, configured_pipeline["midi_data"], configured_pipeline["note_events"])):
            pipeline.run()

            configured_pipeline["midi_data"].write.assert_not_called()

    @pytest.mark.parametrize("one_note_melody", [True, False])
    def test_pipeline_one_note_melody_flag(self, dummy_pipeline, one_note_melody):
        dummy_pipeline._one_note_melody = one_note_melody

        fake_note_events = [(0.0, 1.0, 60, 0.9, [])]
        fake_midi = MagicMock()

        with patch("harmonica_pipeline.harmonica_pipeline.clean_temp_folder"), \
                patch("harmonica_pipeline.harmonica_pipeline.predict",
                      return_value=(None, fake_midi, fake_note_events)) as mock_predict:
            dummy_pipeline._extracted_audio_path = "fake.wav"
            dummy_pipeline._audio_to_midi()

            mock_predict.assert_called_once()
            args, kwargs = mock_predict.call_args
            assert kwargs["audio_path"] == "fake.wav"

    def test_pipeline_call_order(self, configured_pipeline):
        pipeline = configured_pipeline["pipeline"]

        with patch("harmonica_pipeline.harmonica_pipeline.clean_temp_folder") as mock_clean, \
                patch("harmonica_pipeline.harmonica_pipeline.predict",
                      return_value=(
                              None, configured_pipeline["midi_data"],
                              configured_pipeline["note_events"])) as mock_predict:
            pipeline.run()

            # Ensure order: audio → predict → tab mapping → save → animation
            configured_pipeline["pipeline"]._audio_extractor.extract_audio_from_video.assert_called_once()
            mock_predict.assert_called_once()
            configured_pipeline["pipeline"]._tab_mapper.note_events_to_tabs.assert_called_once()
            configured_pipeline["pipeline"]._tab_mapper.save_tabs_to_json.assert_called_once()
            configured_pipeline["pipeline"]._animator.create_animation.assert_called_once_with(
                configured_pipeline["tabs"], "audio.wav"
            )
