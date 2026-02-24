"""Tests for filename_parser module."""

import pytest

from utils.filename_parser import FilenameConfig, parse_filename


class TestFilenameConfig:
    """Tests for FilenameConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = FilenameConfig(song_name="TestSong")

        assert config.song_name == "TestSong"
        assert config.key == "C"  # Default
        assert config.enable_stem is True  # Default
        assert config.fps == 15  # Default
        assert config.tab_buffer == 0.1  # Default
        assert config.original_filename == ""

    def test_custom_values(self):
        """Test custom configuration values."""
        config = FilenameConfig(
            song_name="MySong",
            key="G",
            enable_stem=True,
            fps=30,
            tab_buffer=0.5,
            original_filename="MySong.mp4",
        )

        assert config.song_name == "MySong"
        assert config.key == "G"
        assert config.enable_stem is True
        assert config.fps == 30
        assert config.tab_buffer == 0.5
        assert config.original_filename == "MySong.mp4"


class TestParseFilename:
    """Tests for parse_filename function."""

    # Basic parsing tests
    def test_minimal_filename(self):
        """Test minimal valid filename (song name + key only)."""
        config = parse_filename("MySong_KeyC.mp4")

        assert config.song_name == "MySong"
        assert config.key == "C"
        assert config.enable_stem is True
        assert config.fps == 15
        assert config.tab_buffer == 0.1

    def test_song_name_extraction(self):
        """Test song name extraction."""
        config = parse_filename("PianoMan_KeyG.wav")
        assert config.song_name == "PianoMan"

        config = parse_filename("MyFavorite_Song_KeyD.mp4")
        assert config.song_name == "MyFavorite"  # Only first part

    # Key parsing tests
    def test_all_natural_keys(self):
        """Test parsing all natural keys (A, B, C, D, E, F, G)."""
        for key in ["A", "B", "C", "D", "E", "F", "G"]:
            config = parse_filename(f"Song_Key{key}.mp4")
            assert config.key == key

    def test_sharp_keys(self):
        """Test parsing sharp keys (C#, F#)."""
        config = parse_filename("Song_KeyC#.mp4")
        assert config.key == "C#"

        config = parse_filename("Song_KeyF#.wav")
        assert config.key == "F#"

    def test_flat_keys(self):
        """Test parsing flat keys (Bb, Eb, Ab)."""
        config = parse_filename("Song_KeyBb.mp4")
        assert config.key == "Bb"

        config = parse_filename("Song_KeyEb.wav")
        assert config.key == "Eb"

        config = parse_filename("Song_KeyAb.m4v")
        assert config.key == "Ab"

    def test_key_case_insensitive(self):
        """Test key parsing is case-insensitive."""
        config = parse_filename("Song_keyg.mp4")
        assert config.key == "G"

        config = parse_filename("Song_KEYBB.wav")
        assert config.key == "Bb"

        config = parse_filename("Song_KeyF#.mp4")
        assert config.key == "F#"

    # Stem flag tests
    def test_stem_enabled(self):
        """Test stem separation flag enabled."""
        config = parse_filename("Song_KeyC_Stem.mp4")
        assert config.enable_stem is True

    def test_stem_disabled_explicit(self):
        """Test stem separation explicitly disabled."""
        config = parse_filename("Song_KeyC_NoStem.mp4")
        assert config.enable_stem is False

    def test_stem_case_insensitive(self):
        """Test stem flag is case-insensitive."""
        config = parse_filename("Song_KeyC_stem.mp4")
        assert config.enable_stem is True

        config = parse_filename("Song_KeyC_STEM.wav")
        assert config.enable_stem is True

    # FPS parsing tests
    def test_fps_parsing(self):
        """Test FPS parameter parsing."""
        config = parse_filename("Song_KeyC_FPS15.mp4")
        assert config.fps == 15

        config = parse_filename("Song_KeyC_FPS30.mp4")
        assert config.fps == 30

        config = parse_filename("Song_KeyC_FPS60.wav")
        assert config.fps == 60

    def test_fps_case_insensitive(self):
        """Test FPS parameter is case-insensitive."""
        config = parse_filename("Song_KeyC_fps30.mp4")
        assert config.fps == 30

        config = parse_filename("Song_KeyC_FpS15.wav")
        assert config.fps == 15

    def test_fps_invalid_value(self):
        """Test invalid FPS values raise errors."""
        with pytest.raises(ValueError, match="Invalid FPS"):
            parse_filename("Song_KeyC_FPS0.mp4")

        with pytest.raises(ValueError, match="Invalid FPS"):
            parse_filename("Song_KeyC_FPS100.mp4")

    # Tab buffer parsing tests
    def test_tab_buffer_parsing(self):
        """Test tab buffer parameter parsing."""
        config = parse_filename("Song_KeyC_TabBuffer0.5.mp4")
        assert config.tab_buffer == 0.5

        config = parse_filename("Song_KeyC_TabBuffer0.1.wav")
        assert config.tab_buffer == 0.1

        config = parse_filename("Song_KeyC_TabBuffer2.0.mp4")
        assert config.tab_buffer == 2.0

    def test_tab_buffer_integer(self):
        """Test tab buffer with integer values."""
        config = parse_filename("Song_KeyC_TabBuffer1.mp4")
        assert config.tab_buffer == 1.0

        config = parse_filename("Song_KeyC_TabBuffer0.mp4")
        assert config.tab_buffer == 0.0

    def test_tab_buffer_case_insensitive(self):
        """Test tab buffer parameter is case-insensitive."""
        config = parse_filename("Song_KeyC_tabbuffer0.5.mp4")
        assert config.tab_buffer == 0.5

        config = parse_filename("Song_KeyC_TABBUFFER1.0.wav")
        assert config.tab_buffer == 1.0

    def test_tab_buffer_invalid_value(self):
        """Test invalid tab buffer values raise errors."""
        with pytest.raises(ValueError, match="Invalid TabBuffer"):
            parse_filename("Song_KeyC_TabBuffer-1.mp4")

        with pytest.raises(ValueError, match="Invalid TabBuffer"):
            parse_filename("Song_KeyC_TabBuffer10.mp4")

    # Combined parameters tests
    def test_all_parameters_combined(self):
        """Test filename with all parameters."""
        config = parse_filename("MySong_KeyG_Stem_FPS30_TabBuffer0.5.mp4")

        assert config.song_name == "MySong"
        assert config.key == "G"
        assert config.enable_stem is True
        assert config.fps == 30
        assert config.tab_buffer == 0.5

    def test_parameters_order_independent(self):
        """Test parameter order doesn't matter."""
        config1 = parse_filename("Song_KeyG_FPS30_Stem.mp4")
        config2 = parse_filename("Song_Stem_KeyG_FPS30.mp4")
        config3 = parse_filename("Song_FPS30_Stem_KeyG.wav")

        assert config1.key == config2.key == config3.key == "G"
        assert config1.fps == config2.fps == config3.fps == 30
        assert config1.enable_stem == config2.enable_stem == config3.enable_stem is True

    # File extension tests
    def test_various_extensions(self):
        """Test parsing with various file extensions."""
        for ext in [".mp4", ".wav", ".m4v", ".mov", ".MP4", ".WAV"]:
            config = parse_filename(f"Song_KeyC{ext}")
            assert config.song_name == "Song"
            assert config.key == "C"

    def test_filename_with_path(self):
        """Test parsing filename with full path."""
        config = parse_filename("/path/to/MySong_KeyG_Stem.mp4")
        assert config.song_name == "MySong"
        assert config.key == "G"
        assert config.enable_stem is True
        assert config.original_filename == "MySong_KeyG_Stem.mp4"

    def test_original_filename_preserved(self):
        """Test original filename is preserved."""
        config = parse_filename("MySong_KeyG.mp4")
        assert config.original_filename == "MySong_KeyG.mp4"

        config = parse_filename("/full/path/MySong_KeyG.wav")
        assert config.original_filename == "MySong_KeyG.wav"

    # Error cases
    def test_missing_key_raises_error(self):
        """Test filename without key raises error."""
        with pytest.raises(ValueError, match="Harmonica key not found"):
            parse_filename("MySong.mp4")

        with pytest.raises(ValueError, match="Harmonica key not found"):
            parse_filename("MySong_Stem_FPS30.wav")

    def test_empty_filename_raises_error(self):
        """Test empty filename raises error."""
        with pytest.raises(ValueError, match="Harmonica key not found"):
            parse_filename(".mp4")

    def test_unknown_parameters_ignored(self):
        """Test unknown parameters are silently ignored."""
        config = parse_filename("Song_KeyC_UnknownParam_AnotherOne.mp4")
        assert config.song_name == "Song"
        assert config.key == "C"
        # Unknown params don't affect default values
        assert config.enable_stem is True
        assert config.fps == 15


class TestKeyNormalization:
    """Tests for key normalization."""

    def test_sharp_notation_normalization(self):
        """Test sharp notation converts FS to F#."""
        # Test that KeyFS notation is supported and normalized
        config = parse_filename("Song_KeyFS.mp4")
        assert config.key == "F#"  # Normalized from FS to F#

    def test_flat_notation_normalization(self):
        """Test flat notation converts BB to Bb."""
        # Test that KeyBB notation is normalized to Bb
        config = parse_filename("Song_KeyBB.mp4")
        assert config.key == "Bb"  # Normalized from BB to Bb


class TestRealWorldExamples:
    """Test real-world filename examples."""

    def test_piano_man_example(self):
        """Test Piano Man example from docs."""
        config = parse_filename("PianoMan_KeyC_NoStem_FPS15.mp4")

        assert config.song_name == "PianoMan"
        assert config.key == "C"
        assert config.enable_stem is False
        assert config.fps == 15

    def test_amedi_example(self):
        """Test AMEDI example from docs."""
        config = parse_filename("AMEDI_KeyBb.m4v")

        assert config.song_name == "AMEDI"
        assert config.key == "Bb"
        assert config.enable_stem is True  # Default

    def test_hog_example(self):
        """Test HOG example from docs."""
        config = parse_filename("HOG_G_KeyG.m4v")

        assert config.song_name == "HOG"
        assert config.key == "G"
