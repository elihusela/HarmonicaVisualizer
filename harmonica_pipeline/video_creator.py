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
from image_converter.consts import C_NEW_MODEL_HOLE_MAPPING
from image_converter.figure_factory import FigureFactory
from image_converter.harmonica_layout import HarmonicaLayout
from tab_converter.consts import C_HARMONICA_MAPPING
from tab_converter.models import Tabs, TabEntry
from tab_converter.tab_mapper import TabMapper
from tab_phrase_animator.tab_matcher import TabMatcher
from tab_phrase_animator.tab_phrase_animator import TabPhraseAnimator
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
            self.tab_mapper = TabMapper(C_HARMONICA_MAPPING, TEMP_DIR)
            self.tabs_text_parser = TabTextParser(config.tabs_path)
            self.tab_matcher = TabMatcher()

            # Animation setup
            harmonica_layout = HarmonicaLayout(
                config.harmonica_path, C_NEW_MODEL_HOLE_MAPPING
            )
            figure_factory = FigureFactory(config.harmonica_path)

            self.animator = Animator(harmonica_layout, figure_factory)
            self.tab_phrase_animator = TabPhraseAnimator(
                harmonica_layout, figure_factory
            )

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
        if not video_path.lower().endswith((".mp4", ".mov", ".avi", ".wav")):
            raise VideoCreatorError(f"Unsupported video format: {video_path}")

        if not tabs_path.lower().endswith(".txt"):
            raise VideoCreatorError(f"Tab file must be .txt format: {tabs_path}")

        if not harmonica_path.lower().endswith((".png", ".jpg", ".jpeg")):
            raise VideoCreatorError(
                f"Harmonica image must be PNG/JPG format: {harmonica_path}"
            )

    def create(self) -> None:
        """Run the complete video creation process."""
        print("🎵 Extracting audio from video...")
        self._extract_audio()

        print("🎼 Loading MIDI and converting to tabs...")
        note_events = self._load_midi_note_events()
        tabs = self._note_events_to_tabs(note_events)

        print("🎯 Matching tabs with text notation...")
        matched_tabs = self._match_tabs(tabs)

        print("🎬 Creating harmonica animation...")
        self._create_harmonica_animation(matched_tabs)

        if self.produce_tabs and self.tabs_output_path:
            print("📄 Creating tab phrase animations...")
            self._create_tab_animations(matched_tabs)

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
        parsed_pages = self.tabs_text_parser.get_pages()
        return self.tab_matcher.match(tabs, parsed_pages)

    def _create_harmonica_animation(
        self, matched_tabs: Dict[str, List[List[Optional[List[TabEntry]]]]]
    ) -> None:
        """Create the main harmonica animation video."""
        start = time.perf_counter()
        self.animator.create_animation(
            matched_tabs, self.extracted_audio_path, self.output_video_path
        )
        duration = time.perf_counter() - start
        print(f"⏱ Harmonica animation completed in {duration:.2f}s")

    def _create_tab_animations(
        self, matched_tabs: Dict[str, List[List[Optional[List[TabEntry]]]]]
    ) -> None:
        """Create tab phrase animation video."""
        if self.tabs_output_path is None:
            return
        start = time.perf_counter()
        self.tab_phrase_animator.create_animations(
            matched_tabs, self.extracted_audio_path, self.tabs_output_path
        )
        duration = time.perf_counter() - start
        print(f"⏱ Tab phrase animation completed in {duration:.2f}s")
