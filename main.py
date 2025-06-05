from harmonica_pipeline.harmonica_pipeline import HarmonicaTabsPipeline
from image_converter.animator import Animator
from image_converter.consts import C_BASIC_MODEL_HOLE_MAPPING
from image_converter.figure_factory import FigureFactory
from image_converter.harmonica_layout import HarmonicaLayout
from tab_converter.consts import C_HARMONICA_MAPPING
from tab_converter.tab_mapper import TabMapper
from tab_phrase_animator.tab_phrase_animator import TabPhraseAnimator
from utils.audio_extractor import AudioExtractor
from utils.utils import TEMP_DIR, VIDEO_FILES_DIR, OUTPUTS_DIR

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 5:
        print(
            "Usage: python main.py video.mp4 harmonica_image.png output_video.mov output_tabs.mov"
        )
        # print("Usage: python main.py ShanaTova.mov BasicModel.png output_video.mov output_tabs.mov")

    else:
        harmonica_image_path = "harmonica-models/" + sys.argv[2]
        output_video_path = OUTPUTS_DIR + sys.argv[3]
        output_tabs_path = OUTPUTS_DIR + sys.argv[4]
        pipeline = HarmonicaTabsPipeline(
            TabMapper(C_HARMONICA_MAPPING, TEMP_DIR),
            Animator(
                HarmonicaLayout(harmonica_image_path, C_BASIC_MODEL_HOLE_MAPPING),
                FigureFactory(harmonica_image_path),
            ),
            TabPhraseAnimator(),
            AudioExtractor(
                VIDEO_FILES_DIR + sys.argv[1], TEMP_DIR + "extracted_audio.wav"
            ),
            harmonica_vid_output_path=output_video_path,
            tabs_output_path=output_tabs_path,
        )
        pipeline.run()
