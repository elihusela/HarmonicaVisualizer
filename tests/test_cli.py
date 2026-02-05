"""
Tests for CLI module.

NOTE: These tests require early imports in conftest.py (MidiGenerator, VideoCreator)
to avoid pkg_resources initialization issues when run in isolation. If these tests
fail when run alone but pass in the full suite, check that conftest.py imports are present.
"""

from unittest.mock import MagicMock, patch

import pytest

from cli import (
    DEFAULT_HARMONICA_MODEL,
    create_video_phase,
    full_pipeline,
    generate_midi_phase,
    get_video_base_name,
    interactive_workflow,
    main,
    setup_parser,
    validate_file_exists,
)


class TestSetupParser:
    """Test argument parser setup."""

    def test_setup_parser_creates_parser(self):
        """Test that setup_parser creates an ArgumentParser."""
        parser = setup_parser()
        assert parser is not None
        assert hasattr(parser, "parse_args")

    def test_parser_has_subcommands(self):
        """Test that parser has all subcommands."""
        parser = setup_parser()

        # Test generate-midi subcommand
        args = parser.parse_args(["generate-midi", "test.mp4"])
        assert args.command == "generate-midi"
        assert args.video == "test.mp4"

        # Test create-video subcommand
        args = parser.parse_args(["create-video", "test.mp4", "tabs.txt"])
        assert args.command == "create-video"
        assert args.video == "test.mp4"
        assert args.tabs == "tabs.txt"

        # Test full subcommand
        args = parser.parse_args(["full", "test.mp4", "tabs.txt"])
        assert args.command == "full"
        assert args.video == "test.mp4"
        assert args.tabs == "tabs.txt"

        # Test interactive subcommand with tabs
        args = parser.parse_args(["interactive", "test.mp4", "tabs.txt"])
        assert args.command == "interactive"
        assert args.video == "test.mp4"
        assert args.tabs == "tabs.txt"

        # Test interactive subcommand without tabs (auto-infer)
        args = parser.parse_args(["interactive", "test.mp4"])
        assert args.command == "interactive"
        assert args.video == "test.mp4"
        assert args.tabs is None

    def test_generate_midi_with_output_name(self):
        """Test generate-midi with custom output name."""
        parser = setup_parser()
        args = parser.parse_args(
            ["generate-midi", "test.mp4", "--output-name", "custom"]
        )
        assert args.output_name == "custom"

    def test_create_video_with_options(self):
        """Test create-video with all optional arguments."""
        parser = setup_parser()
        args = parser.parse_args(
            [
                "create-video",
                "test.mp4",
                "tabs.txt",
                "--harmonica-model",
                "model.png",
                "--no-produce-tabs",
            ]
        )
        assert args.harmonica_model == "model.png"
        assert args.no_produce_tabs is True

    def test_create_video_with_only_tabs(self):
        """Test create-video with --only-tabs option."""
        parser = setup_parser()
        args = parser.parse_args(
            ["create-video", "test.mp4", "tabs.txt", "--only-tabs"]
        )
        assert args.only_tabs is True
        assert args.only_harmonica is False

    def test_create_video_with_only_harmonica(self):
        """Test create-video with --only-harmonica option."""
        parser = setup_parser()
        args = parser.parse_args(
            ["create-video", "test.mp4", "tabs.txt", "--only-harmonica"]
        )
        assert args.only_harmonica is True
        assert args.only_tabs is False

    def test_parser_defaults(self):
        """Test that parser has correct default values."""
        parser = setup_parser()
        args = parser.parse_args(["create-video", "test.mp4", "tabs.txt"])
        assert args.harmonica_model == DEFAULT_HARMONICA_MODEL
        assert args.no_produce_tabs is False
        assert args.only_tabs is False
        assert args.only_harmonica is False

    def test_interactive_with_options(self):
        """Test interactive command with all options."""
        parser = setup_parser()
        args = parser.parse_args(
            [
                "interactive",
                "test.mp4",
                "tabs.txt",
                "--session-dir",
                "custom_sessions",
                "--auto-approve",
            ]
        )
        assert args.command == "interactive"
        assert args.video == "test.mp4"
        assert args.tabs == "tabs.txt"
        assert args.session_dir == "custom_sessions"
        assert args.auto_approve is True

    def test_interactive_defaults(self):
        """Test interactive command has correct defaults."""
        parser = setup_parser()
        args = parser.parse_args(["interactive", "test.mp4"])
        assert args.session_dir == "sessions"
        assert args.auto_approve is False
        assert args.tabs is None  # tabs is optional

    def test_interactive_auto_infer_tabs(self):
        """Test interactive command can omit tabs parameter."""
        parser = setup_parser()

        # Without tabs - should be None
        args = parser.parse_args(["interactive", "MySong_KeyG.mp4"])
        assert args.tabs is None

        # With explicit tabs
        args = parser.parse_args(["interactive", "MySong_KeyG.mp4", "CustomTabs.txt"])
        assert args.tabs == "CustomTabs.txt"


class TestValidateFileExists:
    """Test file validation function."""

    def test_validate_file_exists_success(self, temp_test_dir, capsys):
        """Test validation passes for existing file."""
        test_file = temp_test_dir / "test.txt"
        test_file.write_text("content")

        # Should not raise or exit
        validate_file_exists(str(test_file), "Test")

    def test_validate_file_exists_missing_file(self, temp_test_dir, capsys):
        """Test validation fails for missing file."""
        missing_file = temp_test_dir / "nonexistent.txt"

        with pytest.raises(SystemExit) as exc_info:
            validate_file_exists(str(missing_file), "Test")

        assert exc_info.value.code == 1

        captured = capsys.readouterr()
        assert "❌ Error: Test file not found" in captured.out
        assert str(missing_file) in captured.out


class TestGetVideoBaseName:
    """Test video base name extraction."""

    def test_get_video_base_name_mp4(self):
        """Test extracting base name from .mp4 file."""
        assert get_video_base_name("video.mp4") == "video"

    def test_get_video_base_name_mov(self):
        """Test extracting base name from .mov file."""
        assert get_video_base_name("song.mov") == "song"

    def test_get_video_base_name_wav(self):
        """Test extracting base name from .wav file."""
        assert get_video_base_name("audio.wav") == "audio"

    def test_get_video_base_name_with_path(self):
        """Test extracting base name from file with path."""
        assert get_video_base_name("path/to/video.mp4") == "video"

    def test_get_video_base_name_multiple_dots(self):
        """Test file with multiple dots in name."""
        assert get_video_base_name("my.song.version.2.mp4") == "my.song.version.2"


class TestGenerateMidiPhase:
    """Test MIDI generation phase."""

    @patch("harmonica_pipeline.midi_generator.MidiGenerator")
    @patch("cli.os.path.exists")
    def test_generate_midi_video_file(
        self, mock_exists, mock_generator_class, capsys, temp_test_dir
    ):
        """Test MIDI generation from video file."""
        mock_exists.return_value = True
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator

        result = generate_midi_phase("test.mp4")

        # Verify MidiGenerator was called correctly
        mock_generator_class.assert_called_once()
        mock_generator.generate.assert_called_once()

        # Verify output path format
        assert "fixed_midis/test_fixed.mid" in result

        # Verify console output
        captured = capsys.readouterr()
        assert "Phase 1: MIDI Generation" in captured.out
        assert "Phase 1 Complete" in captured.out

    @patch("harmonica_pipeline.midi_generator.MidiGenerator")
    @patch("cli.os.path.exists")
    def test_generate_midi_wav_file_current_dir(
        self, mock_exists, mock_generator_class, capsys
    ):
        """Test MIDI generation from WAV file in current directory."""
        mock_exists.side_effect = lambda path: path == "audio.wav"
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator

        generate_midi_phase("audio.wav")

        # Should use the file in current directory
        call_args = mock_generator_class.call_args[0]
        assert call_args[0] == "audio.wav"

        captured = capsys.readouterr()
        assert "🎵" in captured.out  # WAV emoji

    @patch("harmonica_pipeline.midi_generator.MidiGenerator")
    @patch("cli.os.path.exists")
    def test_generate_midi_wav_file_video_files_dir(
        self, mock_exists, mock_generator_class
    ):
        """Test MIDI generation from WAV file in video-files directory."""
        mock_exists.side_effect = lambda path: "video-files" in path
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator

        generate_midi_phase("audio.wav")

        # Should use video-files directory
        call_args = mock_generator_class.call_args[0]
        assert "video-files" in call_args[0]

    @patch("harmonica_pipeline.midi_generator.MidiGenerator")
    @patch("cli.os.path.exists")
    def test_generate_midi_with_custom_output_name(
        self, mock_exists, mock_generator_class
    ):
        """Test MIDI generation with custom output name."""
        mock_exists.return_value = True
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator

        result = generate_midi_phase("test.mp4", output_name="custom_name")

        assert "custom_name_fixed.mid" in result

    def test_generate_midi_missing_file(self, capsys):
        """Test MIDI generation with missing video file."""
        with pytest.raises(SystemExit) as exc_info:
            generate_midi_phase("nonexistent.mp4")

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "❌ Error" in captured.out

    @patch("harmonica_pipeline.midi_generator.MidiGenerator")
    @patch("cli.os.path.exists")
    def test_generate_midi_next_steps_for_video(
        self, mock_exists, mock_generator_class, capsys
    ):
        """Test that next steps mention .wav file for video inputs."""
        mock_exists.return_value = True
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator

        generate_midi_phase("test.MOV")

        captured = capsys.readouterr()
        assert "test.wav" in captured.out

    @patch("harmonica_pipeline.midi_generator.MidiGenerator")
    @patch("cli.os.path.exists")
    def test_generate_midi_next_steps_for_wav(
        self, mock_exists, mock_generator_class, capsys
    ):
        """Test that next steps use original filename for WAV inputs."""
        mock_exists.return_value = True
        mock_generator = MagicMock()
        mock_generator_class.return_value = mock_generator

        generate_midi_phase("audio.wav")

        captured = capsys.readouterr()
        assert "audio.wav" in captured.out


class TestCreateVideoPhase:
    """Test video creation phase."""

    @patch("harmonica_pipeline.video_creator.VideoCreator")
    @patch("cli.os.path.exists")
    def test_create_video_basic(self, mock_exists, mock_creator_class, capsys):
        """Test basic video creation."""
        mock_exists.return_value = True
        mock_creator = MagicMock()
        mock_creator_class.return_value = mock_creator

        create_video_phase("test.mp4", "tabs.txt")

        # Verify VideoCreator was called
        mock_creator_class.assert_called_once()
        mock_creator.create.assert_called_once_with(
            create_harmonica=True, create_tabs=True
        )

        captured = capsys.readouterr()
        assert "Phase 2: Video Creation" in captured.out
        assert "Phase 2 Complete" in captured.out

    @patch("harmonica_pipeline.video_creator.VideoCreator")
    @patch("cli.os.path.exists")
    def test_create_video_with_custom_harmonica_model(
        self, mock_exists, mock_creator_class
    ):
        """Test video creation with custom harmonica model."""
        mock_exists.return_value = True
        mock_creator = MagicMock()
        mock_creator_class.return_value = mock_creator

        create_video_phase("test.mp4", "tabs.txt", harmonica_model="custom.png")

        # Verify harmonica path includes custom model
        # VideoCreator is now called with a config object
        call_args = mock_creator_class.call_args[0]
        config = call_args[0]
        assert "custom.png" in config.harmonica_path

    @patch("harmonica_pipeline.video_creator.VideoCreator")
    @patch("cli.os.path.exists")
    def test_create_video_no_produce_tabs(self, mock_exists, mock_creator_class):
        """Test video creation with --no-produce-tabs."""
        mock_exists.return_value = True
        mock_creator = MagicMock()
        mock_creator_class.return_value = mock_creator

        create_video_phase("test.mp4", "tabs.txt", produce_tabs=False)

        # Verify tabs_output_path is None
        call_args = mock_creator_class.call_args[0]
        config = call_args[0]
        assert config.tabs_output_path is None

        # Verify create() called with create_tabs=False
        mock_creator.create.assert_called_once_with(
            create_harmonica=True, create_tabs=False
        )

    @patch("harmonica_pipeline.video_creator.VideoCreator")
    @patch("cli.os.path.exists")
    def test_create_video_only_tabs(self, mock_exists, mock_creator_class):
        """Test video creation with --only-tabs."""
        mock_exists.return_value = True
        mock_creator = MagicMock()
        mock_creator_class.return_value = mock_creator

        create_video_phase("test.mp4", "tabs.txt", only_tabs=True)

        # Verify create() called with create_harmonica=False
        mock_creator.create.assert_called_once_with(
            create_harmonica=False, create_tabs=True
        )

    @patch("harmonica_pipeline.video_creator.VideoCreator")
    @patch("cli.os.path.exists")
    def test_create_video_only_harmonica(self, mock_exists, mock_creator_class):
        """Test video creation with --only-harmonica."""
        mock_exists.return_value = True
        mock_creator = MagicMock()
        mock_creator_class.return_value = mock_creator

        create_video_phase("test.mp4", "tabs.txt", only_harmonica=True)

        # Verify create() called with create_tabs=False
        mock_creator.create.assert_called_once_with(
            create_harmonica=True, create_tabs=False
        )

    def test_create_video_conflicting_options(self, capsys):
        """Test that both --only-tabs and --only-harmonica raises error."""
        with pytest.raises(SystemExit) as exc_info:
            create_video_phase(
                "test.mp4", "tabs.txt", only_tabs=True, only_harmonica=True
            )

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Cannot specify both" in captured.out

    def test_create_video_missing_video(self, capsys):
        """Test video creation with missing video file."""
        with pytest.raises(SystemExit):
            create_video_phase("nonexistent.mp4", "tabs.txt")

    @patch("cli.os.path.exists")
    def test_create_video_missing_tabs(self, mock_exists, capsys):
        """Test video creation with missing tabs file."""
        # Video exists, tabs don't
        mock_exists.side_effect = lambda path: "video" in path

        with pytest.raises(SystemExit):
            create_video_phase("test.mp4", "nonexistent.txt")

    @patch("cli.os.path.exists")
    def test_create_video_missing_harmonica_model(self, mock_exists, capsys):
        """Test video creation with missing harmonica model."""
        # Video and tabs exist, harmonica model doesn't
        mock_exists.side_effect = lambda path: "harmonica" not in path

        with pytest.raises(SystemExit):
            create_video_phase("test.mp4", "tabs.txt")

    @patch("cli.os.path.exists")
    def test_create_video_missing_midi(self, mock_exists, capsys):
        """Test video creation with missing MIDI file."""
        # Everything exists except MIDI
        mock_exists.side_effect = lambda path: "fixed_midis" not in path

        with pytest.raises(SystemExit):
            create_video_phase("test.mp4", "tabs.txt")


class TestFullPipeline:
    """Test full pipeline function."""

    @patch("cli.create_video_phase")
    @patch("cli.generate_midi_phase")
    def test_full_pipeline_basic(self, mock_generate, mock_create, capsys):
        """Test basic full pipeline execution."""
        mock_generate.return_value = "fixed_midis/test_fixed.mid"

        full_pipeline("test.mp4", "tabs.txt")

        # Verify both phases were called
        mock_generate.assert_called_once_with("test.mp4", "test")
        mock_create.assert_called_once_with(
            "test.mp4",
            "tabs.txt",
            "C",  # Default harmonica key
            DEFAULT_HARMONICA_MODEL,
            True,
            False,
            False,
            False,
            False,
            0.1,  # Default tab_page_buffer
            False,  # fix_overlaps
            50.0,  # chord_threshold
        )

        captured = capsys.readouterr()
        assert "Full Pipeline" in captured.out
        assert "testing mode" in captured.out.lower()

    @patch("cli.create_video_phase")
    @patch("cli.generate_midi_phase")
    def test_full_pipeline_with_options(self, mock_generate, mock_create):
        """Test full pipeline with all options."""
        mock_generate.return_value = "fixed_midis/test_fixed.mid"

        full_pipeline(
            "test.mp4",
            "tabs.txt",
            harmonica_key="G",
            harmonica_model="custom.png",
            produce_tabs=False,
            only_tabs=True,
            only_harmonica=False,
        )

        # Verify create_video_phase called with options
        mock_create.assert_called_once_with(
            "test.mp4",
            "tabs.txt",
            "G",
            "custom.png",
            False,
            True,
            False,
            False,
            False,
            0.1,
            False,  # fix_overlaps
            50.0,  # chord_threshold
        )


class TestMain:
    """Test main CLI entry point."""

    @patch("cli.generate_midi_phase")
    @patch("sys.argv", ["cli.py", "generate-midi", "test.mp4"])
    def test_main_generate_midi(self, mock_generate):
        """Test main with generate-midi command."""
        main()
        mock_generate.assert_called_once_with(
            "test.mp4",
            None,
            preset=None,
            low_freq=200,
            high_freq=5000,
            noise_reduction=-25,
            target_loudness=-16,
            onset_threshold=0.4,
            frame_threshold=0.3,
            minimum_note_length=127.7,
            minimum_frequency=None,
            maximum_frequency=None,
            no_melodia_trick=False,
        )

    @patch("cli.create_video_phase")
    @patch("sys.argv", ["cli.py", "create-video", "test.mp4", "tabs.txt"])
    def test_main_create_video(self, mock_create):
        """Test main with create-video command."""
        main()
        mock_create.assert_called_once_with(
            "test.mp4",
            "tabs.txt",
            "C",  # Default harmonica key
            DEFAULT_HARMONICA_MODEL,
            True,
            False,
            False,
            False,
            False,
            0.1,  # Default tab_page_buffer
            False,  # fix_overlaps
            50.0,  # chord_threshold
        )

    @patch("cli.full_pipeline")
    @patch("sys.argv", ["cli.py", "full", "test.mp4", "tabs.txt"])
    def test_main_full_pipeline(self, mock_full):
        """Test main with full command."""
        main()
        mock_full.assert_called_once()

    @patch("sys.argv", ["cli.py"])
    def test_main_no_command(self, capsys):
        """Test main with no command prints help and exits."""
        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1

    @patch("cli.generate_midi_phase")
    @patch(
        "sys.argv", ["cli.py", "generate-midi", "test.mp4", "--output-name", "custom"]
    )
    def test_main_with_options(self, mock_generate):
        """Test main passes options correctly."""
        main()
        mock_generate.assert_called_once_with(
            "test.mp4",
            "custom",
            preset=None,
            low_freq=200,
            high_freq=5000,
            noise_reduction=-25,
            target_loudness=-16,
            onset_threshold=0.4,
            frame_threshold=0.3,
            minimum_note_length=127.7,
            minimum_frequency=None,
            maximum_frequency=None,
            no_melodia_trick=False,
        )

    @patch("cli.generate_midi_phase")
    @patch("sys.argv", ["cli.py", "generate-midi", "test.mp4"])
    def test_main_keyboard_interrupt(self, mock_generate, capsys):
        """Test main handles KeyboardInterrupt."""
        mock_generate.side_effect = KeyboardInterrupt()

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Interrupted" in captured.out

    @patch("cli.generate_midi_phase")
    @patch("sys.argv", ["cli.py", "generate-midi", "test.mp4"])
    def test_main_generic_exception(self, mock_generate, capsys):
        """Test main handles generic exceptions."""
        mock_generate.side_effect = ValueError("Test error")

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "❌ Error: Test error" in captured.out

    @patch("cli.create_video_phase")
    @patch(
        "sys.argv", ["cli.py", "create-video", "test.mp4", "tabs.txt", "--only-tabs"]
    )
    def test_main_create_video_only_tabs(self, mock_create):
        """Test main with --only-tabs option."""
        main()
        mock_create.assert_called_once_with(
            "test.mp4",
            "tabs.txt",
            "C",  # Default harmonica key
            DEFAULT_HARMONICA_MODEL,
            True,
            True,
            False,
            False,
            False,
            0.1,  # Default tab_page_buffer
            False,  # fix_overlaps
            50.0,  # chord_threshold
        )

    @patch("cli.create_video_phase")
    @patch(
        "sys.argv",
        ["cli.py", "create-video", "test.mp4", "tabs.txt", "--only-harmonica"],
    )
    def test_main_create_video_only_harmonica(self, mock_create):
        """Test main with --only-harmonica option."""
        main()
        mock_create.assert_called_once_with(
            "test.mp4",
            "tabs.txt",
            "C",  # Default harmonica key
            DEFAULT_HARMONICA_MODEL,
            True,
            False,
            True,
            False,
            False,
            0.1,  # Default tab_page_buffer
            False,  # fix_overlaps
            50.0,  # chord_threshold
        )

    @patch("cli.create_video_phase")
    @patch(
        "sys.argv",
        ["cli.py", "create-video", "test.mp4", "tabs.txt", "--no-produce-tabs"],
    )
    def test_main_create_video_no_produce_tabs(self, mock_create):
        """Test main with --no-produce-tabs option."""
        main()
        mock_create.assert_called_once_with(
            "test.mp4",
            "tabs.txt",
            "C",  # Default harmonica key
            DEFAULT_HARMONICA_MODEL,
            False,
            False,
            False,
            False,
            False,
            0.1,  # Default tab_page_buffer
            False,  # fix_overlaps
            50.0,  # chord_threshold
        )


class TestCLIIntegration:
    """Integration tests for CLI workflows."""

    @patch("harmonica_pipeline.midi_generator.MidiGenerator")
    @patch("cli.os.path.exists")
    def test_realistic_generate_midi_workflow(self, mock_exists, mock_midi_gen):
        """Test realistic generate-midi workflow."""
        mock_exists.return_value = True
        mock_generator = MagicMock()
        mock_midi_gen.return_value = mock_generator

        midi_path = generate_midi_phase("MySong.mp4")

        assert "MySong_fixed.mid" in midi_path
        mock_generator.generate.assert_called_once()

    @patch("harmonica_pipeline.video_creator.VideoCreator")
    @patch("cli.os.path.exists")
    def test_realistic_create_video_workflow(self, mock_exists, mock_creator_class):
        """Test realistic create-video workflow."""
        mock_exists.return_value = True
        mock_creator = MagicMock()
        mock_creator_class.return_value = mock_creator

        create_video_phase("MySong.wav", "MySong.txt")

        # Verify paths are correct
        call_args = mock_creator_class.call_args[0]
        config = call_args[0]
        assert "MySong_fixed.mid" in config.midi_path
        assert "MySong_harmonica.mov" in config.output_video_path
        assert "MySong_tabs.mov" in config.tabs_output_path

    @patch("interactive_workflow.orchestrator.WorkflowOrchestrator")
    @patch("cli.os.path.exists")
    def test_interactive_workflow_integration(
        self, mock_exists, mock_orchestrator_class
    ):
        """Test interactive workflow integration with explicit tabs."""
        mock_exists.return_value = True
        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator

        interactive_workflow("MySong_KeyG.mp4", "MySong.txt", "sessions", True)

        # Verify orchestrator was created with correct parameters
        mock_orchestrator_class.assert_called_once()
        call_kwargs = mock_orchestrator_class.call_args[1]
        assert "MySong_KeyG.mp4" in call_kwargs["input_video"]
        assert "MySong.txt" in call_kwargs["input_tabs"]
        assert call_kwargs["session_dir"] == "sessions"
        assert call_kwargs["auto_approve"] is True

        # Verify run was called
        mock_orchestrator.run.assert_called_once()

    @patch("interactive_workflow.orchestrator.WorkflowOrchestrator")
    @patch("cli.os.path.exists")
    def test_interactive_workflow_auto_infer_tabs(
        self, mock_exists, mock_orchestrator_class
    ):
        """Test interactive workflow auto-infers tab file from video name."""
        mock_exists.return_value = True
        mock_orchestrator = MagicMock()
        mock_orchestrator_class.return_value = mock_orchestrator

        # Call without tabs parameter - should auto-infer
        interactive_workflow("MySong_KeyG.mp4", None, "sessions", True)

        # Verify tabs path was auto-inferred to MySong.txt
        mock_orchestrator_class.assert_called_once()
        call_kwargs = mock_orchestrator_class.call_args[1]
        assert "MySong.txt" in call_kwargs["input_tabs"]

    @patch("cli.interactive_workflow")
    @patch("sys.argv", ["cli.py", "interactive", "test.mp4", "tabs.txt"])
    def test_main_interactive(self, mock_interactive):
        """Test main dispatches to interactive workflow with explicit tabs."""
        main()
        mock_interactive.assert_called_once_with(
            "test.mp4", "tabs.txt", "sessions", False, False, None
        )

    @patch("cli.interactive_workflow")
    @patch("sys.argv", ["cli.py", "interactive", "test.mp4"])
    def test_main_interactive_auto_infer(self, mock_interactive):
        """Test main dispatches to interactive workflow with auto-inferred tabs."""
        main()
        mock_interactive.assert_called_once_with(
            "test.mp4", None, "sessions", False, False, None
        )

    @patch("cli.interactive_workflow")
    @patch(
        "sys.argv",
        [
            "cli.py",
            "interactive",
            "test.mp4",
            "tabs.txt",
            "--session-dir",
            "custom",
            "--auto-approve",
        ],
    )
    def test_main_interactive_with_options(self, mock_interactive):
        """Test main dispatches interactive workflow with options."""
        main()
        mock_interactive.assert_called_once_with(
            "test.mp4", "tabs.txt", "custom", True, False, None
        )

    @patch("cli.interactive_workflow")
    @patch(
        "sys.argv",
        ["cli.py", "interactive", "test.mp4", "--clean"],
    )
    def test_main_interactive_with_clean(self, mock_interactive):
        """Test main dispatches interactive workflow with --clean flag."""
        main()
        mock_interactive.assert_called_once_with(
            "test.mp4", None, "sessions", False, True, None
        )

    @patch("cli.interactive_workflow")
    @patch(
        "sys.argv",
        ["cli.py", "interactive", "test.mp4", "--skip-to", "tabs"],
    )
    def test_main_interactive_with_skip_to(self, mock_interactive):
        """Test main dispatches interactive workflow with --skip-to flag."""
        main()
        mock_interactive.assert_called_once_with(
            "test.mp4", None, "sessions", False, False, "tabs"
        )
