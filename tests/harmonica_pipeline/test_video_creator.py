"""Refactored tests for harmonica_pipeline.video_creator module."""

from unittest.mock import MagicMock
import pytest

from harmonica_pipeline.video_creator import VideoCreator, VideoCreatorError
from harmonica_pipeline.video_creator_config import VideoCreatorConfig
from tab_converter.models import TabEntry
from tab_phrase_animator.tab_text_parser import ParsedNote


def make_parsed_pages(page_data):
    """Helper to convert int-based test data to ParsedNote format."""
    result = {}
    for page_name, lines in page_data.items():
        result[page_name] = [
            [
                [ParsedNote(hole_number=note, is_bend=False) for note in chord]
                for chord in line
            ]
            for line in lines
        ]
    return result


class TestVideoCreatorConfig:
    """Test VideoCreatorConfig dataclass functionality."""

    def test_config_creation_valid(self, basic_config):
        """Test creating a valid VideoCreatorConfig."""
        assert basic_config.video_path.endswith("test.mp4")
        assert basic_config.tabs_path.endswith("test.txt")
        assert basic_config.harmonica_path.endswith("harmonica.png")
        assert basic_config.midi_path.endswith("test.mid")
        assert basic_config.output_video_path.endswith("output.mp4")
        assert basic_config.tabs_output_path is None
        assert basic_config.produce_tabs is True
        assert basic_config.enable_tab_matching is False

    def test_config_with_optional_params(self, config_with_tabs):
        """Test config with optional parameters."""
        assert config_with_tabs.tabs_output_path.endswith("tabs_output.mp4")
        assert config_with_tabs.produce_tabs is True

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

    def test_config_from_cli_args(self, temp_test_dir, create_test_files):
        """Test creating config from CLI arguments."""
        create_test_files(temp_test_dir)

        config = VideoCreatorConfig.from_cli_args(
            video_path=str(temp_test_dir / "test.mp4"),
            tabs_path=str(temp_test_dir / "test.txt"),
            harmonica_path=str(temp_test_dir / "harmonica.png"),
            midi_path=str(temp_test_dir / "test.mid"),
            output_video_path=str(temp_test_dir / "output.mp4"),
            produce_tabs=False,
        )

        assert config.video_path.endswith("test.mp4")
        assert config.produce_tabs is False


class TestVideoCreatorInitialization:
    """Test VideoCreator initialization methods."""

    def test_init_with_config_object(
        self, basic_config, create_video_creator_with_mocks
    ):
        """Test initialization with VideoCreatorConfig object."""
        creator = create_video_creator_with_mocks(basic_config)
        assert creator.config == basic_config
        assert creator.video_path == basic_config.video_path
        assert creator.tabs_path == basic_config.tabs_path

    def test_init_with_legacy_parameters(
        self, temp_test_dir, create_test_files, mock_video_creator_dependencies
    ):
        """Test initialization with legacy parameter style."""
        create_test_files(temp_test_dir)

        creator = VideoCreator(
            config_or_video_path=str(temp_test_dir / "test.mp4"),
            tabs_path=str(temp_test_dir / "test.txt"),
            harmonica_path=str(temp_test_dir / "harmonica.png"),
            midi_path=str(temp_test_dir / "test.mid"),
            output_video_path=str(temp_test_dir / "output.mp4"),
        )
        assert creator.video_path.endswith("test.mp4")
        assert creator.tabs_path.endswith("test.txt")

    def test_init_legacy_missing_parameters(self, temp_test_dir, create_test_files):
        """Test that legacy initialization fails when parameters are missing."""
        create_test_files(temp_test_dir)

        with pytest.raises(VideoCreatorError, match="all path parameters are required"):
            VideoCreator(
                config_or_video_path=str(temp_test_dir / "test.mp4"),
                tabs_path=None,  # Missing required parameter
                harmonica_path=str(temp_test_dir / "harmonica.png"),
                midi_path=str(temp_test_dir / "test.mid"),
                output_video_path=str(temp_test_dir / "output.mp4"),
            )

    def test_from_config_classmethod(
        self, basic_config, create_video_creator_with_mocks
    ):
        """Test from_config class method."""
        creator = VideoCreator.from_config(basic_config)
        assert creator.config == basic_config


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

    @pytest.mark.parametrize(
        "invalid_ext,expected_error",
        [
            ("test.txt", "Unsupported video format"),
            ("test.json", "Tab file must be .txt format"),
            ("harmonica.gif", "Harmonica image must be PNG/JPG format"),
        ],
    )
    def test_invalid_file_formats(self, temp_test_dir, invalid_ext, expected_error):
        """Test error with invalid file formats."""
        # Create files with one invalid extension
        files = {
            "test.mp4": "dummy",
            "test.txt": "dummy",
            "harmonica.png": "dummy",
            "test.mid": "dummy",
        }

        # Override one file with invalid extension
        if "video" in expected_error:
            files["test.txt"] = files.pop("test.mp4")  # Wrong video ext
        elif "Tab file" in expected_error:
            files["test.json"] = files.pop("test.txt")  # Wrong tabs ext
        elif "Harmonica" in expected_error:
            files["harmonica.gif"] = files.pop("harmonica.png")  # Wrong image ext

        for filename, content in files.items():
            (temp_test_dir / filename).write_text(content)

        # Build config with the invalid file
        video_path = temp_test_dir / (
            "test.txt" if "video" in expected_error else "test.mp4"
        )
        tabs_path = temp_test_dir / (
            "test.json" if "Tab file" in expected_error else "test.txt"
        )
        harmonica_path = temp_test_dir / (
            "harmonica.gif" if "Harmonica" in expected_error else "harmonica.png"
        )

        config = VideoCreatorConfig(
            video_path=str(video_path),
            tabs_path=str(tabs_path),
            harmonica_path=str(harmonica_path),
            midi_path=str(temp_test_dir / "test.mid"),
            output_video_path=str(temp_test_dir / "output.mp4"),
        )

        with pytest.raises(VideoCreatorError, match=expected_error):
            VideoCreator(config)

    @pytest.mark.parametrize(
        "video_ext,harmonica_ext",
        [
            ("test.mp4", "harmonica.png"),
            ("test.mov", "harmonica.jpg"),
            ("test.avi", "harmonica.jpeg"),
            ("test.wav", "harmonica.PNG"),  # Case insensitive
        ],
    )
    def test_supported_formats_validation(
        self, temp_test_dir, mock_video_creator_dependencies, video_ext, harmonica_ext
    ):
        """Test that all supported formats are accepted."""
        # Create files with supported extensions
        (temp_test_dir / video_ext).write_text("dummy")
        (temp_test_dir / "test.txt").write_text("dummy")
        (temp_test_dir / harmonica_ext).write_text("dummy")
        (temp_test_dir / "test.mid").write_text("dummy")

        config = VideoCreatorConfig(
            video_path=str(temp_test_dir / video_ext),
            tabs_path=str(temp_test_dir / "test.txt"),
            harmonica_path=str(temp_test_dir / harmonica_ext),
            midi_path=str(temp_test_dir / "test.mid"),
            output_video_path=str(temp_test_dir / f"output_{video_ext}"),
        )

        # Should not raise any validation errors
        creator = VideoCreator(config)
        assert creator.video_path.endswith(video_ext)


class TestVideoCreatorTextBasedStructure:
    """Test the text-based structure implementation (key feature)."""

    def test_create_text_based_structure_basic(
        self,
        config_with_tabs,
        create_video_creator_with_mocks,
        sample_midi_tabs,
        sample_parsed_pages,
    ):
        """Test basic text-based structure creation."""
        creator = create_video_creator_with_mocks(config_with_tabs)

        # Mock tab text parser to return structured pages
        mock_parser = MagicMock()
        mock_parser.get_pages.return_value = sample_parsed_pages
        creator.tabs_text_parser = mock_parser

        # Create mock MIDI tabs
        mock_tabs = MagicMock()
        mock_tabs.tabs = sample_midi_tabs

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

    def test_create_text_based_structure_chronological_order(
        self, config_with_tabs, create_video_creator_with_mocks
    ):
        """Test that MIDI entries are consumed in chronological order."""
        creator = create_video_creator_with_mocks(config_with_tabs)

        # Mock tab text parser - text order matches MIDI chronological order
        mock_parser = MagicMock()
        mock_parser.get_pages.return_value = make_parsed_pages(
            {
                "Page 1": [
                    [[1], [2], [3]]
                ],  # Text order matches MIDI chronological order
            }
        )
        creator.tabs_text_parser = mock_parser

        # MIDI tabs in chronological order: 1, 2, 3
        midi_tabs = [
            TabEntry(tab=1, time=0.0, duration=0.5, confidence=0.8),
            TabEntry(tab=2, time=0.5, duration=0.5, confidence=0.8),
            TabEntry(tab=3, time=1.0, duration=0.5, confidence=0.8),
        ]
        mock_tabs = MagicMock()
        mock_tabs.tabs = midi_tabs

        result = creator._create_text_based_structure(mock_tabs)

        # Should follow text structure and consume MIDI entries in chronological order
        page1 = result["Page 1"][0]

        # Check that entries are correctly mapped - should use MIDI entries in order
        assert page1[0][0].tab == 1
        assert page1[0][0].time == 0.0
        assert page1[1][0].tab == 2
        assert page1[1][0].time == 0.5
        assert page1[2][0].tab == 3
        assert page1[2][0].time == 1.0

    def test_create_text_based_structure_with_fallbacks(
        self, config_with_tabs, create_video_creator_with_mocks
    ):
        """Test structure creation with fallback entries when MIDI runs out."""
        creator = create_video_creator_with_mocks(config_with_tabs)

        mock_parser = MagicMock()
        mock_parser.get_pages.return_value = make_parsed_pages(
            {
                "Page 1": [[[1], [2], [3], [4]]],  # 4 positions in text
            }
        )
        creator.tabs_text_parser = mock_parser

        # Only 2 MIDI entries available
        midi_tabs = [
            TabEntry(tab=1, time=0.0, duration=0.5, confidence=0.8),
            TabEntry(tab=2, time=0.5, duration=0.5, confidence=0.8),
        ]
        mock_tabs = MagicMock()
        mock_tabs.tabs = midi_tabs

        result = creator._create_text_based_structure(mock_tabs)
        page1 = result["Page 1"][0]

        # First two positions should get real MIDI entries
        assert page1[0][0].tab == 1
        assert page1[0][0].time == 0.0
        assert page1[1][0].tab == 2
        assert page1[1][0].time == 0.5

        # Last two positions should get fallback entries
        assert page1[2][0].tab == 3
        assert page1[2][0].time == 1.0  # last_time + 0.5 * 1
        assert page1[2][0].confidence == 0.5  # fallback confidence

        assert page1[3][0].tab == 4
        assert page1[3][0].time == 1.5  # last_time + 0.5 * 2 (incremental)
        assert page1[3][0].confidence == 0.5

    def test_create_text_only_structure_fallback(
        self, config_with_tabs, create_video_creator_with_mocks
    ):
        """Test fallback to text-only structure when no MIDI available."""
        creator = create_video_creator_with_mocks(config_with_tabs)

        parsed_pages = make_parsed_pages(
            {
                "Page 1": [[[1], [2, 3]]],
                "Page 2": [[[4]], [[-5]]],
            }
        )

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

    def test_create_text_based_structure_no_parser_error(
        self, config_with_tabs, create_video_creator_with_mocks, mock_empty_tabs
    ):
        """Test error when text parser is not available."""
        creator = create_video_creator_with_mocks(config_with_tabs)
        creator.tabs_text_parser = None  # Simulate missing parser

        with pytest.raises(VideoCreatorError, match="Tab text parser not available"):
            creator._create_text_based_structure(mock_empty_tabs)

    def test_create_text_based_structure_preserves_bend_info(
        self, config_with_tabs, create_video_creator_with_mocks
    ):
        """Test that bend info from ParsedNote is preserved in TabEntry."""
        creator = create_video_creator_with_mocks(config_with_tabs)

        # Mock parser with bend notation
        from tab_phrase_animator.tab_text_parser import ParsedNote

        mock_parser = MagicMock()
        mock_parser.get_pages.return_value = {
            "Page 1": [
                [
                    [ParsedNote(1, is_bend=False)],  # Regular note
                    [ParsedNote(2, is_bend=True)],  # Bent note
                    [ParsedNote(-3, is_bend=True)],  # Bent draw note
                ]
            ]
        }
        creator.tabs_text_parser = mock_parser

        # MIDI tabs matching text structure
        midi_tabs = [
            TabEntry(tab=1, time=0.0, duration=0.5, confidence=0.8),
            TabEntry(tab=2, time=0.5, duration=0.5, confidence=0.8),
            TabEntry(tab=-3, time=1.0, duration=0.5, confidence=0.8),
        ]
        mock_tabs = MagicMock()
        mock_tabs.tabs = midi_tabs

        result = creator._create_text_based_structure(mock_tabs)

        # Verify bend info is preserved
        page1 = result["Page 1"][0]
        assert page1[0][0].is_bend is False  # Regular note
        assert page1[1][0].is_bend is True  # Bent note
        assert page1[2][0].is_bend is True  # Bent draw note

    def test_create_text_only_structure_preserves_bend_info(
        self, config_with_tabs, create_video_creator_with_mocks
    ):
        """Test that bend info is preserved in text-only fallback."""
        from tab_phrase_animator.tab_text_parser import ParsedNote

        creator = create_video_creator_with_mocks(config_with_tabs)

        parsed_pages = {
            "Page 1": [
                [
                    [ParsedNote(1, is_bend=False)],
                    [ParsedNote(6, is_bend=True)],
                    [ParsedNote(-6, is_bend=True)],
                ]
            ]
        }

        result = creator._create_text_only_structure(parsed_pages)

        # Verify bend info is preserved in fallback entries
        page1 = result["Page 1"][0]
        assert page1[0][0].tab == 1
        assert page1[0][0].is_bend is False
        assert page1[1][0].tab == 6
        assert page1[1][0].is_bend is True
        assert page1[2][0].tab == -6
        assert page1[2][0].is_bend is True


class TestVideoCreatorDirectStructure:
    """Test direct MIDI structure creation."""

    def test_create_direct_tabs_structure_basic(
        self, basic_config, create_video_creator_with_mocks
    ):
        """Test basic direct structure creation from MIDI timing."""
        creator = create_video_creator_with_mocks(basic_config)

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

    def test_create_direct_tabs_structure_no_gaps(
        self, basic_config, create_video_creator_with_mocks
    ):
        """Test direct structure with no timing gaps."""
        creator = create_video_creator_with_mocks(basic_config)

        # Create MIDI tabs with no gaps (all within 2 seconds)
        midi_tabs = [
            TabEntry(tab=1, time=0.0, duration=0.5, confidence=0.8),
            TabEntry(tab=2, time=0.5, duration=0.5, confidence=0.8),
            TabEntry(tab=3, time=1.0, duration=0.5, confidence=0.8),
            TabEntry(tab=4, time=1.5, duration=0.5, confidence=0.8),
        ]
        mock_tabs = MagicMock()
        mock_tabs.tabs = midi_tabs

        result = creator._create_direct_tabs_structure(mock_tabs)

        # Should create only 1 page since no gaps
        assert len(result) == 1
        assert "page_1" in result

        # Page should have all 4 entries
        page1 = result["page_1"][0]
        assert len(page1) == 4

    def test_create_direct_tabs_structure_empty_tabs(
        self, basic_config, create_video_creator_with_mocks, mock_empty_tabs
    ):
        """Test direct structure with empty tabs."""
        creator = create_video_creator_with_mocks(basic_config)

        result = creator._create_direct_tabs_structure(mock_empty_tabs)

        # Should create single empty page
        assert len(result) == 1
        assert "page_1" in result
        assert result["page_1"] == [[]]


class TestVideoCreatorSelectiveCreation:
    """Test selective video creation (harmonica vs tabs)."""

    def test_create_with_selective_options(
        self, config_with_tabs, create_video_creator_with_mocks, mock_empty_tabs
    ):
        """Test create method with selective creation options."""
        creator = create_video_creator_with_mocks(config_with_tabs)

        # Mock the animation components
        mock_animator = MagicMock()
        mock_tab_animator = MagicMock()
        creator.animator = mock_animator
        creator.tab_phrase_animator = mock_tab_animator

        # Mock the internal methods
        creator._extract_audio = MagicMock()
        creator._load_midi_note_events = MagicMock(return_value=[])
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

    def test_create_uses_config_defaults(
        self, config_with_tabs, create_video_creator_with_mocks, mock_empty_tabs
    ):
        """Test that create method uses config defaults when options not specified."""
        config_with_tabs.produce_tabs = False  # Set default to False
        creator = create_video_creator_with_mocks(config_with_tabs)

        mock_animator = MagicMock()
        mock_tab_animator = MagicMock()
        creator.animator = mock_animator
        creator.tab_phrase_animator = mock_tab_animator

        # Mock the internal methods
        creator._extract_audio = MagicMock()
        creator._load_midi_note_events = MagicMock(return_value=[])
        creator._note_events_to_tabs = MagicMock(return_value=mock_empty_tabs)
        creator._create_text_based_structure = MagicMock(return_value={})
        creator._create_direct_tabs_structure = MagicMock(return_value={})

        # Call create without specifying create_tabs - should use config default (False)
        creator.create()
        mock_animator.create_animation.assert_called_once()
        mock_tab_animator.create_animations.assert_not_called()

    def test_create_skips_tabs_when_no_output_path(
        self, basic_config, create_video_creator_with_mocks
    ):
        """Test that tab creation is skipped when no tabs output path is provided."""
        basic_config.tabs_output_path = None  # No tabs output path
        creator = create_video_creator_with_mocks(basic_config)

        mock_animator = MagicMock()
        mock_tab_animator = MagicMock()
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


class TestVideoCreatorIntegration:
    """Test integration with other components."""

    def test_tab_matching_integration(
        self, config_with_tab_matching, create_video_creator_with_mocks
    ):
        """Test integration with tab matching when enabled."""
        creator = create_video_creator_with_mocks(config_with_tab_matching)

        mock_tab_matcher = MagicMock()
        mock_tab_matcher.match.return_value = {"Page 1": [[[]]]}
        creator.tab_matcher = mock_tab_matcher

        assert creator.tab_matcher is not None
        assert creator.config.enable_tab_matching is True

        # Test tab matching workflow
        mock_tabs = MagicMock()
        result = creator._match_tabs(mock_tabs)
        mock_tab_matcher.match.assert_called_once()
        assert result == {"Page 1": [[[]]]}

    def test_tab_matching_disabled(self, basic_config, create_video_creator_with_mocks):
        """Test that tab matching is properly disabled when not configured."""
        basic_config.enable_tab_matching = False
        creator = create_video_creator_with_mocks(basic_config)

        assert creator.tab_matcher is None
        assert creator.config.enable_tab_matching is False

    def test_match_tabs_error_when_disabled(
        self, basic_config, create_video_creator_with_mocks
    ):
        """Test error when trying to match tabs but matching is disabled."""
        creator = create_video_creator_with_mocks(basic_config)
        creator.tab_matcher = None

        mock_tabs = MagicMock()

        with pytest.raises(VideoCreatorError, match="Tab matching is disabled"):
            creator._match_tabs(mock_tabs)

    def test_midi_processing_integration(
        self, basic_config, create_video_creator_with_mocks
    ):
        """Test integration with MIDI processing components."""
        creator = create_video_creator_with_mocks(basic_config)

        mock_note_events = [(0.0, 0.5, 60, 0.8, 0.8)]
        mock_tabs = MagicMock()

        # Mock the internal components
        creator.midi_processor = MagicMock()
        creator.midi_processor.load_note_events.return_value = mock_note_events
        creator.tab_mapper = MagicMock()
        creator.tab_mapper.note_events_to_tabs.return_value = mock_tabs

        # Test MIDI loading
        note_events = creator._load_midi_note_events()
        assert note_events == mock_note_events

        # Test tab conversion
        tabs = creator._note_events_to_tabs(mock_note_events)
        assert tabs == mock_tabs
        creator.tab_mapper.note_events_to_tabs.assert_called_once_with(mock_note_events)


class TestVideoCreatorCoverageGaps:
    """Test cases to achieve 100% coverage for VideoCreator."""

    def test_tab_matching_initialization_with_config(self, config_with_tab_matching):
        """Test tab matching initialization when enabled in config - Line 122."""
        from unittest.mock import patch

        with patch("harmonica_pipeline.video_creator.TabTextParser") as mock_parser:
            with patch("harmonica_pipeline.video_creator.TabMatcher"):
                with patch("harmonica_pipeline.video_creator.HarmonicaLayout"):
                    with patch("harmonica_pipeline.video_creator.FigureFactory"):
                        with patch("harmonica_pipeline.video_creator.Animator"):
                            with patch(
                                "harmonica_pipeline.video_creator.TabPhraseAnimator"
                            ):
                                VideoCreator(config_with_tab_matching)

                                # Verify TabTextParser was initialized with tabs path
                                mock_parser.assert_called_once_with(
                                    config_with_tab_matching.tabs_path
                                )

    def test_midi_processor_error_handling(self, basic_config):
        """Test MidiProcessorError handling in constructor - Lines 139-140."""
        from harmonica_pipeline.midi_processor import MidiProcessorError
        from unittest.mock import patch

        with patch(
            "harmonica_pipeline.video_creator.MidiProcessor",
            side_effect=MidiProcessorError("MIDI error"),
        ):
            with pytest.raises(
                VideoCreatorError, match="MIDI processing error: MIDI error"
            ):
                VideoCreator(basic_config)

    def test_general_exception_handling(self, basic_config):
        """Test general exception handling in constructor - Lines 141-142."""
        from unittest.mock import patch

        with patch(
            "harmonica_pipeline.video_creator.TabMapper",
            side_effect=RuntimeError("General error"),
        ):
            with pytest.raises(
                VideoCreatorError,
                match="Failed to initialize video creator: General error",
            ):
                VideoCreator(basic_config)

    def test_tab_matching_print_statements(
        self, config_with_tab_matching, create_video_creator_with_mocks
    ):
        """Test tab matching print statements - Lines 217-219."""
        from unittest.mock import patch

        creator = create_video_creator_with_mocks(config_with_tab_matching)

        # Test case 1: With tabs_text_parser (text-based structure path)
        creator.tabs_text_parser = MagicMock()
        creator.tab_matcher = MagicMock()

        mock_tabs = MagicMock()

        with patch("builtins.print") as mock_print:
            with patch.object(
                creator, "_create_text_based_structure", return_value=mock_tabs
            ):
                creator.create(create_harmonica=False, create_tabs=False)
                mock_print.assert_any_call(
                    "🎯 Using .txt file structure (preserves bend notation)..."
                )

        # Test case 2: Without tabs_text_parser (match_tabs path)
        creator.tabs_text_parser = None

        with patch("builtins.print") as mock_print:
            with patch.object(creator, "_match_tabs", return_value=mock_tabs):
                creator.create(create_harmonica=False, create_tabs=False)
                mock_print.assert_any_call("🎯 Matching tabs with text notation...")

    def test_audio_extraction_call(self, basic_config, create_video_creator_with_mocks):
        """Test audio extraction method call - Line 241."""
        creator = create_video_creator_with_mocks(basic_config)

        # Mock the audio extractor
        creator.audio_extractor = MagicMock()

        creator._extract_audio()

        # Verify audio extraction was called
        creator.audio_extractor.extract_audio_from_video.assert_called_once()

    def test_empty_create_method_return(
        self, basic_config, create_video_creator_with_mocks
    ):
        """Test empty return in create method - Line 444."""
        creator = create_video_creator_with_mocks(basic_config)

        # Mock the internal methods to avoid actual processing
        creator._extract_audio = MagicMock()
        creator._load_midi_note_events = MagicMock(return_value=[])
        creator._note_events_to_tabs = MagicMock(return_value=MagicMock(tabs=[]))

        # Test with create_harmonica=False and create_tabs=False
        result = creator.create(create_harmonica=False, create_tabs=False)

        # Should return None (line 444)
        assert result is None
