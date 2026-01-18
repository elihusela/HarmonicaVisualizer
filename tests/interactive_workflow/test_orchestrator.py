"""Tests for workflow orchestrator."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from interactive_workflow.orchestrator import WorkflowOrchestrator
from interactive_workflow.state_machine import WorkflowState


class TestOrchestratorInitialization:
    """Tests for WorkflowOrchestrator initialization."""

    def test_create_new_orchestrator(self, tmp_path):
        """Test creating a new orchestrator instance."""
        session_dir = tmp_path / "sessions"

        orchestrator = WorkflowOrchestrator(
            input_video="MySong_KeyG.mp4",
            input_tabs="MySong.txt",
            session_dir=str(session_dir),
            auto_approve=True,
        )

        assert orchestrator.filename_config.song_name == "MySong"
        assert orchestrator.filename_config.key == "G"
        assert orchestrator.session.song_name == "MySong"
        assert orchestrator.session.state == WorkflowState.INIT

    def test_session_file_path_generation(self, tmp_path):
        """Test session file path is generated correctly."""
        session_dir = tmp_path / "sessions"

        orchestrator = WorkflowOrchestrator(
            input_video="TestSong_KeyC.mp4",
            input_tabs="test.txt",
            session_dir=str(session_dir),
            auto_approve=True,
        )

        expected_file = session_dir / "TestSong_session.json"
        assert orchestrator.session_file == str(expected_file)

    def test_session_directory_created(self, tmp_path):
        """Test session directory is created if it doesn't exist."""
        session_dir = tmp_path / "sessions"
        assert not session_dir.exists()

        WorkflowOrchestrator(
            input_video="Song_KeyC.mp4",
            input_tabs="song.txt",
            session_dir=str(session_dir),
            auto_approve=True,
        )

        assert session_dir.exists()

    def test_filename_config_parsed(self, tmp_path):
        """Test filename configuration is parsed correctly."""
        orchestrator = WorkflowOrchestrator(
            input_video="Song_KeyBb_Stem_FPS30.mp4",
            input_tabs="song.txt",
            session_dir=str(tmp_path / "sessions"),
            auto_approve=True,
        )

        assert orchestrator.filename_config.song_name == "Song"
        assert orchestrator.filename_config.key == "Bb"  # Normalized notation
        assert orchestrator.filename_config.enable_stem is True
        assert orchestrator.filename_config.fps == 30


class TestSessionResumption:
    """Tests for session resumption logic."""

    def test_resume_existing_session(self, tmp_path):
        """Test resuming an existing session."""
        session_dir = tmp_path / "sessions"

        # Create initial orchestrator and save session
        orchestrator1 = WorkflowOrchestrator(
            input_video="MySong_KeyG.mp4",
            input_tabs="MySong.txt",
            session_dir=str(session_dir),
            auto_approve=True,
        )
        orchestrator1.session.transition_to(WorkflowState.MIDI_FIXING)
        orchestrator1._save_session()

        # Create new orchestrator with same song - should load existing
        with patch("questionary.confirm") as mock_confirm:
            mock_confirm.return_value.ask.return_value = True

            orchestrator2 = WorkflowOrchestrator(
                input_video="MySong_KeyG.mp4",
                input_tabs="MySong.txt",
                session_dir=str(session_dir),
                auto_approve=False,  # Use questionary
            )

        # Should have resumed the MIDI_FIXING state
        assert orchestrator2.session.state == WorkflowState.MIDI_FIXING
        mock_confirm.assert_called_once()

    def test_create_new_session_when_resume_declined(self, tmp_path):
        """Test creating new session when user declines resume."""
        session_dir = tmp_path / "sessions"

        # Create initial orchestrator and save session
        orchestrator1 = WorkflowOrchestrator(
            input_video="MySong_KeyG.mp4",
            input_tabs="MySong.txt",
            session_dir=str(session_dir),
            auto_approve=True,
        )
        orchestrator1.session.transition_to(WorkflowState.MIDI_FIXING)
        orchestrator1._save_session()

        # Create new orchestrator - decline resume
        with patch("questionary.confirm") as mock_confirm:
            mock_confirm.return_value.ask.return_value = False

            orchestrator2 = WorkflowOrchestrator(
                input_video="MySong_KeyG.mp4",
                input_tabs="MySong.txt",
                session_dir=str(session_dir),
                auto_approve=False,
            )

        # Should have created new session in INIT state
        assert orchestrator2.session.state == WorkflowState.INIT


class TestWorkflowSteps:
    """Tests for individual workflow steps."""

    def test_initialize_step_without_stem(self, tmp_path):
        """Test initialize step transitions correctly without stem."""
        orchestrator = WorkflowOrchestrator(
            input_video="MySong_KeyC.mp4",  # No Stem flag
            input_tabs="MySong.txt",
            session_dir=str(tmp_path / "sessions"),
            auto_approve=True,
        )

        orchestrator._step_initialize()
        assert orchestrator.session.state == WorkflowState.MIDI_GENERATION

    def test_initialize_step_with_stem(self, tmp_path):
        """Test initialize step transitions to stem selection."""
        orchestrator = WorkflowOrchestrator(
            input_video="MySong_KeyC_Stem.mp4",
            input_tabs="MySong.txt",
            session_dir=str(tmp_path / "sessions"),
            auto_approve=True,
        )

        orchestrator._step_initialize()
        assert orchestrator.session.state == WorkflowState.STEM_SELECTION

    def test_stem_selection_step(self, tmp_path):
        """Test stem selection step transitions to MIDI generation."""
        orchestrator = WorkflowOrchestrator(
            input_video="MySong_KeyC_Stem.mp4",
            input_tabs="MySong.txt",
            session_dir=str(tmp_path / "sessions"),
            auto_approve=True,
        )
        orchestrator.session.transition_to(WorkflowState.STEM_SELECTION)

        orchestrator._step_stem_selection()
        assert orchestrator.session.state == WorkflowState.MIDI_GENERATION

    def test_midi_generation_step(self, tmp_path):
        """Test MIDI generation step transitions to MIDI fixing."""
        orchestrator = WorkflowOrchestrator(
            input_video="MySong_KeyC.mp4",
            input_tabs="MySong.txt",
            session_dir=str(tmp_path / "sessions"),
            auto_approve=True,
        )
        orchestrator.session.transition_to(WorkflowState.MIDI_GENERATION)

        # Mock MidiGenerator to avoid actual MIDI generation
        # Mock os.path.exists to return False (no existing MIDI file)
        with patch("harmonica_pipeline.midi_generator.MidiGenerator") as mock_gen:
            with patch("os.path.exists", return_value=False):
                orchestrator._step_midi_generation()
                mock_gen.assert_called_once()
                assert orchestrator.session.state == WorkflowState.MIDI_FIXING

    def test_midi_generation_uses_existing_midi(self, tmp_path):
        """Test MIDI generation skips when existing MIDI found and user declines overwrite."""
        orchestrator = WorkflowOrchestrator(
            input_video="MySong_KeyC.mp4",
            input_tabs="MySong.txt",
            session_dir=str(tmp_path / "sessions"),
            auto_approve=False,
        )
        orchestrator.session.transition_to(WorkflowState.MIDI_GENERATION)

        # Mock os.path.exists to return True (existing MIDI file)
        # Mock questionary to decline overwrite
        with patch("os.path.exists", return_value=True):
            with patch("questionary.confirm") as mock_confirm:
                mock_confirm.return_value.ask.return_value = False
                with patch(
                    "harmonica_pipeline.midi_generator.MidiGenerator"
                ) as mock_gen:
                    orchestrator._step_midi_generation()
                    # Should NOT generate MIDI
                    mock_gen.assert_not_called()
                    # Should transition to MIDI_FIXING
                    assert orchestrator.session.state == WorkflowState.MIDI_FIXING

    def test_midi_generation_overwrites_existing_midi(self, tmp_path):
        """Test MIDI generation overwrites when existing MIDI found and user confirms."""
        orchestrator = WorkflowOrchestrator(
            input_video="MySong_KeyC.mp4",
            input_tabs="MySong.txt",
            session_dir=str(tmp_path / "sessions"),
            auto_approve=False,
        )
        orchestrator.session.transition_to(WorkflowState.MIDI_GENERATION)

        # Mock os.path.exists to return True (existing MIDI file)
        # Mock questionary to accept overwrite
        with patch("os.path.exists", return_value=True):
            with patch("questionary.confirm") as mock_confirm:
                mock_confirm.return_value.ask.return_value = True
                with patch(
                    "harmonica_pipeline.midi_generator.MidiGenerator"
                ) as mock_gen:
                    orchestrator._step_midi_generation()
                    # Should generate MIDI (overwrite)
                    mock_gen.assert_called_once()
                    # Should transition to MIDI_FIXING
                    assert orchestrator.session.state == WorkflowState.MIDI_FIXING

    def test_midi_fixing_step_approved(self, tmp_path):
        """Test MIDI fixing step transitions when approved."""
        orchestrator = WorkflowOrchestrator(
            input_video="MySong_KeyC.mp4",
            input_tabs="MySong.txt",
            session_dir=str(tmp_path / "sessions"),
            auto_approve=True,
        )
        orchestrator.session.transition_to(WorkflowState.MIDI_FIXING)

        orchestrator._step_midi_fixing()
        assert orchestrator.session.state == WorkflowState.HARMONICA_REVIEW

    def test_midi_fixing_step_not_approved(self, tmp_path):
        """Test MIDI fixing step stays in same state when not approved."""
        orchestrator = WorkflowOrchestrator(
            input_video="MySong_KeyC.mp4",
            input_tabs="MySong.txt",
            session_dir=str(tmp_path / "sessions"),
            auto_approve=False,
        )
        orchestrator.session.transition_to(WorkflowState.MIDI_FIXING)

        with patch("questionary.confirm") as mock_confirm:
            mock_confirm.return_value.ask.return_value = False
            orchestrator._step_midi_fixing()

        # Should stay in MIDI_FIXING
        assert orchestrator.session.state == WorkflowState.MIDI_FIXING

    def test_midi_fixing_with_validation_pass(self, tmp_path):
        """Test MIDI fixing step runs validation and proceeds when it passes."""
        from utils.midi_validator import ValidationResult

        orchestrator = WorkflowOrchestrator(
            input_video="MySong_KeyC.mp4",
            input_tabs="MySong.txt",
            session_dir=str(tmp_path / "sessions"),
            auto_approve=True,
        )
        orchestrator.session.transition_to(WorkflowState.MIDI_FIXING)
        orchestrator.session.set_data("generated_midi", str(tmp_path / "test.mid"))

        # Create a dummy MIDI file
        (tmp_path / "test.mid").touch()

        # Mock validation to pass
        with patch("utils.midi_validator.validate_midi") as mock_validate:
            mock_validate.return_value = ValidationResult(
                passed=True, total_midi_notes=10, total_expected_notes=10, issues=[]
            )
            orchestrator._step_midi_fixing()

        assert orchestrator.session.state == WorkflowState.HARMONICA_REVIEW
        mock_validate.assert_called_once()

    def test_midi_fixing_with_validation_fail_proceed(self, tmp_path):
        """Test MIDI fixing step when validation fails and user chooses to proceed."""
        from utils.midi_validator import ValidationResult, ValidationIssue

        orchestrator = WorkflowOrchestrator(
            input_video="MySong_KeyC.mp4",
            input_tabs="MySong.txt",
            session_dir=str(tmp_path / "sessions"),
            auto_approve=False,
        )
        orchestrator.session.transition_to(WorkflowState.MIDI_FIXING)
        orchestrator.session.set_data("generated_midi", str(tmp_path / "test.mid"))

        # Create a dummy MIDI file
        (tmp_path / "test.mid").touch()

        # Mock validation to fail
        with patch("utils.midi_validator.validate_midi") as mock_validate:
            mock_validate.return_value = ValidationResult(
                passed=False,
                total_midi_notes=12,
                total_expected_notes=10,
                issues=[
                    ValidationIssue(
                        position=-1,
                        issue_type="extra",
                        description="Found 2 extra notes",
                    )
                ],
            )
            with patch("questionary.confirm") as mock_confirm:
                # First call: "finished fixing?", Second call: "proceed anyway?"
                mock_confirm.return_value.ask.side_effect = [True, True]
                with patch("questionary.text") as mock_text:
                    # FPS selection - "3" = 15 FPS
                    mock_text.return_value.ask.return_value = "3"
                    orchestrator._step_midi_fixing()

        # Should proceed despite validation failure
        assert orchestrator.session.state == WorkflowState.HARMONICA_REVIEW

    def test_midi_fixing_with_validation_fail_stay(self, tmp_path):
        """Test MIDI fixing step when validation fails and user chooses to fix."""
        from utils.midi_validator import ValidationResult, ValidationIssue

        orchestrator = WorkflowOrchestrator(
            input_video="MySong_KeyC.mp4",
            input_tabs="MySong.txt",
            session_dir=str(tmp_path / "sessions"),
            auto_approve=False,
        )
        orchestrator.session.transition_to(WorkflowState.MIDI_FIXING)
        orchestrator.session.set_data("generated_midi", str(tmp_path / "test.mid"))

        # Create a dummy MIDI file
        (tmp_path / "test.mid").touch()

        # Mock validation to fail
        with patch("utils.midi_validator.validate_midi") as mock_validate:
            mock_validate.return_value = ValidationResult(
                passed=False,
                total_midi_notes=12,
                total_expected_notes=10,
                issues=[
                    ValidationIssue(
                        position=-1,
                        issue_type="extra",
                        description="Found 2 extra notes",
                    )
                ],
            )
            with patch("questionary.confirm") as mock_confirm:
                # First call: "finished fixing?", Second call: "proceed anyway?" -> No
                mock_confirm.return_value.ask.side_effect = [True, False]
                orchestrator._step_midi_fixing()

        # Should stay in MIDI_FIXING
        assert orchestrator.session.state == WorkflowState.MIDI_FIXING

    def test_midi_fixing_validation_error_proceeds(self, tmp_path):
        """Test MIDI fixing step proceeds when validation throws an error."""
        orchestrator = WorkflowOrchestrator(
            input_video="MySong_KeyC.mp4",
            input_tabs="MySong.txt",
            session_dir=str(tmp_path / "sessions"),
            auto_approve=True,
        )
        orchestrator.session.transition_to(WorkflowState.MIDI_FIXING)
        orchestrator.session.set_data("generated_midi", str(tmp_path / "test.mid"))

        # Create a dummy MIDI file
        (tmp_path / "test.mid").touch()

        # Mock validation to throw error
        with patch("utils.midi_validator.validate_midi") as mock_validate:
            mock_validate.side_effect = Exception("Validation failed unexpectedly")
            orchestrator._step_midi_fixing()

        # Should still proceed (don't block on validation errors)
        assert orchestrator.session.state == WorkflowState.HARMONICA_REVIEW

    def test_midi_fixing_no_midi_file_skips_validation(self, tmp_path):
        """Test MIDI fixing step skips validation when MIDI file doesn't exist."""
        orchestrator = WorkflowOrchestrator(
            input_video="MySong_KeyC.mp4",
            input_tabs="MySong.txt",
            session_dir=str(tmp_path / "sessions"),
            auto_approve=True,
        )
        orchestrator.session.transition_to(WorkflowState.MIDI_FIXING)
        # Don't set generated_midi - simulating missing file

        with patch("utils.midi_validator.validate_midi") as mock_validate:
            orchestrator._step_midi_fixing()

        # Should proceed without calling validation
        assert orchestrator.session.state == WorkflowState.HARMONICA_REVIEW
        mock_validate.assert_not_called()

    def test_fps_selection_stored_in_session(self, tmp_path):
        """Test FPS selection is stored in session data."""
        orchestrator = WorkflowOrchestrator(
            input_video="MySong_KeyC.mp4",
            input_tabs="MySong.txt",
            session_dir=str(tmp_path / "sessions"),
            auto_approve=False,
        )
        orchestrator.session.transition_to(WorkflowState.MIDI_FIXING)

        with patch("questionary.confirm") as mock_confirm:
            mock_confirm.return_value.ask.return_value = True
            with patch("questionary.text") as mock_text:
                # "1" = 5 FPS
                mock_text.return_value.ask.return_value = "1"
                orchestrator._step_midi_fixing()

        # FPS should be stored in session
        assert orchestrator.session.get_data("fps") == 5
        assert orchestrator.session.state == WorkflowState.HARMONICA_REVIEW

    def test_fps_selection_auto_approve_uses_default(self, tmp_path):
        """Test FPS selection uses filename config in auto-approve mode."""
        orchestrator = WorkflowOrchestrator(
            input_video="MySong_KeyC_FPS20.mp4",  # FPS encoded in filename
            input_tabs="MySong.txt",
            session_dir=str(tmp_path / "sessions"),
            auto_approve=True,
        )
        orchestrator.session.transition_to(WorkflowState.MIDI_FIXING)

        orchestrator._step_midi_fixing()

        # Should use FPS from filename (20)
        assert orchestrator.session.get_data("fps") == 20
        assert orchestrator.session.state == WorkflowState.HARMONICA_REVIEW

    def test_harmonica_review_step_approved(self, tmp_path):
        """Test harmonica review step transitions when approved."""
        orchestrator = WorkflowOrchestrator(
            input_video="MySong_KeyC.mp4",
            input_tabs="MySong.txt",
            session_dir=str(tmp_path / "sessions"),
            auto_approve=True,
        )
        orchestrator.session.transition_to(WorkflowState.HARMONICA_REVIEW)

        # Mock VideoCreator to avoid actual video generation
        with patch("harmonica_pipeline.video_creator.VideoCreator"):
            orchestrator._step_harmonica_review()
            assert orchestrator.session.state == WorkflowState.TAB_VIDEO_REVIEW

    def test_harmonica_review_step_not_approved(self, tmp_path):
        """Test harmonica review step returns to MIDI fixing when not approved."""
        orchestrator = WorkflowOrchestrator(
            input_video="MySong_KeyC.mp4",
            input_tabs="MySong.txt",
            session_dir=str(tmp_path / "sessions"),
            auto_approve=False,
        )
        orchestrator.session.transition_to(WorkflowState.HARMONICA_REVIEW)

        # Mock VideoCreator to avoid actual video generation
        with patch("harmonica_pipeline.video_creator.VideoCreator"):
            with patch("questionary.confirm") as mock_confirm:
                mock_confirm.return_value.ask.return_value = False
                orchestrator._step_harmonica_review()
                # Should return to MIDI_FIXING for re-editing
                assert orchestrator.session.state == WorkflowState.MIDI_FIXING

    def test_tab_video_review_step_approved(self, tmp_path):
        """Test tab video review step transitions when approved."""
        orchestrator = WorkflowOrchestrator(
            input_video="MySong_KeyC.mp4",
            input_tabs="MySong.txt",
            session_dir=str(tmp_path / "sessions"),
            auto_approve=True,
        )
        orchestrator.session.transition_to(WorkflowState.TAB_VIDEO_REVIEW)

        # Mock VideoCreator to avoid actual video generation
        with patch("harmonica_pipeline.video_creator.VideoCreator"):
            orchestrator._step_tab_video_review()
            assert orchestrator.session.state == WorkflowState.FINALIZATION

    def test_finalization_step(self, tmp_path):
        """Test finalization step marks session complete."""
        orchestrator = WorkflowOrchestrator(
            input_video="MySong_KeyC.mp4",
            input_tabs="MySong.txt",
            session_dir=str(tmp_path / "sessions"),
            auto_approve=True,
        )
        orchestrator.session.transition_to(WorkflowState.FINALIZATION)

        # Mock file operations to avoid creating real ZIPs/folders
        with (
            patch("zipfile.ZipFile"),
            patch("shutil.copy2"),
            patch("pathlib.Path.mkdir"),
        ):
            orchestrator._step_finalization()
        assert orchestrator.session.state == WorkflowState.COMPLETE


class TestWorkflowExecution:
    """Tests for complete workflow execution."""

    def test_execute_current_step_dispatch(self, tmp_path):
        """Test execute_current_step dispatches to correct handler."""
        orchestrator = WorkflowOrchestrator(
            input_video="MySong_KeyC.mp4",
            input_tabs="MySong.txt",
            session_dir=str(tmp_path / "sessions"),
            auto_approve=True,
        )

        # Test INIT state
        orchestrator.session.state = WorkflowState.INIT
        orchestrator._execute_current_step()
        assert orchestrator.session.state == WorkflowState.MIDI_GENERATION

    def test_run_complete_workflow_auto_approve(self, tmp_path):
        """Test running complete workflow with auto-approve."""
        orchestrator = WorkflowOrchestrator(
            input_video="MySong_KeyC.mp4",
            input_tabs="MySong.txt",
            session_dir=str(tmp_path / "sessions"),
            auto_approve=True,
        )

        # Mock MidiGenerator and VideoCreator to avoid actual generation
        with patch("harmonica_pipeline.midi_generator.MidiGenerator"):
            with patch("harmonica_pipeline.video_creator.VideoCreator"):
                # Run workflow - should go through all states automatically
                orchestrator.run()

                # Should complete successfully
                assert orchestrator.session.is_complete()
                assert orchestrator.session.get_progress_percentage() == 100

    def test_run_workflow_with_stem(self, tmp_path):
        """Test workflow with stem separation enabled."""
        orchestrator = WorkflowOrchestrator(
            input_video="MySong_KeyC_Stem.mp4",
            input_tabs="MySong.txt",
            session_dir=str(tmp_path / "sessions"),
            auto_approve=True,
        )

        # Mock MidiGenerator and VideoCreator to avoid actual generation
        with patch("harmonica_pipeline.midi_generator.MidiGenerator"):
            with patch("harmonica_pipeline.video_creator.VideoCreator"):
                orchestrator.run()
                assert orchestrator.session.is_complete()

    def test_workflow_saves_session_after_each_step(self, tmp_path):
        """Test session is saved after each step."""
        session_dir = tmp_path / "sessions"
        orchestrator = WorkflowOrchestrator(
            input_video="MySong_KeyC.mp4",
            input_tabs="MySong.txt",
            session_dir=str(session_dir),
            auto_approve=True,
        )

        # Execute one step
        orchestrator._execute_current_step()
        orchestrator._save_session()

        # Verify session file exists and contains correct state
        session_file = session_dir / "MySong_session.json"
        assert session_file.exists()

        with open(session_file) as f:
            session_data = json.load(f)
        assert session_data["state"] == "midi_generation"


class TestErrorHandling:
    """Tests for error handling and recovery."""

    def test_workflow_error_saves_session(self, tmp_path):
        """Test workflow error saves session state."""
        orchestrator = WorkflowOrchestrator(
            input_video="MySong_KeyC.mp4",
            input_tabs="MySong.txt",
            session_dir=str(tmp_path / "sessions"),
            auto_approve=True,
        )

        # Simulate error during execution
        with patch.object(
            orchestrator,
            "_step_midi_generation",
            side_effect=RuntimeError("Test error"),
        ):
            with pytest.raises(RuntimeError):
                orchestrator.run()

        # Session should be in ERROR state
        assert orchestrator.session.is_error()
        assert "Test error" in orchestrator.session.get_data("error_message", "")

    def test_keyboard_interrupt_saves_session(self, tmp_path):
        """Test keyboard interrupt saves session for resumption."""
        orchestrator = WorkflowOrchestrator(
            input_video="MySong_KeyC.mp4",
            input_tabs="MySong.txt",
            session_dir=str(tmp_path / "sessions"),
            auto_approve=True,
        )

        # Simulate keyboard interrupt
        with patch.object(
            orchestrator, "_step_midi_generation", side_effect=KeyboardInterrupt()
        ):
            orchestrator.run()

        # Session should be saved (not in ERROR state)
        session_file = Path(orchestrator.session_file)
        assert session_file.exists()


class TestSessionPersistence:
    """Tests for session save/load integration."""

    def test_session_saved_correctly(self, tmp_path):
        """Test session is saved with all data."""
        orchestrator = WorkflowOrchestrator(
            input_video="MySong_KeyG_Stem.mp4",
            input_tabs="MySong.txt",
            session_dir=str(tmp_path / "sessions"),
            auto_approve=True,
        )

        orchestrator.session.set_data("test_key", "test_value")
        orchestrator._save_session()

        # Load session file and verify
        with open(orchestrator.session_file) as f:
            session_data = json.load(f)

        assert session_data["song_name"] == "MySong"
        assert session_data["config"]["key"] == "G"
        assert session_data["config"]["enable_stem"] is True
        assert session_data["data"]["test_key"] == "test_value"

    def test_completion_deletes_session_file(self, tmp_path):
        """Test session file is deleted on successful completion."""
        orchestrator = WorkflowOrchestrator(
            input_video="MySong_KeyC.mp4",
            input_tabs="MySong.txt",
            session_dir=str(tmp_path / "sessions"),
            auto_approve=True,
        )

        session_file = Path(orchestrator.session_file)
        orchestrator._save_session()
        assert session_file.exists()

        # Mock MidiGenerator and VideoCreator to avoid actual generation
        with patch("harmonica_pipeline.midi_generator.MidiGenerator"):
            with patch("harmonica_pipeline.video_creator.VideoCreator"):
                # Complete workflow
                orchestrator.run()

                # Session file should be deleted
                assert not session_file.exists()


class TestAutoApproveMode:
    """Tests for auto-approve mode (testing/automation)."""

    def test_auto_approve_skips_prompts(self, tmp_path):
        """Test auto-approve mode skips all user prompts."""
        orchestrator = WorkflowOrchestrator(
            input_video="MySong_KeyC.mp4",
            input_tabs="MySong.txt",
            session_dir=str(tmp_path / "sessions"),
            auto_approve=True,
        )

        # Should not call questionary at all
        with patch("harmonica_pipeline.midi_generator.MidiGenerator"):
            with patch("harmonica_pipeline.video_creator.VideoCreator"):
                with patch("questionary.confirm") as mock_confirm:
                    orchestrator.run()
                    mock_confirm.assert_not_called()

    def test_manual_mode_uses_prompts(self, tmp_path):
        """Test manual mode uses questionary prompts."""
        orchestrator = WorkflowOrchestrator(
            input_video="MySong_KeyC.mp4",
            input_tabs="MySong.txt",
            session_dir=str(tmp_path / "sessions"),
            auto_approve=False,
        )

        orchestrator.session.transition_to(WorkflowState.MIDI_FIXING)

        with patch("questionary.confirm") as mock_confirm:
            mock_confirm.return_value.ask.return_value = True
            with patch("questionary.text") as mock_text:
                # Mock FPS selection - "3" = 15 FPS
                mock_text.return_value.ask.return_value = "3"
                orchestrator._step_midi_fixing()
            mock_confirm.assert_called_once()
