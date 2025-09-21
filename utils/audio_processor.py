"""
Audio Processor - Handles audio preprocessing for optimal MIDI conversion.

Based on the kaki.sh script logic with OOP architecture.
"""

import subprocess


class AudioProcessor:
    """
    Processes audio files for optimal MIDI conversion using proven kaki.sh methodology.

    Applies:
    - Mono conversion (better pitch detection)
    - Bandpass filtering (200Hz-5000Hz keeps melody frequencies)
    - Noise reduction (removes background noise)
    - Loudness normalization (consistent levels)
    """

    def __init__(
        self,
        low_freq: int = 200,
        high_freq: int = 5000,
        noise_reduction_db: int = -25,
        target_lufs: int = -16,
        true_peak_db: float = -1.5,
        lra: int = 11,
        sample_rate: int = 44100,
    ):
        """
        Initialize AudioProcessor with configurable parameters.

        Args:
            low_freq: High-pass filter frequency in Hz (default: 200)
            high_freq: Low-pass filter frequency in Hz (default: 5000)
            noise_reduction_db: Noise reduction strength in dB (default: -25)
            target_lufs: Target loudness in LUFS (default: -16)
            true_peak_db: True peak limit in dB (default: -1.5)
            lra: Loudness range in LU (default: 11)
            sample_rate: Output sample rate in Hz (default: 44100)
        """
        self.low_freq = low_freq
        self.high_freq = high_freq
        self.noise_reduction_db = noise_reduction_db
        self.target_lufs = target_lufs
        self.true_peak_db = true_peak_db
        self.lra = lra
        self.sample_rate = sample_rate

    def process_for_midi(self, input_path: str, output_path: str) -> bool:
        """
        Process audio file for optimal MIDI conversion.

        Args:
            input_path: Path to input audio file
            output_path: Path to save processed audio

        Returns:
            bool: True if processing succeeded, False otherwise
        """
        print(f"🎛️ Processing audio: {input_path}")
        print(
            f"   Filters: {self.low_freq}Hz-{self.high_freq}Hz, Noise: {self.noise_reduction_db}dB"
        )

        try:
            # Build ffmpeg command with kaki.sh parameters
            cmd = self._build_ffmpeg_command(input_path, output_path)

            # Execute processing
            subprocess.run(cmd, capture_output=True, text=True, check=True)

            print(f"✅ Audio processed and saved to: {output_path}")
            return True

        except subprocess.CalledProcessError as e:
            print(f"❌ Audio processing failed: {e}")
            if e.stderr:
                print(f"   Error details: {e.stderr}")
            return False
        except FileNotFoundError:
            print("❌ ffmpeg not found on system")
            return False

    def _build_ffmpeg_command(self, input_path: str, output_path: str) -> list:
        """
        Build ffmpeg command with kaki.sh parameters.

        Returns:
            list: ffmpeg command arguments
        """
        # Audio filter chain (same as kaki.sh)
        audio_filters = (
            f"highpass=f={self.low_freq}, "
            f"lowpass=f={self.high_freq}, "
            f"afftdn=nf={self.noise_reduction_db}, "
            f"loudnorm=I={self.target_lufs}:TP={self.true_peak_db}:LRA={self.lra}"
        )

        return [
            "ffmpeg",
            "-i",
            input_path,
            "-ac",
            "1",  # Convert to mono
            "-af",
            audio_filters,
            "-ar",
            str(self.sample_rate),
            "-y",
            output_path,  # Overwrite output file
        ]

    def get_processing_info(self) -> dict:
        """
        Get current processing configuration.

        Returns:
            dict: Current processing parameters
        """
        return {
            "frequency_range": f"{self.low_freq}-{self.high_freq} Hz",
            "noise_reduction": f"{self.noise_reduction_db} dB",
            "target_loudness": f"{self.target_lufs} LUFS",
            "true_peak": f"{self.true_peak_db} dB",
            "loudness_range": f"{self.lra} LU",
            "sample_rate": f"{self.sample_rate} Hz",
            "output_channels": "1 (mono)",
        }

    def update_parameters(self, **kwargs) -> None:
        """
        Update processing parameters.

        Args:
            **kwargs: Parameter name-value pairs to update
        """
        for param, value in kwargs.items():
            if hasattr(self, param):
                setattr(self, param, value)
                print(f"🔧 Updated {param}: {value}")
            else:
                print(f"⚠️ Unknown parameter: {param}")

    @staticmethod
    def get_recommended_presets() -> dict:
        """
        Get recommended parameter presets for different use cases.

        Returns:
            dict: Preset configurations
        """
        return {
            "harmonica_default": {
                "low_freq": 200,
                "high_freq": 5000,
                "noise_reduction_db": -25,
                "target_lufs": -16,
            },
            "harmonica_strict": {
                "low_freq": 250,
                "high_freq": 3000,
                "noise_reduction_db": -30,
                "target_lufs": -14,
            },
            "general_melody": {
                "low_freq": 150,
                "high_freq": 6000,
                "noise_reduction_db": -20,
                "target_lufs": -16,
            },
            "clean_studio": {
                "low_freq": 100,
                "high_freq": 8000,
                "noise_reduction_db": -15,
                "target_lufs": -18,
            },
        }
