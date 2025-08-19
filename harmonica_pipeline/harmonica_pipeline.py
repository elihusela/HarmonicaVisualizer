from typing import List, Tuple, Optional
import time

import pretty_midi
from basic_pitch import ICASSP_2022_MODEL_PATH
from basic_pitch.inference import predict

from image_converter.animator import Animator
from tab_converter.models import Tabs
from tab_converter.tab_mapper import TabMapper
from tab_phrase_animator.tab_matcher import TabMatcher
from tab_phrase_animator.tab_phrase_animator import TabPhraseAnimator
from tab_phrase_animator.tab_text_parser import TabTextParser
from utils.audio_extractor import AudioExtractor
from utils.utils import TEMP_DIR, clean_temp_folder


class HarmonicaTabsPipeline:
    def __init__(
        self,
        tab_mapper: TabMapper,
        animator: Animator,
        tab_phrase_animator: TabPhraseAnimator,
        audio_extractor: AudioExtractor,
        tabs_text_parser: TabTextParser,
        tab_matcher: TabMatcher,
        harmonica_vid_output_path: str,
        tabs_output_path: str,
        one_note_melody: bool = True,
        save_midi: bool = True,
        existing_midi_path: Optional[str] = None,
        produce_tabs: bool = False,
    ):
        self._tab_mapper = tab_mapper
        self._animator = animator
        self._tab_phrase_animator = tab_phrase_animator
        self._audio_extractor = audio_extractor
        self._tabs_text_parser: TabTextParser = tabs_text_parser
        self._tab_matcher: TabMatcher = tab_matcher
        self._output_path = harmonica_vid_output_path
        self._tabs_output_path = tabs_output_path
        self._one_note_melody = one_note_melody
        self._extracted_audio_path = ""
        self._save_midi = save_midi
        self._debug_midi_path = TEMP_DIR + "extracted_audio_basic_pitch.mid"
        self._existing_midi_path = existing_midi_path
        self._produce_tabs = produce_tabs

    def run(self) -> None:
        clean_temp_folder()
        self._extracted_audio_path = self._extract_audio()

        note_events = self._get_note_events()
        tabs = self._note_events_to_tabs(note_events)
        matched_tabs = self._tab_matcher.match(tabs, self._tabs_text_parser.get_pages())

        start = time.perf_counter()
        self._animator.create_animation(
            matched_tabs, str(self._extracted_audio_path), self._output_path
        )
        print(f"⏱ Animator finished in {time.perf_counter() - start:.2f}s")
        if self._produce_tabs:
            start = time.perf_counter()
            self._tab_phrase_animator.create_animations(
                matched_tabs, self._extracted_audio_path, self._tabs_output_path
            )
            print(f"⏱ TabPhraseAnimator finished in {time.perf_counter() - start:.2f}s")

    def _extract_audio(self) -> str:
        return self._audio_extractor.extract_audio_from_video()

    def _get_note_events(self) -> List:
        if self._existing_midi_path:
            print(f"🎹 Loading existing MIDI file: {self._existing_midi_path}")
            return self._midi_file_to_note_events(self._existing_midi_path)
        else:
            return self._audio_to_midi()

    def _audio_to_midi(self) -> List:
        print("🎼 Running audio-to-MIDI prediction (in-memory)...")
        _, midi_data, note_events = predict(
            audio_path=self._extracted_audio_path,
            model_or_model_path=ICASSP_2022_MODEL_PATH,
            onset_threshold=0.2,
            frame_threshold=0.2,
        )

        if self._save_midi:
            print(f"💾 Saving debug MIDI to {self._debug_midi_path}")
            midi_data.write(self._debug_midi_path)

        return note_events

    @staticmethod
    def _midi_file_to_note_events(
        midi_path: str,
    ) -> List[Tuple[int, float, float, float, float]]:
        midi_data = pretty_midi.PrettyMIDI(midi_path)
        for instrument in midi_data.instruments:
            instrument.pitch_bends = []  # forcibly remove pitch bends

        note_events = []
        for instrument in midi_data.instruments:
            for note in instrument.notes:
                note_events.append(
                    (note.start, note.end, note.pitch, note.velocity / 127.0, 1.0)
                )
        print(
            f"🎵 Extracted {len(note_events)} note events from MIDI file without pitch bends."
        )
        return note_events

    def _note_events_to_tabs(self, note_events: List[Tuple]) -> Tabs:
        tabs = self._tab_mapper.note_events_to_tabs(note_events)
        self._tab_mapper.save_tabs_to_json(tabs, "tabs.json")
        return tabs
