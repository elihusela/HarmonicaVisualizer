"""
Utilities module for HarmonicaTabs project.

Provides directory management, MIDI processing utilities, and project-wide
constants and helper functions.
"""

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, List

import mido
from mido import MidiFile

from tab_converter.consts import SET_TEMPO_MSG


@dataclass
class DirectoryConfig:
    """Configuration for project directories."""

    temp_dir: str
    video_files_dir: str
    tab_files_dir: str
    outputs_dir: str
    midi_dir: str
    create_if_missing: bool = True

    def __post_init__(self):
        """Ensure all directories exist if create_if_missing is True."""
        if self.create_if_missing:
            directories = [
                self.temp_dir,
                self.video_files_dir,
                self.tab_files_dir,
                self.outputs_dir,
                self.midi_dir,
            ]
            for dir_path in directories:
                os.makedirs(dir_path, exist_ok=True)


class UtilsError(Exception):
    """Custom exception for utilities operations."""

    pass


# Project directory configuration
_project_root = Path(__file__).parent.parent
_default_config = DirectoryConfig(
    temp_dir=str(_project_root / "temp") + "/",
    video_files_dir=str(_project_root / "video-files") + "/",
    tab_files_dir=str(_project_root / "tab-files") + "/",
    outputs_dir=str(_project_root / "outputs") + "/",
    midi_dir=str(_project_root / "fixed_midis") + "/",
)

# Backwards compatibility constants
TEMP_DIR = _default_config.temp_dir
VIDEO_FILES_DIR = _default_config.video_files_dir
TAB_FILES_DIR = _default_config.tab_files_dir
OUTPUTS_DIR = _default_config.outputs_dir
MIDI_DIR = _default_config.midi_dir


def get_directory_config() -> DirectoryConfig:
    """
    Get the current directory configuration.

    Returns:
        DirectoryConfig object with current directory paths
    """
    return _default_config


def get_directory_info() -> dict:
    """
    Get comprehensive directory information and status.

    Returns:
        Dict with directory paths, existence status, and sizes
    """
    config = get_directory_config()
    from typing import Dict, Any

    info: Dict[str, Any] = {"project_root": str(_project_root), "directories": {}}

    for dir_name, dir_path in [
        ("temp", config.temp_dir),
        ("video_files", config.video_files_dir),
        ("tab_files", config.tab_files_dir),
        ("outputs", config.outputs_dir),
        ("midi", config.midi_dir),
    ]:
        dir_info = {
            "path": dir_path,
            "exists": os.path.exists(dir_path),
            "is_directory": (
                os.path.isdir(dir_path) if os.path.exists(dir_path) else False
            ),
            "file_count": 0,
            "total_size_bytes": 0,
        }

        if dir_info["exists"] and dir_info["is_directory"]:
            try:
                files = os.listdir(dir_path)
                dir_info["file_count"] = len(files)
                dir_info["total_size_bytes"] = sum(
                    os.path.getsize(os.path.join(dir_path, f))
                    for f in files
                    if os.path.isfile(os.path.join(dir_path, f))
                )
            except OSError:
                pass  # Ignore permission errors

        info["directories"][dir_name] = dir_info

    return info


def clean_temp_folder(path: Optional[str] = None) -> None:
    """
    Clean and recreate a temporary directory.

    Args:
        path: Directory path to clean (defaults to TEMP_DIR)

    Raises:
        UtilsError: If directory operations fail
    """
    target_path = path or TEMP_DIR

    try:
        if os.path.exists(target_path):
            shutil.rmtree(target_path)

        os.makedirs(target_path, exist_ok=True)
        print(f"🧹 Cleaned and recreated '{target_path}' folder.")

    except (OSError, IOError) as e:
        raise UtilsError(f"Failed to clean temp folder '{target_path}': {e}")


def ensure_directories_exist(directories: Optional[List[str]] = None) -> None:
    """
    Ensure project directories exist, creating them if necessary.

    Args:
        directories: Optional list of directory paths (defaults to all project dirs)

    Raises:
        UtilsError: If directory creation fails
    """
    if directories is None:
        config = get_directory_config()
        directories = [
            config.temp_dir,
            config.video_files_dir,
            config.tab_files_dir,
            config.outputs_dir,
            config.midi_dir,
        ]

    for dir_path in directories:
        try:
            os.makedirs(dir_path, exist_ok=True)
        except OSError as e:
            raise UtilsError(f"Failed to create directory '{dir_path}': {e}")


def get_tempo(mid: MidiFile) -> int:
    """
    Extract tempo from a MIDI file.

    Args:
        mid: MIDI file to analyze

    Returns:
        Tempo in microseconds per beat (defaults to 120 BPM if not found)

    Raises:
        UtilsError: If MIDI file processing fails
    """
    if not isinstance(mid, MidiFile):
        raise UtilsError("Invalid MIDI file object provided")

    try:
        for track in mid.tracks:
            for msg in track:
                if msg.type == SET_TEMPO_MSG:
                    return msg.tempo

        # Default to 120 BPM if no tempo found
        return mido.bpm2tempo(120)

    except Exception as e:
        raise UtilsError(f"Failed to extract tempo from MIDI file: {e}")


def get_midi_info(midi_path: str) -> dict:
    """
    Get comprehensive information about a MIDI file.

    Args:
        midi_path: Path to the MIDI file

    Returns:
        Dict with MIDI file information

    Raises:
        UtilsError: If MIDI file cannot be read or analyzed
    """
    if not os.path.exists(midi_path):
        raise UtilsError(f"MIDI file not found: {midi_path}")

    try:
        mid = MidiFile(midi_path)

        # Count note events
        note_events = 0
        for track in mid.tracks:
            for msg in track:
                if msg.type in ["note_on", "note_off"]:
                    note_events += 1

        return {
            "file_path": midi_path,
            "file_size_bytes": os.path.getsize(midi_path),
            "format_type": mid.type,
            "tracks_count": len(mid.tracks),
            "ticks_per_beat": mid.ticks_per_beat,
            "length_seconds": mid.length,
            "tempo_bpm": mido.tempo2bpm(get_tempo(mid)),
            "note_events": note_events,
        }

    except Exception as e:
        raise UtilsError(f"Failed to analyze MIDI file '{midi_path}': {e}")


def validate_file_path(file_path: str, file_type: str = "file") -> None:
    """
    Validate that a file path exists and is accessible.

    Args:
        file_path: Path to validate
        file_type: Description of file type for error messages

    Raises:
        UtilsError: If file validation fails
    """
    if not file_path:
        raise UtilsError(f"Empty {file_type} path provided")

    if not os.path.exists(file_path):
        raise UtilsError(f"{file_type.capitalize()} not found: {file_path}")

    if not os.path.isfile(file_path):
        raise UtilsError(f"Path is not a file: {file_path}")


def get_file_info(file_path: str) -> dict:
    """
    Get comprehensive file information.

    Args:
        file_path: Path to the file

    Returns:
        Dict with file properties

    Raises:
        UtilsError: If file cannot be accessed
    """
    validate_file_path(file_path)

    try:
        stat = os.stat(file_path)
        return {
            "path": file_path,
            "name": os.path.basename(file_path),
            "size_bytes": stat.st_size,
            "size_mb": stat.st_size / (1024 * 1024),
            "extension": os.path.splitext(file_path)[1].lower(),
            "modified_timestamp": stat.st_mtime,
            "is_readable": os.access(file_path, os.R_OK),
            "is_writable": os.access(file_path, os.W_OK),
        }
    except OSError as e:
        raise UtilsError(f"Failed to get file info for '{file_path}': {e}")
