"""Filename-based configuration parser for interactive workflow.

Parses video/audio filenames to extract configuration parameters.

Example filenames:
    - SongName_KeyG_Stem.mp4 → G harmonica, with stem separation
    - PianoMan_KeyC_FPS15.mp4 → C harmonica, 15 FPS
    - MyTune_KeyBb_TabBuffer0.5.wav → Bb harmonica, 0.5s tab buffer
"""

import os
import re
from dataclasses import dataclass


@dataclass
class FilenameConfig:
    """Configuration extracted from filename.

    Attributes:
        song_name: Base name of the song (first part before _)
        key: Harmonica key (A, Ab, B, Bb, C, C#, D, E, Eb, F, F#, G)
        enable_stem: Whether to run stem separation
        fps: Frames per second for video generation
        tab_buffer: Buffer time (seconds) between tab pages
        original_filename: The original filename (with extension)
    """

    song_name: str
    key: str = "C"
    enable_stem: bool = True
    fps: int = 15
    tab_buffer: float = 0.1
    original_filename: str = ""


def parse_filename(filename: str) -> FilenameConfig:
    """Parse configuration from filename.

    Filename format: SongName_Param1_Param2_...ext

    Supported parameters:
        - Key[A-G][b#]? : Harmonica key (required)
          Examples: KeyC, KeyG, KeyBb, KeyF#
        - Stem : Enable stem separation
        - NoStem : Explicitly disable stem separation (default)
        - FPS[0-9]+ : Set FPS (e.g., FPS15, FPS30)
        - TabBuffer[0-9.]+ : Set tab page buffer (e.g., TabBuffer0.5)

    Args:
        filename: Video/audio filename (with or without path)

    Returns:
        FilenameConfig with extracted parameters

    Raises:
        ValueError: If filename format is invalid or key is missing

    Examples:
        >>> parse_filename("MySong_KeyG_Stem.mp4")
        FilenameConfig(song_name='MySong', key='G', enable_stem=True, ...)

        >>> parse_filename("PianoMan_KeyC_FPS30.wav")
        FilenameConfig(song_name='PianoMan', key='C', fps=30, ...)

        >>> parse_filename("/path/to/Tune_KeyBb_TabBuffer0.5.m4v")
        FilenameConfig(song_name='Tune', key='Bb', tab_buffer=0.5, ...)
    """
    # Extract just the filename (no path)
    base_filename = os.path.basename(filename)

    # Remove extension
    name_without_ext = os.path.splitext(base_filename)[0]

    # Check for empty filename (e.g., ".mp4")
    if not name_without_ext:
        raise ValueError(f"Invalid filename format: {filename}")

    # Split by underscore
    parts = name_without_ext.split("_")

    if not parts:
        raise ValueError(f"Invalid filename format: {filename}")

    # First part is always the song name
    song_name = parts[0]

    if not song_name:
        raise ValueError(f"Invalid filename format: {filename}")

    # Initialize config with defaults
    config = FilenameConfig(song_name=song_name, original_filename=base_filename)

    # Track if key was explicitly set
    key_found = False

    # Parse remaining parts
    for part in parts[1:]:
        # Parse harmonica key (supports both # and S for sharps, b and B for flats)
        if match := re.match(r"^Key([A-G][bB#sS]?)$", part, re.IGNORECASE):
            config.key = match.group(1).upper()
            # Normalize key notation (FS -> F#, BB -> Bb, etc.)
            config.key = _normalize_key(config.key)
            key_found = True

        # Parse stem flag
        elif part.lower() == "stem":
            config.enable_stem = True

        elif part.lower() == "nostem":
            config.enable_stem = False

        # Parse FPS
        elif match := re.match(r"^FPS(\d+)$", part, re.IGNORECASE):
            config.fps = int(match.group(1))
            if config.fps <= 0 or config.fps > 60:
                raise ValueError(f"Invalid FPS value: {config.fps}. Must be 1-60.")

        # Parse tab buffer (allow minus sign to catch negative values)
        elif match := re.match(r"^TabBuffer([-\d.]+)$", part, re.IGNORECASE):
            config.tab_buffer = float(match.group(1))
            if config.tab_buffer < 0 or config.tab_buffer > 5.0:
                raise ValueError(
                    f"Invalid TabBuffer value: {config.tab_buffer}. Must be 0-5.0."
                )

        # Unknown parameter - ignore or warn?
        # For now, silently ignore unknown parts

    # Validate: Key is required
    if not key_found:
        raise ValueError(
            f"Harmonica key not found in filename: {filename}. "
            f"Expected format: SongName_Key[A-G][b#]?_..._ext"
        )

    return config


def _normalize_key(key: str) -> str:
    """Normalize key notation for consistency.

    Converts:
        - FS -> F#
        - CS -> C#
        - DS -> D#
        - GS -> G#
        - AS -> A#
        - BB -> Bb
        - EB -> Eb
        - AB -> Ab
        - DB -> Db
        - GB -> Gb

    Args:
        key: Key string (e.g., "FS", "BB", "C")

    Returns:
        Normalized key (e.g., "F#", "Bb", "C")
    """
    key = key.upper()

    # Handle sharp notation: FS -> F#
    sharp_map = {"FS": "F#", "CS": "C#", "DS": "D#", "GS": "G#", "AS": "A#"}
    if key in sharp_map:
        return sharp_map[key]

    # Handle flat notation: BB -> Bb
    flat_map = {"BB": "Bb", "EB": "Eb", "AB": "Ab", "DB": "Db", "GB": "Gb"}
    if key in flat_map:
        return flat_map[key]

    # Already normalized or natural note
    return key
