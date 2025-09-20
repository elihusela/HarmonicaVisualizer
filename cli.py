#!/usr/bin/env python3
"""
HarmonicaTabs CLI - Two-phase pipeline for harmonica video generation.

Phase 1: Generate MIDI from video
Phase 2: Create harmonica video from fixed MIDI
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Optional

from utils.utils import TEMP_DIR, VIDEO_FILES_DIR, OUTPUTS_DIR, TAB_FILES_DIR, MIDI_DIR

# Configuration constants
DEFAULT_HARMONICA_MODEL = "CNewModel.png"
MIDI_SUFFIX = "_fixed.mid"


def setup_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate animated harmonica tablature videos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Phase 1: Generate MIDI from video
  python cli.py generate-midi song.mp4

  # Phase 2: Create video from fixed MIDI
  python cli.py create-video song.mp4 song_tabs.txt

  # Full pipeline (for testing)
  python cli.py full song.mp4 song_tabs.txt
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Pipeline phase to run")

    # Phase 1: Generate MIDI
    midi_parser = subparsers.add_parser(
        "generate-midi", help="Extract audio and generate MIDI file"
    )
    midi_parser.add_argument("video", help="Input video file (in video-files/)")
    midi_parser.add_argument(
        "--output-name", help="Custom name for generated MIDI (default: video name)"
    )

    # Phase 2: Create video
    video_parser = subparsers.add_parser(
        "create-video", help="Create harmonica video from fixed MIDI"
    )
    video_parser.add_argument("video", help="Input video file (in video-files/)")
    video_parser.add_argument("tabs", help="Tab file (in tab-files/)")
    video_parser.add_argument(
        "--harmonica-model",
        default=DEFAULT_HARMONICA_MODEL,
        help=f"Harmonica image (default: {DEFAULT_HARMONICA_MODEL})",
    )
    video_parser.add_argument(
        "--no-produce-tabs", action="store_true", help="Skip tab phrase generation"
    )

    # Full pipeline (for testing)
    full_parser = subparsers.add_parser(
        "full", help="Run complete pipeline without MIDI editing"
    )
    full_parser.add_argument("video", help="Input video file (in video-files/)")
    full_parser.add_argument("tabs", help="Tab file (in tab-files/)")
    full_parser.add_argument(
        "--harmonica-model",
        default=DEFAULT_HARMONICA_MODEL,
        help=f"Harmonica image (default: {DEFAULT_HARMONICA_MODEL})",
    )
    full_parser.add_argument(
        "--no-produce-tabs", action="store_true", help="Skip tab phrase generation"
    )

    return parser


def validate_file_exists(file_path: str, file_type: str) -> None:
    """Validate that a file exists, with helpful error message."""
    if not os.path.exists(file_path):
        print(f"❌ Error: {file_type} file not found: {file_path}")
        sys.exit(1)


def get_video_base_name(video_file: str) -> str:
    """Get base name from video file for naming other files."""
    return Path(video_file).stem


def generate_midi_phase(video: str, output_name: Optional[str] = None) -> str:
    """Phase 1: Generate MIDI from video audio."""
    from harmonica_pipeline.midi_generator import MidiGenerator

    video_path = os.path.join(VIDEO_FILES_DIR, video)
    validate_file_exists(video_path, "Video")

    base_name = output_name or get_video_base_name(video)
    output_midi_path = os.path.join(TEMP_DIR, f"{base_name}_generated.mid")

    print("🎬 Starting Phase 1: MIDI Generation")
    print(f"📹 Video: {video_path}")
    print(f"🎼 Output MIDI: {output_midi_path}")

    generator = MidiGenerator(video_path, output_midi_path)
    generator.generate()

    print("✅ Phase 1 Complete!")
    print(f"🎼 Generated MIDI saved to: {output_midi_path}")
    print()
    print("📝 Next steps:")
    print(f"   1. Open {output_midi_path} in your DAW (Ableton, etc.)")
    print(f"   2. Fix the MIDI and save to: fixed_midis/{base_name}_fixed.mid")
    print(f"   3. Run Phase 2: python cli.py create-video {video} <tabs.txt>")

    return output_midi_path


def create_video_phase(
    video: str,
    tabs: str,
    harmonica_model: str = DEFAULT_HARMONICA_MODEL,
    produce_tabs: bool = True,
) -> None:
    """Phase 2: Create video from fixed MIDI."""
    from harmonica_pipeline.video_creator import VideoCreator

    # Generate smart defaults
    base_name = get_video_base_name(video)
    midi_name = f"{base_name}{MIDI_SUFFIX}"
    output_video = f"{base_name}_harmonica.mov"
    tabs_output_video = f"{base_name}_tabs.mov" if produce_tabs else None

    # Validate all input files exist
    video_path = os.path.join(VIDEO_FILES_DIR, video)
    validate_file_exists(video_path, "Video")

    tabs_path = os.path.join(TAB_FILES_DIR, tabs)
    validate_file_exists(tabs_path, "Tabs")

    harmonica_path = os.path.join("harmonica-models", harmonica_model)
    validate_file_exists(harmonica_path, "Harmonica model")

    midi_path = os.path.join(MIDI_DIR, midi_name)
    validate_file_exists(midi_path, "MIDI")

    output_video_path = os.path.join(OUTPUTS_DIR, output_video)
    tabs_output_path = (
        os.path.join(OUTPUTS_DIR, tabs_output_video) if tabs_output_video else None
    )

    print("🎬 Starting Phase 2: Video Creation")
    print(f"📹 Video: {video_path}")
    print(f"🎼 MIDI: {midi_path}")
    print(f"📄 Tabs: {tabs_path}")
    print(f"🎭 Model: {harmonica_path}")
    print(f"🎥 Output: {output_video_path}")

    creator = VideoCreator(
        video_path=video_path,
        tabs_path=tabs_path,
        harmonica_path=harmonica_path,
        midi_path=midi_path,
        output_video_path=output_video_path,
        tabs_output_path=tabs_output_path,
        produce_tabs=produce_tabs,
    )
    creator.create()

    print("✅ Phase 2 Complete!")
    print(f"🎥 Video saved to: {output_video_path}")


def full_pipeline(
    video: str,
    tabs: str,
    harmonica_model: str = DEFAULT_HARMONICA_MODEL,
    produce_tabs: bool = True,
) -> None:
    """Run complete pipeline for testing (no manual MIDI editing)."""
    print("🎬 Starting Full Pipeline (Testing Mode)")

    # Phase 1: Generate MIDI
    base_name = get_video_base_name(video)
    generated_midi_path = generate_midi_phase(video, base_name)

    print("⚠️  Continuing with unedited MIDI (testing mode)")

    # Copy generated MIDI to fixed_midis for Phase 2
    import shutil

    fixed_midi_name = f"{base_name}{MIDI_SUFFIX}"
    fixed_midi_path = os.path.join(MIDI_DIR, fixed_midi_name)
    shutil.copy2(generated_midi_path, fixed_midi_path)
    print(f"📋 Copied unedited MIDI to: {fixed_midi_path}")

    # Phase 2: Create video
    create_video_phase(video, tabs, harmonica_model, produce_tabs)


def main():
    parser = setup_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "generate-midi":
            generate_midi_phase(args.video, args.output_name)

        elif args.command == "create-video":
            create_video_phase(
                args.video, args.tabs, args.harmonica_model, not args.no_produce_tabs
            )

        elif args.command == "full":
            full_pipeline(
                args.video, args.tabs, args.harmonica_model, not args.no_produce_tabs
            )

    except KeyboardInterrupt:
        print("\n❌ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
