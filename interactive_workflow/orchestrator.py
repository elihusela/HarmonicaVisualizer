"""Interactive workflow orchestrator for HarmonicaTabs pipeline.

This module orchestrates the complete interactive workflow:
1. Parse input files and configuration
2. Initialize or resume workflow session
3. Execute pipeline steps with user approval gates
4. Handle cleanup and finalization
"""

import os

import questionary
from rich.console import Console
from rich.panel import Panel

from interactive_workflow.state_machine import WorkflowSession, WorkflowState
from utils.filename_parser import parse_filename


class WorkflowOrchestrator:
    """Orchestrates the interactive harmonica tabs generation workflow.

    Manages workflow state, user interactions, and pipeline execution
    with approval gates between major steps.

    Attributes:
        console: Rich console for beautiful terminal output
        session: Current workflow session state
        session_file: Path to session persistence file
    """

    def __init__(
        self,
        input_video: str,
        input_tabs: str,
        session_dir: str = "sessions",
        auto_approve: bool = False,
    ):
        """Initialize workflow orchestrator.

        Args:
            input_video: Path to input video/audio file
            input_tabs: Path to input tab file (or MIDI for auto-generation)
            session_dir: Directory for session persistence files
            auto_approve: If True, skip all approval prompts (for testing)
        """
        self.console = Console()
        self.auto_approve = auto_approve

        # Parse configuration from filename
        self.filename_config = parse_filename(input_video)

        # Initialize or resume session
        self.session_file = self._get_session_file_path(session_dir)
        self.session = self._initialize_session(input_video, input_tabs)

    def _get_session_file_path(self, session_dir: str) -> str:
        """Generate session file path based on song name.

        Args:
            session_dir: Directory for session files

        Returns:
            Full path to session JSON file
        """
        os.makedirs(session_dir, exist_ok=True)
        return os.path.join(
            session_dir, f"{self.filename_config.song_name}_session.json"
        )

    def _initialize_session(self, input_video: str, input_tabs: str) -> WorkflowSession:
        """Initialize or resume workflow session.

        Args:
            input_video: Path to input video/audio file
            input_tabs: Path to input tab file

        Returns:
            WorkflowSession instance (new or resumed)
        """
        # Try to load existing session
        existing_session = WorkflowSession.load(self.session_file)

        if existing_session:
            self.console.print(
                Panel(
                    f"[yellow]Found existing session for {existing_session.song_name}[/yellow]\n"
                    f"State: {existing_session.state.value}\n"
                    f"Progress: {existing_session.get_progress_percentage()}%",
                    title="Resume Session",
                )
            )

            if (
                self.auto_approve
                or questionary.confirm("Resume existing session?", default=True).ask()
            ):
                return existing_session

        # Create new session
        self.console.print(
            Panel(
                f"[green]Creating new workflow session[/green]\n"
                f"Song: {self.filename_config.song_name}\n"
                f"Key: {self.filename_config.key}\n"
                f"Stem separation: {self.filename_config.enable_stem}\n"
                f"FPS: {self.filename_config.fps}",
                title="New Session",
            )
        )

        return WorkflowSession.create(
            song_name=self.filename_config.song_name,
            input_video=input_video,
            input_tabs=input_tabs,
            config={
                "key": self.filename_config.key,
                "enable_stem": self.filename_config.enable_stem,
                "fps": self.filename_config.fps,
                "tab_buffer": self.filename_config.tab_buffer,
            },
        )

    def run(self) -> None:
        """Execute the complete interactive workflow.

        Runs through all workflow states with approval gates:
        1. Stem selection (if enabled)
        2. MIDI generation
        3. MIDI fixing (user DAW step)
        4. Harmonica video generation and review
        5. Full tab video generation and review
        6. Finalization and cleanup
        """
        try:
            while not self.session.is_complete() and not self.session.is_error():
                self._execute_current_step()
                self._save_session()

            if self.session.is_complete():
                self._show_completion_message()
            elif self.session.is_error():
                self._show_error_message()

        except KeyboardInterrupt:
            self.console.print("\n[yellow]Workflow interrupted by user[/yellow]")
            self._save_session()
            self.console.print(
                f"[dim]Session saved. Resume with: {self.session_file}[/dim]"
            )
        except Exception as e:
            self.console.print(f"\n[red]Error: {e}[/red]")
            self.session.transition_to(WorkflowState.ERROR)
            self.session.set_data("error_message", str(e))
            self._save_session()
            raise

    def _execute_current_step(self) -> None:
        """Execute the current workflow step based on session state."""
        state = self.session.state

        if state == WorkflowState.INIT:
            self._step_initialize()
        elif state == WorkflowState.STEM_SELECTION:
            self._step_stem_selection()
        elif state == WorkflowState.MIDI_GENERATION:
            self._step_midi_generation()
        elif state == WorkflowState.MIDI_FIXING:
            self._step_midi_fixing()
        elif state == WorkflowState.HARMONICA_REVIEW:
            self._step_harmonica_review()
        elif state == WorkflowState.TAB_VIDEO_REVIEW:
            self._step_tab_video_review()
        elif state == WorkflowState.FINALIZATION:
            self._step_finalization()
        else:
            raise ValueError(f"Unknown workflow state: {state}")

    def _step_initialize(self) -> None:
        """Initialize workflow - determine next step."""
        if self.filename_config.enable_stem:
            self.session.transition_to(WorkflowState.STEM_SELECTION)
        else:
            self.session.transition_to(WorkflowState.MIDI_GENERATION)

    def _step_stem_selection(self) -> None:
        """Execute stem separation and let user select best stem.

        TODO: Implement stem separation logic
        - Run Demucs on input audio
        - Present user with 4 stems
        - Let user pick best one
        - Save selected stem path to session
        """
        self.console.print(
            Panel(
                "[yellow]Stem separation not yet implemented[/yellow]\n"
                "This step will use Demucs to separate audio sources.",
                title="Stem Selection",
            )
        )
        # For now, skip to next step
        self.session.transition_to(WorkflowState.MIDI_GENERATION)

    def _step_midi_generation(self) -> None:
        """Generate MIDI from audio using basic_pitch.

        TODO: Implement MIDI generation
        - Use MidiGenerator from harmonica_pipeline
        - Process audio to MIDI
        - Save generated MIDI path to session
        """
        self.console.print(
            Panel(
                "[yellow]MIDI generation not yet fully integrated[/yellow]\n"
                "This step will generate MIDI using basic_pitch.",
                title="MIDI Generation",
            )
        )
        # For now, skip to next step
        self.session.transition_to(WorkflowState.MIDI_FIXING)

    def _step_midi_fixing(self) -> None:
        """Pause for user to fix MIDI in DAW.

        User manually edits the generated MIDI in Ableton/Logic/etc.
        Workflow waits for user confirmation before continuing.
        """
        self.console.print(
            Panel(
                "[cyan]Please fix the MIDI file in your DAW[/cyan]\n\n"
                f"Generated MIDI: {self.session.get_data('generated_midi', 'temp/*_generated.mid')}\n"
                f"Save fixed MIDI to: {self.session.get_data('fixed_midi', 'fixed_midis/*_fixed.mid')}\n\n"
                "When done, return here and confirm.",
                title="MIDI Fixing",
            )
        )

        if (
            self.auto_approve
            or questionary.confirm(
                "Have you finished fixing the MIDI?", default=False
            ).ask()
        ):
            self.session.transition_to(WorkflowState.HARMONICA_REVIEW)

    def _step_harmonica_review(self) -> None:
        """Generate harmonica animation and wait for user approval.

        TODO: Implement harmonica video generation
        - Use VideoCreator from harmonica_pipeline
        - Generate harmonica hole animation
        - Show preview to user
        - Loop until approved
        """
        self.console.print(
            Panel(
                "[yellow]Harmonica video generation not yet fully integrated[/yellow]\n"
                "This step will generate the harmonica hole animation.",
                title="Harmonica Video",
            )
        )

        if (
            self.auto_approve
            or questionary.confirm("Approve harmonica video?", default=True).ask()
        ):
            self.session.transition_to(WorkflowState.TAB_VIDEO_REVIEW)
        # else: stay in same state for re-generation

    def _step_tab_video_review(self) -> None:
        """Generate full tab video and wait for user approval.

        TODO: Implement full tab video generation
        - Use FullTabVideoCompositor
        - Generate page-by-page tab animation
        - Show preview to user
        - Loop until approved
        """
        self.console.print(
            Panel(
                "[yellow]Tab video generation not yet fully integrated[/yellow]\n"
                "This step will generate the full tab page animation.",
                title="Tab Video",
            )
        )

        if (
            self.auto_approve
            or questionary.confirm("Approve tab video?", default=True).ask()
        ):
            self.session.transition_to(WorkflowState.FINALIZATION)
        # else: stay in same state for re-generation

    def _step_finalization(self) -> None:
        """Finalize workflow - cleanup, ZIP, archive.

        TODO: Implement finalization
        - ZIP final videos
        - Move MIDI/tabs to legacy folder
        - Clean up temp files
        - Mark session complete
        """
        self.console.print(
            Panel(
                "[green]Finalizing workflow...[/green]\n"
                "- Creating output ZIP\n"
                "- Archiving MIDI and tabs\n"
                "- Cleaning up temp files",
                title="Finalization",
            )
        )

        # Mark complete
        self.session.transition_to(WorkflowState.COMPLETE)

    def _save_session(self) -> None:
        """Save current session state to disk."""
        self.session.save(self.session_file)

    def _show_completion_message(self) -> None:
        """Display completion message with output locations."""
        self.console.print(
            Panel(
                f"[green bold]Workflow Complete![/green bold]\n\n"
                f"Song: {self.session.song_name}\n"
                f"Outputs: outputs/{self.session.song_name}_*.mov\n"
                f"Session: {self.session_file}",
                title="Success",
            )
        )

        # Clean up session file
        self.session.delete(self.session_file)

    def _show_error_message(self) -> None:
        """Display error message with recovery instructions."""
        error_msg = self.session.get_data("error_message", "Unknown error")
        self.console.print(
            Panel(
                f"[red bold]Workflow Error[/red bold]\n\n"
                f"Error: {error_msg}\n\n"
                f"Session saved to: {self.session_file}\n"
                "Fix the issue and resume the workflow.",
                title="Error",
            )
        )
