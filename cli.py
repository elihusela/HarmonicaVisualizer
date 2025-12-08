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

from utils.utils import VIDEO_FILES_DIR, OUTPUTS_DIR, TAB_FILES_DIR, MIDI_DIR

# Configuration constants
DEFAULT_HARMONICA_MODEL = "G.png"
MIDI_SUFFIX = "_fixed.mid"


def setup_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate animated harmonica tablature videos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Phase 1: Generate MIDI from video or audio
  python cli.py generate-midi song.mp4
  python cli.py generate-midi song.wav

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
    midi_parser.add_argument(
        "video",
        help="Input video or audio file (in video-files/ or current directory for .wav files)",
    )
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
        "--key",
        type=str,
        default="C",
        help="Harmonica key (C, G, BB, etc.). Default: C",
    )
    video_parser.add_argument(
        "--harmonica-model",
        default=DEFAULT_HARMONICA_MODEL,
        help="Harmonica image (default: auto-selected based on --key)",
    )
    video_parser.add_argument(
        "--no-produce-tabs", action="store_true", help="Skip tab phrase generation"
    )
    video_parser.add_argument(
        "--only-tabs",
        action="store_true",
        help="Only create tab phrase animations (skip harmonica)",
    )
    video_parser.add_argument(
        "--only-harmonica",
        action="store_true",
        help="Only create harmonica animation (skip tabs)",
    )
    video_parser.add_argument(
        "--no-full-tab-video",
        action="store_true",
        help="Skip full tab video generation (only create individual page videos)",
    )
    video_parser.add_argument(
        "--only-full-tab-video",
        action="store_true",
        help="Only create full tab video (skip individual page videos)",
    )
    video_parser.add_argument(
        "--tab-page-buffer",
        type=float,
        default=0.5,
        help="Buffer time (seconds) before/after notes on each tab page. "
        "Increase if pages overlap or vanish early. Default: 0.5",
    )

    # Full pipeline (for testing)
    full_parser = subparsers.add_parser(
        "full", help="Run complete pipeline without MIDI editing"
    )
    full_parser.add_argument("video", help="Input video file (in video-files/)")
    full_parser.add_argument("tabs", help="Tab file (in tab-files/)")
    full_parser.add_argument(
        "--key",
        type=str,
        default="C",
        help="Harmonica key (C, G, BB, etc.). Default: C",
    )
    full_parser.add_argument(
        "--harmonica-model",
        default=DEFAULT_HARMONICA_MODEL,
        help="Harmonica image (default: auto-selected based on --key)",
    )
    full_parser.add_argument(
        "--no-produce-tabs", action="store_true", help="Skip tab phrase generation"
    )
    full_parser.add_argument(
        "--only-tabs",
        action="store_true",
        help="Only create tab phrase animations (skip harmonica)",
    )
    full_parser.add_argument(
        "--only-harmonica",
        action="store_true",
        help="Only create harmonica animation (skip tabs)",
    )
    full_parser.add_argument(
        "--no-full-tab-video",
        action="store_true",
        help="Skip full tab video generation (only create individual page videos)",
    )
    full_parser.add_argument(
        "--only-full-tab-video",
        action="store_true",
        help="Only create full tab video (skip individual page videos)",
    )
    full_parser.add_argument(
        "--tab-page-buffer",
        type=float,
        default=0.5,
        help="Buffer time (seconds) before/after notes on each tab page. "
        "Increase if pages overlap or vanish early. Default: 0.5",
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

    # For WAV files, check current directory first, then video-files directory
    if video.endswith(".wav"):
        if os.path.exists(video):
            video_path = video
        else:
            video_path = os.path.join(VIDEO_FILES_DIR, video)
    else:
        video_path = os.path.join(VIDEO_FILES_DIR, video)

    file_type = "Audio file" if video.endswith(".wav") else "Video"
    validate_file_exists(video_path, file_type)

    base_name = output_name or get_video_base_name(video)
    # Save directly to fixed_midis directory for in-place editing
    output_midi_path = os.path.join(MIDI_DIR, f"{base_name}_fixed.mid")

    print("🎬 Starting Phase 1: MIDI Generation")
    emoji = "🎵" if video.endswith(".wav") else "📹"
    print(f"{emoji} Input: {video_path}")
    print(f"🎼 Output MIDI: {output_midi_path}")

    generator = MidiGenerator(video_path, output_midi_path)
    generator.generate()

    print("✅ Phase 1 Complete!")
    print(f"🎼 Generated MIDI saved to: {output_midi_path}")
    print()
    print("📝 Next steps:")
    print(f"   1. Open {output_midi_path} in your DAW to edit")
    print("   2. Save the fixed MIDI in the same location (overwrites original)")
    if video.lower().endswith((".mov", ".mp4", ".avi")):
        wav_name = f"{base_name}.wav"
        print(f"   3. Run Phase 2: python cli.py create-video {wav_name} <tabs.txt>")
    else:
        print(f"   3. Run Phase 2: python cli.py create-video {video} <tabs.txt>")

    return output_midi_path


def create_video_phase(
    video: str,
    tabs: str,
    harmonica_key: str = "C",
    harmonica_model: str = DEFAULT_HARMONICA_MODEL,
    produce_tabs: bool = True,
    only_tabs: bool = False,
    only_harmonica: bool = False,
    no_full_tab_video: bool = False,
    only_full_tab_video: bool = False,
    tab_page_buffer: float = 0.5,
) -> None:
    """Phase 2: Create video from fixed MIDI."""
    from harmonica_pipeline.video_creator import VideoCreator
    from harmonica_pipeline.video_creator_config import VideoCreatorConfig

    # Handle conflicting options
    if only_tabs and only_harmonica:
        print("❌ Error: Cannot specify both --only-tabs and --only-harmonica")
        sys.exit(1)

    if no_full_tab_video and only_full_tab_video:
        print(
            "❌ Error: Cannot specify both --no-full-tab-video and --only-full-tab-video"
        )
        sys.exit(1)

    # Determine what to create based on options
    # If only_full_tab_video, skip harmonica and only create tabs (for stitching)
    if only_full_tab_video:
        create_harmonica = False
        create_tabs = True
    else:
        create_harmonica = not only_tabs  # Create harmonica unless only tabs requested
        create_tabs = (
            produce_tabs and not only_harmonica
        )  # Create tabs unless only harmonica requested

    # Determine full tab video behavior
    # Note: If only_full_tab_video is set, we still need to generate individual pages first
    # as the compositor stitches them together
    produce_full_tab_video = not no_full_tab_video

    # Generate smart defaults
    base_name = get_video_base_name(video)
    midi_name = f"{base_name}{MIDI_SUFFIX}"
    output_video = f"{base_name}_harmonica.mov"
    tabs_output_video = f"{base_name}_tabs.mov" if create_tabs else None

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
    print(f"🎹 Key: {harmonica_key}")
    print(f"🎭 Model: {harmonica_path}")
    print(f"🎥 Output: {output_video_path}")
    if create_tabs and tabs_output_path:
        print(f"📄 Tabs output: {tabs_output_path}")
        if produce_full_tab_video:
            full_tab_path = tabs_output_path.replace("_tabs.mov", "_full_tabs.mov")
            print(f"🎬 Full tabs: {full_tab_path}")

    # Create configuration object
    config = VideoCreatorConfig(
        video_path=video_path,
        tabs_path=tabs_path,
        harmonica_path=harmonica_path,
        midi_path=midi_path,
        output_video_path=output_video_path,
        tabs_output_path=tabs_output_path,
        produce_tabs=create_tabs,
        produce_full_tab_video=produce_full_tab_video,
        only_full_tab_video=only_full_tab_video,
        harmonica_key=harmonica_key,
        tab_page_buffer=tab_page_buffer,
    )

    creator = VideoCreator(config)
    creator.create(create_harmonica=create_harmonica, create_tabs=create_tabs)

    print("✅ Phase 2 Complete!")
    print(f"🎥 Video saved to: {output_video_path}")
    if only_full_tab_video and create_tabs and tabs_output_path:
        full_tab_path = tabs_output_path.replace("_tabs.mov", "_full_tabs.mov")
        print(f"📄 Full tab video saved to: {full_tab_path}")


def full_pipeline(
    video: str,
    tabs: str,
    harmonica_key: str = "C",
    harmonica_model: str = DEFAULT_HARMONICA_MODEL,
    produce_tabs: bool = True,
    only_tabs: bool = False,
    only_harmonica: bool = False,
    no_full_tab_video: bool = False,
    only_full_tab_video: bool = False,
    tab_page_buffer: float = 0.5,
) -> None:
    """Run complete pipeline for testing (no manual MIDI editing)."""
    print("🎬 Starting Full Pipeline (Testing Mode)")

    # Phase 1: Generate MIDI (already saves to fixed_midis directory)
    base_name = get_video_base_name(video)
    generated_midi_path = generate_midi_phase(video, base_name)

    print("⚠️  Continuing with unedited MIDI (testing mode)")
    print(f"📋 MIDI ready at: {generated_midi_path}")

    # Phase 2: Create video (MIDI is already in the right location)
    create_video_phase(
        video,
        tabs,
        harmonica_key,
        harmonica_model,
        produce_tabs,
        only_tabs,
        only_harmonica,
        no_full_tab_video,
        only_full_tab_video,
        tab_page_buffer,
    )


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
                args.video,
                args.tabs,
                args.key,
                args.harmonica_model,
                not args.no_produce_tabs,
                args.only_tabs,
                args.only_harmonica,
                args.no_full_tab_video,
                args.only_full_tab_video,
                args.tab_page_buffer,
            )

        elif args.command == "full":
            full_pipeline(
                args.video,
                args.tabs,
                args.key,
                args.harmonica_model,
                not args.no_produce_tabs,
                args.only_tabs,
                args.only_harmonica,
                args.no_full_tab_video,
                args.only_full_tab_video,
                args.tab_page_buffer,
            )

    except KeyboardInterrupt:
        print("\n❌ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
