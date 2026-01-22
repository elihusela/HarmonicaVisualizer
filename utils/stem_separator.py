"""
Stem Separator - Demucs integration for harmonica isolation.

Uses Demucs htdemucs_6s model to separate audio into 6 stems:
vocals, drums, bass, guitar, piano, other

Harmonica typically ends up in the "other" stem.
"""

import os
import subprocess
import sys
from pathlib import Path


class StemSeparatorError(Exception):
    """Error during stem separation."""

    pass


class StemSeparator:
    """Separates audio into stems using Demucs."""

    # 6-stem model for best harmonica isolation
    MODEL = "htdemucs_6s"

    # Harmonica typically ends up in "other" (not vocals/drums/bass/guitar/piano)
    DEFAULT_STEM = "other"

    def __init__(self, output_dir: str = "stems"):
        """
        Initialize stem separator.

        Args:
            output_dir: Directory for separated stems (default: stems/)
        """
        self.output_dir = output_dir

    def _check_demucs_installed(self) -> bool:
        """Check if Demucs is available."""
        try:
            import demucs  # noqa: F401

            return True
        except ImportError:
            return False

    def _detect_device(self) -> str:
        """Detect best available device (cuda > mps > cpu)."""
        try:
            import torch

            if torch.cuda.is_available():
                return "cuda"
            if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                return "mps"
        except ImportError:
            pass
        return "cpu"

    def separate(
        self,
        input_file: str,
        stem: str = DEFAULT_STEM,
    ) -> str:
        """
        Separate audio and return path to specified stem.

        Args:
            input_file: Path to input audio/video file
            stem: Which stem to return (default: "other" for harmonica)

        Returns:
            Path to the separated stem file (MP3)

        Raises:
            StemSeparatorError: If separation fails
        """
        if not self._check_demucs_installed():
            raise StemSeparatorError("Demucs not installed. Run: pip install demucs")

        input_path = Path(input_file)
        if not input_path.exists():
            raise StemSeparatorError(f"Input file not found: {input_file}")

        # Extract audio from video if needed
        audio_file = self._prepare_audio(input_file)

        # Run Demucs
        device = self._detect_device()
        cmd = [
            sys.executable,
            "-m",
            "demucs",
            "-n",
            self.MODEL,
            "-o",
            self.output_dir,
            "--mp3",  # Use MP3 to avoid torchcodec issues
            "-d",
            device,
            audio_file,
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise StemSeparatorError(f"Demucs failed: {e.stderr}")

        # Find the output stem file
        audio_name = Path(audio_file).stem
        stem_path = Path(self.output_dir) / self.MODEL / audio_name / f"{stem}.mp3"

        if not stem_path.exists():
            raise StemSeparatorError(
                f"Expected stem not found: {stem_path}\n"
                f"Demucs output: {result.stdout}"
            )

        return str(stem_path)

    def _prepare_audio(self, input_file: str) -> str:
        """
        Prepare audio file for Demucs (extract from video if needed).

        Args:
            input_file: Input file path

        Returns:
            Path to audio file (WAV)
        """
        input_path = Path(input_file)
        video_extensions = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".webm"}

        if input_path.suffix.lower() not in video_extensions:
            # Already an audio file
            return input_file

        # Extract audio from video
        os.makedirs("temp", exist_ok=True)
        output_wav = f"temp/{input_path.stem}_extracted.wav"

        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            input_file,
            "-vn",  # No video
            "-acodec",
            "pcm_s16le",
            "-ar",
            "44100",
            "-ac",
            "2",
            output_wav,
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True)
        except subprocess.CalledProcessError as e:
            raise StemSeparatorError(f"Audio extraction failed: {e.stderr}")
        except FileNotFoundError:
            raise StemSeparatorError("ffmpeg not found. Please install ffmpeg.")

        return output_wav
