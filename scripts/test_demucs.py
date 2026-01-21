#!/usr/bin/env python3
"""
Demucs Stem Separation Test Script

Tests Demucs on your audio/video files to see how well it separates harmonica
from other instruments.

Usage:
    python scripts/test_demucs.py <input_file>
    python scripts/test_demucs.py video-files/MySong.mp4
    python scripts/test_demucs.py --check-gpu  # Just check GPU availability

Requirements (will be installed if missing):
    pip install torch demucs

Output:
    stems/<song_name>/
    ├── vocals.wav      # Singing/melodic content (harmonica often here)
    ├── drums.wav       # Percussion
    ├── bass.wav        # Bass instruments
    ├── guitar.wav      # Guitar (6-stem model)
    ├── piano.wav       # Piano (6-stem model)
    └── other.wav       # Everything else
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def check_dependencies():
    """Check if required packages are installed."""
    missing = []

    try:
        import torch

        print(f"PyTorch version: {torch.__version__}")
    except ImportError:
        missing.append("torch")

    try:
        import demucs  # noqa: F401

        print("Demucs installed: Yes")
    except ImportError:
        missing.append("demucs")

    if missing:
        print(f"\nMissing packages: {', '.join(missing)}")
        print("\nInstall with:")
        print("  pip install torch demucs")
        print("\nFor Apple Silicon (M1/M2/M3), install PyTorch with MPS support:")
        print("  pip install torch torchvision torchaudio")
        return False

    return True


def check_gpu():
    """Check GPU availability and type."""
    try:
        import torch

        print("\n=== GPU Status ===")

        # Check CUDA (NVIDIA)
        if torch.cuda.is_available():
            print("CUDA available: Yes")
            print(f"CUDA device: {torch.cuda.get_device_name(0)}")
            print(
                f"CUDA memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB"
            )
            return "cuda"

        # Check MPS (Apple Silicon)
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            print("MPS (Apple Silicon) available: Yes")
            return "mps"

        print("No GPU available - will use CPU (slower)")
        return "cpu"

    except ImportError:
        print("PyTorch not installed - cannot check GPU")
        return None


def extract_audio(input_file: str, output_wav: str) -> bool:
    """Extract audio from video file using ffmpeg."""
    print(f"\nExtracting audio from: {input_file}")

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        input_file,
        "-vn",  # No video
        "-acodec",
        "pcm_s16le",  # WAV format
        "-ar",
        "44100",  # 44.1kHz
        "-ac",
        "2",  # Stereo
        output_wav,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"FFmpeg error: {result.stderr}")
            return False
        print(f"Audio extracted to: {output_wav}")
        return True
    except FileNotFoundError:
        print("FFmpeg not found. Please install ffmpeg.")
        return False


def run_demucs(input_file: str, output_dir: str, model: str = "htdemucs_6s"):
    """
    Run Demucs stem separation.

    Models:
    - htdemucs: 4 stems (vocals, drums, bass, other)
    - htdemucs_6s: 6 stems (vocals, drums, bass, guitar, piano, other)
    """
    print(f"\n=== Running Demucs ({model}) ===")
    print(f"Input: {input_file}")
    print(f"Output: {output_dir}")
    print("\nThis may take a few minutes...")

    # Build command
    cmd = [
        sys.executable,
        "-m",
        "demucs",
        "-n",
        model,  # Model name
        "-o",
        output_dir,  # Output directory
        input_file,
    ]

    # Check GPU and add device flag
    device = check_gpu()
    if device == "cuda":
        cmd.extend(["-d", "cuda"])
    elif device == "mps":
        cmd.extend(["-d", "mps"])
    else:
        cmd.extend(["-d", "cpu"])

    print(f"\nCommand: {' '.join(cmd)}")
    print("\n" + "=" * 50)

    # Run demucs
    result = subprocess.run(cmd)

    if result.returncode == 0:
        print("\n" + "=" * 50)
        print("Stem separation complete!")

        # List output files
        song_name = Path(input_file).stem
        stems_dir = Path(output_dir) / model / song_name

        if stems_dir.exists():
            print(f"\nOutput files in: {stems_dir}")
            for stem_file in sorted(stems_dir.glob("*.wav")):
                size_mb = stem_file.stat().st_size / (1024 * 1024)
                print(f"  - {stem_file.name} ({size_mb:.1f} MB)")

            print("\n=== What to look for ===")
            print("For harmonica separation, check these stems:")
            print("  1. vocals.wav - Harmonica often ends up here (melodic)")
            print("  2. other.wav  - Or here if not recognized as melodic")
            print("  3. guitar.wav - Occasionally mixed in (similar frequency)")
            print("\nListen to each and see which has the cleanest harmonica!")
    else:
        print(f"\nDemucs failed with return code: {result.returncode}")


def main():
    parser = argparse.ArgumentParser(
        description="Test Demucs stem separation on audio/video files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("input_file", nargs="?", help="Input audio or video file")
    parser.add_argument(
        "--check-gpu", action="store_true", help="Just check GPU availability"
    )
    parser.add_argument(
        "--output",
        "-o",
        default="stems",
        help="Output directory for stems (default: stems/)",
    )
    parser.add_argument(
        "--model",
        "-m",
        default="htdemucs_6s",
        choices=["htdemucs", "htdemucs_6s"],
        help="Demucs model: htdemucs (4 stems) or htdemucs_6s (6 stems, default)",
    )

    args = parser.parse_args()

    # Just check GPU
    if args.check_gpu:
        if not check_dependencies():
            sys.exit(1)
        check_gpu()
        sys.exit(0)

    # Need input file
    if not args.input_file:
        parser.print_help()
        print("\nError: Please provide an input file")
        sys.exit(1)

    # Check dependencies
    if not check_dependencies():
        sys.exit(1)

    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: File not found: {args.input_file}")
        sys.exit(1)

    # If video file, extract audio first
    video_extensions = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".webm"}
    if input_path.suffix.lower() in video_extensions:
        temp_wav = f"temp/{input_path.stem}_extracted.wav"
        os.makedirs("temp", exist_ok=True)

        if not extract_audio(str(input_path), temp_wav):
            sys.exit(1)

        input_file = temp_wav
    else:
        input_file = str(input_path)

    # Run Demucs
    run_demucs(input_file, args.output, args.model)


if __name__ == "__main__":
    main()
