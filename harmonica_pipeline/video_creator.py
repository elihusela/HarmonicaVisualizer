"""
Video Creator - Phase 2 of the HarmonicaTabs pipeline.

Creates harmonica animation videos from fixed MIDI files and tab notation.
"""

import os
import time
from typing import List, Tuple, Optional, Dict, Union

from harmonica_pipeline.midi_processor import MidiProcessor, MidiProcessorError
from harmonica_pipeline.video_creator_config import VideoCreatorConfig
from image_converter.animator import Animator
from image_converter.figure_factory import FigureFactory
from image_converter.harmonica_layout import HarmonicaLayout
from tab_converter.models import Tabs, TabEntry
from tab_converter.tab_mapper import TabMapper
from tab_phrase_animator.full_tab_video_compositor import FullTabVideoCompositor
from tab_phrase_animator.tab_matcher import TabMatcher
from tab_phrase_animator.tab_phrase_animator import TabPhraseAnimator, PageStatistics
from tab_phrase_animator.tab_text_parser import TabTextParser
from utils.audio_extractor import AudioExtractor
from utils.utils import TEMP_DIR


class VideoCreatorError(Exception):
    """Custom exception for video creation errors."""

    pass


class VideoCreator:
    """Handles video creation from fixed MIDI files and tab notation."""

    def __init__(
        self,
        config_or_video_path: Union[VideoCreatorConfig, str],
        tabs_path: Optional[str] = None,
        harmonica_path: Optional[str] = None,
        midi_path: Optional[str] = None,
        output_video_path: Optional[str] = None,
        tabs_output_path: Optional[str] = None,
        produce_tabs: bool = True,
    ):
        """
        Initialize video creator.

        Args:
            config_or_video_path: Either VideoCreatorConfig object or video file path (for backwards compatibility)
            tabs_path: Path to tab text file (only if using old-style initialization)
            harmonica_path: Path to harmonica model image (only if using old-style initialization)
            midi_path: Path to fixed MIDI file (only if using old-style initialization)
            output_video_path: Path for output harmonica video (only if using old-style initialization)
            tabs_output_path: Optional path for tab phrase video
            produce_tabs: Whether to generate tab phrase animations

        Raises:
            VideoCreatorError: If any input files are missing or invalid
        """
        # Support both config object and legacy parameter style
        if isinstance(config_or_video_path, VideoCreatorConfig):
            config = config_or_video_path
        else:
            # Legacy initialization - create config from parameters
            if any(
                param is None
                for param in [tabs_path, harmonica_path, midi_path, output_video_path]
            ):
                raise VideoCreatorError(
                    "When using legacy initialization, all path parameters are required"
                )

            config = VideoCreatorConfig.from_cli_args(
                video_path=config_or_video_path,
                tabs_path=tabs_path,  # type: ignore[arg-type]
                harmonica_path=harmonica_path,  # type: ignore[arg-type]
                midi_path=midi_path,  # type: ignore[arg-type]
                output_video_path=output_video_path,  # type: ignore[arg-type]
                tabs_output_path=tabs_output_path,
                produce_tabs=produce_tabs,
            )

        # Validate input files
        self._validate_input_files(
            config.video_path, config.tabs_path, config.harmonica_path, config.midi_path
        )

        # Store configuration
        self.config = config
        self.video_path = config.video_path
        self.tabs_path = config.tabs_path
        self.harmonica_path = config.harmonica_path
        self.midi_path = config.midi_path
        self.output_video_path = config.output_video_path
        self.tabs_output_path = config.tabs_output_path
        self.produce_tabs = config.produce_tabs

        try:
            # Audio extraction setup
            self.extracted_audio_path = TEMP_DIR + "extracted_audio.wav"
            self.audio_extractor = AudioExtractor(
                config.video_path, self.extracted_audio_path
            )

            # MIDI and tab processing setup
            self.midi_processor = MidiProcessor(config.midi_path)
            # Use key-specific MIDI mapping from config
            self.tab_mapper = TabMapper(config._key_config.midi_mapping, TEMP_DIR)

            # Tab text parsing setup (always load if producing tabs)
            self.tabs_text_parser: Optional[TabTextParser]
            if config.produce_tabs or config.enable_tab_matching:
                self.tabs_text_parser = TabTextParser(config.tabs_path)
                print(f"📖 Loaded tab text file: {config.tabs_path}")
            else:
                self.tabs_text_parser = None

            # Tab matching setup (optional)
            self.tab_matcher: Optional[TabMatcher]
            if config.enable_tab_matching:
                if not self.tabs_text_parser:
                    self.tabs_text_parser = TabTextParser(config.tabs_path)
                self.tab_matcher = TabMatcher(enable_debug=False)
                print("🔍 Tab matching enabled (experimental)")
            else:
                self.tab_matcher = None

            # Animation setup
            # Use key-specific hole mapping from config
            harmonica_layout = HarmonicaLayout(
                config.harmonica_path, config._key_config.hole_mapping
            )
            figure_factory = FigureFactory(config.harmonica_path)

            self.animator = Animator(harmonica_layout, figure_factory)

            # Create AnimationConfig with custom buffer if specified
            from tab_phrase_animator.tab_phrase_animator import AnimationConfig

            animation_config = AnimationConfig(time_buffer=config.tab_page_buffer)

            self.tab_phrase_animator = TabPhraseAnimator(
                harmonica_layout, figure_factory, config=animation_config
            )
            self.full_tab_compositor = FullTabVideoCompositor()

        except MidiProcessorError as e:
            raise VideoCreatorError(f"MIDI processing error: {e}")
        except Exception as e:
            raise VideoCreatorError(f"Failed to initialize video creator: {e}")

    @classmethod
    def from_config(cls, config: VideoCreatorConfig) -> "VideoCreator":
        """
        Create VideoCreator from configuration object.

        Args:
            config: VideoCreatorConfig object

        Returns:
            VideoCreator instance
        """
        return cls(config)

    def _validate_input_files(
        self, video_path: str, tabs_path: str, harmonica_path: str, midi_path: str
    ) -> None:
        """
        Validate that all required input files exist.

        Raises:
            VideoCreatorError: If any required files are missing
        """
        files_to_check = [
            (video_path, "Video file"),
            (tabs_path, "Tab file"),
            (harmonica_path, "Harmonica model image"),
            (midi_path, "MIDI file"),
        ]

        for file_path, file_type in files_to_check:
            if not os.path.exists(file_path):
                raise VideoCreatorError(f"{file_type} not found: {file_path}")

        # Validate file extensions
        if not video_path.lower().endswith((".mp4", ".mov", ".avi", ".m4v", ".wav")):
            raise VideoCreatorError(f"Unsupported video format: {video_path}")

        if not tabs_path.lower().endswith(".txt"):
            raise VideoCreatorError(f"Tab file must be .txt format: {tabs_path}")

        if not harmonica_path.lower().endswith((".png", ".jpg", ".jpeg")):
            raise VideoCreatorError(
                f"Harmonica image must be PNG/JPG format: {harmonica_path}"
            )

    def create(
        self, create_harmonica: bool = True, create_tabs: Optional[bool] = None
    ) -> None:
        """
        Run the complete video creation process.

        Args:
            create_harmonica: Whether to create harmonica animation (default: True)
            create_tabs: Whether to create tab phrase animations (default: uses self.produce_tabs)
        """
        # Use defaults if not specified
        if create_tabs is None:
            create_tabs = self.produce_tabs

        print("🎵 Extracting audio from video...")
        self._extract_audio()

        print("🎼 Loading MIDI and converting to tabs...")
        note_events = self._load_midi_note_events()
        tabs = self._note_events_to_tabs(note_events)

        # Tab matching - use .txt file structure when available (preserves bend info)
        # This applies to both tab phrase animations AND harmonica animations
        if self.tabs_text_parser:
            print("🎯 Using .txt file structure (preserves bend notation)...")
            matched_tabs = self._create_text_based_structure(tabs)
        elif self.config.enable_tab_matching and self.tab_matcher:
            print("🎯 Matching tabs with text notation...")
            matched_tabs = self._match_tabs(tabs)
        else:
            print("⏭️  Using direct MIDI-to-animation structure")
            matched_tabs = self._create_direct_tabs_structure(tabs)

        if create_harmonica:
            print("🎬 Creating harmonica animation...")
            self._create_harmonica_animation(matched_tabs)
        else:
            print("⏭️  Skipping harmonica animation")

        if create_tabs and self.tabs_output_path:
            print("📄 Creating tab phrase animations...")
            self._create_tab_animations(matched_tabs)
        elif not create_tabs:
            print("⏭️  Skipping tab phrase animations")

        print("✅ Video creation complete!")

    def _extract_audio(self) -> None:
        """Extract audio from the video file."""
        self.audio_extractor.extract_audio_from_video()

    def _load_midi_note_events(self) -> List[Tuple[float, float, int, float, float]]:
        """Load note events from the fixed MIDI file."""
        return self.midi_processor.load_note_events()

    def _note_events_to_tabs(self, note_events: List[Tuple]) -> Tabs:
        """Convert note events to harmonica tabs."""
        tabs = self.tab_mapper.note_events_to_tabs(note_events)
        self.tab_mapper.save_tabs_to_json(tabs, "tabs.json")
        return tabs

    def _match_tabs(
        self, tabs: Tabs
    ) -> Dict[str, List[List[Optional[List[TabEntry]]]]]:
        """Match generated tabs with parsed text notation."""
        if not self.tabs_text_parser or not self.tab_matcher:
            raise VideoCreatorError(
                "Tab matching is disabled but _match_tabs was called"
            )
        parsed_pages = self.tabs_text_parser.get_pages()
        return self.tab_matcher.match(tabs, parsed_pages)

    def _create_direct_tabs_structure(
        self, tabs: Tabs
    ) -> Dict[str, List[List[Optional[List[TabEntry]]]]]:
        """
        Create a simple animation structure directly from MIDI tabs.

        Bypasses tab matching and creates multiple pages based on timing gaps
        to generate multiple tab phrase animations instead of just one.
        """
        tab_entries = tabs.tabs if hasattr(tabs, "tabs") else tabs

        if not tab_entries:
            return {"page_1": [[]]}

        # Sort entries by time
        tab_entries_list: List[TabEntry] = tab_entries  # type: ignore[assignment]
        sorted_entries: List[TabEntry] = sorted(tab_entries_list, key=lambda e: e.time)

        # Split into pages based on timing gaps (> 2 seconds indicates new phrase/page)
        pages: List[List[TabEntry]] = []
        current_page: List[TabEntry] = []
        last_time = sorted_entries[0].time

        for entry in sorted_entries:
            # If there's a gap of more than 2 seconds, start a new page
            if entry.time - last_time > 2.0 and current_page:
                pages.append(current_page)
                current_page = []

            current_page.append(entry)
            last_time = entry.time

        # Add the last page if it has content
        if current_page:
            pages.append(current_page)

        # Create structure with multiple pages
        direct_structure: Dict[str, List[List[Optional[List[TabEntry]]]]] = {}
        for i, page_entries in enumerate(pages, 1):
            direct_structure[f"page_{i}"] = [
                # Single line with each tab entry as its own "chord"
                [[entry] for entry in page_entries]
            ]

        print(f"📄 Created {len(pages)} tab phrase pages from MIDI timing")
        return direct_structure

    def _create_text_based_structure(
        self, tabs: Tabs
    ) -> Dict[str, List[List[Optional[List[TabEntry]]]]]:
        """
        Create animation structure based on .txt file page/line definitions.

        Uses the parsed .txt file structure to maintain proper page breaks
        and line organization, consuming MIDI entries sequentially to match
        the exact note count specified in the text file.
        """
        if not self.tabs_text_parser:
            raise VideoCreatorError("Tab text parser not available")

        # Get parsed page structure from .txt file
        parsed_pages = self.tabs_text_parser.get_pages()
        tab_entries = tabs.tabs if hasattr(tabs, "tabs") else tabs

        if not tab_entries:
            print("⚠️  No MIDI tab entries found, using text structure only")
            return self._create_text_only_structure(parsed_pages)

        # Sort MIDI entries by time to maintain chronological order
        tab_entries_list: List[TabEntry] = tab_entries  # type: ignore[assignment]
        sorted_midi_entries: List[TabEntry] = sorted(
            tab_entries_list, key=lambda e: e.time
        )
        midi_index = 0  # Global index tracking position in MIDI entries

        print(
            f"🔍 Text-based structure matching: {len(parsed_pages)} text pages, "
            f"{len(sorted_midi_entries)} total MIDI entries"
        )

        # Build structure following .txt file organization
        animation_structure: Dict[str, List[List[Optional[List[TabEntry]]]]] = {}

        for page_name, page_lines in parsed_pages.items():
            page_start_midi_index = midi_index
            animation_lines: List[List[Optional[List[TabEntry]]]] = []

            for line_chords in page_lines:
                animation_chords: List[Optional[List[TabEntry]]] = []

                for chord_tabs in line_chords:
                    if not chord_tabs:
                        animation_chords.append(None)
                        continue

                    # For each note in the chord, take the next MIDI entry sequentially
                    chord_entries = []
                    for parsed_note in chord_tabs:
                        if midi_index < len(sorted_midi_entries):
                            # Use the next MIDI entry regardless of hole number match
                            # This ensures we consume exactly the number of notes in the text file
                            midi_entry = sorted_midi_entries[midi_index]
                            matched_entry = TabEntry(
                                tab=parsed_note.hole_number,  # Preserve text file notation
                                time=midi_entry.time,
                                duration=midi_entry.duration,
                                confidence=midi_entry.confidence,
                                is_bend=parsed_note.is_bend,  # Preserve bend from text
                                bend_notation=parsed_note.bend_notation,  # Preserve bend notation
                            )
                            chord_entries.append(matched_entry)
                            midi_index += 1
                        else:
                            # Ran out of MIDI entries - create placeholder
                            last_time = (
                                sorted_midi_entries[-1].time
                                if sorted_midi_entries
                                else 0.0
                            )
                            fallback_entry = TabEntry(
                                tab=parsed_note.hole_number,
                                time=last_time
                                + 0.5 * (midi_index - len(sorted_midi_entries) + 1),
                                duration=0.5,
                                confidence=0.5,
                                is_bend=parsed_note.is_bend,
                                bend_notation=parsed_note.bend_notation,
                            )
                            chord_entries.append(fallback_entry)
                            midi_index += 1

                    if chord_entries:
                        animation_chords.append(chord_entries)
                    else:
                        animation_chords.append(None)

                animation_lines.append(animation_chords)

            animation_structure[page_name] = animation_lines
            page_midi_count = midi_index - page_start_midi_index

            # Count actual notes in text for this page
            text_note_count = sum(
                len(chord_tabs)
                for line_chords in page_lines
                for chord_tabs in line_chords
                if chord_tabs
            )

            print(
                f"   📄 {page_name}: consumed {page_midi_count} MIDI entries (text specified {text_note_count} notes)"
            )

        print(f"📖 Created {len(animation_structure)} pages using .txt file structure")
        print(f"🎵 Consumed {midi_index}/{len(sorted_midi_entries)} total MIDI entries")

        if midi_index != len(sorted_midi_entries):
            remaining = len(sorted_midi_entries) - midi_index
            print(
                f"⚠️  Warning: {remaining} MIDI entries unused (text file has fewer notes than MIDI)"
            )

        return animation_structure

    def _create_text_only_structure(
        self, parsed_pages
    ) -> Dict[str, List[List[Optional[List[TabEntry]]]]]:
        """
        Create structure from text file only (fallback when no MIDI available).
        """
        animation_structure: Dict[str, List[List[Optional[List[TabEntry]]]]] = {}

        for page_name, page_lines in parsed_pages.items():
            animation_lines: List[List[Optional[List[TabEntry]]]] = []

            for line_chords in page_lines:
                animation_chords: List[Optional[List[TabEntry]]] = []

                for chord_tabs in line_chords:
                    if not chord_tabs:
                        animation_chords.append(None)
                        continue

                    # Create dummy TabEntry objects with 0.5 second duration
                    # chord_tabs contains ParsedNote objects
                    chord_entries = [
                        TabEntry(
                            tab=parsed_note.hole_number,
                            time=0.0,
                            duration=0.5,
                            confidence=1.0,
                            is_bend=parsed_note.is_bend,
                            bend_notation=parsed_note.bend_notation,
                        )
                        for parsed_note in chord_tabs
                    ]
                    animation_chords.append(chord_entries)

                animation_lines.append(animation_chords)

            animation_structure[page_name] = animation_lines

        return animation_structure

    def _create_harmonica_animation(
        self, matched_tabs: Dict[str, List[List[Optional[List[TabEntry]]]]]
    ) -> None:
        """Create the main harmonica animation video."""
        start = time.perf_counter()
        # Get audio duration to show harmonica for full video length
        audio_duration = self._get_audio_duration(self.extracted_audio_path)
        self.animator.create_animation(
            matched_tabs,
            self.extracted_audio_path,
            self.output_video_path,
            audio_duration=audio_duration,
        )
        duration = time.perf_counter() - start
        print(f"⏱ Harmonica animation completed in {duration:.2f}s")

    def _create_tab_animations(
        self, matched_tabs: Dict[str, List[List[Optional[List[TabEntry]]]]]
    ) -> None:
        """Create tab phrase animation videos (individual pages and full video)."""
        if self.tabs_output_path is None:
            return

        start = time.perf_counter()

        # Get audio duration to show first/last pages for full timing
        audio_duration = self._get_audio_duration(self.extracted_audio_path)

        # Create individual page animations
        page_statistics: List[PageStatistics] = (
            self.tab_phrase_animator.create_animations(
                matched_tabs,
                self.extracted_audio_path,
                self.tabs_output_path,
                audio_duration=audio_duration,
            )
        )

        duration = time.perf_counter() - start
        print(f"⏱ Tab phrase animation completed in {duration:.2f}s")

        # Create full tab video if enabled
        if self.config.produce_full_tab_video and page_statistics:
            print("🎬 Creating full tab video...")
            full_start = time.perf_counter()

            # Get audio duration
            audio_duration = self._get_audio_duration(self.extracted_audio_path)

            # Generate full tab video path
            full_tab_output = self.tabs_output_path.replace(
                "_tabs.mov", "_full_tabs.mov"
            )
            if full_tab_output == self.tabs_output_path:
                # If replacement didn't work, append _full
                full_tab_output = self.tabs_output_path.replace(".mov", "_full.mov")

            try:
                self.full_tab_compositor.generate(
                    page_statistics,
                    audio_duration,
                    full_tab_output,
                    audio_path=self.extracted_audio_path,
                )
                full_duration = time.perf_counter() - full_start
                print(f"⏱ Full tab video completed in {full_duration:.2f}s")

                # Clean up individual page files if only full video requested
                if self.config.only_full_tab_video:
                    print("🗑️  Cleaning up individual page files...")
                    for stat in page_statistics:
                        try:
                            if os.path.exists(stat.output_file):
                                os.remove(stat.output_file)
                        except OSError:
                            pass  # Ignore cleanup errors

            except Exception as e:
                print(f"⚠️  Warning: Failed to create full tab video: {e}")

    def _get_audio_duration(self, audio_path: str) -> float:
        """
        Get the duration of an audio file using ffprobe.

        Args:
            audio_path: Path to the audio file

        Returns:
            Duration in seconds

        Raises:
            VideoCreatorError: If duration cannot be determined
        """
        import subprocess
        import json

        try:
            cmd = [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                audio_path,
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            data = json.loads(result.stdout)
            duration = float(data["format"]["duration"])
            return duration
        except Exception as e:
            raise VideoCreatorError(f"Failed to get audio duration: {e}")
