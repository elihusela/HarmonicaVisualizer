"""Interactive workflow orchestrator for HarmonicaTabs pipeline.

This module orchestrates the complete interactive workflow:
1. Parse input files and configuration
2. Initialize or resume workflow session
3. Execute pipeline steps with user approval gates
4. Handle cleanup and finalization
"""

import logging
import os
import platform
import subprocess
import warnings
from datetime import datetime

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

    # Map CLI skip-to values to WorkflowState
    SKIP_TO_STATE_MAP = {
        "midi-fixing": WorkflowState.MIDI_FIXING,
        "harmonica": WorkflowState.HARMONICA_REVIEW,
        "tabs": WorkflowState.TAB_VIDEO_REVIEW,
        "finalize": WorkflowState.FINALIZATION,
    }

    def __init__(
        self,
        input_video: str,
        input_tabs: str,
        session_dir: str = "sessions",
        auto_approve: bool = False,
        skip_to: str | None = None,
    ):
        """Initialize workflow orchestrator.

        Args:
            input_video: Path to input video/audio file
            input_tabs: Path to input tab file (or MIDI for auto-generation)
            session_dir: Directory for session persistence files
            auto_approve: If True, skip all approval prompts (for testing)
            skip_to: Skip directly to a specific stage (midi-fixing, harmonica, tabs, finalize)
        """
        self.console = Console()
        self.auto_approve = auto_approve
        self.session_dir = session_dir
        self.skip_to = skip_to

        # Configure logging to suppress library warnings
        self._configure_logging(session_dir)

        # Parse configuration from filename
        self.filename_config = parse_filename(input_video)

        # Initialize or resume session
        self.session_file = self._get_session_file_path(session_dir)
        self.session = self._initialize_session(input_video, input_tabs)

        # Handle skip_to: jump directly to specified stage
        if skip_to:
            self._apply_skip_to(skip_to, input_video)

    def _configure_logging(self, session_dir: str) -> None:
        """Configure logging to redirect library warnings to a log file.

        Suppresses noisy warnings from third-party libraries (scikit-learn,
        TensorFlow, MoviePy, etc.) and redirects them to a log file.

        Args:
            session_dir: Directory to store the log file
        """
        os.makedirs(session_dir, exist_ok=True)
        log_file = os.path.join(session_dir, "workflow.log")
        self.log_file = log_file

        # Create file handler for all warnings/errors
        file_handler = logging.FileHandler(log_file, mode="a")
        file_handler.setLevel(logging.WARNING)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )

        # Configure root logger to use file handler
        root_logger = logging.getLogger()
        root_logger.addHandler(file_handler)

        # Suppress noisy third-party loggers (redirect to file only)
        noisy_loggers = [
            "moviepy",
            "imageio",
            "imageio_ffmpeg",
            "PIL",
            "matplotlib",
            "numba",
            "tensorflow",
            "absl",
            "basic_pitch",
            "librosa",
        ]
        for logger_name in noisy_loggers:
            logger = logging.getLogger(logger_name)
            logger.setLevel(logging.ERROR)
            # Only use file handler, not console
            logger.handlers = [file_handler]
            logger.propagate = False

        # Suppress Python warnings (scikit-learn, etc.)
        warnings.filterwarnings("ignore", category=UserWarning)
        warnings.filterwarnings("ignore", category=FutureWarning)
        warnings.filterwarnings("ignore", category=DeprecationWarning)

        # Redirect warnings to log file
        logging.captureWarnings(True)
        warnings_logger = logging.getLogger("py.warnings")
        warnings_logger.handlers = [file_handler]
        warnings_logger.propagate = False

        # Log session start
        logging.info(f"Workflow session started at {datetime.now()}")

    def _open_folder(self, folder_path: str) -> None:
        """Open a folder in the system file browser.

        Works on macOS (Finder), Windows (Explorer), and Linux (xdg-open).

        Args:
            folder_path: Path to the folder to open
        """
        if self.auto_approve:
            return  # Skip in auto-approve mode (testing)

        try:
            abs_path = os.path.abspath(folder_path)
            if not os.path.exists(abs_path):
                os.makedirs(abs_path, exist_ok=True)

            system = platform.system()
            if system == "Darwin":  # macOS
                subprocess.run(["open", abs_path], check=False)
            elif system == "Windows":
                subprocess.run(["explorer", abs_path], check=False)
            else:  # Linux
                subprocess.run(["xdg-open", abs_path], check=False)

            self.console.print(f"[dim]📂 Opened folder: {abs_path}[/dim]")
        except Exception as e:
            logging.warning(f"Could not open folder {folder_path}: {e}")

    def _apply_skip_to(self, skip_to: str, input_video: str) -> None:
        """Apply skip_to by setting session state and required data.

        Args:
            skip_to: Stage to skip to (midi-fixing, harmonica, tabs, finalize)
            input_video: Original input video path (for deriving MIDI path)
        """
        from utils.utils import MIDI_DIR, OUTPUTS_DIR

        target_state = self.SKIP_TO_STATE_MAP.get(skip_to)
        if not target_state:
            self.console.print(f"[yellow]Unknown skip-to stage: {skip_to}[/yellow]")
            return

        self.console.print(
            Panel(
                f"[cyan]Skipping to: {skip_to}[/cyan]\n\n"
                f"Target state: {target_state.value}",
                title="⏭️  Skip Mode",
            )
        )

        # Set up required session data based on target state
        # All stages need the MIDI path
        midi_path = os.path.join(MIDI_DIR, f"{self.session.song_name}_fixed.mid")
        if os.path.exists(midi_path):
            self.session.set_data("generated_midi", midi_path)
            self.console.print(f"[green]✓ Found MIDI: {midi_path}[/green]")
        else:
            self.console.print(
                f"[yellow]⚠️  MIDI not found: {midi_path}[/yellow]\n"
                "[dim]Video generation may fail without MIDI.[/dim]"
            )

        # For harmonica/tabs/finalize, check for existing videos
        if target_state in (
            WorkflowState.TAB_VIDEO_REVIEW,
            WorkflowState.FINALIZATION,
        ):
            harmonica_video = os.path.join(
                OUTPUTS_DIR, f"{self.session.song_name}_harmonica.mov"
            )
            if os.path.exists(harmonica_video):
                self.session.set_data("harmonica_video", harmonica_video)
                self.console.print(
                    f"[green]✓ Found harmonica video: {harmonica_video}[/green]"
                )

        if target_state == WorkflowState.FINALIZATION:
            tab_video = os.path.join(
                OUTPUTS_DIR, f"{self.session.song_name}_full_tabs.mov"
            )
            if os.path.exists(tab_video):
                self.session.set_data("tab_video", tab_video)
                self.console.print(f"[green]✓ Found tab video: {tab_video}[/green]")

        # Transition to target state
        self.session.state = target_state
        self._save_session()
        self.console.print(
            f"[green]✓ Session state set to: {target_state.value}[/green]\n"
        )

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
                f"FPS: {self.filename_config.fps}\n\n"
                f"[dim]Logs: {self.log_file}[/dim]",
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
        # Check if already selected (resuming session)
        if self.session.get_data("selected_audio"):
            self.console.print(
                f"[dim]Using previously selected stem: "
                f"{self.session.get_data('selected_audio')}[/dim]"
            )
            self.session.transition_to(WorkflowState.MIDI_GENERATION)
            return

        from utils.utils import VIDEO_FILES_DIR
        from pathlib import Path

        self.console.print(
            Panel(
                "[cyan]Manual Stem Separation Required[/cyan]\n\n"
                "1. Separate stems using your preferred tool (Demucs, RX, etc.)\n"
                "2. Save the stem you want to use in the video-files/ folder\n"
                "3. Select the stem file below\n\n"
                f"[dim]Looking in: {VIDEO_FILES_DIR}/[/dim]",
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
            # Find available audio files in video-files/
            video_files_path = Path(VIDEO_FILES_DIR)
            audio_extensions = {".wav", ".mp3", ".m4a", ".flac", ".aiff"}
            available_files = []

            if video_files_path.exists():
                for f in sorted(video_files_path.iterdir()):
                    if f.suffix.lower() in audio_extensions:
                        available_files.append(f.name)

            if available_files:
                # Show numbered list for easier selection (arrow keys often don't work)
                self.console.print("\n[cyan]Available audio files:[/cyan]")
                for idx, filename in enumerate(available_files, 1):
                    self.console.print(f"  {idx}. {filename}")
                self.console.print("  0. [Skip - use original video]")
                self.console.print()

                choice = questionary.text(
                    "Enter number to select (or 0 to skip):",
                    default="1",
                ).ask()

                try:
                    choice_num = int(choice) if choice else 0
                    if choice_num == 0:
                        self.console.print(
                            "[yellow]No stem selected, using original file[/yellow]"
                        )
                        selected_stem = self.session.input_video
                    elif 1 <= choice_num <= len(available_files):
                        selected_stem = os.path.join(
                            VIDEO_FILES_DIR, available_files[choice_num - 1]
                        )
                    else:
                        self.console.print(
                            "[yellow]Invalid choice, using original file[/yellow]"
                        )
                        selected_stem = self.session.input_video
                except ValueError:
                    self.console.print(
                        "[yellow]Invalid input, using original file[/yellow]"
                    )
                    selected_stem = self.session.input_video
            else:
                # No audio files found, ask for manual input
                self.console.print(
                    "[yellow]No audio files found in video-files/[/yellow]"
                )
                stem_file = questionary.text(
                    "Enter stem filename (or press Enter to skip):",
                ).ask()

                if stem_file and stem_file.strip():
                    selected_stem = os.path.join(VIDEO_FILES_DIR, stem_file.strip())
                else:
                    self.console.print(
                        "[yellow]No stem provided, using original file[/yellow]"
                    )
                    selected_stem = self.session.input_video

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

        # Open the MIDI folder for user to edit
        self._open_folder(MIDI_DIR)

        self.session.transition_to(WorkflowState.MIDI_FIXING)

    def _step_midi_fixing(self) -> None:
        """Pause for user to fix MIDI in DAW.

        User manually edits the generated MIDI in Ableton/Logic/etc.
        Workflow waits for user confirmation, then validates MIDI before continuing.
        """
        self.console.print(
            Panel(
                "[cyan]Fix the MIDI file in your DAW[/cyan]\n\n"
                f"MIDI: {self.session.get_data('generated_midi', 'temp/*_generated.mid')}\n"
                f"Tabs: {self.session.input_tabs}\n\n"
                "💡 [dim]You can edit both files now - they'll both reload on regeneration[/dim]\n\n"
                "When done, return here and confirm.",
                title="MIDI & Tabs Fixing",
            )
        )

        if not (
            self.auto_approve
            or questionary.confirm(
                "Have you finished fixing the MIDI?", default=False
            ).ask()
        ):
            return  # User not ready, stay in MIDI_FIXING state

        # Validate MIDI before proceeding
        validation_passed = self._validate_midi()

        proceed = False
        if validation_passed:
            proceed = True
        elif self.auto_approve:
            # In auto-approve mode, proceed despite validation failure
            self.console.print(
                "[yellow]Auto-approve: proceeding despite validation issues[/yellow]"
            )
            proceed = True
        else:
            # Ask user if they want to proceed anyway
            proceed_anyway = questionary.confirm(
                "Proceed anyway despite validation issues?",
                default=False,
            ).ask()

            if proceed_anyway:
                self.console.print(
                    "[yellow]⚠️  Proceeding with validation issues...[/yellow]"
                )
                proceed = True
            # else: stay in MIDI_FIXING state

        if proceed:
            # Ask for FPS selection before video generation
            self._select_fps()
            self.session.transition_to(WorkflowState.HARMONICA_REVIEW)

    def _validate_midi(self) -> bool:
        """Validate MIDI file against tab file.

        Returns:
            True if validation passed, False otherwise
        """
        from utils.midi_validator import validate_midi

        midi_path = self.session.get_data("generated_midi")
        tabs_path = self.session.input_tabs
        harmonica_key = self.session.config.get("key", "C")

        if not midi_path or not os.path.exists(midi_path):
            self.console.print(
                "[yellow]⚠️  Cannot validate: MIDI file not found[/yellow]"
            )
            return True  # Skip validation if no MIDI

        self.console.print("[dim]Validating MIDI against tab file...[/dim]")

        try:
            result = validate_midi(midi_path, tabs_path, harmonica_key)

            if result.passed:
                self.console.print(
                    Panel(
                        f"[green]{result.get_summary()}[/green]",
                        title="✅ Validation Passed",
                    )
                )
                return True
            else:
                self.console.print(
                    Panel(
                        f"[red]{result.get_summary()}[/red]",
                        title="❌ Validation Failed",
                    )
                )
                return False

        except Exception as e:
            self.console.print(
                f"[yellow]⚠️  Validation error: {e}[/yellow]\n"
                "[dim]Proceeding without validation...[/dim]"
            )
            return True  # Don't block on validation errors

    def _select_fps(self) -> None:
        """Ask user to select FPS for video generation.

        Lower FPS = faster rendering, good for sparse notes.
        Higher FPS = smoother animation, better for dense notes.
        """
        # Check if already selected (resuming session)
        if self.session.get_data("fps"):
            return

        self.console.print(
            Panel(
                "[cyan]Select video frame rate (FPS)[/cyan]\n\n"
                "Lower FPS = faster rendering (good for long videos with sparse notes)\n"
                "Higher FPS = smoother animation (better for fast note sequences)\n\n"
                "[dim]Tip: For 2+ minute videos with few notes, use 5-10 FPS[/dim]",
                title="Video Quality Settings",
            )
        )

        if self.auto_approve:
            # Use default FPS from filename config or 15
            fps = self.filename_config.fps
            self.console.print(f"[dim]Auto-approve: using {fps} FPS[/dim]")
        else:
            # Show numbered options for easier selection
            fps_options = [5, 10, 15, 20, 30]
            self.console.print("\n[cyan]FPS Options:[/cyan]")
            self.console.print(
                "  1. 5 FPS  - Fastest render, minimal animation (sparse notes)"
            )
            self.console.print(
                "  2. 10 FPS - Fast render, smooth enough for most cases (Recommended)"
            )
            self.console.print("  3. 15 FPS - Balanced quality and speed")
            self.console.print("  4. 20 FPS - Higher quality, slower render")
            self.console.print(
                "  5. 30 FPS - Full quality, slowest render (dense notes)"
            )
            self.console.print()

            choice = questionary.text(
                "Enter number (1-5), default is 2 (10 FPS):",
                default="2",
            ).ask()

            try:
                choice_num = int(choice) if choice else 2
                if 1 <= choice_num <= 5:
                    fps = fps_options[choice_num - 1]
                else:
                    fps = 10  # Default to 10 FPS
            except ValueError:
                fps = 10  # Default to 10 FPS

        self.session.set_data("fps", fps)
        self.console.print(f"[green]✓ Using {fps} FPS for video generation[/green]")

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

        # Get FPS from session (selected after MIDI fixing)
        fps = self.session.get_data("fps", 15)

        self.console.print(
            Panel(
                f"[cyan]Generating harmonica animation[/cyan]\n\n"
                f"Video: {video_path}\n"
                f"MIDI: {midi_path}\n"
                f"Key: {harmonica_key}\n"
                f"FPS: {fps}\n"
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
            fps=fps,
        )

        # Generate harmonica video
        creator = VideoCreator(config)
        creator.create(create_harmonica=True, create_tabs=False)

        self.console.print(
            f"[green]✓ Harmonica video created: {output_video_path}[/green]"
        )

        # Save output path to session
        self.session.set_data("harmonica_video", output_video_path)

        # Open outputs folder for user to review the video
        self._open_folder(OUTPUTS_DIR)

        # Wait for user approval
        if (
            self.auto_approve
            or questionary.confirm(
                "Approve harmonica video? (Open the file to review first)",
                default=True,
            ).ask()
        ):
            self.session.transition_to(WorkflowState.TAB_VIDEO_REVIEW)
        else:
            # User declined - go back to MIDI fixing to adjust timing
            self.console.print(
                "[yellow]⮌ Returning to MIDI fixing step. "
                "Fix your MIDI and we'll regenerate the harmonica video.[/yellow]"
            )
            self.session.transition_to(WorkflowState.MIDI_FIXING)

    def _step_tab_video_review(self) -> None:
        """Generate full tab video and wait for user approval.

        Generates the full tab page animation video (compositor) and allows
        user to review it. If not approved, user can go back to MIDI fixing.
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
        output_video = f"{self.session.song_name}_full_tabs.mov"
        output_video_path = os.path.join(OUTPUTS_DIR, output_video)

        # Get FPS from session (selected after MIDI fixing)
        fps = self.session.get_data("fps", 15)

        self.console.print(
            Panel(
                f"[cyan]Generating full tab video[/cyan]\n\n"
                f"Tabs: {tabs_path}\n"
                f"MIDI: {midi_path}\n"
                f"FPS: {fps}\n"
                f"Output: {output_video_path}\n\n"
                "[dim]This may take 2-3 minutes...[/dim]",
                title="Tab Video Generation",
            )
        )

        # Create configuration
        # Note: output_video_path is required by config validation even for tab-only
        dummy_harmonica_path = os.path.join(
            OUTPUTS_DIR, f"{self.session.song_name}_dummy.mov"
        )
        config = VideoCreatorConfig(
            video_path=video_path,
            tabs_path=tabs_path,
            harmonica_path=harmonica_path,
            midi_path=midi_path,
            output_video_path=dummy_harmonica_path,  # Required but won't be created
            tabs_output_path=output_video_path,
            produce_tabs=False,  # Not creating individual page videos
            produce_full_tab_video=True,  # Create full compositor video
            only_full_tab_video=True,  # Skip individual pages
            harmonica_key=harmonica_key,
            tab_page_buffer=self.session.config.get("tab_buffer", 0.1),
            fps=fps,
        )

        # Generate tab video
        creator = VideoCreator(config)
        creator.create(create_harmonica=False, create_tabs=True)

        self.console.print(f"[green]✓ Tab video created: {output_video_path}[/green]")

        # Save output path to session
        self.session.set_data("tab_video", output_video_path)

        # Open outputs folder for user to review the video
        self._open_folder(OUTPUTS_DIR)

        # Wait for user approval
        if (
            self.auto_approve
            or questionary.confirm(
                "Approve tab video? (Open the file to review first)",
                default=True,
            ).ask()
        ):
            self.session.transition_to(WorkflowState.FINALIZATION)
        else:
            # User declined - go back to MIDI fixing
            self.console.print(
                "[yellow]⮌ Returning to MIDI fixing step. "
                "Fix your MIDI/tabs and we'll regenerate the tab video.[/yellow]"
            )
            self.session.transition_to(WorkflowState.MIDI_FIXING)

    def _step_finalization(self) -> None:
        """Finalize workflow - cleanup, ZIP, archive.

        Creates final output package and archives source files.
        """
        import shutil
        from datetime import datetime
        from pathlib import Path

        self.console.print(
            Panel(
                "[cyan]Finalizing workflow...[/cyan]\n"
                "- Creating output ZIP\n"
                "- Archiving MIDI and tabs\n"
                "- Session cleanup",
                title="Finalization",
            )
        )

        # Create output ZIP with both videos
        timestamp = datetime.now().strftime("%Y%m%d")
        zip_name = f"{self.session.song_name}_{self.session.config.get('key', 'C')}_{timestamp}"
        zip_path = os.path.join("outputs", zip_name)

        # Get video paths from session
        harmonica_video = self.session.get_data("harmonica_video")
        tab_video = self.session.get_data("tab_video")

        if harmonica_video or tab_video:
            self.console.print(f"[dim]Creating ZIP: {zip_path}.zip[/dim]")

            # Create ZIP with only this song's videos
            import zipfile

            with zipfile.ZipFile(f"{zip_path}.zip", "w", zipfile.ZIP_DEFLATED) as zf:
                if harmonica_video and os.path.exists(harmonica_video):
                    zf.write(harmonica_video, os.path.basename(harmonica_video))
                if tab_video and os.path.exists(tab_video):
                    zf.write(tab_video, os.path.basename(tab_video))

            self.console.print(f"[green]✓ Created ZIP: {zip_path}.zip[/green]")

        # Archive MIDI and tabs to legacy folder
        legacy_dir = os.path.join("legacy", f"{self.session.song_name}_{timestamp}")
        Path(legacy_dir).mkdir(parents=True, exist_ok=True)

        midi_path = self.session.get_data("generated_midi")
        if midi_path and os.path.exists(midi_path):
            shutil.copy2(
                midi_path, os.path.join(legacy_dir, os.path.basename(midi_path))
            )
            self.console.print(f"[green]✓ Archived MIDI to: {legacy_dir}/[/green]")

        if os.path.exists(self.session.input_tabs):
            shutil.copy2(
                self.session.input_tabs,
                os.path.join(legacy_dir, os.path.basename(self.session.input_tabs)),
            )
            self.console.print(f"[green]✓ Archived tabs to: {legacy_dir}/[/green]")

        # Mark complete
        self.console.print("[green bold]✓ Workflow finalized![/green bold]")
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
