"""Workflow state management for interactive pipeline.

Tracks workflow progress, saves/loads session state, and enables resuming
after interruptions or crashes.
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional


class WorkflowState(Enum):
    """Workflow step states.

    States represent the current step in the interactive pipeline:
    - INIT: Initial state, no processing started
    - STEM_SELECTION: Waiting for user to select stem (if enabled)
    - MIDI_GENERATION: Generating MIDI from audio
    - MIDI_FIXING: Waiting for user to fix MIDI in DAW
    - HARMONICA_REVIEW: Waiting for user to approve harmonica video
    - TAB_VIDEO_REVIEW: Waiting for user to approve tab video
    - FINALIZATION: Creating final package, cleanup
    - COMPLETE: Workflow finished successfully
    - ERROR: Workflow encountered an error
    """

    INIT = "init"
    STEM_SELECTION = "stem_selection"
    MIDI_GENERATION = "midi_generation"
    MIDI_FIXING = "midi_fixing"
    HARMONICA_REVIEW = "harmonica_review"
    TAB_VIDEO_REVIEW = "tab_video_review"
    FINALIZATION = "finalization"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class WorkflowSession:
    """Workflow session state and data.

    Tracks current workflow state, configuration, and intermediate files.
    Can be saved to/loaded from JSON for crash recovery.

    Attributes:
        state: Current workflow state
        song_name: Base song name (from filename)
        input_video: Original input video/audio file path
        input_tabs: Original tab file path
        config: Configuration from filename parsing (as dict)
        data: Additional session data (file paths, user choices, etc.)
        created_at: Session creation timestamp
        updated_at: Last update timestamp
    """

    state: WorkflowState
    song_name: str
    input_video: str
    input_tabs: str
    config: Dict[str, Any] = field(default_factory=dict)
    data: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def __post_init__(self):
        """Convert state to WorkflowState enum if needed."""
        if isinstance(self.state, str):
            self.state = WorkflowState(self.state)

    def transition_to(self, new_state: WorkflowState) -> None:
        """Transition to a new workflow state.

        Args:
            new_state: The state to transition to

        Raises:
            ValueError: If transition is invalid
        """
        # Validate state transition (basic validation)
        if new_state == WorkflowState.ERROR:
            # Can always transition to ERROR
            pass
        elif self.state == WorkflowState.COMPLETE:
            # Cannot transition from COMPLETE (except to ERROR)
            if new_state != WorkflowState.ERROR:
                raise ValueError(
                    f"Cannot transition from COMPLETE to {new_state.value}"
                )
        elif self.state == WorkflowState.ERROR:
            # Cannot transition from ERROR (workflow must restart)
            raise ValueError(f"Cannot transition from ERROR to {new_state.value}")

        # Update state and timestamp
        self.state = new_state
        self.updated_at = datetime.now().isoformat()

    def set_data(self, key: str, value: Any) -> None:
        """Set session data value.

        Args:
            key: Data key
            value: Data value (must be JSON-serializable)
        """
        self.data[key] = value
        self.updated_at = datetime.now().isoformat()

    def get_data(self, key: str, default: Any = None) -> Any:
        """Get session data value.

        Args:
            key: Data key
            default: Default value if key not found

        Returns:
            Data value or default
        """
        return self.data.get(key, default)

    def save(self, session_file: str) -> None:
        """Save session to JSON file.

        Args:
            session_file: Path to session file

        Raises:
            IOError: If file cannot be written
        """
        # Ensure directory exists
        session_path = Path(session_file)
        session_path.parent.mkdir(parents=True, exist_ok=True)

        # Convert to dict and save
        session_dict = {
            "state": self.state.value,  # Convert enum to string
            "song_name": self.song_name,
            "input_video": self.input_video,
            "input_tabs": self.input_tabs,
            "config": self.config,
            "data": self.data,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

        with open(session_file, "w") as f:
            json.dump(session_dict, f, indent=2)

    @classmethod
    def load(cls, session_file: str) -> Optional["WorkflowSession"]:
        """Load session from JSON file.

        Args:
            session_file: Path to session file

        Returns:
            WorkflowSession instance or None if file doesn't exist

        Raises:
            ValueError: If session file is corrupted
        """
        if not os.path.exists(session_file):
            return None

        try:
            with open(session_file, "r") as f:
                session_dict = json.load(f)

            # Create WorkflowSession from dict
            return cls(
                state=WorkflowState(session_dict["state"]),
                song_name=session_dict["song_name"],
                input_video=session_dict["input_video"],
                input_tabs=session_dict["input_tabs"],
                config=session_dict.get("config", {}),
                data=session_dict.get("data", {}),
                created_at=session_dict.get("created_at", datetime.now().isoformat()),
                updated_at=session_dict.get("updated_at", datetime.now().isoformat()),
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            raise ValueError(f"Corrupted session file: {session_file}") from e

    @classmethod
    def create(
        cls,
        song_name: str,
        input_video: str,
        input_tabs: str,
        config: Optional[Dict[str, Any]] = None,
    ) -> "WorkflowSession":
        """Create a new workflow session.

        Args:
            song_name: Song name
            input_video: Input video/audio file path
            input_tabs: Input tab file path
            config: Configuration dict (from filename parser)

        Returns:
            New WorkflowSession instance
        """
        return cls(
            state=WorkflowState.INIT,
            song_name=song_name,
            input_video=input_video,
            input_tabs=input_tabs,
            config=config or {},
            data={},
        )

    def delete(self, session_file: str) -> None:
        """Delete session file.

        Args:
            session_file: Path to session file
        """
        if os.path.exists(session_file):
            os.remove(session_file)

    def is_complete(self) -> bool:
        """Check if workflow is complete.

        Returns:
            True if state is COMPLETE
        """
        return self.state == WorkflowState.COMPLETE

    def is_error(self) -> bool:
        """Check if workflow encountered an error.

        Returns:
            True if state is ERROR
        """
        return self.state == WorkflowState.ERROR

    def get_progress_percentage(self) -> int:
        """Get workflow progress as percentage.

        Returns:
            Progress percentage (0-100)
        """
        # Map states to progress percentages
        progress_map = {
            WorkflowState.INIT: 0,
            WorkflowState.STEM_SELECTION: 10,
            WorkflowState.MIDI_GENERATION: 25,
            WorkflowState.MIDI_FIXING: 40,
            WorkflowState.HARMONICA_REVIEW: 55,
            WorkflowState.TAB_VIDEO_REVIEW: 75,
            WorkflowState.FINALIZATION: 90,
            WorkflowState.COMPLETE: 100,
            WorkflowState.ERROR: 0,  # Error resets progress
        }
        return progress_map.get(self.state, 0)
