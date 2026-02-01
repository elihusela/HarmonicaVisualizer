#!/usr/bin/env python3
"""
HarmonicaTabs CLI - Two-phase pipeline for harmonica video generation.

Phase 1: Generate MIDI from video
Phase 2: Create harmonica video from fixed MIDI
"""

# Suppress third-party library warnings BEFORE importing them
# This must come before any library imports to catch import-time warnings
import warnings
import logging
import os

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Suppress TensorFlow/basic_pitch warnings
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # Suppress TF logging

# Suppress specific noisy loggers
for logger_name in ["tensorflow", "absl", "numba", "moviepy", "imageio"]:
    logging.getLogger(logger_name).setLevel(logging.ERROR)

import argparse  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Optional  # noqa: E402

from utils.utils import (  # noqa: E402
    VIDEO_FILES_DIR,
    OUTPUTS_DIR,
    TAB_FILES_DIR,
    MIDI_DIR,
)

# Configuration constants
DEFAULT_HARMONICA_MODEL = "G.png"
MIDI_SUFFIX = "_fixed.mid"


def setup_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate animated harmonica tablature videos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive workflow (recommended) - select file from menu
  python cli.py interactive

  # Interactive workflow - specify file directly
  python cli.py interactive MySong_KeyG_Stem.mp4

  # Interactive workflow - explicit tab file
  python cli.py interactive MySong_KeyG_Stem.mp4 CustomTabs.txt

  # Stem separation - isolate harmonica from background
  python cli.py split-stems MySong.mp4
  python cli.py split-stems MySong.mp4 --output-dir my_stems

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

    # MIDI Validation
    validate_parser = subparsers.add_parser(
        "validate-midi",
        help="Validate MIDI file against tab file before video generation",
    )
    validate_parser.add_argument(
        "midi", help="MIDI file (in fixed_midis/ or absolute path)"
    )
    validate_parser.add_argument("tabs", help="Tab file (in tab-files/)")
    validate_parser.add_argument(
        "--key",
        type=str,
        default="C",
        help="Harmonica key (C, G, BB, etc.). Default: C",
    )

    # Tab generation from MIDI
    tabs_parser = subparsers.add_parser(
        "generate-tabs",
        help="Generate .txt tab file from MIDI (starting point for manual editing)",
    )
    tabs_parser.add_argument(
        "midi", help="MIDI file (in fixed_midis/ or absolute path)"
    )
    tabs_parser.add_argument(
        "--key",
        type=str,
        default="C",
        help="Harmonica key (C, G, BB, etc.). Default: C",
    )
    tabs_parser.add_argument(
        "--output",
        type=str,
        help="Output tab file name. Default: <midi_name>.txt in tab-files/",
    )
    tabs_parser.add_argument(
        "--notes-per-line",
        type=int,
        default=6,
        help="Maximum notes/chords per line. Default: 6",
    )
    tabs_parser.add_argument(
        "--notes-per-page",
        type=int,
        default=24,
        help="Maximum notes/chords per page. Default: 24",
    )

    # Stem separation
    stem_parser = subparsers.add_parser(
        "split-stems",
        help="Separate audio into stems using Demucs AI (harmonica ends up in 'other')",
    )
    stem_parser.add_argument(
        "input", help="Input video or audio file (in video-files/ or current directory)"
    )
    stem_parser.add_argument(
        "--output-dir",
        default="stems",
        help="Output directory for separated stems. Default: stems/",
    )
    stem_parser.add_argument(
        "--stem",
        default="other",
        choices=["vocals", "drums", "bass", "guitar", "piano", "other"],
        help="Which stem to highlight/return path for. Default: other (where harmonica typically ends up)",
    )

    # Interactive workflow
    interactive_parser = subparsers.add_parser(
        "interactive",
        help="Run interactive workflow with approval gates and state persistence",
    )
    interactive_parser.add_argument(
        "video",
        nargs="?",
        help="Input video/audio file (optional - will prompt for selection if not provided)",
    )
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
    interactive_parser.add_argument(
        "--clean",
        action="store_true",
        help="Delete existing session and start fresh",
    )
    interactive_parser.add_argument(
        "--skip-to",
        choices=["midi-fixing", "harmonica", "tabs", "finalize"],
        help=(
            "Skip directly to a specific stage. Useful when you already have "
            "MIDI/videos ready. Choices: "
            "midi-fixing (have MIDI, need to fix/validate), "
            "harmonica (regenerate harmonica video), "
            "tabs (regenerate tab video only), "
            "finalize (just create ZIP/archive)"
        ),
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


def validate_midi_phase(midi: str, tabs: str, harmonica_key: str = "C") -> None:
    """Validate MIDI file against tab file."""
    from utils.midi_validator import validate_midi

    # Resolve file paths
    if os.path.isabs(midi):
        midi_path = midi
    elif midi.startswith("fixed_midis/"):
        midi_path = midi
    else:
        midi_path = os.path.join(MIDI_DIR, midi)

    tabs_path = os.path.join(TAB_FILES_DIR, tabs)

    # Validate files exist
    validate_file_exists(midi_path, "MIDI")
    validate_file_exists(tabs_path, "Tabs")

    print("🔍 Starting MIDI Validation")
    print(f"🎼 MIDI: {midi_path}")
    print(f"📄 Tabs: {tabs_path}")
    print(f"🎹 Key: {harmonica_key}")
    print()

    # Run validation
    try:
        result = validate_midi(midi_path, tabs_path, harmonica_key)
        print(result.get_summary())
        print()

        # Exit with appropriate code
        if result.passed:
            print("✅ Validation successful! Ready for video generation.")
            sys.exit(0)
        else:
            print(
                "❌ Validation failed. Fix the issues above before running create-video."
            )
            sys.exit(1)

    except Exception as e:
        print(f"❌ Validation error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


def generate_tabs_phase(
    midi: str,
    harmonica_key: str = "C",
    output: Optional[str] = None,
    notes_per_line: int = 6,
    notes_per_page: int = 24,
) -> str:
    """Generate .txt tab file from MIDI.

    Args:
        midi: MIDI file path
        harmonica_key: Harmonica key (C, G, Bb, etc.)
        output: Output tab file name (optional)
        notes_per_line: Max notes per line
        notes_per_page: Max notes per page

    Returns:
        Path to the generated tab file
    """
    from harmonica_pipeline.harmonica_key_registry import get_harmonica_config
    from harmonica_pipeline.midi_processor import MidiProcessor
    from tab_converter.tab_generator import TabGenerator, TabGeneratorConfig
    from tab_converter.tab_mapper import TabMapper

    # Resolve MIDI path
    if os.path.isabs(midi):
        midi_path = midi
    elif midi.startswith("fixed_midis/"):
        midi_path = midi
    else:
        midi_path = os.path.join(MIDI_DIR, midi)

    validate_file_exists(midi_path, "MIDI")

    # Determine output path
    if output:
        if os.path.isabs(output):
            output_path = output
        else:
            output_path = os.path.join(TAB_FILES_DIR, output)
    else:
        # Default: same name as MIDI, in tab-files/
        base_name = get_video_base_name(midi_path)
        # Remove _fixed suffix if present
        if base_name.endswith("_fixed"):
            base_name = base_name[:-6]
        output_path = os.path.join(TAB_FILES_DIR, f"{base_name}.txt")

    print("📝 Starting Tab Generation")
    print(f"🎼 MIDI: {midi_path}")
    print(f"🎹 Key: {harmonica_key}")
    print(f"📄 Output: {output_path}")
    print(f"📊 Format: {notes_per_line} notes/line, {notes_per_page} notes/page")
    print()

    # Get harmonica mapping for the key
    key_config = get_harmonica_config(harmonica_key)
    mapping = key_config.midi_mapping

    # Load MIDI and convert to note events
    processor = MidiProcessor(midi_path)
    note_events = processor.load_note_events()

    # Convert to tabs
    mapper = TabMapper(mapping, "temp")
    tabs = mapper.note_events_to_tabs(note_events)

    # Generate tab file
    config = TabGeneratorConfig(
        notes_per_line=notes_per_line,
        notes_per_page=notes_per_page,
    )
    generator = TabGenerator(config)
    content = generator.generate(tabs)

    # Write to file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write(content)

    print()
    print("✅ Tab generation complete!")
    print(f"📄 Generated: {output_path}")
    print()
    print("📝 Next steps:")
    print(f"   1. Open {output_path} and review/edit the tabs")
    tab_name = os.path.basename(output_path)
    print(
        f"   2. Run validation: python cli.py validate-midi {midi} {tab_name} --key {harmonica_key}"
    )

    return output_path


def split_stems_phase(
    input_file: str,
    output_dir: str = "stems",
    stem: str = "other",
) -> str:
    """Separate audio into stems using Demucs AI.

    Args:
        input_file: Input video or audio file
        output_dir: Directory for separated stems
        stem: Which stem to highlight (default: 'other' for harmonica)

    Returns:
        Path to the specified stem file
    """
    from utils.stem_separator import StemSeparator, StemSeparatorError

    # Resolve file path
    if os.path.exists(input_file):
        input_path = input_file
    else:
        input_path = os.path.join(VIDEO_FILES_DIR, input_file)

    validate_file_exists(input_path, "Input file")

    print("🎵 Starting Stem Separation")
    print(f"📹 Input: {input_path}")
    print(f"📂 Output: {output_dir}/")
    print(f"🎯 Target stem: {stem}")
    print()

    try:
        separator = StemSeparator(output_dir=output_dir)

        # Check device
        device = separator._detect_device()
        device_emoji = {"cuda": "🚀 GPU (CUDA)", "mps": "🍎 GPU (MPS)", "cpu": "🐢 CPU"}
        print(f"🖥️  Device: {device_emoji.get(device, device)}")
        print()

        print("⏳ Running Demucs 6-stem separation (this may take a while)...")
        stem_path = separator.separate(input_path, stem=stem)

        print()
        print("✅ Stem separation complete!")
        print()
        print("📂 Generated stems:")
        # List all stems in output directory
        from pathlib import Path

        stem_dir = Path(stem_path).parent
        for stem_file in sorted(stem_dir.glob("*.mp3")):
            marker = "👉" if stem_file.stem == stem else "  "
            print(f"   {marker} {stem_file}")

        print()
        print(f"🎯 Recommended stem for harmonica: {stem_path}")
        print()
        print("📝 Next steps:")
        print(f"   1. Listen to {stem_path} to verify harmonica isolation")
        print(f"   2. Generate MIDI: python cli.py generate-midi {stem_path}")

        return stem_path

    except StemSeparatorError as e:
        print(f"❌ Stem separation failed: {e}")
        sys.exit(1)


def _select_video_file() -> Optional[str]:
    """Prompt user to select a video/audio file from video-files/ directory.

    Returns:
        Selected filename or None if cancelled
    """
    import questionary

    # Get list of video/audio files
    video_extensions = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".webm", ".wav", ".mp3"}
    files = []

    if os.path.exists(VIDEO_FILES_DIR):
        for f in os.listdir(VIDEO_FILES_DIR):
            if any(f.lower().endswith(ext) for ext in video_extensions):
                files.append(f)

    if not files:
        print(f"❌ No video/audio files found in {VIDEO_FILES_DIR}/")
        print("   Supported formats: .mp4, .mov, .avi, .mkv, .m4v, .webm, .wav, .mp3")
        return None

    # Sort files alphabetically
    files.sort()

    print("🎵 Select a video/audio file to process:")
    print()

    # Use questionary to select a file
    selected = questionary.select(
        "Choose file:",
        choices=files + ["[Cancel]"],
    ).ask()

    if selected == "[Cancel]" or selected is None:
        return None

    return selected


def interactive_workflow(
    video: Optional[str] = None,
    tabs: Optional[str] = None,
    session_dir: str = "sessions",
    auto_approve: bool = False,
    clean: bool = False,
    skip_to: Optional[str] = None,
) -> None:
    """Run interactive workflow with approval gates and session persistence.

    This workflow:
    - Parses configuration from filename
    - Saves/resumes session state
    - Pauses at each step for user approval
    - Handles MIDI fixing iteration
    - Supports crash recovery

    Args:
        video: Input video/audio file (filename encodes configuration).
               If not provided, prompts for file selection from video-files/
        tabs: Tab file (.txt) - optional, defaults to same name as video
        session_dir: Directory for session files
        auto_approve: Skip all approval prompts (for testing)
        clean: Delete existing session and start fresh
        skip_to: Skip directly to a specific stage (midi-fixing, harmonica, tabs, finalize)
    """
    from interactive_workflow.orchestrator import WorkflowOrchestrator
    from utils.filename_parser import parse_filename

    # If no video provided, prompt for file selection
    if video is None:
        video = _select_video_file()
        if video is None:
            print("❌ No file selected. Exiting.")
            sys.exit(0)

    # Parse filename to get song name (needed for session file path)
    filename_config = parse_filename(video)

    # Handle --clean flag: delete existing session
    if clean:
        session_file = os.path.join(
            session_dir, f"{filename_config.song_name}_session.json"
        )
        if os.path.exists(session_file):
            os.remove(session_file)
            print(f"🧹 Cleaned existing session: {session_file}")
        else:
            print(f"🧹 No existing session to clean for {filename_config.song_name}")

    # Resolve file paths
    # For WAV files, check current directory first
    if video.endswith(".wav") and os.path.exists(video):
        video_path = video
    else:
        video_path = os.path.join(VIDEO_FILES_DIR, video)

    # Auto-infer tab file from video name if not provided
    if tabs is None:
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
    if skip_to:
        print(f"⏭️  Skipping to: {skip_to}")
    print()

    # Create and run orchestrator
    orchestrator = WorkflowOrchestrator(
        input_video=video_path,
        input_tabs=tabs_path,
        session_dir=session_dir,
        auto_approve=auto_approve,
        skip_to=skip_to,
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

        elif args.command == "validate-midi":
            validate_midi_phase(args.midi, args.tabs, args.key)

        elif args.command == "generate-tabs":
            generate_tabs_phase(
                args.midi,
                args.key,
                args.output,
                args.notes_per_line,
                args.notes_per_page,
            )

        elif args.command == "split-stems":
            split_stems_phase(args.input, args.output_dir, args.stem)

        elif args.command == "interactive":
            # tabs is optional, will be None if not provided
            interactive_workflow(
                args.video,
                args.tabs,
                args.session_dir,
                args.auto_approve,
                args.clean,
                args.skip_to,
            )

    except KeyboardInterrupt:
        print("\n❌ Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
