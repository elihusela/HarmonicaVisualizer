"""Tests for harmonica_pipeline.midi_generator - Audio to MIDI conversion."""

from unittest.mock import Mock, patch

import pytest

from harmonica_pipeline.midi_generator import MidiGenerator


class TestMidiGeneratorInitialization:
    """Test MidiGenerator initialization and setup."""

    @patch("harmonica_pipeline.midi_generator.AudioExtractor")
    @patch("harmonica_pipeline.midi_generator.AudioProcessor")
    def test_midi_generator_creation_video_input(
        self, mock_audio_processor, mock_audio_extractor, temp_test_dir
    ):
        """Test MidiGenerator creation with video input."""
        video_path = str(temp_test_dir / "test_video.mp4")
        output_path = str(temp_test_dir / "output.mid")

        generator = MidiGenerator(video_path, output_path)

        assert generator.video_path == video_path
        assert generator.output_midi_path == output_path
        assert generator.enable_audio_processing is True
        assert generator.is_video_input is True
        assert "extracted_audio.wav" in generator.extracted_audio_path
        assert "midi_ready_audio.wav" in generator.processed_audio_path

        # Verify components were initialized
        mock_audio_extractor.assert_called_once()
        mock_audio_processor.assert_called_once()

    @patch("harmonica_pipeline.midi_generator.AudioExtractor")
    @patch("harmonica_pipeline.midi_generator.AudioProcessor")
    def test_midi_generator_creation_wav_input(
        self, mock_audio_processor, mock_audio_extractor, temp_test_dir
    ):
        """Test MidiGenerator creation with WAV input."""
        wav_path = str(temp_test_dir / "test_audio.wav")
        output_path = str(temp_test_dir / "output.mid")

        generator = MidiGenerator(wav_path, output_path)

        assert generator.video_path == wav_path
        assert generator.output_midi_path == output_path
        assert generator.is_video_input is False

    @patch("harmonica_pipeline.midi_generator.AudioExtractor")
    @patch("harmonica_pipeline.midi_generator.AudioProcessor")
    def test_midi_generator_audio_processing_disabled(
        self, mock_audio_processor, mock_audio_extractor, temp_test_dir
    ):
        """Test MidiGenerator with audio processing disabled."""
        video_path = str(temp_test_dir / "test_video.mp4")
        output_path = str(temp_test_dir / "output.mid")

        generator = MidiGenerator(
            video_path, output_path, enable_audio_processing=False
        )

        assert generator.enable_audio_processing is False

    @patch("harmonica_pipeline.midi_generator.AudioExtractor")
    @patch("harmonica_pipeline.midi_generator.AudioProcessor")
    def test_midi_generator_file_type_detection(
        self, mock_audio_processor, mock_audio_extractor, temp_test_dir
    ):
        """Test file type detection for various extensions."""
        output_path = str(temp_test_dir / "output.mid")

        # Test various video formats
        video_formats = ["mp4", "MP4", "avi", "mov", "MOV", "mkv"]
        for ext in video_formats:
            video_path = str(temp_test_dir / f"test.{ext}")
            generator = MidiGenerator(video_path, output_path)
            assert generator.is_video_input is True

        # Test WAV format (case insensitive)
        wav_formats = ["wav", "WAV", "Wav"]
        for ext in wav_formats:
            wav_path = str(temp_test_dir / f"test.{ext}")
            generator = MidiGenerator(wav_path, output_path)
            assert generator.is_video_input is False


class TestMidiGeneratorAudioExtraction:
    """Test audio extraction functionality."""

    @patch("harmonica_pipeline.midi_generator.AudioExtractor")
    @patch("harmonica_pipeline.midi_generator.AudioProcessor")
    def test_extract_audio_success(
        self, mock_audio_processor, mock_audio_extractor, temp_test_dir
    ):
        """Test successful audio extraction from video."""
        video_path = str(temp_test_dir / "test_video.mp4")
        output_path = str(temp_test_dir / "output.mid")

        generator = MidiGenerator(video_path, output_path)

        # Mock the audio extractor
        mock_extractor = Mock()
        mock_extractor.extract_audio_from_video.return_value = "/path/to/extracted.wav"
        generator.audio_extractor = mock_extractor

        with patch("builtins.print"):
            generator._extract_audio()

        assert generator.extracted_audio_path == "/path/to/extracted.wav"
        mock_extractor.extract_audio_from_video.assert_called_once()

    @patch("harmonica_pipeline.midi_generator.AudioExtractor")
    @patch("harmonica_pipeline.midi_generator.AudioProcessor")
    def test_extract_audio_updates_path(
        self, mock_audio_processor, mock_audio_extractor, temp_test_dir
    ):
        """Test that audio extraction updates the extracted path."""
        video_path = str(temp_test_dir / "test_video.mp4")
        output_path = str(temp_test_dir / "output.mid")

        generator = MidiGenerator(video_path, output_path)
        original_path = generator.extracted_audio_path

        # Mock the audio extractor to return a different path
        mock_extractor = Mock()
        mock_extractor.extract_audio_from_video.return_value = "/new/path/audio.wav"
        generator.audio_extractor = mock_extractor

        with patch("builtins.print"):
            generator._extract_audio()

        assert generator.extracted_audio_path != original_path
        assert generator.extracted_audio_path == "/new/path/audio.wav"


class TestMidiGeneratorAudioProcessing:
    """Test audio processing functionality."""

    @patch("harmonica_pipeline.midi_generator.AudioExtractor")
    @patch("harmonica_pipeline.midi_generator.AudioProcessor")
    def test_process_audio_success(
        self, mock_audio_processor, mock_audio_extractor, temp_test_dir
    ):
        """Test successful audio processing."""
        video_path = str(temp_test_dir / "test_video.mp4")
        output_path = str(temp_test_dir / "output.mid")

        generator = MidiGenerator(video_path, output_path)
        generator.extracted_audio_path = "/path/to/extracted.wav"

        # Mock the audio processor
        mock_processor = Mock()
        mock_processor.process_for_midi.return_value = True
        generator.audio_processor = mock_processor

        generator._process_audio_for_midi()

        mock_processor.process_for_midi.assert_called_once_with(
            "/path/to/extracted.wav", generator.processed_audio_path
        )

    @patch("harmonica_pipeline.midi_generator.AudioExtractor")
    @patch("harmonica_pipeline.midi_generator.AudioProcessor")
    def test_process_audio_failure_fallback(
        self, mock_audio_processor, mock_audio_extractor, temp_test_dir
    ):
        """Test fallback when audio processing fails."""
        video_path = str(temp_test_dir / "test_video.mp4")
        output_path = str(temp_test_dir / "output.mid")

        generator = MidiGenerator(video_path, output_path)
        generator.extracted_audio_path = "/path/to/extracted.wav"

        # Mock the audio processor to fail
        mock_processor = Mock()
        mock_processor.process_for_midi.return_value = False
        generator.audio_processor = mock_processor

        with patch("builtins.print") as mock_print:
            generator._process_audio_for_midi()

        # Should fall back to unprocessed audio
        assert generator.processed_audio_path == generator.extracted_audio_path
        mock_print.assert_called_with(
            "⚠️ Audio processing failed, using unprocessed audio"
        )

    @patch("harmonica_pipeline.midi_generator.AudioExtractor")
    @patch("harmonica_pipeline.midi_generator.AudioProcessor")
    def test_process_audio_exception_handling(
        self, mock_audio_processor, mock_audio_extractor, temp_test_dir
    ):
        """Test handling of processing exceptions."""
        video_path = str(temp_test_dir / "test_video.mp4")
        output_path = str(temp_test_dir / "output.mid")

        generator = MidiGenerator(video_path, output_path)
        generator.extracted_audio_path = "/path/to/extracted.wav"

        # Mock the audio processor to raise an exception
        mock_processor = Mock()
        mock_processor.process_for_midi.side_effect = Exception("Processing error")
        generator.audio_processor = mock_processor

        with pytest.raises(Exception, match="Processing error"):
            generator._process_audio_for_midi()


class TestMidiGeneratorAudioToMidi:
    """Test MIDI conversion functionality."""

    @patch("harmonica_pipeline.midi_generator.AudioExtractor")
    @patch("harmonica_pipeline.midi_generator.AudioProcessor")
    def test_audio_to_midi_success(
        self, mock_audio_processor, mock_audio_extractor, temp_test_dir
    ):
        """Test successful audio to MIDI conversion."""
        video_path = str(temp_test_dir / "test_video.mp4")
        output_path = str(temp_test_dir / "output.mid")

        generator = MidiGenerator(video_path, output_path)
        generator.processed_audio_path = "/path/to/processed.wav"

        # Mock basic_pitch predict function
        mock_midi_data = Mock()
        mock_note_events = [
            ("note1", "data1"),
            ("note2", "data2"),
            ("note3", "data3"),
        ]

        with (
            patch(
                "harmonica_pipeline.midi_generator.predict",
                return_value=(None, mock_midi_data, mock_note_events),
            ),
            patch("builtins.print") as mock_print,
        ):
            generator._audio_to_midi()

        mock_midi_data.write.assert_called_once_with(output_path)
        mock_print.assert_any_call("🎵 Generated 3 note events")
        mock_print.assert_any_call(f"💾 MIDI saved to: {output_path}")

    @patch("harmonica_pipeline.midi_generator.AudioExtractor")
    @patch("harmonica_pipeline.midi_generator.AudioProcessor")
    def test_audio_to_midi_parameters(
        self, mock_audio_processor, mock_audio_extractor, temp_test_dir
    ):
        """Test that correct parameters are passed to basic_pitch."""
        video_path = str(temp_test_dir / "test_video.mp4")
        output_path = str(temp_test_dir / "output.mid")

        generator = MidiGenerator(video_path, output_path)
        generator.processed_audio_path = "/path/to/processed.wav"

        mock_midi_data = Mock()
        mock_note_events = []

        with (
            patch(
                "harmonica_pipeline.midi_generator.predict",
                return_value=(None, mock_midi_data, mock_note_events),
            ) as mock_predict,
            patch("builtins.print"),
        ):
            generator._audio_to_midi()

        # Verify correct parameters were passed
        mock_predict.assert_called_once()
        call_args = mock_predict.call_args
        assert call_args.kwargs["audio_path"] == "/path/to/processed.wav"
        assert call_args.kwargs["onset_threshold"] == 0.4
        assert call_args.kwargs["frame_threshold"] == 0.3

    @patch("harmonica_pipeline.midi_generator.AudioExtractor")
    @patch("harmonica_pipeline.midi_generator.AudioProcessor")
    def test_audio_to_midi_empty_events(
        self, mock_audio_processor, mock_audio_extractor, temp_test_dir
    ):
        """Test handling of empty note events."""
        video_path = str(temp_test_dir / "test_video.mp4")
        output_path = str(temp_test_dir / "output.mid")

        generator = MidiGenerator(video_path, output_path)
        generator.processed_audio_path = "/path/to/processed.wav"

        mock_midi_data = Mock()
        mock_note_events = []

        with (
            patch(
                "harmonica_pipeline.midi_generator.predict",
                return_value=(None, mock_midi_data, mock_note_events),
            ),
            patch("builtins.print") as mock_print,
        ):
            generator._audio_to_midi()

        mock_print.assert_any_call("🎵 Generated 0 note events")


class TestMidiGeneratorWavSaving:
    """Test WAV saving functionality for reuse."""

    @patch("harmonica_pipeline.midi_generator.AudioExtractor")
    @patch("harmonica_pipeline.midi_generator.AudioProcessor")
    def test_save_wav_for_reuse_success(
        self, mock_audio_processor, mock_audio_extractor, temp_test_dir
    ):
        """Test successful WAV saving for reuse."""
        video_path = str(temp_test_dir / "test_video.mp4")
        output_path = str(temp_test_dir / "output.mid")

        generator = MidiGenerator(video_path, output_path)
        generator.extracted_audio_path = str(temp_test_dir / "extracted.wav")

        # Create a mock extracted audio file
        extracted_file = temp_test_dir / "extracted.wav"
        extracted_file.write_text("mock audio data")

        with (
            patch(
                "harmonica_pipeline.midi_generator.VIDEO_FILES_DIR",
                str(temp_test_dir) + "/",
            ),
            patch("builtins.print") as mock_print,
        ):
            generator._save_extracted_wav_for_reuse()

        # Check that file was copied
        expected_path = temp_test_dir / "test_video.wav"
        assert expected_path.exists()
        assert expected_path.read_text() == "mock audio data"

        # Check print messages
        mock_print.assert_any_call(
            f"💾 Extracted WAV saved for reuse: {str(expected_path)}"
        )
        mock_print.assert_any_call(
            "   Use for Phase 2: python cli.py create-video test_video.wav <tabs.txt>"
        )

    @patch("harmonica_pipeline.midi_generator.AudioExtractor")
    @patch("harmonica_pipeline.midi_generator.AudioProcessor")
    def test_save_wav_for_reuse_failure(
        self, mock_audio_processor, mock_audio_extractor, temp_test_dir
    ):
        """Test handling of WAV saving failure."""
        video_path = str(temp_test_dir / "test_video.mp4")
        output_path = str(temp_test_dir / "output.mid")

        generator = MidiGenerator(video_path, output_path)
        generator.extracted_audio_path = "/nonexistent/path.wav"

        with (
            patch(
                "harmonica_pipeline.midi_generator.VIDEO_FILES_DIR",
                str(temp_test_dir) + "/",
            ),
            patch("builtins.print") as mock_print,
        ):
            generator._save_extracted_wav_for_reuse()

        # Check error handling
        mock_print.assert_any_call(
            "⚠️ Could not save extracted WAV: [Errno 2] No such file or directory: '/nonexistent/path.wav'"
        )

    @patch("harmonica_pipeline.midi_generator.AudioExtractor")
    @patch("harmonica_pipeline.midi_generator.AudioProcessor")
    def test_save_wav_complex_filename(
        self, mock_audio_processor, mock_audio_extractor, temp_test_dir
    ):
        """Test WAV saving with complex video filename."""
        video_path = str(temp_test_dir / "My Video File (2024).mp4")
        output_path = str(temp_test_dir / "output.mid")

        generator = MidiGenerator(video_path, output_path)
        generator.extracted_audio_path = str(temp_test_dir / "extracted.wav")

        # Create a mock extracted audio file
        extracted_file = temp_test_dir / "extracted.wav"
        extracted_file.write_text("mock audio data")

        with (
            patch(
                "harmonica_pipeline.midi_generator.VIDEO_FILES_DIR",
                str(temp_test_dir) + "/",
            ),
            patch("builtins.print"),
        ):
            generator._save_extracted_wav_for_reuse()

        # Check that file was saved with correct base name
        expected_path = temp_test_dir / "My Video File (2024).wav"
        assert expected_path.exists()


class TestMidiGeneratorMainGenerate:
    """Test the main generate() method integration."""

    @patch("harmonica_pipeline.midi_generator.AudioExtractor")
    @patch("harmonica_pipeline.midi_generator.AudioProcessor")
    def test_generate_video_input_full_pipeline(
        self, mock_audio_processor, mock_audio_extractor, temp_test_dir
    ):
        """Test complete generation pipeline with video input."""
        video_path = str(temp_test_dir / "test_video.mp4")
        output_path = str(temp_test_dir / "output.mid")

        generator = MidiGenerator(video_path, output_path)

        # Mock all dependencies
        with (
            patch.object(generator, "_extract_audio") as mock_extract,
            patch.object(generator, "_process_audio_for_midi") as mock_process,
            patch.object(generator, "_audio_to_midi") as mock_midi,
            patch.object(generator, "_save_extracted_wav_for_reuse") as mock_save,
            patch("harmonica_pipeline.midi_generator.clean_temp_folder") as mock_clean,
            patch("builtins.print"),
        ):
            generator.generate()

        # Verify all steps were called
        mock_clean.assert_called_once()
        mock_extract.assert_called_once()
        mock_process.assert_called_once()
        mock_midi.assert_called_once()
        mock_save.assert_called_once()

    @patch("harmonica_pipeline.midi_generator.AudioExtractor")
    @patch("harmonica_pipeline.midi_generator.AudioProcessor")
    def test_generate_wav_input_pipeline(
        self, mock_audio_processor, mock_audio_extractor, temp_test_dir
    ):
        """Test generation pipeline with WAV input."""
        wav_path = str(temp_test_dir / "test_audio.wav")
        output_path = str(temp_test_dir / "output.mid")

        generator = MidiGenerator(wav_path, output_path)

        # Mock all dependencies
        with (
            patch.object(generator, "_extract_audio") as mock_extract,
            patch.object(generator, "_process_audio_for_midi") as mock_process,
            patch.object(generator, "_audio_to_midi") as mock_midi,
            patch.object(generator, "_save_extracted_wav_for_reuse") as mock_save,
            patch("harmonica_pipeline.midi_generator.clean_temp_folder") as mock_clean,
            patch("builtins.print"),
        ):
            generator.generate()

        # Verify steps for WAV input
        mock_clean.assert_called_once()
        mock_extract.assert_not_called()  # Skip extraction for WAV
        mock_process.assert_called_once()
        mock_midi.assert_called_once()
        mock_save.assert_not_called()  # Skip saving for WAV input

        # Check that WAV path is used directly
        assert generator.extracted_audio_path == wav_path

    @patch("harmonica_pipeline.midi_generator.AudioExtractor")
    @patch("harmonica_pipeline.midi_generator.AudioProcessor")
    def test_generate_no_audio_processing(
        self, mock_audio_processor, mock_audio_extractor, temp_test_dir
    ):
        """Test generation pipeline with audio processing disabled."""
        video_path = str(temp_test_dir / "test_video.mp4")
        output_path = str(temp_test_dir / "output.mid")

        generator = MidiGenerator(
            video_path, output_path, enable_audio_processing=False
        )

        # Mock all dependencies
        with (
            patch.object(generator, "_extract_audio") as mock_extract,
            patch.object(generator, "_process_audio_for_midi") as mock_process,
            patch.object(generator, "_audio_to_midi") as mock_midi,
            patch.object(generator, "_save_extracted_wav_for_reuse") as mock_save,
            patch("harmonica_pipeline.midi_generator.clean_temp_folder") as mock_clean,
            patch("builtins.print"),
        ):
            generator.generate()

        # Verify processing was skipped
        mock_clean.assert_called_once()
        mock_extract.assert_called_once()
        mock_process.assert_not_called()  # Processing disabled
        mock_midi.assert_called_once()
        mock_save.assert_called_once()

        # Check that processed path equals extracted path
        assert generator.processed_audio_path == generator.extracted_audio_path

    @patch("harmonica_pipeline.midi_generator.AudioExtractor")
    @patch("harmonica_pipeline.midi_generator.AudioProcessor")
    def test_generate_print_messages(
        self, mock_audio_processor, mock_audio_extractor, temp_test_dir
    ):
        """Test that correct progress messages are printed."""
        video_path = str(temp_test_dir / "test_video.mp4")
        output_path = str(temp_test_dir / "output.mid")

        generator = MidiGenerator(video_path, output_path)

        # Mock all dependencies
        with (
            patch.object(generator, "_extract_audio"),
            patch.object(generator, "_process_audio_for_midi"),
            patch.object(generator, "_audio_to_midi"),
            patch.object(generator, "_save_extracted_wav_for_reuse"),
            patch("harmonica_pipeline.midi_generator.clean_temp_folder"),
            patch("builtins.print") as mock_print,
        ):
            generator.generate()

        # Check expected print messages
        print_calls = [call.args[0] for call in mock_print.call_args_list]
        assert "🧹 Cleaning temporary files..." in print_calls
        assert "🎬 Step 1: Extracting audio from video..." in print_calls
        assert "🎛️ Step 2: Processing audio for MIDI conversion..." in print_calls
        assert "🎼 Step 3: Converting audio to MIDI..." in print_calls
        assert "💾 MIDI generation complete!" in print_calls

    @patch("harmonica_pipeline.midi_generator.AudioExtractor")
    @patch("harmonica_pipeline.midi_generator.AudioProcessor")
    def test_generate_wav_input_messages(
        self, mock_audio_processor, mock_audio_extractor, temp_test_dir
    ):
        """Test print messages for WAV input."""
        wav_path = str(temp_test_dir / "test_audio.wav")
        output_path = str(temp_test_dir / "output.mid")

        generator = MidiGenerator(wav_path, output_path)

        with (
            patch.object(generator, "_process_audio_for_midi"),
            patch.object(generator, "_audio_to_midi"),
            patch("harmonica_pipeline.midi_generator.clean_temp_folder"),
            patch("builtins.print") as mock_print,
        ):
            generator.generate()

        # Check WAV-specific message
        print_calls = [call.args[0] for call in mock_print.call_args_list]
        assert "🎵 Step 1: Using WAV file directly..." in print_calls

    @patch("harmonica_pipeline.midi_generator.AudioExtractor")
    @patch("harmonica_pipeline.midi_generator.AudioProcessor")
    def test_generate_no_processing_messages(
        self, mock_audio_processor, mock_audio_extractor, temp_test_dir
    ):
        """Test print messages when processing is disabled."""
        video_path = str(temp_test_dir / "test_video.mp4")
        output_path = str(temp_test_dir / "output.mid")

        generator = MidiGenerator(
            video_path, output_path, enable_audio_processing=False
        )

        with (
            patch.object(generator, "_extract_audio"),
            patch.object(generator, "_audio_to_midi"),
            patch.object(generator, "_save_extracted_wav_for_reuse"),
            patch("harmonica_pipeline.midi_generator.clean_temp_folder"),
            patch("builtins.print") as mock_print,
        ):
            generator.generate()

        # Check skip processing message
        print_calls = [call.args[0] for call in mock_print.call_args_list]
        assert "⏭️  Step 2: Skipping audio processing..." in print_calls


class TestMidiGeneratorIntegration:
    """Integration tests combining multiple MidiGenerator features."""

    def test_real_file_paths_integration(self, temp_test_dir):
        """Test with realistic file paths and directory structures."""
        # Create test video file
        video_file = temp_test_dir / "test_video.mp4"
        video_file.write_bytes(b"fake video data")

        output_file = temp_test_dir / "output.mid"

        generator = MidiGenerator(str(video_file), str(output_file))

        # Verify paths are set correctly
        assert generator.video_path == str(video_file)
        assert generator.output_midi_path == str(output_file)
        assert video_file.exists()

    @patch("harmonica_pipeline.midi_generator.AudioExtractor")
    @patch("harmonica_pipeline.midi_generator.AudioProcessor")
    def test_path_handling_edge_cases(
        self, mock_audio_processor, mock_audio_extractor, temp_test_dir
    ):
        """Test handling of various path formats."""
        # Test relative paths
        video_path = "relative/path/video.mp4"
        output_path = "relative/output.mid"

        generator = MidiGenerator(video_path, output_path)
        assert generator.video_path == video_path
        assert generator.output_midi_path == output_path

        # Test paths with spaces and special characters
        special_video = str(temp_test_dir / "My Video (2024) - Test!.mp4")
        special_output = str(temp_test_dir / "My Output [Final].mid")

        generator = MidiGenerator(special_video, special_output)
        assert generator.video_path == special_video
        assert generator.output_midi_path == special_output

    @patch("harmonica_pipeline.midi_generator.AudioExtractor")
    @patch("harmonica_pipeline.midi_generator.AudioProcessor")
    def test_component_initialization(
        self, mock_audio_processor, mock_audio_extractor, temp_test_dir
    ):
        """Test that all components are properly initialized."""
        video_path = str(temp_test_dir / "test.mp4")
        output_path = str(temp_test_dir / "output.mid")

        generator = MidiGenerator(video_path, output_path)

        # Check that components exist and have expected types
        assert hasattr(generator, "audio_extractor")
        assert hasattr(generator, "audio_processor")
        assert generator.audio_extractor is not None
        assert generator.audio_processor is not None

    @patch("harmonica_pipeline.midi_generator.AudioExtractor")
    @patch("harmonica_pipeline.midi_generator.AudioProcessor")
    def test_error_handling_integration(
        self, mock_audio_processor, mock_audio_extractor, temp_test_dir
    ):
        """Test error handling across the pipeline."""
        video_path = str(temp_test_dir / "test.mp4")
        output_path = str(temp_test_dir / "output.mid")

        generator = MidiGenerator(video_path, output_path)

        # Test that exceptions from components are properly propagated
        with patch.object(
            generator.audio_extractor,
            "extract_audio_from_video",
            side_effect=Exception("Extraction failed"),
        ):
            with pytest.raises(Exception, match="Extraction failed"):
                generator._extract_audio()

    @patch("harmonica_pipeline.midi_generator.AudioExtractor")
    @patch("harmonica_pipeline.midi_generator.AudioProcessor")
    def test_temp_directory_usage(
        self, mock_audio_processor, mock_audio_extractor, temp_test_dir
    ):
        """Test temporary directory path generation."""
        video_path = str(temp_test_dir / "test.mp4")
        output_path = str(temp_test_dir / "output.mid")

        generator = MidiGenerator(video_path, output_path)

        # Check that temp paths are generated correctly
        assert "extracted_audio.wav" in generator.extracted_audio_path
        assert "midi_ready_audio.wav" in generator.processed_audio_path
        assert generator.extracted_audio_path != generator.processed_audio_path
