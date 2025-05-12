from moviepy import VideoFileClip


def extract_audio_from_video(vid_path: str, audio_path: str = 'temp/extracted_audio.wav'):
    video_clip = VideoFileClip(vid_path)
    audio = video_clip.audio
    audio.write_audiofile(audio_path)
    print(f"🎧 Audio extracted and saved to {audio_path}")
    return audio_path
