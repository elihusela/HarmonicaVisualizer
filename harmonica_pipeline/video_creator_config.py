"""
Video Creator Configuration - Clean configuration object for VideoCreator.

Organizes VideoCreator parameters to reduce constructor complexity.
"""

from dataclasses import dataclass
from typing import Optional


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
    enable_tab_matching: bool = False  # Tab matching with text files (experimental)

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
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
        from pathlib import Path

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
        )
