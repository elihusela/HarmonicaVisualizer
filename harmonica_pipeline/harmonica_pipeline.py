from basic_pitch import ICASSP_2022_MODEL_PATH
from basic_pitch.inference import predict_and_save

from image_converter.animator import Animator
from tab_converter.models import Tabs
from tab_converter.tab_mapper import TabMapper
from utils.media_utils import extract_audio_from_video
from utils.utils import TEMP_DIR, clean_temp_folder, save_tabs_to_json


class HarmonicaTabsPipeline:
    def __init__(self, tab_mapper: TabMapper, animator: Animator, video_path: str,
                 output_video: str,
                 melody: bool = False):
        self._tab_mapper = tab_mapper
        self._animator = animator
        self.video_path = video_path
        self.output_path = output_video
        self._extracted_audio_path = TEMP_DIR + "extracted_audio.wav"
        self.midi_path = TEMP_DIR + "extracted_audio_basic_pitch.mid"
        self.tabs_json_path = TEMP_DIR + "tabs.json"
        self.melody = melody

    def _extract_audio(self):
        extract_audio_from_video(self.video_path, str(self._extracted_audio_path))

    def _audio_to_midi(self):
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

    def render_animation(self, tabs: Tabs):
        self._animator.create_animation(tabs, str(self._extracted_audio_path), self.output_path)

    def run(self):
        clean_temp_folder()
        self._extract_audio()
        self._audio_to_midi()
        tabs = self.midi_to_tabs()
        self.render_animation(tabs)
