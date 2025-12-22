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
        """Wait for user to provide manually separated stem file.

        User separates stems offline (Demucs, RX, etc.) and provides
        the stem file they want to use for MIDI generation.

        Future: Auto-run Demucs here and let user pick from results.
        """
        self.console.print(
            Panel(
                "[cyan]Manual Stem Separation Required[/cyan]\n\n"
                "1. Separate stems using your preferred tool (Demucs, RX, etc.)\n"
                "2. Save the stem you want to use in the video-files/ folder\n"
                "3. Provide the filename below\n\n"
                "[dim]Example: MySong_vocals.wav[/dim]",
                title="Stem Selection",
            )
        )

        if self.auto_approve:
            # For testing: just use original video
            self.console.print(
                "[dim]Auto-approve mode: using original input file[/dim]"
            )
            selected_stem = self.session.input_video
        else:
            # Prompt user for stem filename
            from utils.utils import VIDEO_FILES_DIR

            stem_file = questionary.text(
                "Enter stem filename:",
                default=f"{self.session.song_name}.wav",
            ).ask()

            if not stem_file:
                # User cancelled
                self.console.print(
                    "[yellow]No stem provided, using original file[/yellow]"
                )
                selected_stem = self.session.input_video
            else:
                selected_stem = os.path.join(VIDEO_FILES_DIR, stem_file)

        self.session.set_data("selected_audio", selected_stem)
        self.console.print(f"[green]✓ Using audio: {selected_stem}[/green]")
        self.session.transition_to(WorkflowState.MIDI_GENERATION)

    def _step_midi_generation(self) -> None:
        """Generate MIDI from audio using basic_pitch.

        Uses MidiGenerator which automatically handles:
        - Video files (.mp4, .mov) - extracts audio first
        - Audio files (.wav) - uses directly
        """
        from harmonica_pipeline.midi_generator import MidiGenerator
        from utils.utils import MIDI_DIR

        # Use selected stem if available (from stem selection step)
        # Otherwise use original input (video or audio)
        input_file = self.session.get_data("selected_audio", self.session.input_video)
        output_midi = os.path.join(MIDI_DIR, f"{self.session.song_name}_fixed.mid")

        # Check if MIDI file already exists
        if os.path.exists(output_midi):
            self.console.print(
                Panel(
                    f"[yellow]MIDI file already exists[/yellow]\n\n"
                    f"Found: {output_midi}\n\n"
                    "This may be a previously fixed MIDI file.\n"
                    "Regenerating will overwrite your edits!",
                    title="⚠️  Existing MIDI Detected",
                )
            )

            if (
                self.auto_approve
                or questionary.confirm(
                    "Overwrite existing MIDI file?", default=False
                ).ask()
            ):
                # User wants to overwrite - proceed with generation
                self.console.print("[yellow]Regenerating MIDI...[/yellow]")
            else:
                # User wants to keep existing - skip generation
                self.console.print(
                    f"[green]✓ Using existing MIDI: {output_midi}[/green]"
                )
                self.session.set_data("generated_midi", output_midi)
                self.session.transition_to(WorkflowState.MIDI_FIXING)
                return

        self.console.print(
            Panel(
                f"[cyan]Generating MIDI from audio[/cyan]\n\n"
                f"Input: {input_file}\n"
                f"Output: {output_midi}\n\n"
                "[dim]This may take 30-60 seconds...[/dim]",
                title="MIDI Generation",
            )
        )

        # Generate MIDI
        generator = MidiGenerator(input_file, output_midi)
        generator.generate()

        # Save to session
        self.session.set_data("generated_midi", output_midi)

        self.console.print(f"[green]✓ MIDI generated: {output_midi}[/green]")
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

        Generates the harmonica hole animation video and allows user to
        review it. If not approved, user can regenerate (future: with
        different parameters).
        """
        from harmonica_pipeline.video_creator import VideoCreator
        from harmonica_pipeline.video_creator_config import VideoCreatorConfig
        from harmonica_pipeline.harmonica_key_registry import get_harmonica_config
        from utils.utils import OUTPUTS_DIR

        # Get configuration
        harmonica_key = self.session.config.get("key", "C")
        harmonica_config = get_harmonica_config(harmonica_key)

        # Get paths from session
        video_path = self.session.input_video
        tabs_path = self.session.input_tabs
        midi_path = self.session.get_data(
            "generated_midi", f"fixed_midis/{self.session.song_name}_fixed.mid"
        )
        harmonica_path = os.path.join("harmonica-models", harmonica_config.model_image)

        # Output paths
        output_video = f"{self.session.song_name}_harmonica.mov"
        output_video_path = os.path.join(OUTPUTS_DIR, output_video)

        self.console.print(
            Panel(
                f"[cyan]Generating harmonica animation[/cyan]\n\n"
                f"Video: {video_path}\n"
                f"MIDI: {midi_path}\n"
                f"Key: {harmonica_key}\n"
                f"Model: {harmonica_path}\n"
                f"Output: {output_video_path}\n\n"
                "[dim]This may take 1-2 minutes...[/dim]",
                title="Harmonica Video Generation",
            )
        )

        # Create configuration
        config = VideoCreatorConfig(
            video_path=video_path,
            tabs_path=tabs_path,
            harmonica_path=harmonica_path,
            midi_path=midi_path,
            output_video_path=output_video_path,
            tabs_output_path=None,  # No tabs yet
            produce_tabs=False,
            produce_full_tab_video=False,
            only_full_tab_video=False,
            harmonica_key=harmonica_key,
            tab_page_buffer=self.session.config.get("tab_buffer", 0.1),
        )

        # Generate harmonica video
        creator = VideoCreator(config)
        creator.create(create_harmonica=True, create_tabs=False)

        self.console.print(
            f"[green]✓ Harmonica video created: {output_video_path}[/green]"
        )

        # Save output path to session
        self.session.set_data("harmonica_video", output_video_path)

        # Wait for user approval
        if (
            self.auto_approve
            or questionary.confirm(
                "Approve harmonica video? (Open the file to review first)",
                default=True,
            ).ask()
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
