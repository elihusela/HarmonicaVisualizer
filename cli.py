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
  # Interactive workflow (recommended) - tab file auto-inferred
  python cli.py interactive MySong_KeyG_Stem.mp4

  # Interactive workflow - explicit tab file
  python cli.py interactive MySong_KeyG_Stem.mp4 CustomTabs.txt

  # Phase 1: Generate MIDI from video or audio
  python cli.py generate-midi song.mp4
  python cli.py generate-midi song.wav

  # Phase 1: Generate MIDI with custom parameters (quiet/muddy audio with chords)
  python cli.py generate-midi song.wav --preset harmonica_strict --no-melodia-trick
  python cli.py generate-midi song.wav --preset harmonica_strict \\
      --onset-threshold 0.25 --frame-threshold 0.18 --no-melodia-trick
  python cli.py generate-midi song.wav --target-loudness -10 \\
      --noise-reduction -35 --low-freq 250 --high-freq 3000 \\
      --onset-threshold 0.25 --frame-threshold 0.2 --no-melodia-trick

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

    # Audio Processing Parameters
    audio_group = midi_parser.add_argument_group("Audio Processing")
    audio_group.add_argument(
        "--preset",
        choices=[
            "harmonica_default",
            "harmonica_strict",
            "general_melody",
            "clean_studio",
        ],
        help="Audio processing preset (overrides individual audio settings)",
    )
    audio_group.add_argument(
        "--low-freq",
        type=int,
        default=200,
        help="High-pass filter frequency in Hz (default: 200)",
    )
    audio_group.add_argument(
        "--high-freq",
        type=int,
        default=5000,
        help="Low-pass filter frequency in Hz (default: 5000)",
    )
    audio_group.add_argument(
        "--noise-reduction",
        type=int,
        default=-25,
        help="Noise reduction strength in dB (default: -25)",
    )
    audio_group.add_argument(
        "--target-loudness",
        type=int,
        default=-16,
        help="Target loudness in LUFS (default: -16). Lower = louder (e.g., -12)",
    )

    # basic_pitch MIDI Generation Parameters
    midi_group = midi_parser.add_argument_group("MIDI Generation (basic_pitch)")
    midi_group.add_argument(
        "--onset-threshold",
        type=float,
        default=0.4,
        help="Onset detection sensitivity (default: 0.4). Lower = detect quieter notes (try 0.3 for chords)",
    )
    midi_group.add_argument(
        "--frame-threshold",
        type=float,
        default=0.3,
        help="Frame detection sensitivity (default: 0.3). Lower = detect quieter notes (try 0.2 for chords)",
    )
    midi_group.add_argument(
        "--minimum-note-length",
        type=float,
        default=127.7,
        help="Minimum note duration in ms (default: 127.7)",
    )
    midi_group.add_argument(
        "--minimum-frequency",
        type=float,
        help="Minimum frequency in Hz (default: None). Harmonica: ~200Hz",
    )
    midi_group.add_argument(
        "--maximum-frequency",
        type=float,
        help="Maximum frequency in Hz (default: None). Harmonica: ~3000Hz",
    )
    midi_group.add_argument(
        "--no-melodia-trick",
        action="store_true",
        help="Disable melodia trick (enables better chord detection but may add noise)",
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
        default=0.1,
        help="Buffer time (seconds) before/after notes on each tab page. "
        "Increase if pages overlap or vanish early. Default: 0.1",
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
        default=0.1,
        help="Buffer time (seconds) before/after notes on each tab page. "
        "Increase if pages overlap or vanish early. Default: 0.1",
    )

    # Interactive workflow
    interactive_parser = subparsers.add_parser(
        "interactive",
        help="Run interactive workflow with approval gates and state persistence",
    )
    interactive_parser.add_argument("video", help="Input video/audio file")
    interactive_parser.add_argument(
        "tabs",
        nargs="?",
        help="Tab file (.txt) - optional, defaults to same name as video",
    )
    interactive_parser.add_argument(
        "--session-dir",
        default="sessions",
        help="Directory for session persistence files. Default: sessions/",
    )
    interactive_parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Skip all approval prompts (for testing/automation)",
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


def generate_midi_phase(
    video: str,
    output_name: Optional[str] = None,
    # Audio processing params
    preset: Optional[str] = None,
    low_freq: int = 200,
    high_freq: int = 5000,
    noise_reduction: int = -25,
    target_loudness: int = -16,
    # basic_pitch params
    onset_threshold: float = 0.4,
    frame_threshold: float = 0.3,
    minimum_note_length: float = 127.7,
    minimum_frequency: Optional[float] = None,
    maximum_frequency: Optional[float] = None,
    no_melodia_trick: bool = False,
) -> str:
    """Phase 1: Generate MIDI from video audio."""
    from harmonica_pipeline.midi_generator import MidiGenerator
    from utils.audio_processor import AudioProcessor

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

    # Apply preset if specified
    audio_params = {}
    if preset:
        presets = AudioProcessor.get_recommended_presets()
        if preset in presets:
            audio_params = presets[preset]
            print(f"🎛️ Using preset: {preset}")
        else:
            print(f"⚠️ Unknown preset '{preset}', using custom parameters")
    else:
        # Use custom parameters
        audio_params = {
            "low_freq": low_freq,
            "high_freq": high_freq,
            "noise_reduction_db": noise_reduction,
            "target_lufs": target_loudness,
        }

    # Print audio processing settings
    print(
        f"🎛️ Audio: {audio_params.get('low_freq', low_freq)}-{audio_params.get('high_freq', high_freq)}Hz, "
        f"Noise: {audio_params.get('noise_reduction_db', noise_reduction)}dB, "
        f"Loudness: {audio_params.get('target_lufs', target_loudness)}LUFS"
    )

    # Print MIDI generation settings
    melodia_status = "OFF" if no_melodia_trick else "ON"
    print(
        f"🎼 MIDI: onset={onset_threshold}, frame={frame_threshold}, "
        f"melodia_trick={melodia_status}"
    )
    if minimum_frequency or maximum_frequency:
        freq_range = f"{minimum_frequency or 'None'}-{maximum_frequency or 'None'}Hz"
        print(f"   Freq range: {freq_range}")

    generator = MidiGenerator(
        video_path,
        output_midi_path,
        audio_processor_params=audio_params,
        onset_threshold=onset_threshold,
        frame_threshold=frame_threshold,
        minimum_note_length=minimum_note_length,
        minimum_frequency=minimum_frequency,
        maximum_frequency=maximum_frequency,
        melodia_trick=not no_melodia_trick,
    )
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
    tab_page_buffer: float = 0.1,
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
    tab_page_buffer: float = 0.1,
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


def interactive_workflow(
    video: str,
    tabs: Optional[str] = None,
    session_dir: str = "sessions",
    auto_approve: bool = False,
) -> None:
    """Run interactive workflow with approval gates and session persistence.

    This workflow:
    - Parses configuration from filename
    - Saves/resumes session state
    - Pauses at each step for user approval
    - Handles MIDI fixing iteration
    - Supports crash recovery

    Args:
        video: Input video/audio file (filename encodes configuration)
        tabs: Tab file (.txt) - optional, defaults to same name as video
        session_dir: Directory for session files
        auto_approve: Skip all approval prompts (for testing)
    """
    from interactive_workflow.orchestrator import WorkflowOrchestrator

    # Resolve file paths
    # For WAV files, check current directory first
    if video.endswith(".wav") and os.path.exists(video):
        video_path = video
    else:
        video_path = os.path.join(VIDEO_FILES_DIR, video)

    # Auto-infer tab file from video name if not provided
    if tabs is None:
        # Extract song name from filename (removes extension and parameters like _KeyG_Stem)
        from utils.filename_parser import parse_filename

        filename_config = parse_filename(video)
        tabs = f"{filename_config.song_name}.txt"

    tabs_path = os.path.join(TAB_FILES_DIR, tabs)

    # Validate inputs exist
    file_type = "Audio file" if video.endswith(".wav") else "Video"
    validate_file_exists(video_path, file_type)
    validate_file_exists(tabs_path, "Tabs")

    print("🎭 Starting Interactive Workflow")
    print(f"📹 Input: {video_path}")
    print(f"📄 Tabs: {tabs_path}")
    print(f"💾 Sessions: {session_dir}/")
    print()

    # Create and run orchestrator
    orchestrator = WorkflowOrchestrator(
        input_video=video_path,
        input_tabs=tabs_path,
        session_dir=session_dir,
        auto_approve=auto_approve,
    )

    orchestrator.run()


def main():
    parser = setup_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "generate-midi":
            generate_midi_phase(
                args.video,
                args.output_name,
                preset=args.preset,
                low_freq=args.low_freq,
                high_freq=args.high_freq,
                noise_reduction=args.noise_reduction,
                target_loudness=args.target_loudness,
                onset_threshold=args.onset_threshold,
                frame_threshold=args.frame_threshold,
                minimum_note_length=args.minimum_note_length,
                minimum_frequency=args.minimum_frequency,
                maximum_frequency=args.maximum_frequency,
                no_melodia_trick=args.no_melodia_trick,
            )

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

        elif args.command == "interactive":
            # tabs is optional, will be None if not provided
            interactive_workflow(
                args.video, args.tabs, args.session_dir, args.auto_approve
            )

    except KeyboardInterrupt:
        print("\n❌ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
