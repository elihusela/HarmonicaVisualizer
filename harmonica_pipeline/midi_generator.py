"""
MIDI Generator - Phase 1 of the HarmonicaTabs pipeline.

Extracts audio from video and generates MIDI using basic_pitch.
"""

from basic_pitch import ICASSP_2022_MODEL_PATH
from basic_pitch.inference import predict

from utils.audio_extractor import AudioExtractor
from utils.utils import TEMP_DIR, clean_temp_folder


class MidiGenerator:
    """Handles audio extraction and MIDI generation from video files."""

    def __init__(self, video_path: str, output_midi_path: str):
        """
        Initialize MIDI generator.

        Args:
            video_path: Path to input video file
            output_midi_path: Path where generated MIDI should be saved
        """
        self.video_path = video_path
        self.output_midi_path = output_midi_path
        self.extracted_audio_path = TEMP_DIR + "extracted_audio.wav"

        # Initialize audio extractor
        self.audio_extractor = AudioExtractor(video_path, self.extracted_audio_path)

    def generate(self) -> None:
        """Run the complete MIDI generation process."""
        print("🧹 Cleaning temporary files...")
        clean_temp_folder()

        print("🎵 Extracting audio from video...")
        self._extract_audio()

        print("🎼 Converting audio to MIDI...")
        self._audio_to_midi()

        print("💾 MIDI generation complete!")

    def _extract_audio(self) -> None:
        """Extract audio from the video file."""
        self.audio_extractor.extract_audio_from_video()
        print(f"✅ Audio extracted to: {self.extracted_audio_path}")

    def _audio_to_midi(self) -> None:
        """Convert extracted audio to MIDI using basic_pitch."""
        print("🎼 Running audio-to-MIDI prediction...")

        _, midi_data, note_events = predict(
            audio_path=self.extracted_audio_path,
            model_or_model_path=ICASSP_2022_MODEL_PATH,
            onset_threshold=0.2,
            frame_threshold=0.2,
        )

        print(f"🎵 Generated {len(note_events)} note events")

        # Save the MIDI file
        midi_data.write(self.output_midi_path)
        print(f"💾 MIDI saved to: {self.output_midi_path}")
