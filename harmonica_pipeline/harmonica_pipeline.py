from typing import List, Dict

from basic_pitch import ICASSP_2022_MODEL_PATH
from basic_pitch.inference import predict

from image_converter.animator import Animator
from tab_converter.models import Tabs
from tab_converter.tab_mapper import TabMapper
from utils.audio_extractor import AudioExtractor
from utils.utils import TEMP_DIR, clean_temp_folder


class HarmonicaTabsPipeline:
    def __init__(self, tab_mapper: TabMapper, animator: Animator, audio_extractor: AudioExtractor,
                 melody: bool = False, save_midi: bool = True):
        self._tab_mapper = tab_mapper
        self._animator = animator
        self._audio_extractor = audio_extractor
        self._midi_path = TEMP_DIR + "extracted_audio_basic_pitch.mid"
        self.melody = melody
        self._extracted_audio_path = ""
        self._save_midi = save_midi

    def run(self) -> None:
        clean_temp_folder()
        self._extracted_audio_path = self._extract_audio()
        note_events = self._audio_to_midi()
        tabs = self._note_events_to_tabs(note_events)
        self.render_animation(tabs)

    def _extract_audio(self) -> str:
        return self._audio_extractor.extract_audio_from_video()

    def _audio_to_midi(self) -> List:
        print("🎼 Running audio-to-MIDI prediction (in-memory)...")
        _, midi_data, note_events = predict(
            audio_path=self._extracted_audio_path,
            model_or_model_path=ICASSP_2022_MODEL_PATH
        )

        if self._save_midi:
            print(f"💾 Saving debug MIDI to {self._midi_path}")
            midi_data.write(self._midi_path)

        return note_events

    def _note_events_to_tabs(self, note_events: List[Dict]) -> Tabs:
        tabs = self._tab_mapper.note_events_to_tabs(note_events)
        self._tab_mapper.save_tabs_to_json(tabs, "tabs.json")
        return tabs

    def render_animation(self, tabs: Tabs) -> None:
        self._animator.create_animation(tabs, str(self._extracted_audio_path))
