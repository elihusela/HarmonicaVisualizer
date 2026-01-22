"""
MIDI Generator - Phase 1 of the HarmonicaTabs pipeline.

Extracts audio from video and generates MIDI using basic_pitch.
"""

from typing import Optional

from basic_pitch import ICASSP_2022_MODEL_PATH
from basic_pitch.inference import predict

from utils.audio_extractor import AudioExtractor
from utils.audio_processor import AudioProcessor
from utils.utils import TEMP_DIR, VIDEO_FILES_DIR, clean_temp_folder


class MidiGenerator:
    """Handles audio extraction and MIDI generation from video files."""

    def __init__(
        self,
        video_path: str,
        output_midi_path: str,
        enable_audio_processing: bool = True,
        audio_processor_params: Optional[dict] = None,
        onset_threshold: float = 0.4,
        frame_threshold: float = 0.3,
        minimum_note_length: float = 127.7,
        minimum_frequency: Optional[float] = None,
        maximum_frequency: Optional[float] = None,
        melodia_trick: bool = True,
        temp_dir: Optional[str] = None,
    ):
        """
        Initialize MIDI generator.

        Args:
            video_path: Path to input video or audio file
            output_midi_path: Path where generated MIDI should be saved
            enable_audio_processing: Whether to apply kaki.sh audio processing
            audio_processor_params: Dict of AudioProcessor parameters (low_freq, high_freq, etc.)
            onset_threshold: basic_pitch onset detection threshold (default: 0.4)
            frame_threshold: basic_pitch frame detection threshold (default: 0.3)
            minimum_note_length: Minimum note duration in ms (default: 127.7)
            minimum_frequency: Minimum frequency in Hz (default: None)
            maximum_frequency: Maximum frequency in Hz (default: None)
            melodia_trick: Enable melodia trick post-processing (default: True)
            temp_dir: Project-specific temp directory (default: global TEMP_DIR)
        """
        self.video_path = video_path
        self.output_midi_path = output_midi_path
        self.temp_dir = temp_dir or TEMP_DIR
        self.extracted_audio_path = self.temp_dir + "extracted_audio.wav"
        self.processed_audio_path = self.temp_dir + "midi_ready_audio.wav"

        # Audio processing settings
        self.enable_audio_processing = enable_audio_processing
        self.is_video_input = not video_path.lower().endswith(".wav")

        # basic_pitch parameters
        self.onset_threshold = onset_threshold
        self.frame_threshold = frame_threshold
        self.minimum_note_length = minimum_note_length
        self.minimum_frequency = minimum_frequency
        self.maximum_frequency = maximum_frequency
        self.melodia_trick = melodia_trick

        # Initialize audio processing components
        self.audio_extractor = AudioExtractor(video_path, self.extracted_audio_path)

        # Initialize AudioProcessor with custom parameters if provided
        if audio_processor_params:
            self.audio_processor = AudioProcessor(**audio_processor_params)
        else:
            self.audio_processor = AudioProcessor()  # Uses kaki.sh defaults

    def generate(self) -> None:
        """Run the complete 3-step MIDI generation process."""
        print("🧹 Cleaning temporary files...")
        clean_temp_folder(self.temp_dir)

        # Step 1: Extract WAV from video (if input is video)
        if self.is_video_input:
            print("🎬 Step 1: Extracting audio from video...")
            self._extract_audio()
        else:
            print("🎵 Step 1: Using WAV file directly...")
            self.extracted_audio_path = self.video_path

        # Step 2: Process audio with kaki.sh logic
        if self.enable_audio_processing:
            print("🎛️ Step 2: Processing audio for MIDI conversion...")
            self._process_audio_for_midi()
        else:
            print("⏭️  Step 2: Skipping audio processing...")
            self.processed_audio_path = self.extracted_audio_path

        # Step 3: Convert processed audio to MIDI
        print("🎼 Step 3: Converting audio to MIDI...")
        self._audio_to_midi()

        # Step 4: Save extracted WAV for Phase 2 reuse (if from video)
        if self.is_video_input:
            self._save_extracted_wav_for_reuse()

        print("💾 MIDI generation complete!")

    def _extract_audio(self) -> None:
        """Extract audio from the video file."""
        actual_audio_path = self.audio_extractor.extract_audio_from_video()
        self.extracted_audio_path = actual_audio_path
        print(f"✅ Audio ready at: {self.extracted_audio_path}")

    def _process_audio_for_midi(self) -> None:
        """Process audio using AudioProcessor class with kaki.sh logic."""
        success = self.audio_processor.process_for_midi(
            self.extracted_audio_path, self.processed_audio_path
        )

        if not success:
            print("⚠️ Audio processing failed, using unprocessed audio")
            self.processed_audio_path = self.extracted_audio_path

    def _audio_to_midi(self) -> None:
        """Convert processed audio to MIDI using basic_pitch."""
        print("🎼 Running audio-to-MIDI prediction...")

        _, midi_data, note_events = predict(
            audio_path=self.processed_audio_path,
            model_or_model_path=ICASSP_2022_MODEL_PATH,
            onset_threshold=self.onset_threshold,
            frame_threshold=self.frame_threshold,
            minimum_note_length=self.minimum_note_length,
            minimum_frequency=self.minimum_frequency,
            maximum_frequency=self.maximum_frequency,
            melodia_trick=self.melodia_trick,
        )

        print(f"🎵 Generated {len(note_events)} note events")

        # Save the MIDI file
        midi_data.write(self.output_midi_path)
        print(f"💾 MIDI saved to: {self.output_midi_path}")

    def _save_extracted_wav_for_reuse(self) -> None:
        """Save extracted WAV to video-files/ for Phase 2 reuse."""
        import shutil
        from pathlib import Path

        # Get video base name (without extension)
        video_base = Path(self.video_path).stem
        reusable_wav_path = f"{VIDEO_FILES_DIR}{video_base}.wav"

        try:
            # Copy extracted audio to video-files/ with video base name
            shutil.copy2(self.extracted_audio_path, reusable_wav_path)
            print(f"💾 Extracted WAV saved for reuse: {reusable_wav_path}")
            print(
                f"   Use for Phase 2: python cli.py create-video {video_base}.wav <tabs.txt>"
            )
        except Exception as e:
            print(f"⚠️ Could not save extracted WAV: {e}")
            print(f"   Manual copy: cp {self.extracted_audio_path} {reusable_wav_path}")
