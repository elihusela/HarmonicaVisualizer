"""
Video Creator Configuration - Clean configuration object for VideoCreator.

Organizes VideoCreator parameters to reduce constructor complexity.
"""

from dataclasses import dataclass
from typing import Optional

from harmonica_pipeline.harmonica_key_registry import get_harmonica_config


@dataclass
class VideoCreatorConfig:
    """Configuration object for VideoCreator initialization."""

    # Input files
    video_path: str
    tabs_path: str
    harmonica_path: str
    midi_path: str

    # Output files
    output_video_path: str
    tabs_output_path: Optional[str] = None

    # Options
    produce_tabs: bool = True
    produce_full_tab_video: bool = True  # Generate single continuous tab video
    only_full_tab_video: bool = (
        False  # Only output full video, clean up individual pages
    )
    enable_tab_matching: bool = False  # Tab matching with text files (experimental)
    harmonica_key: str = "C"  # Default to C harmonica

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        from pathlib import Path

        # Get key configuration and potentially override harmonica_path
        try:
            key_config = get_harmonica_config(self.harmonica_key)
        except ValueError as e:
            raise ValueError(f"Invalid harmonica key: {e}")

        # If harmonica_path is the default "G.png" (old default),
        # use the key-specific model from the registry instead
        harmonica_path_obj = Path(self.harmonica_path)
        if harmonica_path_obj.name == "G.png":
            # User is using old default, override with key-specific model
            self.harmonica_path = f"harmonica-models/{key_config.model_image}"
        elif not harmonica_path_obj.is_absolute() and not str(
            harmonica_path_obj
        ).startswith("harmonica-models/"):
            # User provided a relative filename without directory, prepend harmonica-models/
            self.harmonica_path = f"harmonica-models/{harmonica_path_obj.name}"

        # Store key config for VideoCreator to access
        self._key_config = key_config

        # Ensure all required paths are provided
        required_paths = [
            self.video_path,
            self.tabs_path,
            self.harmonica_path,
            self.midi_path,
            self.output_video_path,
        ]

        for path in required_paths:
            if not path or not isinstance(path, str):
                raise ValueError(f"Invalid path provided: {path}")

        # Validate output directory exists for output files
        for output_path in [self.output_video_path, self.tabs_output_path]:
            if output_path:
                output_dir = Path(output_path).parent
                if not output_dir.exists():
                    try:
                        output_dir.mkdir(parents=True, exist_ok=True)
                    except Exception as e:
                        raise ValueError(
                            f"Cannot create output directory {output_dir}: {e}"
                        )

    @classmethod
    def from_cli_args(
        cls,
        video_path: str,
        tabs_path: str,
        harmonica_path: str,
        midi_path: str,
        output_video_path: str,
        tabs_output_path: Optional[str] = None,
        produce_tabs: bool = True,
        produce_full_tab_video: bool = True,
        only_full_tab_video: bool = False,
        harmonica_key: str = "C",
    ) -> "VideoCreatorConfig":
        """
        Create configuration from CLI arguments.

        Args:
            video_path: Path to original video file
            tabs_path: Path to tab text file
            harmonica_path: Path to harmonica model image
            midi_path: Path to fixed MIDI file
            output_video_path: Path for output harmonica video
            tabs_output_path: Optional path for tab phrase video
            produce_tabs: Whether to generate tab phrase animations
            produce_full_tab_video: Whether to generate single continuous tab video
            only_full_tab_video: Only output full video, clean up individual pages
            harmonica_key: Harmonica key (C, G, BB, etc.)

        Returns:
            VideoCreatorConfig instance
        """
        return cls(
            video_path=video_path,
            tabs_path=tabs_path,
            harmonica_path=harmonica_path,
            midi_path=midi_path,
            output_video_path=output_video_path,
            tabs_output_path=tabs_output_path,
            produce_tabs=produce_tabs,
            produce_full_tab_video=produce_full_tab_video,
            only_full_tab_video=only_full_tab_video,
            harmonica_key=harmonica_key,
        )
