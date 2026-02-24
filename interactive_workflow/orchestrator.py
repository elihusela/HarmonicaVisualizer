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
from utils.utils import get_project_temp_dir


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
        "tab-generation": WorkflowState.TAB_GENERATION,
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

        # Create project-specific temp directory for parallel project support
        self.project_temp_dir = get_project_temp_dir(self.session.song_name)

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
        elif state == WorkflowState.TAB_GENERATION:
            self._step_tab_generation()
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
        """Handle stem separation - either auto via Demucs or manual selection.

        Offers two options:
        1. Run Demucs automatically (6-stem model, uses "other" stem for harmonica)
        2. Manual selection from video-files/ folder
        """
        # Check if already selected (resuming session)
        if self.session.get_data("selected_audio"):
            self.console.print(
                f"[dim]Using previously selected stem: "
                f"{self.session.get_data('selected_audio')}[/dim]"
            )
            self.session.transition_to(WorkflowState.MIDI_GENERATION)
            return

        from pathlib import Path

        from utils.utils import VIDEO_FILES_DIR

        self.console.print(
            Panel(
                "[cyan]Stem Separation[/cyan]\n\n"
                "Separate harmonica from other instruments for better MIDI detection.\n\n"
                "[bold]Option 1:[/bold] Run Demucs AI (automatic, ~30 seconds)\n"
                "[bold]Option 2:[/bold] Use pre-separated file from video-files/",
                title="Stem Selection",
            )
        )

        # Ask if user wants to run Demucs
        if not self.auto_approve:
            run_demucs = questionary.confirm(
                "Run Demucs stem separation?",
                default=True,
            ).ask()

            if run_demucs:
                if self._run_demucs_separation():
                    return  # Success - already transitioned to MIDI_GENERATION
                # Demucs failed - fall through to manual selection

        # Manual selection flow
        self.console.print("\n[cyan]Manual Selection:[/cyan]")

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

    def _run_demucs_separation(self) -> bool:
        """Run Demucs stem separation and use "other" stem for harmonica.

        Automatically:
        1. Extracts audio from video if needed
        2. Runs Demucs 6-stem model
        3. Uses "other.mp3" stem (where harmonica typically ends up)

        Returns:
            True if separation succeeded, False if failed (fall back to manual)
        """
        from utils.stem_separator import StemSeparator, StemSeparatorError

        self.console.print(
            Panel(
                "[cyan]Running Demucs Stem Separation[/cyan]\n\n"
                "Model: htdemucs_6s (6 stems)\n"
                "Output: stems/ folder\n"
                "Using: 'other' stem (best for harmonica)\n\n"
                "[dim]This may take 30-60 seconds...[/dim]",
                title="Demucs",
            )
        )

        try:
            separator = StemSeparator(output_dir="stems")
            stem_path = separator.separate(
                self.session.input_video,
                stem="other",  # Harmonica typically ends up here
            )

            self.session.set_data("selected_audio", stem_path)
            self.console.print("[green]✓ Stem separation complete![/green]")
            self.console.print(f"[green]✓ Using: {stem_path}[/green]")
            self.session.transition_to(WorkflowState.MIDI_GENERATION)
            return True

        except StemSeparatorError as e:
            self.console.print(f"[red]✗ Stem separation failed: {e}[/red]")
            self.console.print("[yellow]Falling back to manual selection...[/yellow]")
            return False

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

        # Generate MIDI (using project-specific temp directory)
        generator = MidiGenerator(
            input_file, output_midi, temp_dir=self.project_temp_dir
        )
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

        if not self.auto_approve:
            ready = questionary.confirm(
                "Have you finished fixing the MIDI/tabs?", default=False
            ).ask()
            if ready is None or not ready:
                self.console.print("[yellow]Exiting workflow.[/yellow]")
                raise SystemExit(0)

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
            self.session.transition_to(WorkflowState.TAB_GENERATION)

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

    def _step_tab_generation(self) -> None:
        """Offer to generate tabs from MIDI, then validate.

        Always offers to generate tabs from MIDI (will overwrite if file exists).
        If user declines, returns to MIDI fixing step.
        """
        tabs_path = self.session.input_tabs
        tab_file_exists = os.path.exists(tabs_path)

        # Always offer to generate tabs
        if tab_file_exists:
            self.console.print(
                Panel(
                    f"[cyan]Tab file found[/cyan]\n\n"
                    f"Path: {tabs_path}\n\n"
                    "You can regenerate tabs from MIDI if needed.\n"
                    "[dim]This will overwrite the existing file.[/dim]\n\n"
                    "[dim]Press N to go back and fix MIDI first.[/dim]",
                    title="📝 Tab Generation",
                )
            )
            prompt = "Generate new tabs from MIDI?"
            default = True
        else:
            self.console.print(
                Panel(
                    f"[yellow]Tab file not found[/yellow]\n\n"
                    f"Expected: {tabs_path}\n\n"
                    "You can generate tabs automatically from the MIDI file.\n"
                    "The generated tabs may need manual editing.\n\n"
                    "[dim]Press N to go back and fix MIDI first.[/dim]",
                    title="📝 Tab Generation",
                )
            )
            prompt = "Generate tabs from MIDI?"
            default = True

        # Ask about generation
        if self.auto_approve:
            # Auto-approve: generate only if file missing, otherwise continue with existing
            if not tab_file_exists:
                self._generate_tabs_from_midi()
            # Always continue forward in auto-approve mode
            if os.path.exists(tabs_path):
                self._validate_midi()
            else:
                self.session.set_data("skip_tab_video", True)
            self._select_fps()
            self.session.transition_to(WorkflowState.HARMONICA_REVIEW)
        else:
            # Manual mode: ask user
            generate_tabs = questionary.confirm(prompt, default=default).ask()

            if generate_tabs:
                self._generate_tabs_from_midi()

                # Run validation after generation
                if os.path.exists(tabs_path):
                    self._validate_midi()

                # Select FPS before video generation
                self._select_fps()

                self.session.transition_to(WorkflowState.HARMONICA_REVIEW)
            else:
                # User declined - offer to continue without tabs or go back
                if tab_file_exists:
                    # File exists, use it and continue
                    self.console.print("[green]✓ Using existing tab file[/green]")
                    self._validate_midi()
                    self._select_fps()
                    self.session.transition_to(WorkflowState.HARMONICA_REVIEW)
                else:
                    # No file - ask what to do
                    continue_without = questionary.confirm(
                        "Continue without tabs? (tab video will be skipped)",
                        default=False,
                    ).ask()

                    if continue_without:
                        self.console.print(
                            "[yellow]⏭️  Skipping tab video generation[/yellow]"
                        )
                        self.session.set_data("skip_tab_video", True)
                        self._select_fps()
                        self.session.transition_to(WorkflowState.HARMONICA_REVIEW)
                    else:
                        self.console.print(
                            "[yellow]⮌ Returning to MIDI fixing step.[/yellow]"
                        )
                        self.session.transition_to(WorkflowState.MIDI_FIXING)

    def _generate_tabs_from_midi(self) -> None:
        """Generate tab file from MIDI using the tab generator.

        Uses the same logic as cli.py generate-tabs command.
        """
        from tab_converter.tab_generator import TabGenerator, TabGeneratorConfig
        from tab_converter.tab_mapper import create_tab_mapper
        from harmonica_pipeline.midi_processor import MidiProcessor
        from utils.utils import TAB_FILES_DIR

        midi_path = self.session.get_data("generated_midi")
        harmonica_key = self.session.config.get("key", "C")
        output_path = self.session.input_tabs

        if not midi_path or not os.path.exists(midi_path):
            self.console.print("[red]✗ Cannot generate tabs: MIDI file not found[/red]")
            return

        self.console.print(
            Panel(
                f"[cyan]Generating tabs from MIDI[/cyan]\n\n"
                f"MIDI: {midi_path}\n"
                f"Key: {harmonica_key}\n"
                f"Output: {output_path}",
                title="📝 Tab Generation",
            )
        )

        try:
            # Load MIDI and convert to note events
            processor = MidiProcessor(midi_path)
            note_events = processor.load_note_events()

            # Convert to tabs using factory function
            mapper = create_tab_mapper(harmonica_key, output_path="temp")
            tabs = mapper.note_events_to_tabs(note_events)

            # Generate tab file with default formatting
            config = TabGeneratorConfig(
                notes_per_line=6,
                notes_per_page=24,
            )
            generator = TabGenerator(config)
            content = generator.generate(tabs)

            # Write to file
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            with open(output_path, "w") as f:
                f.write(content)

            self.console.print(f"[green]✓ Generated tabs: {output_path}[/green]")

            # Check if notes seem too high (wrong octave detection)
            self._check_octave_warning(tabs)

            # Open the tab file folder for user to review/edit
            self._open_folder(TAB_FILES_DIR)

            # Pause for user to review the generated tabs
            if not self.auto_approve:
                questionary.confirm(
                    "Review/edit the generated tabs, then press Enter to continue",
                    default=True,
                ).ask()

        except Exception as e:
            self.console.print(f"[red]✗ Tab generation failed: {e}[/red]")

    def _check_octave_warning(self, tabs) -> None:
        """Check if generated tabs suggest MIDI is in wrong octave.

        If most notes are in holes 7-10, the MIDI might be an octave too high.
        Shows a warning to help user identify pitch detection issues.
        """
        if not tabs or not tabs.tabs:
            return

        # Count notes in upper register (holes 7-10, including draws)
        upper_register = 0
        middle_register = 0
        lower_register = 0

        for tab_entry in tabs.tabs:
            hole = abs(tab_entry.tab)
            if hole >= 7:
                upper_register += 1
            elif hole >= 4:
                middle_register += 1
            else:
                lower_register += 1

        total = len(tabs.tabs)
        upper_percent = (upper_register / total) * 100 if total > 0 else 0

        # If more than 60% of notes are in upper register, warn user
        if upper_percent > 60:
            self.console.print(
                Panel(
                    f"[yellow]⚠️  Most notes ({upper_percent:.0f}%) are in holes 7-10[/yellow]\n\n"
                    f"Upper register (7-10): {upper_register} notes\n"
                    f"Middle register (4-6): {middle_register} notes\n"
                    f"Lower register (1-3): {lower_register} notes\n\n"
                    "This often means the MIDI is [bold]one octave too high[/bold].\n\n"
                    "[cyan]Fix:[/cyan] Transpose the MIDI down 12 semitones in your DAW,\n"
                    "then regenerate tabs.",
                    title="🎵 Octave Warning",
                )
            )

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

        # Create configuration (using project-specific temp directory)
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
            temp_dir=self.project_temp_dir,
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
            # Clear FPS so user can choose again
            self.session.set_data("fps", None)
            self.session.transition_to(WorkflowState.MIDI_FIXING)

    def _step_tab_video_review(self) -> None:
        """Generate full tab video and wait for user approval.

        Generates the full tab page animation video (compositor) and allows
        user to review it. If not approved, user can go back to MIDI fixing.
        """
        # Check if tab video should be skipped (no tab file)
        if self.session.get_data("skip_tab_video"):
            self.console.print(
                "[yellow]⏭️  Skipping tab video generation (no tab file)[/yellow]"
            )
            self.session.transition_to(WorkflowState.FINALIZATION)
            return

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

        # Output paths (video_creator will rename _tabs.mov to _full_tabs.mov)
        output_video = f"{self.session.song_name}_tabs.mov"
        output_video_path = os.path.join(OUTPUTS_DIR, output_video)
        # The actual output file will be named _full_tabs.mov
        final_output_path = os.path.join(
            OUTPUTS_DIR, f"{self.session.song_name}_full_tabs.mov"
        )

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

        # Create configuration (using project-specific temp directory)
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
            temp_dir=self.project_temp_dir,
        )

        # Generate tab video
        creator = VideoCreator(config)
        creator.create(create_harmonica=False, create_tabs=True)

        self.console.print(f"[green]✓ Tab video created: {final_output_path}[/green]")

        # Save output path to session (the actual _full_tabs.mov file)
        self.session.set_data("tab_video", final_output_path)

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
            # User declined - ask what they want to do
            action = questionary.select(
                "What would you like to do?",
                choices=[
                    "Regenerate tab video (keeps harmonica video)",
                    "Go back to MIDI fixing (regenerates both videos)",
                ],
            ).ask()

            if action and "MIDI fixing" in action:
                self.console.print("[yellow]⮌ Returning to MIDI fixing step.[/yellow]")
                self.session.set_data("fps", None)
                self.session.transition_to(WorkflowState.MIDI_FIXING)
            else:
                self.console.print("[yellow]⮌ Regenerating tab video...[/yellow]")
                self.session.transition_to(WorkflowState.TAB_VIDEO_REVIEW)

    def _step_finalization(self) -> None:
        """Finalize workflow - cleanup, ZIP, archive.

        Creates final output package and archives source files.
        """
        import shutil
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
        zip_name = f"{self.session.song_name}_{self.session.config.get('key', 'C')}"
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
        legacy_dir = os.path.join("legacy", self.session.song_name)
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
