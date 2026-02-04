"""Tests for state_machine module."""

import json
from datetime import datetime

import pytest

from interactive_workflow.state_machine import WorkflowSession, WorkflowState


class TestWorkflowState:
    """Tests for WorkflowState enum."""

    def test_all_states_defined(self):
        """Test all expected states are defined."""
        expected_states = [
            "INIT",
            "STEM_SELECTION",
            "MIDI_GENERATION",
            "MIDI_FIXING",
            "HARMONICA_REVIEW",
            "TAB_VIDEO_REVIEW",
            "FINALIZATION",
            "COMPLETE",
            "ERROR",
        ]

        for state_name in expected_states:
            assert hasattr(WorkflowState, state_name)

    def test_state_values(self):
        """Test state enum values are lowercase."""
        assert WorkflowState.INIT.value == "init"
        assert WorkflowState.STEM_SELECTION.value == "stem_selection"
        assert WorkflowState.COMPLETE.value == "complete"
        assert WorkflowState.ERROR.value == "error"


class TestWorkflowSessionCreation:
    """Tests for WorkflowSession creation."""

    def test_create_minimal_session(self):
        """Test creating session with minimal parameters."""
        session = WorkflowSession.create(
            song_name="TestSong",
            input_video="test.mp4",
            input_tabs="test.txt",
        )

        assert session.song_name == "TestSong"
        assert session.input_video == "test.mp4"
        assert session.input_tabs == "test.txt"
        assert session.state == WorkflowState.INIT
        assert session.config == {}
        assert session.data == {}
        assert session.created_at is not None
        assert session.updated_at is not None

    def test_create_session_with_config(self):
        """Test creating session with configuration."""
        config = {"key": "G", "fps": 30, "enable_stem": True}
        session = WorkflowSession.create(
            song_name="TestSong",
            input_video="test.mp4",
            input_tabs="test.txt",
            config=config,
        )

        assert session.config == config
        assert session.config["key"] == "G"
        assert session.config["fps"] == 30

    def test_direct_instantiation(self):
        """Test direct instantiation of WorkflowSession."""
        session = WorkflowSession(
            state=WorkflowState.INIT,
            song_name="MySong",
            input_video="video.mp4",
            input_tabs="tabs.txt",
        )

        assert session.state == WorkflowState.INIT
        assert session.song_name == "MySong"

    def test_string_state_conversion(self):
        """Test automatic conversion of string state to enum."""
        session = WorkflowSession(
            state="init",  # String instead of enum
            song_name="MySong",
            input_video="video.mp4",
            input_tabs="tabs.txt",
        )

        assert isinstance(session.state, WorkflowState)
        assert session.state == WorkflowState.INIT


class TestWorkflowSessionDataManagement:
    """Tests for session data get/set."""

    def test_set_and_get_data(self):
        """Test setting and getting session data."""
        session = WorkflowSession.create(
            song_name="Test", input_video="test.mp4", input_tabs="test.txt"
        )

        session.set_data("selected_stem", "vocals.wav")
        assert session.get_data("selected_stem") == "vocals.wav"

    def test_get_nonexistent_data_returns_default(self):
        """Test getting non-existent data returns default."""
        session = WorkflowSession.create(
            song_name="Test", input_video="test.mp4", input_tabs="test.txt"
        )

        assert session.get_data("nonexistent") is None
        assert session.get_data("nonexistent", "default") == "default"

    def test_set_data_updates_timestamp(self):
        """Test setting data updates updated_at timestamp."""
        session = WorkflowSession.create(
            song_name="Test", input_video="test.mp4", input_tabs="test.txt"
        )

        original_updated = session.updated_at
        session.set_data("test_key", "test_value")

        # Timestamp should change (or at least not be earlier)
        assert session.updated_at >= original_updated

    def test_multiple_data_entries(self):
        """Test storing multiple data entries."""
        session = WorkflowSession.create(
            song_name="Test", input_video="test.mp4", input_tabs="test.txt"
        )

        session.set_data("stem", "vocals.wav")
        session.set_data("midi_file", "generated.mid")
        session.set_data("harmonica_video", "harmonica.mov")

        assert session.get_data("stem") == "vocals.wav"
        assert session.get_data("midi_file") == "generated.mid"
        assert session.get_data("harmonica_video") == "harmonica.mov"


class TestWorkflowSessionStateTransitions:
    """Tests for state transitions."""

    def test_basic_transition(self):
        """Test basic state transition."""
        session = WorkflowSession.create(
            song_name="Test", input_video="test.mp4", input_tabs="test.txt"
        )

        assert session.state == WorkflowState.INIT

        session.transition_to(WorkflowState.MIDI_GENERATION)
        assert session.state == WorkflowState.MIDI_GENERATION

    def test_transition_updates_timestamp(self):
        """Test state transition updates timestamp."""
        session = WorkflowSession.create(
            song_name="Test", input_video="test.mp4", input_tabs="test.txt"
        )

        original_updated = session.updated_at
        session.transition_to(WorkflowState.MIDI_GENERATION)

        assert session.updated_at >= original_updated

    def test_sequential_transitions(self):
        """Test multiple sequential transitions."""
        session = WorkflowSession.create(
            song_name="Test", input_video="test.mp4", input_tabs="test.txt"
        )

        # Simulate workflow progression
        session.transition_to(WorkflowState.MIDI_GENERATION)
        assert session.state == WorkflowState.MIDI_GENERATION

        session.transition_to(WorkflowState.MIDI_FIXING)
        assert session.state == WorkflowState.MIDI_FIXING

        session.transition_to(WorkflowState.HARMONICA_REVIEW)
        assert session.state == WorkflowState.HARMONICA_REVIEW

        session.transition_to(WorkflowState.COMPLETE)
        assert session.state == WorkflowState.COMPLETE

    def test_transition_to_error_always_allowed(self):
        """Test transition to ERROR is always allowed."""
        session = WorkflowSession.create(
            song_name="Test", input_video="test.mp4", input_tabs="test.txt"
        )

        # Can transition from any state to ERROR
        session.transition_to(WorkflowState.MIDI_GENERATION)
        session.transition_to(WorkflowState.ERROR)
        assert session.state == WorkflowState.ERROR

    def test_cannot_transition_from_complete(self):
        """Test cannot transition from COMPLETE (except to ERROR)."""
        session = WorkflowSession.create(
            song_name="Test", input_video="test.mp4", input_tabs="test.txt"
        )

        session.transition_to(WorkflowState.COMPLETE)

        with pytest.raises(ValueError, match="Cannot transition from COMPLETE"):
            session.transition_to(WorkflowState.MIDI_GENERATION)

    def test_cannot_transition_from_error(self):
        """Test cannot transition from ERROR."""
        session = WorkflowSession.create(
            song_name="Test", input_video="test.mp4", input_tabs="test.txt"
        )

        session.transition_to(WorkflowState.ERROR)

        with pytest.raises(ValueError, match="Cannot transition from ERROR"):
            session.transition_to(WorkflowState.INIT)


class TestWorkflowSessionPersistence:
    """Tests for save/load functionality."""

    def test_save_and_load_session(self, tmp_path):
        """Test saving and loading session."""
        session_file = tmp_path / "session.json"

        # Create and save session
        original_session = WorkflowSession.create(
            song_name="TestSong",
            input_video="video.mp4",
            input_tabs="tabs.txt",
            config={"key": "G", "fps": 30},
        )
        original_session.set_data("test_key", "test_value")
        original_session.transition_to(WorkflowState.MIDI_GENERATION)
        original_session.save(str(session_file))

        # Load session
        loaded_session = WorkflowSession.load(str(session_file))

        assert loaded_session is not None
        assert loaded_session.song_name == "TestSong"
        assert loaded_session.input_video == "video.mp4"
        assert loaded_session.input_tabs == "tabs.txt"
        assert loaded_session.state == WorkflowState.MIDI_GENERATION
        assert loaded_session.config["key"] == "G"
        assert loaded_session.get_data("test_key") == "test_value"

    def test_load_nonexistent_session_returns_none(self):
        """Test loading non-existent session returns None."""
        loaded_session = WorkflowSession.load("/nonexistent/session.json")
        assert loaded_session is None

    def test_save_creates_directory(self, tmp_path):
        """Test save creates directory if it doesn't exist."""
        session_file = tmp_path / "nested" / "dir" / "session.json"

        session = WorkflowSession.create(
            song_name="Test", input_video="test.mp4", input_tabs="test.txt"
        )
        session.save(str(session_file))

        assert session_file.exists()
        assert session_file.parent.exists()

    def test_saved_file_is_valid_json(self, tmp_path):
        """Test saved file is valid JSON."""
        session_file = tmp_path / "session.json"

        session = WorkflowSession.create(
            song_name="TestSong",
            input_video="video.mp4",
            input_tabs="tabs.txt",
        )
        session.save(str(session_file))

        # Verify JSON is valid
        with open(session_file, "r") as f:
            data = json.load(f)

        assert data["song_name"] == "TestSong"
        assert data["state"] == "init"

    def test_load_corrupted_session_raises_error(self, tmp_path):
        """Test loading corrupted session raises error."""
        session_file = tmp_path / "corrupted.json"

        # Write invalid JSON
        with open(session_file, "w") as f:
            f.write("{invalid json}")

        with pytest.raises(ValueError, match="Corrupted session file"):
            WorkflowSession.load(str(session_file))

    def test_delete_session_file(self, tmp_path):
        """Test deleting session file."""
        session_file = tmp_path / "session.json"

        session = WorkflowSession.create(
            song_name="Test", input_video="test.mp4", input_tabs="test.txt"
        )
        session.save(str(session_file))

        assert session_file.exists()

        session.delete(str(session_file))
        assert not session_file.exists()

    def test_delete_nonexistent_session_file(self):
        """Test deleting non-existent session file doesn't raise error."""
        session = WorkflowSession.create(
            song_name="Test", input_video="test.mp4", input_tabs="test.txt"
        )

        # Should not raise error
        session.delete("/nonexistent/session.json")


class TestWorkflowSessionUtilities:
    """Tests for utility methods."""

    def test_is_complete(self):
        """Test is_complete() method."""
        session = WorkflowSession.create(
            song_name="Test", input_video="test.mp4", input_tabs="test.txt"
        )

        assert not session.is_complete()

        session.transition_to(WorkflowState.COMPLETE)
        assert session.is_complete()

    def test_is_error(self):
        """Test is_error() method."""
        session = WorkflowSession.create(
            song_name="Test", input_video="test.mp4", input_tabs="test.txt"
        )

        assert not session.is_error()

        session.transition_to(WorkflowState.ERROR)
        assert session.is_error()

    def test_get_progress_percentage(self):
        """Test get_progress_percentage() method."""
        session = WorkflowSession.create(
            song_name="Test", input_video="test.mp4", input_tabs="test.txt"
        )

        # Test progress increases through workflow
        assert session.get_progress_percentage() == 0  # INIT

        session.transition_to(WorkflowState.STEM_SELECTION)
        assert session.get_progress_percentage() == 10

        session.transition_to(WorkflowState.MIDI_GENERATION)
        assert session.get_progress_percentage() == 25

        session.transition_to(WorkflowState.MIDI_FIXING)
        assert session.get_progress_percentage() == 35

        session.transition_to(WorkflowState.TAB_GENERATION)
        assert session.get_progress_percentage() == 45

        session.transition_to(WorkflowState.HARMONICA_REVIEW)
        assert session.get_progress_percentage() == 55

        session.transition_to(WorkflowState.TAB_VIDEO_REVIEW)
        assert session.get_progress_percentage() == 75

        session.transition_to(WorkflowState.FINALIZATION)
        assert session.get_progress_percentage() == 90

        session.transition_to(WorkflowState.COMPLETE)
        assert session.get_progress_percentage() == 100

    def test_progress_resets_on_error(self):
        """Test progress resets to 0 on error."""
        session = WorkflowSession.create(
            song_name="Test", input_video="test.mp4", input_tabs="test.txt"
        )

        session.transition_to(WorkflowState.MIDI_GENERATION)
        assert session.get_progress_percentage() == 25

        session.transition_to(WorkflowState.ERROR)
        assert session.get_progress_percentage() == 0


class TestWorkflowSessionTimestamps:
    """Tests for timestamp functionality."""

    def test_created_at_set_on_creation(self):
        """Test created_at is set when session is created."""
        session = WorkflowSession.create(
            song_name="Test", input_video="test.mp4", input_tabs="test.txt"
        )

        # Should be a valid ISO timestamp
        datetime.fromisoformat(session.created_at)

    def test_updated_at_set_on_creation(self):
        """Test updated_at is set when session is created."""
        session = WorkflowSession.create(
            song_name="Test", input_video="test.mp4", input_tabs="test.txt"
        )

        # Should be a valid ISO timestamp
        datetime.fromisoformat(session.updated_at)

    def test_timestamps_preserved_on_load(self, tmp_path):
        """Test timestamps are preserved when loading session."""
        session_file = tmp_path / "session.json"

        original_session = WorkflowSession.create(
            song_name="Test", input_video="test.mp4", input_tabs="test.txt"
        )
        original_created = original_session.created_at
        original_updated = original_session.updated_at

        original_session.save(str(session_file))

        loaded_session = WorkflowSession.load(str(session_file))

        assert loaded_session.created_at == original_created
        assert loaded_session.updated_at == original_updated
