"""Tests for harmonica_pipeline.video_creator module."""

from unittest.mock import MagicMock, patch
import pytest

from harmonica_pipeline.video_creator import VideoCreator, VideoCreatorError
from harmonica_pipeline.video_creator_config import VideoCreatorConfig
from tab_converter.models import TabEntry


class TestVideoCreatorConfig:
    """Test VideoCreatorConfig dataclass functionality."""

    def test_config_creation_valid(self, temp_test_dir):
        """Test creating a valid VideoCreatorConfig."""
        # Create dummy files
        video_path = temp_test_dir / "test.mp4"
        tabs_path = temp_test_dir / "test.txt"
        harmonica_path = temp_test_dir / "harmonica.png"
        midi_path = temp_test_dir / "test.mid"
        output_path = temp_test_dir / "output.mp4"

        for path in [video_path, tabs_path, harmonica_path, midi_path]:
            path.write_text("dummy")

        config = VideoCreatorConfig(
            video_path=str(video_path),
            tabs_path=str(tabs_path),
            harmonica_path=str(harmonica_path),
            midi_path=str(midi_path),
            output_video_path=str(output_path),
        )

        assert config.video_path == str(video_path)
        assert config.tabs_path == str(tabs_path)
        assert config.harmonica_path == str(harmonica_path)
        assert config.midi_path == str(midi_path)
        assert config.output_video_path == str(output_path)
        assert config.tabs_output_path is None
        assert config.produce_tabs is True
        assert config.enable_tab_matching is False

    def test_config_with_optional_params(self, temp_test_dir):
        """Test config with optional parameters."""
        # Create dummy files
        video_path = temp_test_dir / "test.mp4"
        tabs_path = temp_test_dir / "test.txt"
        harmonica_path = temp_test_dir / "harmonica.png"
        midi_path = temp_test_dir / "test.mid"
        output_path = temp_test_dir / "output.mp4"
        tabs_output_path = temp_test_dir / "tabs_output.mp4"

        for path in [video_path, tabs_path, harmonica_path, midi_path]:
            path.write_text("dummy")

        config = VideoCreatorConfig(
            video_path=str(video_path),
            tabs_path=str(tabs_path),
            harmonica_path=str(harmonica_path),
            midi_path=str(midi_path),
            output_video_path=str(output_path),
            tabs_output_path=str(tabs_output_path),
            produce_tabs=False,
            enable_tab_matching=True,
        )

        assert config.tabs_output_path == str(tabs_output_path)
        assert config.produce_tabs is False
        assert config.enable_tab_matching is True

    def test_config_invalid_path_validation(self):
        """Test that invalid paths raise ValueError."""
        with pytest.raises(ValueError, match="Invalid path provided"):
            VideoCreatorConfig(
                video_path="",  # Empty path
                tabs_path="valid.txt",
                harmonica_path="valid.png",
                midi_path="valid.mid",
                output_video_path="output.mp4",
            )

    def test_config_from_cli_args(self, temp_test_dir):
        """Test creating config from CLI arguments."""
        # Create dummy files
        video_path = temp_test_dir / "test.mp4"
        tabs_path = temp_test_dir / "test.txt"
        harmonica_path = temp_test_dir / "harmonica.png"
        midi_path = temp_test_dir / "test.mid"
        output_path = temp_test_dir / "output.mp4"

        for path in [video_path, tabs_path, harmonica_path, midi_path]:
            path.write_text("dummy")

        config = VideoCreatorConfig.from_cli_args(
            video_path=str(video_path),
            tabs_path=str(tabs_path),
            harmonica_path=str(harmonica_path),
            midi_path=str(midi_path),
            output_video_path=str(output_path),
            produce_tabs=False,
        )

        assert config.video_path == str(video_path)
        assert config.produce_tabs is False


class TestVideoCreatorInitialization:
    """Test VideoCreator initialization methods."""

    def test_init_with_config_object(self, temp_test_dir):
        """Test initialization with VideoCreatorConfig object."""
        config = self._create_valid_config(temp_test_dir)

        with patch.multiple(
            "harmonica_pipeline.video_creator",
            AudioExtractor=MagicMock(),
            MidiProcessor=MagicMock(),
            TabMapper=MagicMock(),
            TabTextParser=MagicMock(),
            TabMatcher=MagicMock(),
            HarmonicaLayout=MagicMock(),
            FigureFactory=MagicMock(),
            Animator=MagicMock(),
            TabPhraseAnimator=MagicMock(),
        ):
            creator = VideoCreator(config)
            assert creator.config == config
            assert creator.video_path == config.video_path
            assert creator.tabs_path == config.tabs_path

    def test_init_with_legacy_parameters(self, temp_test_dir):
        """Test initialization with legacy parameter style."""
        video_path, tabs_path, harmonica_path, midi_path, output_path = (
            self._create_dummy_files(temp_test_dir)
        )

        with patch.multiple(
            "harmonica_pipeline.video_creator",
            AudioExtractor=MagicMock(),
            MidiProcessor=MagicMock(),
            TabMapper=MagicMock(),
            TabTextParser=MagicMock(),
            HarmonicaLayout=MagicMock(),
            FigureFactory=MagicMock(),
            Animator=MagicMock(),
            TabPhraseAnimator=MagicMock(),
        ):
            creator = VideoCreator(
                config_or_video_path=str(video_path),
                tabs_path=str(tabs_path),
                harmonica_path=str(harmonica_path),
                midi_path=str(midi_path),
                output_video_path=str(output_path),
            )
            assert creator.video_path == str(video_path)
            assert creator.tabs_path == str(tabs_path)

    def test_init_legacy_missing_parameters(self, temp_test_dir):
        """Test that legacy initialization fails when parameters are missing."""
        video_path = temp_test_dir / "test.mp4"
        video_path.write_text("dummy")

        with pytest.raises(VideoCreatorError, match="all path parameters are required"):
            VideoCreator(
                config_or_video_path=str(video_path),
                tabs_path=None,  # Missing required parameter
                harmonica_path="harmonica.png",
                midi_path="test.mid",
                output_video_path="output.mp4",
            )

    def test_from_config_classmethod(self, temp_test_dir):
        """Test from_config class method."""
        config = self._create_valid_config(temp_test_dir)

        with patch.multiple(
            "harmonica_pipeline.video_creator",
            AudioExtractor=MagicMock(),
            MidiProcessor=MagicMock(),
            TabMapper=MagicMock(),
            TabTextParser=MagicMock(),
            HarmonicaLayout=MagicMock(),
            FigureFactory=MagicMock(),
            Animator=MagicMock(),
            TabPhraseAnimator=MagicMock(),
        ):
            creator = VideoCreator.from_config(config)
            assert creator.config == config

    def _create_dummy_files(self, temp_dir):
        """Helper to create dummy files for testing."""
        video_path = temp_dir / "test.mp4"
        tabs_path = temp_dir / "test.txt"
        harmonica_path = temp_dir / "harmonica.png"
        midi_path = temp_dir / "test.mid"
        output_path = temp_dir / "output.mp4"

        for path in [video_path, tabs_path, harmonica_path, midi_path]:
            path.write_text("dummy")

        return video_path, tabs_path, harmonica_path, midi_path, output_path

    def _create_valid_config(self, temp_dir):
        """Helper to create a valid VideoCreatorConfig."""
        video_path, tabs_path, harmonica_path, midi_path, output_path = (
            self._create_dummy_files(temp_dir)
        )
        return VideoCreatorConfig(
            video_path=str(video_path),
            tabs_path=str(tabs_path),
            harmonica_path=str(harmonica_path),
            midi_path=str(midi_path),
            output_video_path=str(output_path),
        )


class TestVideoCreatorValidation:
    """Test VideoCreator input validation and error handling."""

    def test_missing_video_file(self, temp_test_dir):
        """Test error when video file is missing."""
        config = VideoCreatorConfig(
            video_path="/nonexistent/video.mp4",  # Missing file
            tabs_path=str(temp_test_dir / "test.txt"),
            harmonica_path=str(temp_test_dir / "harmonica.png"),
            midi_path=str(temp_test_dir / "test.mid"),
            output_video_path=str(temp_test_dir / "output.mp4"),
        )

        # Create other required files
        (temp_test_dir / "test.txt").write_text("dummy")
        (temp_test_dir / "harmonica.png").write_text("dummy")
        (temp_test_dir / "test.mid").write_text("dummy")

        with pytest.raises(VideoCreatorError, match="Video file not found"):
            VideoCreator(config)

    def test_missing_tabs_file(self, temp_test_dir):
        """Test error when tabs file is missing."""
        config = VideoCreatorConfig(
            video_path=str(temp_test_dir / "test.mp4"),
            tabs_path="/nonexistent/tabs.txt",  # Missing file
            harmonica_path=str(temp_test_dir / "harmonica.png"),
            midi_path=str(temp_test_dir / "test.mid"),
            output_video_path=str(temp_test_dir / "output.mp4"),
        )

        # Create other required files
        (temp_test_dir / "test.mp4").write_text("dummy")
        (temp_test_dir / "harmonica.png").write_text("dummy")
        (temp_test_dir / "test.mid").write_text("dummy")

        with pytest.raises(VideoCreatorError, match="Tab file not found"):
            VideoCreator(config)

    def test_invalid_video_format(self, temp_test_dir):
        """Test error with unsupported video format."""
        # Create files with invalid video extension
        video_path = temp_test_dir / "test.txt"  # Wrong extension
        tabs_path = temp_test_dir / "test.txt"
        harmonica_path = temp_test_dir / "harmonica.png"
        midi_path = temp_test_dir / "test.mid"

        for path in [video_path, tabs_path, harmonica_path, midi_path]:
            path.write_text("dummy")

        config = VideoCreatorConfig(
            video_path=str(video_path),
            tabs_path=str(tabs_path),
            harmonica_path=str(harmonica_path),
            midi_path=str(midi_path),
            output_video_path=str(temp_test_dir / "output.mp4"),
        )

        with pytest.raises(VideoCreatorError, match="Unsupported video format"):
            VideoCreator(config)

    def test_invalid_tabs_format(self, temp_test_dir):
        """Test error with non-.txt tabs file."""
        # Create files with invalid tabs extension
        video_path = temp_test_dir / "test.mp4"
        tabs_path = temp_test_dir / "test.json"  # Wrong extension
        harmonica_path = temp_test_dir / "harmonica.png"
        midi_path = temp_test_dir / "test.mid"

        for path in [video_path, tabs_path, harmonica_path, midi_path]:
            path.write_text("dummy")

        config = VideoCreatorConfig(
            video_path=str(video_path),
            tabs_path=str(tabs_path),
            harmonica_path=str(harmonica_path),
            midi_path=str(midi_path),
            output_video_path=str(temp_test_dir / "output.mp4"),
        )

        with pytest.raises(VideoCreatorError, match="Tab file must be .txt format"):
            VideoCreator(config)

    def test_invalid_harmonica_format(self, temp_test_dir):
        """Test error with unsupported harmonica image format."""
        # Create files with invalid harmonica extension
        video_path = temp_test_dir / "test.mp4"
        tabs_path = temp_test_dir / "test.txt"
        harmonica_path = temp_test_dir / "harmonica.gif"  # Wrong extension
        midi_path = temp_test_dir / "test.mid"

        for path in [video_path, tabs_path, harmonica_path, midi_path]:
            path.write_text("dummy")

        config = VideoCreatorConfig(
            video_path=str(video_path),
            tabs_path=str(tabs_path),
            harmonica_path=str(harmonica_path),
            midi_path=str(midi_path),
            output_video_path=str(temp_test_dir / "output.mp4"),
        )

        with pytest.raises(
            VideoCreatorError, match="Harmonica image must be PNG/JPG format"
        ):
            VideoCreator(config)

    def test_supported_formats_validation(self, temp_test_dir):
        """Test that all supported formats are accepted."""
        supported_combinations = [
            ("test.mp4", "harmonica.png"),
            ("test.mov", "harmonica.jpg"),
            ("test.avi", "harmonica.jpeg"),
            ("test.wav", "harmonica.PNG"),  # Case insensitive
        ]

        for video_ext, harmonica_ext in supported_combinations:
            # Create files with supported extensions
            video_path = temp_test_dir / video_ext
            tabs_path = temp_test_dir / "test.txt"
            harmonica_path = temp_test_dir / harmonica_ext
            midi_path = temp_test_dir / "test.mid"

            for path in [video_path, tabs_path, harmonica_path, midi_path]:
                path.write_text("dummy")

            config = VideoCreatorConfig(
                video_path=str(video_path),
                tabs_path=str(tabs_path),
                harmonica_path=str(harmonica_path),
                midi_path=str(midi_path),
                output_video_path=str(temp_test_dir / f"output_{video_ext}"),
            )

            # Should not raise any validation errors
            with patch.multiple(
                "harmonica_pipeline.video_creator",
                AudioExtractor=MagicMock(),
                MidiProcessor=MagicMock(),
                TabMapper=MagicMock(),
                TabTextParser=MagicMock(),
                HarmonicaLayout=MagicMock(),
                FigureFactory=MagicMock(),
                Animator=MagicMock(),
                TabPhraseAnimator=MagicMock(),
            ):
                creator = VideoCreator(config)
                assert creator.video_path == str(video_path)


class TestVideoCreatorTextBasedStructure:
    """Test the text-based structure implementation (key feature)."""

    def test_create_text_based_structure_basic(self, temp_test_dir):
        """Test basic text-based structure creation."""
        config = self._create_config_with_tabs(temp_test_dir)

        # Mock tab text parser to return structured pages
        mock_parser = MagicMock()
        mock_parser.get_pages.return_value = {
            "Page 1": [[[1], [2, 3]]],  # Line 1: chord 1, chord 2+3
            "Page 2": [[[4]], [[-5, -6]]],  # Line 1: chord 4, Line 2: chord -5+-6
        }

        # Create mock MIDI tabs
        midi_tabs = [
            TabEntry(tab=1, time=0.0, duration=0.5, confidence=0.8),
            TabEntry(tab=2, time=0.5, duration=0.5, confidence=0.8),
            TabEntry(tab=3, time=1.0, duration=0.5, confidence=0.8),
            TabEntry(tab=4, time=1.5, duration=0.5, confidence=0.8),
            TabEntry(tab=-5, time=2.0, duration=0.5, confidence=0.8),
            TabEntry(tab=-6, time=2.5, duration=0.5, confidence=0.8),
        ]
        mock_tabs = MagicMock()
        mock_tabs.tabs = midi_tabs

        with patch.multiple(
            "harmonica_pipeline.video_creator",
            AudioExtractor=MagicMock(),
            MidiProcessor=MagicMock(),
            TabMapper=MagicMock(),
            TabTextParser=MagicMock(return_value=mock_parser),
            HarmonicaLayout=MagicMock(),
            FigureFactory=MagicMock(),
            Animator=MagicMock(),
            TabPhraseAnimator=MagicMock(),
        ):
            creator = VideoCreator(config)
            creator.tabs_text_parser = mock_parser

            # Test text-based structure creation
            result = creator._create_text_based_structure(mock_tabs)

            # Should have 2 pages matching the text structure
            assert len(result) == 2
            assert "Page 1" in result
            assert "Page 2" in result

            # Page 1 should have 1 line with 2 chords
            page1 = result["Page 1"]
            assert len(page1) == 1  # 1 line
            assert len(page1[0]) == 2  # 2 chords

            # First chord should have 1 tab entry (hole 1)
            chord1 = page1[0][0]
            assert len(chord1) == 1
            assert chord1[0].tab == 1

            # Second chord should have 2 tab entries (holes 2, 3)
            chord2 = page1[0][1]
            assert len(chord2) == 2
            assert chord2[0].tab == 2
            assert chord2[1].tab == 3

    def test_create_text_based_structure_chronological_order(self, temp_test_dir):
        """Test that MIDI entries are consumed in chronological order, creating fallbacks when needed."""
        config = self._create_config_with_tabs(temp_test_dir)

        # Mock tab text parser - text order that requires chronological processing
        mock_parser = MagicMock()
        mock_parser.get_pages.return_value = {
            "Page 1": [[[1], [2], [3]]],  # Text order matches MIDI chronological order
        }

        # MIDI tabs in chronological order: 1, 2, 3
        midi_tabs = [
            TabEntry(tab=1, time=0.0, duration=0.5, confidence=0.8),
            TabEntry(tab=2, time=0.5, duration=0.5, confidence=0.8),
            TabEntry(tab=3, time=1.0, duration=0.5, confidence=0.8),
        ]
        mock_tabs = MagicMock()
        mock_tabs.tabs = midi_tabs

        with patch.multiple(
            "harmonica_pipeline.video_creator",
            AudioExtractor=MagicMock(),
            MidiProcessor=MagicMock(),
            TabMapper=MagicMock(),
            TabTextParser=MagicMock(return_value=mock_parser),
            HarmonicaLayout=MagicMock(),
            FigureFactory=MagicMock(),
            Animator=MagicMock(),
            TabPhraseAnimator=MagicMock(),
        ):
            creator = VideoCreator(config)
            creator.tabs_text_parser = mock_parser

            result = creator._create_text_based_structure(mock_tabs)

            # Should follow text structure and consume MIDI entries in chronological order
            page1 = result["Page 1"][0]

            # Check that entries are correctly mapped - should use MIDI entries in order
            # First text position wants tab 1, should find first MIDI entry with tab=1
            assert page1[0][0].tab == 1
            assert page1[0][0].time == 0.0  # First MIDI entry for tab 1

            # Second text position wants tab 2, should find next MIDI entry with tab=2
            assert page1[1][0].tab == 2
            assert page1[1][0].time == 0.5  # Second MIDI entry for tab 2

            # Third text position wants tab 3, should find next MIDI entry with tab=3
            assert page1[2][0].tab == 3
            assert page1[2][0].time == 1.0  # Third MIDI entry for tab 3

    def test_create_text_based_structure_with_fallbacks(self, temp_test_dir):
        """Test structure creation with fallback entries when MIDI runs out."""
        config = self._create_config_with_tabs(temp_test_dir)

        mock_parser = MagicMock()
        mock_parser.get_pages.return_value = {
            "Page 1": [[[1], [2], [3], [4]]],  # 4 positions in text
        }

        # Only 2 MIDI entries available
        midi_tabs = [
            TabEntry(tab=1, time=0.0, duration=0.5, confidence=0.8),
            TabEntry(tab=2, time=0.5, duration=0.5, confidence=0.8),
        ]
        mock_tabs = MagicMock()
        mock_tabs.tabs = midi_tabs

        with patch.multiple(
            "harmonica_pipeline.video_creator",
            AudioExtractor=MagicMock(),
            MidiProcessor=MagicMock(),
            TabMapper=MagicMock(),
            TabTextParser=MagicMock(return_value=mock_parser),
            HarmonicaLayout=MagicMock(),
            FigureFactory=MagicMock(),
            Animator=MagicMock(),
            TabPhraseAnimator=MagicMock(),
        ):
            creator = VideoCreator(config)
            creator.tabs_text_parser = mock_parser

            result = creator._create_text_based_structure(mock_tabs)

            page1 = result["Page 1"][0]

            # First two positions should get real MIDI entries
            assert page1[0][0].tab == 1
            assert page1[0][0].time == 0.0
            assert page1[1][0].tab == 2
            assert page1[1][0].time == 0.5

            # Last two positions should get fallback entries
            assert page1[2][0].tab == 3
            assert page1[2][0].time == 1.0  # last_time + 0.5
            assert page1[2][0].confidence == 0.5  # fallback confidence

            assert page1[3][0].tab == 4
            assert page1[3][0].time == 1.0  # last_time + 0.5
            assert page1[3][0].confidence == 0.5

    def test_create_text_only_structure_fallback(self, temp_test_dir):
        """Test fallback to text-only structure when no MIDI available."""
        config = self._create_config_with_tabs(temp_test_dir)

        mock_parser = MagicMock()
        parsed_pages = {
            "Page 1": [[[1], [2, 3]]],
            "Page 2": [[[4]], [[-5]]],
        }

        with patch.multiple(
            "harmonica_pipeline.video_creator",
            AudioExtractor=MagicMock(),
            MidiProcessor=MagicMock(),
            TabMapper=MagicMock(),
            TabTextParser=MagicMock(return_value=mock_parser),
            HarmonicaLayout=MagicMock(),
            FigureFactory=MagicMock(),
            Animator=MagicMock(),
            TabPhraseAnimator=MagicMock(),
        ):
            creator = VideoCreator(config)

            result = creator._create_text_only_structure(parsed_pages)

            # Should create structure with dummy timing
            assert len(result) == 2

            # Check that all entries have dummy timing
            page1 = result["Page 1"][0]
            assert page1[0][0].tab == 1
            assert page1[0][0].time == 0.0  # dummy time
            assert page1[0][0].duration == 0.5
            assert page1[0][0].confidence == 1.0

            # Multi-note chord
            chord2 = page1[1]
            assert len(chord2) == 2
            assert chord2[0].tab == 2
            assert chord2[1].tab == 3

    def test_create_text_based_structure_no_parser_error(self, temp_test_dir):
        """Test error when text parser is not available."""
        config = self._create_config_with_tabs(temp_test_dir)

        with patch.multiple(
            "harmonica_pipeline.video_creator",
            AudioExtractor=MagicMock(),
            MidiProcessor=MagicMock(),
            TabMapper=MagicMock(),
            TabTextParser=MagicMock(),
            HarmonicaLayout=MagicMock(),
            FigureFactory=MagicMock(),
            Animator=MagicMock(),
            TabPhraseAnimator=MagicMock(),
        ):
            creator = VideoCreator(config)
            creator.tabs_text_parser = None  # Simulate missing parser

            mock_tabs = MagicMock()
            mock_tabs.tabs = []

            with pytest.raises(
                VideoCreatorError, match="Tab text parser not available"
            ):
                creator._create_text_based_structure(mock_tabs)

    def _create_config_with_tabs(self, temp_dir):
        """Helper to create config with tabs enabled."""
        video_path = temp_dir / "test.mp4"
        tabs_path = temp_dir / "test.txt"
        harmonica_path = temp_dir / "harmonica.png"
        midi_path = temp_dir / "test.mid"
        output_path = temp_dir / "output.mp4"
        tabs_output_path = temp_dir / "tabs_output.mp4"

        for path in [video_path, tabs_path, harmonica_path, midi_path]:
            path.write_text("dummy")

        return VideoCreatorConfig(
            video_path=str(video_path),
            tabs_path=str(tabs_path),
            harmonica_path=str(harmonica_path),
            midi_path=str(midi_path),
            output_video_path=str(output_path),
            tabs_output_path=str(tabs_output_path),
            produce_tabs=True,
        )


class TestVideoCreatorDirectStructure:
    """Test direct MIDI structure creation."""

    def test_create_direct_tabs_structure_basic(self, temp_test_dir):
        """Test basic direct structure creation from MIDI timing."""
        config = self._create_basic_config(temp_test_dir)

        # Create MIDI tabs with timing gaps
        midi_tabs = [
            TabEntry(tab=1, time=0.0, duration=0.5, confidence=0.8),
            TabEntry(tab=2, time=0.5, duration=0.5, confidence=0.8),
            TabEntry(tab=3, time=1.0, duration=0.5, confidence=0.8),
            # Gap of 3 seconds
            TabEntry(tab=4, time=4.0, duration=0.5, confidence=0.8),
            TabEntry(tab=5, time=4.5, duration=0.5, confidence=0.8),
        ]
        mock_tabs = MagicMock()
        mock_tabs.tabs = midi_tabs

        with patch.multiple(
            "harmonica_pipeline.video_creator",
            AudioExtractor=MagicMock(),
            MidiProcessor=MagicMock(),
            TabMapper=MagicMock(),
            TabTextParser=MagicMock(),
            HarmonicaLayout=MagicMock(),
            FigureFactory=MagicMock(),
            Animator=MagicMock(),
            TabPhraseAnimator=MagicMock(),
        ):
            creator = VideoCreator(config)

            result = creator._create_direct_tabs_structure(mock_tabs)

            # Should create 2 pages due to timing gap
            assert len(result) == 2
            assert "page_1" in result
            assert "page_2" in result

            # Page 1 should have first 3 entries
            page1 = result["page_1"][0]
            assert len(page1) == 3
            assert page1[0][0].tab == 1
            assert page1[1][0].tab == 2
            assert page1[2][0].tab == 3

            # Page 2 should have last 2 entries
            page2 = result["page_2"][0]
            assert len(page2) == 2
            assert page2[0][0].tab == 4
            assert page2[1][0].tab == 5

    def test_create_direct_tabs_structure_no_gaps(self, temp_test_dir):
        """Test direct structure with no timing gaps."""
        config = self._create_basic_config(temp_test_dir)

        # Create MIDI tabs with no gaps (all within 2 seconds)
        midi_tabs = [
            TabEntry(tab=1, time=0.0, duration=0.5, confidence=0.8),
            TabEntry(tab=2, time=0.5, duration=0.5, confidence=0.8),
            TabEntry(tab=3, time=1.0, duration=0.5, confidence=0.8),
            TabEntry(tab=4, time=1.5, duration=0.5, confidence=0.8),
        ]
        mock_tabs = MagicMock()
        mock_tabs.tabs = midi_tabs

        with patch.multiple(
            "harmonica_pipeline.video_creator",
            AudioExtractor=MagicMock(),
            MidiProcessor=MagicMock(),
            TabMapper=MagicMock(),
            TabTextParser=MagicMock(),
            HarmonicaLayout=MagicMock(),
            FigureFactory=MagicMock(),
            Animator=MagicMock(),
            TabPhraseAnimator=MagicMock(),
        ):
            creator = VideoCreator(config)

            result = creator._create_direct_tabs_structure(mock_tabs)

            # Should create only 1 page since no gaps
            assert len(result) == 1
            assert "page_1" in result

            # Page should have all 4 entries
            page1 = result["page_1"][0]
            assert len(page1) == 4

    def test_create_direct_tabs_structure_empty_tabs(self, temp_test_dir):
        """Test direct structure with empty tabs."""
        config = self._create_basic_config(temp_test_dir)

        mock_tabs = MagicMock()
        mock_tabs.tabs = []

        with patch.multiple(
            "harmonica_pipeline.video_creator",
            AudioExtractor=MagicMock(),
            MidiProcessor=MagicMock(),
            TabMapper=MagicMock(),
            TabTextParser=MagicMock(),
            HarmonicaLayout=MagicMock(),
            FigureFactory=MagicMock(),
            Animator=MagicMock(),
            TabPhraseAnimator=MagicMock(),
        ):
            creator = VideoCreator(config)

            result = creator._create_direct_tabs_structure(mock_tabs)

            # Should create single empty page
            assert len(result) == 1
            assert "page_1" in result
            assert result["page_1"] == [[]]

    def _create_basic_config(self, temp_dir):
        """Helper to create basic config."""
        video_path = temp_dir / "test.mp4"
        tabs_path = temp_dir / "test.txt"
        harmonica_path = temp_dir / "harmonica.png"
        midi_path = temp_dir / "test.mid"
        output_path = temp_dir / "output.mp4"

        for path in [video_path, tabs_path, harmonica_path, midi_path]:
            path.write_text("dummy")

        return VideoCreatorConfig(
            video_path=str(video_path),
            tabs_path=str(tabs_path),
            harmonica_path=str(harmonica_path),
            midi_path=str(midi_path),
            output_video_path=str(output_path),
        )


class TestVideoCreatorSelectiveCreation:
    """Test selective video creation (harmonica vs tabs)."""

    def test_create_with_selective_options(self, temp_test_dir):
        """Test create method with selective creation options."""
        config = self._create_config_with_tabs(temp_test_dir)

        # Mock all the animation components
        mock_animator = MagicMock()
        mock_tab_animator = MagicMock()
        mock_audio_extractor = MagicMock()

        with patch.multiple(
            "harmonica_pipeline.video_creator",
            AudioExtractor=MagicMock(return_value=mock_audio_extractor),
            MidiProcessor=MagicMock(),
            TabMapper=MagicMock(),
            TabTextParser=MagicMock(),
            HarmonicaLayout=MagicMock(),
            FigureFactory=MagicMock(),
            Animator=MagicMock(return_value=mock_animator),
            TabPhraseAnimator=MagicMock(return_value=mock_tab_animator),
        ):
            creator = VideoCreator(config)
            creator.animator = mock_animator
            creator.tab_phrase_animator = mock_tab_animator
            creator.audio_extractor = mock_audio_extractor

            # Mock the internal methods
            creator._extract_audio = MagicMock()
            creator._load_midi_note_events = MagicMock(return_value=[])
            # Create proper mock tabs with empty .tabs attribute
            mock_empty_tabs = MagicMock()
            mock_empty_tabs.tabs = []
            creator._note_events_to_tabs = MagicMock(return_value=mock_empty_tabs)
            creator._create_text_based_structure = MagicMock(return_value={})
            creator._create_direct_tabs_structure = MagicMock(return_value={})

            # Test: Create only harmonica (no tabs)
            creator.create(create_harmonica=True, create_tabs=False)

            mock_animator.create_animation.assert_called_once()
            mock_tab_animator.create_animations.assert_not_called()

            # Reset mocks
            mock_animator.reset_mock()
            mock_tab_animator.reset_mock()

            # Test: Create only tabs (no harmonica)
            creator.create(create_harmonica=False, create_tabs=True)

            mock_animator.create_animation.assert_not_called()
            mock_tab_animator.create_animations.assert_called_once()

            # Reset mocks
            mock_animator.reset_mock()
            mock_tab_animator.reset_mock()

            # Test: Create both (default behavior)
            creator.create(create_harmonica=True, create_tabs=True)

            mock_animator.create_animation.assert_called_once()
            mock_tab_animator.create_animations.assert_called_once()

    def test_create_uses_config_defaults(self, temp_test_dir):
        """Test that create method uses config defaults when options not specified."""
        config = self._create_config_with_tabs(temp_test_dir)
        config.produce_tabs = False  # Set default to False

        mock_animator = MagicMock()
        mock_tab_animator = MagicMock()

        with patch.multiple(
            "harmonica_pipeline.video_creator",
            AudioExtractor=MagicMock(),
            MidiProcessor=MagicMock(),
            TabMapper=MagicMock(),
            TabTextParser=MagicMock(),
            HarmonicaLayout=MagicMock(),
            FigureFactory=MagicMock(),
            Animator=MagicMock(return_value=mock_animator),
            TabPhraseAnimator=MagicMock(return_value=mock_tab_animator),
        ):
            creator = VideoCreator(config)
            creator.animator = mock_animator
            creator.tab_phrase_animator = mock_tab_animator

            # Mock the internal methods
            creator._extract_audio = MagicMock()
            creator._load_midi_note_events = MagicMock(return_value=[])
            # Create proper mock tabs with empty .tabs attribute
            mock_empty_tabs = MagicMock()
            mock_empty_tabs.tabs = []
            creator._note_events_to_tabs = MagicMock(return_value=mock_empty_tabs)
            creator._create_text_based_structure = MagicMock(return_value={})
            creator._create_direct_tabs_structure = MagicMock(return_value={})

            # Call create without specifying create_tabs - should use config default (False)
            creator.create()

            mock_animator.create_animation.assert_called_once()
            mock_tab_animator.create_animations.assert_not_called()

    def test_create_skips_tabs_when_no_output_path(self, temp_test_dir):
        """Test that tab creation is skipped when no tabs output path is provided."""
        config = self._create_basic_config(temp_test_dir)
        config.tabs_output_path = None  # No tabs output path

        mock_animator = MagicMock()
        mock_tab_animator = MagicMock()

        with patch.multiple(
            "harmonica_pipeline.video_creator",
            AudioExtractor=MagicMock(),
            MidiProcessor=MagicMock(),
            TabMapper=MagicMock(),
            TabTextParser=MagicMock(),
            HarmonicaLayout=MagicMock(),
            FigureFactory=MagicMock(),
            Animator=MagicMock(return_value=mock_animator),
            TabPhraseAnimator=MagicMock(return_value=mock_tab_animator),
        ):
            creator = VideoCreator(config)
            creator.animator = mock_animator
            creator.tab_phrase_animator = mock_tab_animator

            # Mock the internal methods
            creator._extract_audio = MagicMock()
            creator._load_midi_note_events = MagicMock(return_value=[])
            creator._note_events_to_tabs = MagicMock(return_value=MagicMock())
            creator._create_direct_tabs_structure = MagicMock(return_value={})

            # Should skip tabs even when create_tabs=True due to no output path
            creator.create(create_harmonica=True, create_tabs=True)

            mock_animator.create_animation.assert_called_once()
            mock_tab_animator.create_animations.assert_not_called()

    def _create_config_with_tabs(self, temp_dir):
        """Helper to create config with tabs enabled."""
        video_path = temp_dir / "test.mp4"
        tabs_path = temp_dir / "test.txt"
        harmonica_path = temp_dir / "harmonica.png"
        midi_path = temp_dir / "test.mid"
        output_path = temp_dir / "output.mp4"
        tabs_output_path = temp_dir / "tabs_output.mp4"

        for path in [video_path, tabs_path, harmonica_path, midi_path]:
            path.write_text("dummy")

        return VideoCreatorConfig(
            video_path=str(video_path),
            tabs_path=str(tabs_path),
            harmonica_path=str(harmonica_path),
            midi_path=str(midi_path),
            output_video_path=str(output_path),
            tabs_output_path=str(tabs_output_path),
            produce_tabs=True,
        )

    def _create_basic_config(self, temp_dir):
        """Helper to create basic config."""
        video_path = temp_dir / "test.mp4"
        tabs_path = temp_dir / "test.txt"
        harmonica_path = temp_dir / "harmonica.png"
        midi_path = temp_dir / "test.mid"
        output_path = temp_dir / "output.mp4"

        for path in [video_path, tabs_path, harmonica_path, midi_path]:
            path.write_text("dummy")

        return VideoCreatorConfig(
            video_path=str(video_path),
            tabs_path=str(tabs_path),
            harmonica_path=str(harmonica_path),
            midi_path=str(midi_path),
            output_video_path=str(output_path),
        )


class TestVideoCreatorIntegration:
    """Test integration with other components."""

    def test_tab_matching_integration(self, temp_test_dir):
        """Test integration with tab matching when enabled."""
        config = self._create_config_with_matching_enabled(temp_test_dir)

        mock_tab_matcher = MagicMock()
        mock_tab_matcher.match.return_value = {"Page 1": [[[]]]}

        with patch.multiple(
            "harmonica_pipeline.video_creator",
            AudioExtractor=MagicMock(),
            MidiProcessor=MagicMock(),
            TabMapper=MagicMock(),
            TabTextParser=MagicMock(),
            TabMatcher=MagicMock(return_value=mock_tab_matcher),
            HarmonicaLayout=MagicMock(),
            FigureFactory=MagicMock(),
            Animator=MagicMock(),
            TabPhraseAnimator=MagicMock(),
        ):
            creator = VideoCreator(config)
            assert creator.tab_matcher is not None
            assert creator.config.enable_tab_matching is True

            # Test tab matching workflow
            mock_tabs = MagicMock()
            result = creator._match_tabs(mock_tabs)

            mock_tab_matcher.match.assert_called_once()
            assert result == {"Page 1": [[[]]]}

    def test_tab_matching_disabled(self, temp_test_dir):
        """Test that tab matching is properly disabled when not configured."""
        config = self._create_basic_config(temp_test_dir)
        config.enable_tab_matching = False

        with patch.multiple(
            "harmonica_pipeline.video_creator",
            AudioExtractor=MagicMock(),
            MidiProcessor=MagicMock(),
            TabMapper=MagicMock(),
            TabTextParser=MagicMock(),
            HarmonicaLayout=MagicMock(),
            FigureFactory=MagicMock(),
            Animator=MagicMock(),
            TabPhraseAnimator=MagicMock(),
        ):
            creator = VideoCreator(config)
            assert creator.tab_matcher is None
            assert creator.config.enable_tab_matching is False

    def test_match_tabs_error_when_disabled(self, temp_test_dir):
        """Test error when trying to match tabs but matching is disabled."""
        config = self._create_basic_config(temp_test_dir)

        with patch.multiple(
            "harmonica_pipeline.video_creator",
            AudioExtractor=MagicMock(),
            MidiProcessor=MagicMock(),
            TabMapper=MagicMock(),
            TabTextParser=MagicMock(),
            HarmonicaLayout=MagicMock(),
            FigureFactory=MagicMock(),
            Animator=MagicMock(),
            TabPhraseAnimator=MagicMock(),
        ):
            creator = VideoCreator(config)
            creator.tab_matcher = None

            mock_tabs = MagicMock()

            with pytest.raises(VideoCreatorError, match="Tab matching is disabled"):
                creator._match_tabs(mock_tabs)

    def test_midi_processing_integration(self, temp_test_dir):
        """Test integration with MIDI processing components."""
        config = self._create_basic_config(temp_test_dir)

        mock_midi_processor = MagicMock()
        mock_note_events = [(0.0, 0.5, 60, 0.8, 0.8)]
        mock_midi_processor.load_note_events.return_value = mock_note_events

        mock_tab_mapper = MagicMock()
        mock_tabs = MagicMock()
        mock_tab_mapper.note_events_to_tabs.return_value = mock_tabs

        with patch.multiple(
            "harmonica_pipeline.video_creator",
            AudioExtractor=MagicMock(),
            MidiProcessor=MagicMock(return_value=mock_midi_processor),
            TabMapper=MagicMock(return_value=mock_tab_mapper),
            TabTextParser=MagicMock(),
            HarmonicaLayout=MagicMock(),
            FigureFactory=MagicMock(),
            Animator=MagicMock(),
            TabPhraseAnimator=MagicMock(),
        ):
            creator = VideoCreator(config)
            creator.midi_processor = mock_midi_processor
            creator.tab_mapper = mock_tab_mapper

            # Test MIDI loading
            note_events = creator._load_midi_note_events()
            assert note_events == mock_note_events

            # Test tab conversion
            tabs = creator._note_events_to_tabs(mock_note_events)
            assert tabs == mock_tabs
            mock_tab_mapper.note_events_to_tabs.assert_called_once_with(
                mock_note_events
            )

    def _create_config_with_matching_enabled(self, temp_dir):
        """Helper to create config with tab matching enabled."""
        config = self._create_basic_config(temp_dir)
        config.enable_tab_matching = True
        return config

    def _create_basic_config(self, temp_dir):
        """Helper to create basic config."""
        video_path = temp_dir / "test.mp4"
        tabs_path = temp_dir / "test.txt"
        harmonica_path = temp_dir / "harmonica.png"
        midi_path = temp_dir / "test.mid"
        output_path = temp_dir / "output.mp4"

        for path in [video_path, tabs_path, harmonica_path, midi_path]:
            path.write_text("dummy")

        return VideoCreatorConfig(
            video_path=str(video_path),
            tabs_path=str(tabs_path),
            harmonica_path=str(harmonica_path),
            midi_path=str(midi_path),
            output_video_path=str(output_path),
        )
