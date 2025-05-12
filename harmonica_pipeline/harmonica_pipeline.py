from basic_pitch import ICASSP_2022_MODEL_PATH
from basic_pitch.inference import predict_and_save

from image_converter.animator import Animator
from tab_converter.models import Tabs
from tab_converter.tab_mapper import TabMapper
from utils.audio_extractor import AudioExtractor
from utils.utils import TEMP_DIR, clean_temp_folder, save_tabs_to_json


class HarmonicaTabsPipeline:
    def __init__(self, tab_mapper: TabMapper, animator: Animator, audio_extractor: AudioExtractor,
                 melody: bool = False):
        self._tab_mapper = tab_mapper
        self._animator = animator
        self._audio_extractor = audio_extractor
        self.midi_path = TEMP_DIR + "extracted_audio_basic_pitch.mid"
        self.tabs_json_path = TEMP_DIR + "tabs.json"
        self.melody = melody
        self._extracted_audio_path = ""

    def run(self) -> None:
        clean_temp_folder()
        self._extracted_audio_path = self._extract_audio()
        self._audio_to_midi()
        tabs = self.midi_to_tabs()
        self.render_animation(tabs)

    def _extract_audio(self) -> str:
        return self._audio_extractor.extract_audio_from_video()

    def _audio_to_midi(self) -> None:
        predict_and_save([self._extracted_audio_path],
                         TEMP_DIR,
                         True,
                         False,
                         False,
                         False,
                         multiple_pitch_bends=not self.melody,  # 🧠 invert logic: melody → single note
                         model_or_model_path=ICASSP_2022_MODEL_PATH)
        print(f"🎼 Audio to MIDI conversion complete → {self.midi_path}")

    def midi_to_tabs(self) -> Tabs:
        tabs = self._tab_mapper.midi_to_tabs_with_timing(str(self.midi_path))
        save_tabs_to_json(tabs, str(self.tabs_json_path))
        return tabs

    def render_animation(self, tabs: Tabs) -> None:
        self._animator.create_animation(tabs, str(self._extracted_audio_path))
