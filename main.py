import os

from harmonica_pipeline.harmonica_pipeline import HarmonicaTabsPipeline
from image_converter.animator import Animator
from image_converter.consts import C_NEW_MODEL_HOLE_MAPPING
from image_converter.figure_factory import FigureFactory
from image_converter.harmonica_layout import HarmonicaLayout
from tab_converter.consts import C_HARMONICA_MAPPING
from tab_converter.tab_mapper import TabMapper
from tab_phrase_animator.tab_matcher import TabMatcher
from tab_phrase_animator.tab_phrase_animator import TabPhraseAnimator
from tab_phrase_animator.tab_text_parser import TabTextParser
from utils.audio_extractor import AudioExtractor
from utils.utils import TEMP_DIR, VIDEO_FILES_DIR, OUTPUTS_DIR, TAB_FILES_DIR, MIDI_DIR

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 6:
        print(
            "Usage: python main.py video.mp4 PCN.txt harmonica_image.png output_video.mov output_tabs.mov midi.mid"
        )
        # print("Usage: python main.py ShanaTova.mov tabs.txt BasicModel.png output_video.mov output_tabs.mov")

    else:
        harmonica_image_path = "harmonica-models/" + sys.argv[3]
        tab_file_path = TAB_FILES_DIR + sys.argv[2]
        output_video_path = OUTPUTS_DIR + sys.argv[4]
        output_tabs_path = OUTPUTS_DIR + sys.argv[5]
        existing_midi: str = sys.argv[6] if len(sys.argv) > 6 else ""
        existing_midi_path: str = (
            os.path.join(MIDI_DIR, existing_midi) if existing_midi else ""
        )

        pipeline = HarmonicaTabsPipeline(
            TabMapper(C_HARMONICA_MAPPING, TEMP_DIR),
            Animator(
                HarmonicaLayout(harmonica_image_path, C_NEW_MODEL_HOLE_MAPPING),
                FigureFactory(harmonica_image_path),
            ),
            TabPhraseAnimator(
                HarmonicaLayout(harmonica_image_path, C_NEW_MODEL_HOLE_MAPPING),
                FigureFactory(harmonica_image_path),
            ),
            AudioExtractor(
                VIDEO_FILES_DIR + sys.argv[1], TEMP_DIR + "extracted_audio.wav"
            ),
            TabTextParser(tab_file_path),
            TabMatcher(),
            harmonica_vid_output_path=output_video_path,
            tabs_output_path=output_tabs_path,
            save_midi=True,
            existing_midi_path=existing_midi_path,
            produce_tabs=False,
        )
        pipeline.run()
