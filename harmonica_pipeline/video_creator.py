"""
Video Creator - Phase 2 of the HarmonicaTabs pipeline.

Creates harmonica animation videos from fixed MIDI files and tab notation.
"""

import time
from typing import List, Tuple, Optional, Dict

import pretty_midi

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


class VideoCreator:
    """Handles video creation from fixed MIDI files and tab notation."""

    def __init__(
        self,
        video_path: str,
        tabs_path: str,
        harmonica_path: str,
        midi_path: str,
        output_video_path: str,
        tabs_output_path: Optional[str] = None,
        produce_tabs: bool = True,
    ):
        """
        Initialize video creator.

        Args:
            video_path: Path to original video file
            tabs_path: Path to tab text file
            harmonica_path: Path to harmonica model image
            midi_path: Path to fixed MIDI file
            output_video_path: Path for output harmonica video
            tabs_output_path: Optional path for tab phrase video
            produce_tabs: Whether to generate tab phrase animations
        """
        self.video_path = video_path
        self.tabs_path = tabs_path
        self.harmonica_path = harmonica_path
        self.midi_path = midi_path
        self.output_video_path = output_video_path
        self.tabs_output_path = tabs_output_path
        self.produce_tabs = produce_tabs

        # Audio extraction setup
        self.extracted_audio_path = TEMP_DIR + "extracted_audio.wav"
        self.audio_extractor = AudioExtractor(video_path, self.extracted_audio_path)

        # Tab processing setup
        self.tab_mapper = TabMapper(C_HARMONICA_MAPPING, TEMP_DIR)
        self.tabs_text_parser = TabTextParser(tabs_path)
        self.tab_matcher = TabMatcher()

        # Animation setup
        harmonica_layout = HarmonicaLayout(harmonica_path, C_NEW_MODEL_HOLE_MAPPING)
        figure_factory = FigureFactory(harmonica_path)

        self.animator = Animator(harmonica_layout, figure_factory)
        self.tab_phrase_animator = TabPhraseAnimator(harmonica_layout, figure_factory)

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
        print(f"🎹 Loading MIDI file: {self.midi_path}")

        midi_data = pretty_midi.PrettyMIDI(self.midi_path)

        # Remove pitch bends (as done in original pipeline)
        for instrument in midi_data.instruments:
            instrument.pitch_bends = []

        note_events = []
        for instrument in midi_data.instruments:
            for note in instrument.notes:
                note_events.append(
                    (note.start, note.end, note.pitch, note.velocity / 127.0, 1.0)
                )

        print(f"🎵 Loaded {len(note_events)} note events from MIDI")
        return note_events

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
