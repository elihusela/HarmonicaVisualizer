"""Tests for utils.utils module."""

import os
import time
from pathlib import Path
from unittest.mock import patch
import pytest

import mido
from mido import MidiFile, MidiTrack, Message, MetaMessage

from utils.utils import (
    DirectoryConfig,
    UtilsError,
    get_directory_config,
    get_directory_info,
    clean_temp_folder,
    ensure_directories_exist,
    get_tempo,
    get_midi_info,
    validate_file_path,
    get_file_info,
    TEMP_DIR,
    VIDEO_FILES_DIR,
    TAB_FILES_DIR,
    OUTPUTS_DIR,
    MIDI_DIR,
)


class TestDirectoryConfig:
    """Test DirectoryConfig dataclass functionality."""

    def test_directory_config_creation(self):
        """Test DirectoryConfig creation without auto-creation."""
        config = DirectoryConfig(
            temp_dir="/tmp/test",
            video_files_dir="/tmp/videos",
            tab_files_dir="/tmp/tabs",
            outputs_dir="/tmp/outputs",
            midi_dir="/tmp/midis",
            create_if_missing=False,
        )

        assert config.temp_dir == "/tmp/test"
        assert config.video_files_dir == "/tmp/videos"
        assert config.tab_files_dir == "/tmp/tabs"
        assert config.outputs_dir == "/tmp/outputs"
        assert config.midi_dir == "/tmp/midis"
        assert config.create_if_missing is False

    def test_directory_config_auto_creation(self, temp_test_dir):
        """Test DirectoryConfig with automatic directory creation."""
        test_dirs = {
            "temp_dir": str(temp_test_dir / "temp"),
            "video_files_dir": str(temp_test_dir / "videos"),
            "tab_files_dir": str(temp_test_dir / "tabs"),
            "outputs_dir": str(temp_test_dir / "outputs"),
            "midi_dir": str(temp_test_dir / "midis"),
        }

        config = DirectoryConfig(
            **test_dirs,
            create_if_missing=True,
        )

        # All directories should exist after creation
        for dir_path in test_dirs.values():
            assert os.path.exists(dir_path)
            assert os.path.isdir(dir_path)

    def test_directory_config_creation_failure(self):
        """Test DirectoryConfig when directory creation fails."""
        with patch("os.makedirs", side_effect=OSError("Permission denied")):
            with pytest.raises(OSError):
                DirectoryConfig(
                    temp_dir="/root/restricted",
                    video_files_dir="/root/videos",
                    tab_files_dir="/root/tabs",
                    outputs_dir="/root/outputs",
                    midi_dir="/root/midis",
                    create_if_missing=True,
                )


class TestDirectoryManagement:
    """Test directory management functions."""

    def test_get_directory_config(self):
        """Test getting default directory configuration."""
        config = get_directory_config()

        assert isinstance(config, DirectoryConfig)
        assert config.temp_dir.endswith("temp/")
        assert config.video_files_dir.endswith("video-files/")
        assert config.tab_files_dir.endswith("tab-files/")
        assert config.outputs_dir.endswith("outputs/")
        assert config.midi_dir.endswith("fixed_midis/")

    def test_backwards_compatibility_constants(self):
        """Test that backwards compatibility constants exist."""
        assert TEMP_DIR.endswith("temp/")
        assert VIDEO_FILES_DIR.endswith("video-files/")
        assert TAB_FILES_DIR.endswith("tab-files/")
        assert OUTPUTS_DIR.endswith("outputs/")
        assert MIDI_DIR.endswith("fixed_midis/")

    def test_get_directory_info(self, temp_test_dir):
        """Test getting comprehensive directory information."""
        # Create some test directories and files
        test_dirs = ["temp", "videos", "tabs", "outputs", "midis"]
        for dir_name in test_dirs:
            dir_path = temp_test_dir / dir_name
            dir_path.mkdir()
            # Add some test files
            (dir_path / "test1.txt").write_text("content1")
            (dir_path / "test2.txt").write_text("content2" * 100)

        # Mock the default config to use our test directories
        mock_config = DirectoryConfig(
            temp_dir=str(temp_test_dir / "temp") + "/",
            video_files_dir=str(temp_test_dir / "videos") + "/",
            tab_files_dir=str(temp_test_dir / "tabs") + "/",
            outputs_dir=str(temp_test_dir / "outputs") + "/",
            midi_dir=str(temp_test_dir / "midis") + "/",
            create_if_missing=False,
        )

        with patch("utils.utils.get_directory_config", return_value=mock_config):
            info = get_directory_info()

        assert "project_root" in info
        assert "directories" in info

        for dir_name in ["temp", "video_files", "tab_files", "outputs", "midi"]:
            dir_info = info["directories"][dir_name]
            assert dir_info["exists"] is True
            assert dir_info["is_directory"] is True
            assert dir_info["file_count"] == 2
            assert dir_info["total_size_bytes"] > 0

    def test_get_directory_info_missing_directories(self):
        """Test directory info with missing directories."""
        mock_config = DirectoryConfig(
            temp_dir="/nonexistent/temp/",
            video_files_dir="/nonexistent/videos/",
            tab_files_dir="/nonexistent/tabs/",
            outputs_dir="/nonexistent/outputs/",
            midi_dir="/nonexistent/midis/",
            create_if_missing=False,
        )

        with patch("utils.utils.get_directory_config", return_value=mock_config):
            info = get_directory_info()

        for dir_name in ["temp", "video_files", "tab_files", "outputs", "midi"]:
            dir_info = info["directories"][dir_name]
            assert dir_info["exists"] is False
            assert dir_info["is_directory"] is False
            assert dir_info["file_count"] == 0
            assert dir_info["total_size_bytes"] == 0

    def test_clean_temp_folder_default_path(self, temp_test_dir):
        """Test cleaning temp folder with default path."""
        test_temp = temp_test_dir / "custom_temp"
        test_temp.mkdir()
        test_file = test_temp / "test.txt"
        test_file.write_text("content")

        assert test_file.exists()

        with patch("utils.utils.TEMP_DIR", str(test_temp) + "/"):
            clean_temp_folder()

        # Directory should exist but file should be gone
        assert test_temp.exists()
        assert not test_file.exists()

    def test_clean_temp_folder_custom_path(self, temp_test_dir):
        """Test cleaning temp folder with custom path."""
        test_temp = temp_test_dir / "custom_temp"
        test_temp.mkdir()
        test_file = test_temp / "test.txt"
        test_file.write_text("content")

        assert test_file.exists()

        clean_temp_folder(str(test_temp))

        # Directory should exist but file should be gone
        assert test_temp.exists()
        assert not test_file.exists()

    def test_clean_temp_folder_nonexistent(self, temp_test_dir):
        """Test cleaning non-existent temp folder."""
        test_temp = temp_test_dir / "nonexistent"

        clean_temp_folder(str(test_temp))

        # Directory should be created
        assert test_temp.exists()

    def test_clean_temp_folder_permission_error(self):
        """Test cleaning temp folder with permission error."""
        with patch("utils.utils.shutil.rmtree", side_effect=OSError("Permission denied")):
            with pytest.raises(UtilsError, match="Failed to clean temp folder"):
                clean_temp_folder("/restricted/path")

    def test_ensure_directories_exist_default(self, temp_test_dir):
        """Test ensuring default directories exist."""
        test_dirs = [
            str(temp_test_dir / "temp"),
            str(temp_test_dir / "videos"),
            str(temp_test_dir / "tabs"),
            str(temp_test_dir / "outputs"),
            str(temp_test_dir / "midis"),
        ]

        mock_config = DirectoryConfig(
            temp_dir=test_dirs[0],
            video_files_dir=test_dirs[1],
            tab_files_dir=test_dirs[2],
            outputs_dir=test_dirs[3],
            midi_dir=test_dirs[4],
            create_if_missing=False,
        )

        with patch("utils.utils.get_directory_config", return_value=mock_config):
            ensure_directories_exist()

        for dir_path in test_dirs:
            assert os.path.exists(dir_path)

    def test_ensure_directories_exist_custom(self, temp_test_dir):
        """Test ensuring custom directories exist."""
        test_dirs = [
            str(temp_test_dir / "custom1"),
            str(temp_test_dir / "custom2"),
        ]

        ensure_directories_exist(test_dirs)

        for dir_path in test_dirs:
            assert os.path.exists(dir_path)

    def test_ensure_directories_exist_failure(self):
        """Test ensure directories with creation failure."""
        with patch("os.makedirs", side_effect=OSError("Permission denied")):
            with pytest.raises(UtilsError, match="Failed to create directory"):
                ensure_directories_exist(["/root/restricted"])


class TestMidiUtilities:
    """Test MIDI processing utilities."""

    def test_get_tempo_with_tempo_message(self):
        """Test tempo extraction from MIDI with tempo message."""
        # Create a MIDI file with tempo
        mid = MidiFile()
        track = MidiTrack()
        track.append(MetaMessage("set_tempo", tempo=500000, time=0))  # 120 BPM
        mid.tracks.append(track)

        tempo = get_tempo(mid)
        assert tempo == 500000

    def test_get_tempo_without_tempo_message(self):
        """Test tempo extraction from MIDI without tempo message."""
        # Create a MIDI file without tempo
        mid = MidiFile()
        track = MidiTrack()
        track.append(Message("note_on", channel=0, note=60, velocity=64, time=0))
        mid.tracks.append(track)

        tempo = get_tempo(mid)
        assert tempo == mido.bpm2tempo(120)  # Default 120 BPM

    def test_get_tempo_invalid_input(self):
        """Test tempo extraction with invalid input."""
        with pytest.raises(UtilsError, match="Invalid MIDI file object"):
            get_tempo("not a midi file")

    def test_get_tempo_exception_handling(self):
        """Test tempo extraction with exception during processing."""
        # Create a real MIDI file and patch mido.bpm2tempo to fail
        mid = MidiFile()
        track = MidiTrack()
        track.append(Message("note_on", channel=0, note=60, velocity=64, time=0))
        mid.tracks.append(track)

        # Mock mido.bpm2tempo to raise exception when default tempo is calculated
        with patch("utils.utils.mido.bpm2tempo", side_effect=Exception("MIDI error")):
            with pytest.raises(UtilsError, match="Failed to extract tempo"):
                get_tempo(mid)

    def test_get_midi_info_success(self, temp_test_dir):
        """Test getting MIDI file information successfully."""
        midi_path = temp_test_dir / "test.mid"

        # Create a test MIDI file
        mid = MidiFile()
        track = MidiTrack()
        track.append(MetaMessage("set_tempo", tempo=500000, time=0))
        track.append(Message("note_on", channel=0, note=60, velocity=64, time=480))
        track.append(Message("note_off", channel=0, note=60, velocity=64, time=480))
        mid.tracks.append(track)
        mid.save(str(midi_path))

        info = get_midi_info(str(midi_path))

        assert info["file_path"] == str(midi_path)
        assert info["file_size_bytes"] > 0
        assert info["format_type"] == 1  # Default MIDI format
        assert info["tracks_count"] == 1
        assert info["ticks_per_beat"] == 480  # Default
        assert "length_seconds" in info
        assert "tempo_bpm" in info
        assert info["note_events"] == 2  # note_on + note_off

    def test_get_midi_info_file_not_found(self):
        """Test getting MIDI info for non-existent file."""
        with pytest.raises(UtilsError, match="MIDI file not found"):
            get_midi_info("/nonexistent/file.mid")

    def test_get_midi_info_invalid_file(self, temp_test_dir):
        """Test getting MIDI info for invalid MIDI file."""
        midi_path = temp_test_dir / "invalid.mid"
        midi_path.write_text("not a midi file")

        with pytest.raises(UtilsError, match="Failed to analyze MIDI file"):
            get_midi_info(str(midi_path))


class TestFileUtilities:
    """Test file validation and information utilities."""

    def test_validate_file_path_success(self, temp_test_dir):
        """Test successful file path validation."""
        test_file = temp_test_dir / "test.txt"
        test_file.write_text("content")

        # Should not raise any exception
        validate_file_path(str(test_file))
        validate_file_path(str(test_file), "custom file")

    def test_validate_file_path_empty(self):
        """Test file path validation with empty path."""
        with pytest.raises(UtilsError, match="Empty file path provided"):
            validate_file_path("")

        with pytest.raises(UtilsError, match="Empty custom path provided"):
            validate_file_path("", "custom")

    def test_validate_file_path_not_found(self):
        """Test file path validation with non-existent file."""
        with pytest.raises(UtilsError, match="File not found"):
            validate_file_path("/nonexistent/file.txt")

        with pytest.raises(UtilsError, match="Custom file not found"):
            validate_file_path("/nonexistent/file.txt", "custom file")

    def test_validate_file_path_not_file(self, temp_test_dir):
        """Test file path validation with directory instead of file."""
        with pytest.raises(UtilsError, match="Path is not a file"):
            validate_file_path(str(temp_test_dir))

    def test_get_file_info_success(self, temp_test_dir):
        """Test getting file information successfully."""
        test_file = temp_test_dir / "test.txt"
        content = "test content for file info"
        test_file.write_text(content)

        # Wait a moment to ensure timestamp is set
        time.sleep(0.01)

        info = get_file_info(str(test_file))

        assert info["path"] == str(test_file)
        assert info["name"] == "test.txt"
        assert info["size_bytes"] == len(content)
        assert info["size_mb"] == len(content) / (1024 * 1024)
        assert info["extension"] == ".txt"
        assert info["modified_timestamp"] > 0
        assert info["is_readable"] is True
        assert info["is_writable"] is True

    def test_get_file_info_not_found(self):
        """Test getting file info for non-existent file."""
        with pytest.raises(UtilsError, match="File not found"):
            get_file_info("/nonexistent/file.txt")

    def test_get_file_info_permission_error(self, temp_test_dir):
        """Test getting file info with permission error."""
        test_file = temp_test_dir / "test.txt"
        test_file.write_text("content")

        # We need to patch both os.exists and os.stat since validation checks exist first
        with patch("utils.utils.os.path.exists", return_value=True):
            with patch("utils.utils.os.path.isfile", return_value=True):
                with patch(
                    "utils.utils.os.stat", side_effect=OSError("Permission denied")
                ):
                    with pytest.raises(UtilsError, match="Failed to get file info"):
                        get_file_info(str(test_file))

    def test_get_file_info_no_extension(self, temp_test_dir):
        """Test getting file info for file without extension."""
        test_file = temp_test_dir / "README"
        test_file.write_text("readme content")

        info = get_file_info(str(test_file))

        assert info["name"] == "README"
        assert info["extension"] == ""

    def test_get_file_info_complex_extension(self, temp_test_dir):
        """Test getting file info for file with complex extension."""
        test_file = temp_test_dir / "archive.tar.gz"
        test_file.write_text("archive content")

        info = get_file_info(str(test_file))

        assert info["name"] == "archive.tar.gz"
        assert info["extension"] == ".gz"  # os.path.splitext only gets last extension


class TestUtilsErrorHandling:
    """Test error handling throughout utils module."""

    def test_utils_error_creation(self):
        """Test UtilsError exception creation."""
        error = UtilsError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)

    def test_utils_error_inheritance(self):
        """Test UtilsError exception inheritance."""
        error = UtilsError("Test")
        assert isinstance(error, Exception)

        # Should be catchable as Exception
        try:
            raise error
        except Exception as e:
            assert isinstance(e, UtilsError)


class TestIntegrationScenarios:
    """Test integration scenarios and edge cases."""

    def test_directory_workflow_integration(self, temp_test_dir):
        """Test complete directory management workflow."""
        # Setup custom directory structure
        base_dir = temp_test_dir / "project"
        config = DirectoryConfig(
            temp_dir=str(base_dir / "temp") + "/",
            video_files_dir=str(base_dir / "videos") + "/",
            tab_files_dir=str(base_dir / "tabs") + "/",
            outputs_dir=str(base_dir / "outputs") + "/",
            midi_dir=str(base_dir / "midis") + "/",
            create_if_missing=True,
        )

        # Verify directories were created
        assert os.path.exists(config.temp_dir)
        assert os.path.exists(config.video_files_dir)

        # Add some content
        (Path(config.temp_dir) / "temp_file.txt").write_text("temp content")
        (Path(config.video_files_dir) / "video.mp4").write_text("video content")

        # Clean temp folder
        clean_temp_folder(config.temp_dir)

        # Temp should be clean but video files should remain
        assert not (Path(config.temp_dir) / "temp_file.txt").exists()
        assert (Path(config.video_files_dir) / "video.mp4").exists()

    def test_midi_analysis_workflow(self, temp_test_dir):
        """Test complete MIDI analysis workflow."""
        midi_path = temp_test_dir / "complex.mid"

        # Create complex MIDI file
        mid = MidiFile()
        track = MidiTrack()
        track.append(MetaMessage("set_tempo", tempo=600000, time=0))  # 100 BPM
        track.append(Message("note_on", channel=0, note=60, velocity=64, time=480))
        track.append(Message("note_on", channel=0, note=64, velocity=64, time=240))
        track.append(Message("note_off", channel=0, note=60, velocity=64, time=240))
        track.append(Message("note_off", channel=0, note=64, velocity=64, time=240))
        mid.tracks.append(track)
        mid.save(str(midi_path))

        # Validate file
        validate_file_path(str(midi_path), "MIDI file")

        # Get file info
        file_info = get_file_info(str(midi_path))
        assert file_info["extension"] == ".mid"

        # Get MIDI-specific info
        midi_info = get_midi_info(str(midi_path))
        assert midi_info["note_events"] == 4  # 2 note_on + 2 note_off
        assert midi_info["tempo_bpm"] == 100
        assert midi_info["tracks_count"] == 1

    def test_error_propagation_workflow(self, temp_test_dir):
        """Test error propagation through utility functions."""
        # Start with file validation
        nonexistent_file = str(temp_test_dir / "nonexistent.mid")

        with pytest.raises(UtilsError, match="MIDI file not found"):
            get_midi_info(nonexistent_file)

        # Create invalid MIDI file
        invalid_midi = temp_test_dir / "invalid.mid"
        invalid_midi.write_text("invalid content")

        with pytest.raises(UtilsError, match="Failed to analyze MIDI file"):
            get_midi_info(str(invalid_midi))
