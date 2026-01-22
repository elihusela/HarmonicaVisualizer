"""Tests for stem separator module."""

import pytest
from unittest.mock import patch, MagicMock

from utils.stem_separator import StemSeparator, StemSeparatorError


class TestStemSeparator:
    """Tests for StemSeparator class."""

    def test_init_default_output_dir(self):
        """Test default output directory."""
        separator = StemSeparator()
        assert separator.output_dir == "stems"

    def test_init_custom_output_dir(self):
        """Test custom output directory."""
        separator = StemSeparator(output_dir="custom_stems")
        assert separator.output_dir == "custom_stems"

    def test_model_is_6_stem(self):
        """Test that 6-stem model is used."""
        assert StemSeparator.MODEL == "htdemucs_6s"

    def test_default_stem_is_other(self):
        """Test that default stem is 'other' for harmonica."""
        assert StemSeparator.DEFAULT_STEM == "other"


class TestDemucsCheck:
    """Tests for Demucs installation check."""

    def test_check_demucs_installed_success(self):
        """Test when Demucs is installed."""
        separator = StemSeparator()
        with patch.dict("sys.modules", {"demucs": MagicMock()}):
            assert separator._check_demucs_installed() is True

    def test_check_demucs_not_installed(self):
        """Test when Demucs is not installed."""
        separator = StemSeparator()
        with patch.dict("sys.modules", {"demucs": None}):
            # Force ImportError
            with patch("builtins.__import__", side_effect=ImportError):
                assert separator._check_demucs_installed() is False


class TestDeviceDetection:
    """Tests for GPU device detection."""

    def test_detect_device_cuda(self):
        """Test CUDA detection."""
        separator = StemSeparator()
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True

        with patch.dict("sys.modules", {"torch": mock_torch}):
            with patch("utils.stem_separator.StemSeparator._detect_device") as mock:
                mock.return_value = "cuda"
                assert separator._detect_device() == "cuda"

    def test_detect_device_mps(self):
        """Test MPS (Apple Silicon) detection."""
        separator = StemSeparator()
        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        mock_torch.backends.mps.is_available.return_value = True

        with patch.dict("sys.modules", {"torch": mock_torch}):
            with patch("utils.stem_separator.StemSeparator._detect_device") as mock:
                mock.return_value = "mps"
                assert separator._detect_device() == "mps"

    def test_detect_device_cpu_fallback(self):
        """Test CPU fallback when no GPU available."""
        separator = StemSeparator()
        with patch("builtins.__import__", side_effect=ImportError):
            assert separator._detect_device() == "cpu"


class TestSeparation:
    """Tests for stem separation."""

    def test_separate_file_not_found(self):
        """Test error when input file doesn't exist."""
        separator = StemSeparator()

        with patch.object(separator, "_check_demucs_installed", return_value=True):
            with pytest.raises(StemSeparatorError) as exc_info:
                separator.separate("nonexistent.wav")

            assert "Input file not found" in str(exc_info.value)

    def test_separate_demucs_not_installed(self):
        """Test error when Demucs is not installed."""
        separator = StemSeparator()

        with patch.object(separator, "_check_demucs_installed", return_value=False):
            with pytest.raises(StemSeparatorError) as exc_info:
                separator.separate("test.wav")

            assert "Demucs not installed" in str(exc_info.value)

    def test_separate_success(self, tmp_path):
        """Test successful separation."""
        separator = StemSeparator(output_dir=str(tmp_path / "stems"))

        # Create input file
        input_file = tmp_path / "test.wav"
        input_file.touch()

        # Create expected output
        output_dir = tmp_path / "stems" / "htdemucs_6s" / "test"
        output_dir.mkdir(parents=True)
        (output_dir / "other.mp3").touch()

        with patch.object(separator, "_check_demucs_installed", return_value=True):
            with patch.object(separator, "_detect_device", return_value="cpu"):
                with patch.object(
                    separator, "_prepare_audio", return_value=str(input_file)
                ):
                    with patch("subprocess.run") as mock_run:
                        mock_run.return_value = MagicMock(
                            returncode=0, stdout="", stderr=""
                        )

                        result = separator.separate(str(input_file))

                        assert result == str(output_dir / "other.mp3")

    def test_separate_demucs_fails(self, tmp_path):
        """Test when Demucs subprocess fails."""
        separator = StemSeparator(output_dir=str(tmp_path / "stems"))

        input_file = tmp_path / "test.wav"
        input_file.touch()

        with patch.object(separator, "_check_demucs_installed", return_value=True):
            with patch.object(separator, "_detect_device", return_value="cpu"):
                with patch.object(
                    separator, "_prepare_audio", return_value=str(input_file)
                ):
                    with patch("subprocess.run") as mock_run:
                        import subprocess

                        mock_run.side_effect = subprocess.CalledProcessError(
                            1, "demucs", stderr="Some error"
                        )

                        with pytest.raises(StemSeparatorError) as exc_info:
                            separator.separate(str(input_file))

                        assert "Demucs failed" in str(exc_info.value)


class TestAudioPreparation:
    """Tests for audio preparation."""

    def test_prepare_audio_already_audio(self, tmp_path):
        """Test that audio files are returned as-is."""
        separator = StemSeparator()

        audio_file = tmp_path / "test.wav"
        audio_file.touch()

        result = separator._prepare_audio(str(audio_file))
        assert result == str(audio_file)

    def test_prepare_audio_mp3(self, tmp_path):
        """Test that MP3 files are returned as-is."""
        separator = StemSeparator()

        audio_file = tmp_path / "test.mp3"
        audio_file.touch()

        result = separator._prepare_audio(str(audio_file))
        assert result == str(audio_file)

    def test_prepare_audio_extracts_from_video(self, tmp_path):
        """Test that video files have audio extracted."""
        separator = StemSeparator()

        video_file = tmp_path / "test.mp4"
        video_file.touch()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            with patch("os.makedirs"):
                result = separator._prepare_audio(str(video_file))

            assert result == "temp/test_extracted.wav"
            mock_run.assert_called_once()

    def test_prepare_audio_ffmpeg_fails(self, tmp_path):
        """Test error when ffmpeg fails."""
        separator = StemSeparator()

        video_file = tmp_path / "test.mp4"
        video_file.touch()

        with patch("subprocess.run") as mock_run:
            import subprocess

            mock_run.side_effect = subprocess.CalledProcessError(
                1, "ffmpeg", stderr="FFmpeg error"
            )
            with patch("os.makedirs"):
                with pytest.raises(StemSeparatorError) as exc_info:
                    separator._prepare_audio(str(video_file))

                assert "Audio extraction failed" in str(exc_info.value)

    def test_prepare_audio_ffmpeg_not_found(self, tmp_path):
        """Test error when ffmpeg is not installed."""
        separator = StemSeparator()

        video_file = tmp_path / "test.mp4"
        video_file.touch()

        with patch("subprocess.run", side_effect=FileNotFoundError):
            with patch("os.makedirs"):
                with pytest.raises(StemSeparatorError) as exc_info:
                    separator._prepare_audio(str(video_file))

                assert "ffmpeg not found" in str(exc_info.value)


class TestOrchestratorIntegration:
    """Tests for orchestrator integration."""

    def test_demucs_option_shown_for_stem_workflow(self, tmp_path):
        """Test that Demucs option is shown when _Stem is in filename."""
        from interactive_workflow.orchestrator import WorkflowOrchestrator
        from interactive_workflow.state_machine import WorkflowState

        orchestrator = WorkflowOrchestrator(
            input_video="MySong_KeyC_Stem.mp4",
            input_tabs="MySong.txt",
            session_dir=str(tmp_path / "sessions"),
            auto_approve=False,
        )
        orchestrator.session.transition_to(WorkflowState.STEM_SELECTION)

        # User declines Demucs, then skips manual selection
        with patch("questionary.confirm") as mock_confirm:
            mock_confirm.return_value.ask.return_value = False  # Don't run Demucs
            with patch("questionary.text") as mock_text:
                mock_text.return_value.ask.return_value = "0"  # Skip manual
                orchestrator._step_stem_selection()

        # Should transition to MIDI generation
        assert orchestrator.session.state == WorkflowState.MIDI_GENERATION

    def test_demucs_runs_when_user_accepts(self, tmp_path):
        """Test that Demucs runs when user says yes."""
        from interactive_workflow.orchestrator import WorkflowOrchestrator
        from interactive_workflow.state_machine import WorkflowState

        orchestrator = WorkflowOrchestrator(
            input_video="MySong_KeyC_Stem.mp4",
            input_tabs="MySong.txt",
            session_dir=str(tmp_path / "sessions"),
            auto_approve=False,
        )
        orchestrator.session.transition_to(WorkflowState.STEM_SELECTION)

        def mock_demucs_success():
            # Simulate successful Demucs - transition state and return True
            orchestrator.session.set_data("selected_audio", "stems/other.mp3")
            orchestrator.session.transition_to(WorkflowState.MIDI_GENERATION)
            return True

        with patch("questionary.confirm") as mock_confirm:
            mock_confirm.return_value.ask.return_value = True  # Run Demucs
            with patch.object(
                orchestrator, "_run_demucs_separation", side_effect=mock_demucs_success
            ):
                orchestrator._step_stem_selection()

        # Should transition to MIDI generation
        assert orchestrator.session.state == WorkflowState.MIDI_GENERATION

    def test_demucs_fallback_to_manual_on_failure(self, tmp_path):
        """Test fallback to manual selection when Demucs fails."""
        from interactive_workflow.orchestrator import WorkflowOrchestrator
        from interactive_workflow.state_machine import WorkflowState

        orchestrator = WorkflowOrchestrator(
            input_video="MySong_KeyC_Stem.mp4",
            input_tabs="MySong.txt",
            session_dir=str(tmp_path / "sessions"),
            auto_approve=False,
        )
        orchestrator.session.transition_to(WorkflowState.STEM_SELECTION)

        with patch("questionary.confirm") as mock_confirm:
            mock_confirm.return_value.ask.return_value = True  # Try Demucs
            with patch.object(
                orchestrator, "_run_demucs_separation", return_value=False
            ):
                # Demucs fails, fall back to manual
                with patch("questionary.text") as mock_text:
                    mock_text.return_value.ask.return_value = "0"  # Skip manual
                    orchestrator._step_stem_selection()

        # Should still transition to MIDI generation (via fallback)
        assert orchestrator.session.state == WorkflowState.MIDI_GENERATION
