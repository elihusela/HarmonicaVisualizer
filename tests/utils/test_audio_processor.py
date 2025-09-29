"""Tests for utils.audio_processor module."""

from unittest.mock import patch, MagicMock
import subprocess

from utils.audio_processor import AudioProcessor


class TestAudioProcessorInitialization:
    """Test AudioProcessor initialization and parameter handling."""

    def test_audio_processor_default_initialization(self):
        """Test AudioProcessor with default parameters."""
        processor = AudioProcessor()

        # Test default values
        assert processor.low_freq == 200
        assert processor.high_freq == 5000
        assert processor.noise_reduction_db == -25
        assert processor.target_lufs == -16
        assert processor.true_peak_db == -1.5
        assert processor.lra == 11
        assert processor.sample_rate == 44100

    def test_audio_processor_custom_initialization(self):
        """Test AudioProcessor with custom parameters."""
        processor = AudioProcessor(
            low_freq=250,
            high_freq=3000,
            noise_reduction_db=-30,
            target_lufs=-14,
            true_peak_db=-2.0,
            lra=15,
            sample_rate=48000,
        )

        assert processor.low_freq == 250
        assert processor.high_freq == 3000
        assert processor.noise_reduction_db == -30
        assert processor.target_lufs == -14
        assert processor.true_peak_db == -2.0
        assert processor.lra == 15
        assert processor.sample_rate == 48000

    def test_audio_processor_edge_case_values(self):
        """Test AudioProcessor with edge case parameter values."""
        # Very narrow frequency range
        processor = AudioProcessor(low_freq=1000, high_freq=1500)
        assert processor.low_freq == 1000
        assert processor.high_freq == 1500

        # Extreme noise reduction
        processor_extreme = AudioProcessor(noise_reduction_db=-50)
        assert processor_extreme.noise_reduction_db == -50

        # High sample rate
        processor_high_sr = AudioProcessor(sample_rate=96000)
        assert processor_high_sr.sample_rate == 96000


class TestAudioProcessing:
    """Test audio processing functionality."""

    @patch("utils.audio_processor.subprocess.run")
    def test_process_for_midi_success(self, mock_subprocess):
        """Test successful audio processing."""
        mock_subprocess.return_value = MagicMock(returncode=0)

        processor = AudioProcessor()
        result = processor.process_for_midi("/path/input.wav", "/path/output.wav")

        assert result is True
        mock_subprocess.assert_called_once()

        # Verify subprocess call arguments
        call_args = mock_subprocess.call_args[0][0]  # First positional argument
        assert call_args[0] == "ffmpeg"
        assert "/path/input.wav" in call_args
        assert "/path/output.wav" in call_args

    @patch("utils.audio_processor.subprocess.run")
    def test_process_for_midi_subprocess_error(self, mock_subprocess):
        """Test audio processing with subprocess error."""
        mock_subprocess.side_effect = subprocess.CalledProcessError(
            1, "ffmpeg", stderr="Audio encoding failed"
        )

        processor = AudioProcessor()
        result = processor.process_for_midi("/path/input.wav", "/path/output.wav")

        assert result is False
        mock_subprocess.assert_called_once()

    @patch("utils.audio_processor.subprocess.run")
    def test_process_for_midi_ffmpeg_not_found(self, mock_subprocess):
        """Test audio processing when ffmpeg is not found."""
        mock_subprocess.side_effect = FileNotFoundError("ffmpeg not found")

        processor = AudioProcessor()
        result = processor.process_for_midi("/path/input.wav", "/path/output.wav")

        assert result is False
        mock_subprocess.assert_called_once()

    @patch("utils.audio_processor.subprocess.run")
    def test_process_for_midi_custom_parameters(self, mock_subprocess):
        """Test audio processing with custom parameters."""
        mock_subprocess.return_value = MagicMock(returncode=0)

        processor = AudioProcessor(
            low_freq=300, high_freq=4000, noise_reduction_db=-20, sample_rate=48000
        )

        result = processor.process_for_midi("/input.wav", "/output.wav")
        assert result is True

        # Verify custom parameters in ffmpeg command
        call_args = mock_subprocess.call_args[0][0]
        audio_filters_arg = None
        sample_rate_arg = None

        for i, arg in enumerate(call_args):
            if arg == "-af" and i + 1 < len(call_args):
                audio_filters_arg = call_args[i + 1]
            elif arg == "-ar" and i + 1 < len(call_args):
                sample_rate_arg = call_args[i + 1]

        assert "highpass=f=300" in audio_filters_arg
        assert "lowpass=f=4000" in audio_filters_arg
        assert "afftdn=nf=-20" in audio_filters_arg
        assert sample_rate_arg == "48000"


class TestFFmpegCommandBuilding:
    """Test ffmpeg command construction."""

    def test_build_ffmpeg_command_default(self):
        """Test ffmpeg command building with default parameters."""
        processor = AudioProcessor()
        cmd = processor._build_ffmpeg_command("/input.wav", "/output.wav")

        # Check basic structure
        assert cmd[0] == "ffmpeg"
        assert cmd[1] == "-i"
        assert cmd[2] == "/input.wav"
        assert cmd[3] == "-ac"
        assert cmd[4] == "1"  # Mono conversion
        assert cmd[5] == "-af"
        # cmd[6] is the audio filter string
        assert cmd[7] == "-ar"
        assert cmd[8] == "44100"
        assert cmd[9] == "-y"
        assert cmd[10] == "/output.wav"

    def test_build_ffmpeg_command_audio_filters(self):
        """Test audio filter string construction."""
        processor = AudioProcessor(
            low_freq=250,
            high_freq=3000,
            noise_reduction_db=-30,
            target_lufs=-14,
            true_peak_db=-2.0,
            lra=15,
        )

        cmd = processor._build_ffmpeg_command("/input.wav", "/output.wav")
        audio_filters = cmd[6]  # The -af argument value

        # Check all filter components
        assert "highpass=f=250" in audio_filters
        assert "lowpass=f=3000" in audio_filters
        assert "afftdn=nf=-30" in audio_filters
        assert "loudnorm=I=-14:TP=-2.0:LRA=15" in audio_filters

    def test_build_ffmpeg_command_custom_sample_rate(self):
        """Test ffmpeg command with custom sample rate."""
        processor = AudioProcessor(sample_rate=96000)
        cmd = processor._build_ffmpeg_command("/input.wav", "/output.wav")

        # Find sample rate argument
        ar_index = cmd.index("-ar")
        assert cmd[ar_index + 1] == "96000"

    def test_build_ffmpeg_command_special_paths(self):
        """Test ffmpeg command with special file paths."""
        processor = AudioProcessor()

        # Test with spaces in paths
        cmd = processor._build_ffmpeg_command(
            "/path with spaces/input.wav", "/output path/file.wav"
        )
        assert cmd[2] == "/path with spaces/input.wav"
        assert cmd[10] == "/output path/file.wav"

        # Test with long paths
        long_input = "/very/long/directory/structure/with/many/nested/folders/input.wav"
        long_output = "/another/very/long/path/structure/output.wav"
        cmd = processor._build_ffmpeg_command(long_input, long_output)
        assert cmd[2] == long_input
        assert cmd[10] == long_output


class TestParameterManagement:
    """Test parameter updating and management."""

    def test_get_processing_info(self):
        """Test getting current processing configuration."""
        processor = AudioProcessor(
            low_freq=300, high_freq=4000, noise_reduction_db=-20, target_lufs=-14
        )

        info = processor.get_processing_info()

        assert info["frequency_range"] == "300-4000 Hz"
        assert info["noise_reduction"] == "-20 dB"
        assert info["target_loudness"] == "-14 LUFS"
        assert info["true_peak"] == "-1.5 dB"  # Default value
        assert info["loudness_range"] == "11 LU"  # Default value
        assert info["sample_rate"] == "44100 Hz"  # Default value
        assert info["output_channels"] == "1 (mono)"

    def test_update_parameters_valid(self, capsys):
        """Test updating valid parameters."""
        processor = AudioProcessor()

        processor.update_parameters(
            low_freq=400, high_freq=6000, noise_reduction_db=-15
        )

        assert processor.low_freq == 400
        assert processor.high_freq == 6000
        assert processor.noise_reduction_db == -15

        # Check console output
        captured = capsys.readouterr()
        assert "🔧 Updated low_freq: 400" in captured.out
        assert "🔧 Updated high_freq: 6000" in captured.out
        assert "🔧 Updated noise_reduction_db: -15" in captured.out

    def test_update_parameters_invalid(self, capsys):
        """Test updating invalid parameters."""
        processor = AudioProcessor()

        processor.update_parameters(low_freq=500, invalid_param=123)  # Valid  # Invalid

        assert processor.low_freq == 500  # Valid update applied
        assert not hasattr(processor, "invalid_param")  # Invalid param not added

        # Check console output
        captured = capsys.readouterr()
        assert "🔧 Updated low_freq: 500" in captured.out
        assert "⚠️ Unknown parameter: invalid_param" in captured.out

    def test_update_parameters_empty(self):
        """Test updating with no parameters."""
        processor = AudioProcessor()
        original_values = {
            "low_freq": processor.low_freq,
            "high_freq": processor.high_freq,
            "noise_reduction_db": processor.noise_reduction_db,
        }

        processor.update_parameters()  # No parameters

        # Values should remain unchanged
        assert processor.low_freq == original_values["low_freq"]
        assert processor.high_freq == original_values["high_freq"]
        assert processor.noise_reduction_db == original_values["noise_reduction_db"]


class TestPresets:
    """Test preset configurations."""

    def test_get_recommended_presets_structure(self):
        """Test recommended presets structure and content."""
        presets = AudioProcessor.get_recommended_presets()

        # Check preset names exist
        assert "harmonica_default" in presets
        assert "harmonica_strict" in presets
        assert "general_melody" in presets
        assert "clean_studio" in presets

        # Check preset structure
        for preset_name, preset_config in presets.items():
            assert isinstance(preset_config, dict)
            assert "low_freq" in preset_config
            assert "high_freq" in preset_config
            assert "noise_reduction_db" in preset_config
            assert "target_lufs" in preset_config

    def test_harmonica_default_preset(self):
        """Test harmonica default preset values."""
        presets = AudioProcessor.get_recommended_presets()
        harmonica_default = presets["harmonica_default"]

        assert harmonica_default["low_freq"] == 200
        assert harmonica_default["high_freq"] == 5000
        assert harmonica_default["noise_reduction_db"] == -25
        assert harmonica_default["target_lufs"] == -16

    def test_harmonica_strict_preset(self):
        """Test harmonica strict preset values."""
        presets = AudioProcessor.get_recommended_presets()
        harmonica_strict = presets["harmonica_strict"]

        assert harmonica_strict["low_freq"] == 250
        assert harmonica_strict["high_freq"] == 3000
        assert harmonica_strict["noise_reduction_db"] == -30
        assert harmonica_strict["target_lufs"] == -14

    def test_preset_application(self, capsys):
        """Test applying preset to AudioProcessor instance."""
        processor = AudioProcessor()
        presets = AudioProcessor.get_recommended_presets()

        # Apply harmonica_strict preset
        strict_preset = presets["harmonica_strict"]
        processor.update_parameters(**strict_preset)

        assert processor.low_freq == 250
        assert processor.high_freq == 3000
        assert processor.noise_reduction_db == -30
        assert processor.target_lufs == -14

        # Check console output shows updates
        captured = capsys.readouterr()
        assert "🔧 Updated" in captured.out

    def test_preset_frequency_ranges_logical(self):
        """Test that preset frequency ranges are logical."""
        presets = AudioProcessor.get_recommended_presets()

        for preset_name, preset_config in presets.items():
            low_freq = preset_config["low_freq"]
            high_freq = preset_config["high_freq"]

            # High frequency should be greater than low frequency
            assert high_freq > low_freq, f"Invalid frequency range in {preset_name}"

            # Frequencies should be positive
            assert low_freq > 0, f"Invalid low frequency in {preset_name}"
            assert high_freq > 0, f"Invalid high frequency in {preset_name}"


class TestIntegration:
    """Test AudioProcessor integration scenarios."""

    @patch("utils.audio_processor.subprocess.run")
    def test_full_workflow_with_preset(self, mock_subprocess):
        """Test full workflow: create processor, apply preset, process audio."""
        mock_subprocess.return_value = MagicMock(returncode=0)

        # Create processor and apply harmonica_strict preset
        processor = AudioProcessor()
        presets = AudioProcessor.get_recommended_presets()
        processor.update_parameters(**presets["harmonica_strict"])

        # Process audio
        result = processor.process_for_midi("/input.wav", "/output.wav")

        assert result is True

        # Verify preset parameters were used in ffmpeg command
        call_args = mock_subprocess.call_args[0][0]
        audio_filters = call_args[6]  # The -af argument value

        assert "highpass=f=250" in audio_filters  # harmonica_strict low_freq
        assert "lowpass=f=3000" in audio_filters  # harmonica_strict high_freq
        assert "afftdn=nf=-30" in audio_filters  # harmonica_strict noise_reduction
        assert "loudnorm=I=-14" in audio_filters  # harmonica_strict target_lufs

    def test_multiple_parameter_updates(self):
        """Test multiple parameter updates maintain consistency."""
        processor = AudioProcessor()

        # Get initial info
        initial_info = processor.get_processing_info()

        # Update parameters multiple times
        processor.update_parameters(low_freq=300)
        processor.update_parameters(high_freq=4000, noise_reduction_db=-20)
        processor.update_parameters(target_lufs=-12)

        # Get final info
        final_info = processor.get_processing_info()

        # Verify updates were applied
        assert "300-4000 Hz" in final_info["frequency_range"]
        assert "-20 dB" in final_info["noise_reduction"]
        assert "-12 LUFS" in final_info["target_loudness"]

        # Verify unchanged parameters remain the same
        assert final_info["sample_rate"] == initial_info["sample_rate"]
        assert final_info["output_channels"] == initial_info["output_channels"]

    @patch("utils.audio_processor.subprocess.run")
    def test_error_handling_preserves_state(self, mock_subprocess):
        """Test that processing errors don't affect processor state."""
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "ffmpeg")

        processor = AudioProcessor(low_freq=400, high_freq=6000)

        # Processing should fail but state should be preserved
        result = processor.process_for_midi("/input.wav", "/output.wav")
        assert result is False

        # Processor state should be unchanged
        assert processor.low_freq == 400
        assert processor.high_freq == 6000

        # Should still be able to get info
        info = processor.get_processing_info()
        assert "400-6000 Hz" in info["frequency_range"]
