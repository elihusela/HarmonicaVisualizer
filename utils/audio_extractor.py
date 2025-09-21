import subprocess
from moviepy import VideoFileClip


class AudioExtractor:
    def __init__(self, video_path: str, audio_result_path: str):
        self._vid_path = video_path
        self._audio_result_path = audio_result_path

    def extract_audio_from_video(self) -> str:
        if ".wav" in self._vid_path:
            return self._vid_path

        try:
            # First try moviepy
            return self._extract_with_moviepy()
        except Exception as e:
            print(f"⚠️ MoviePy extraction failed: {e}")
            print("🔄 Trying direct ffmpeg extraction...")
            return self._extract_with_ffmpeg()

    def _extract_with_moviepy(self) -> str:
        """Extract audio using moviepy (original method)."""
        video_clip = VideoFileClip(self._vid_path)
        audio = video_clip.audio
        audio.write_audiofile(self._audio_result_path)
        print(f"🎧 Audio extracted and saved to {self._audio_result_path}")
        return self._audio_result_path

    def _extract_with_ffmpeg(self) -> str:
        """Extract audio using direct ffmpeg (fallback for complex videos)."""
        try:
            # Use ffmpeg directly to extract the first audio stream
            cmd = [
                "ffmpeg",
                "-i",
                self._vid_path,
                "-map",
                "0:a:0",  # Select first audio stream
                "-acodec",
                "pcm_s16le",  # Convert to WAV format
                "-ar",
                "44100",  # 44.1kHz sample rate
                "-ac",
                "2",  # Stereo
                "-y",
                self._audio_result_path,
            ]

            subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(
                f"🎧 Audio extracted with ffmpeg and saved to {self._audio_result_path}"
            )
            return self._audio_result_path

        except subprocess.CalledProcessError as e:
            print(f"❌ FFmpeg extraction failed: {e}")
            raise Exception(f"Could not extract audio from {self._vid_path}")
        except FileNotFoundError:
            print("❌ ffmpeg not found on system")
            raise Exception("ffmpeg required for audio extraction")
