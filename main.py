from harmonica_pipeline.harmonica_pipeline import HarmonicaTabsPipeline
from image_converter.animator import Animator
from tab_converter.consts import C_HARMONICA_MAPPING
from tab_converter.tab_mapper import TabMapper

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 4:
        print("Usage: python main.py video.mp4 harmonica_image.png output_video.mp4")
    else:
        pipeline = HarmonicaTabsPipeline(TabMapper(C_HARMONICA_MAPPING), Animator("harmonica-models/" + sys.argv[2]),
                                         video_path="video-files/" + sys.argv[1],
                                         output_video="outputs/" + sys.argv[3]
                                         )
        pipeline.run()
