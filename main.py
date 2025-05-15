from harmonica_pipeline.harmonica_pipeline import HarmonicaTabsPipeline
from image_converter.animator import Animator
from tab_converter.consts import C_HARMONICA_MAPPING
from tab_converter.tab_mapper import TabMapper
from utils.audio_extractor import AudioExtractor
from utils.utils import TEMP_DIR, VIDEO_FILES_DIR, OUTPUTS_DIR

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 4:
        print("Usage: python main.py video.mp4 harmonica_image.png output_video.mp4")
        # print("Usage: python main.py ShanaTova.mov BasicModel.png output_video.mp4")

    else:
        harmonica_image_path = "harmonica-models/" + sys.argv[2]
        output_path = OUTPUTS_DIR + sys.argv[3]
        pipeline = HarmonicaTabsPipeline(
            TabMapper(C_HARMONICA_MAPPING, TEMP_DIR),
            Animator(harmonica_image_path, output_path),
            AudioExtractor(
                VIDEO_FILES_DIR + sys.argv[1], TEMP_DIR + "extracted_audio.wav"
            ),
        )
        pipeline.run()
