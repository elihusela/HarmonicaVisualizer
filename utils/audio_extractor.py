from moviepy import VideoFileClip


class AudioExtractor:
    def __init__(self, video_path: str, audio_result_path: str):
        self._vid_path = video_path
        self._audio_result_path = audio_result_path

    def extract_audio_from_video(self) -> str:
        if ".wav" in self._vid_path:
            return self._vid_path
        video_clip = VideoFileClip(self._vid_path)
        audio = video_clip.audio
        audio.write_audiofile(self._audio_result_path)
        print(f"🎧 Audio extracted and saved to {self._audio_result_path}")
        return self._audio_result_path
