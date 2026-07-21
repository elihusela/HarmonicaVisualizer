"""FCPXML generator for Final Cut Pro project automation.

Generates minimal FCPXML files for importing into Final Cut Pro.
Uses nested clip structure (harmonica/tabs nested inside original video).
"""

import os
from typing import Optional


def generate_fcpxml(
    song_name: str,
    original_video_path: str,
    harmonica_video_path: str,
    tabs_video_path: str,
    output_dir: str = "final-cut",
    video_resolution: tuple = (2160, 3840),
    frame_rate: float = 30.0,
    duration_seconds: Optional[float] = None,
) -> str:
    """Generate an FCPXML project file for Final Cut Pro.

    Creates a valid FCPXML that FCP can import:
    - Original video as primary clip in spine
    - Harmonica and tabs nested inside original (on lanes 1, 2)
    - All clips time-synchronized at offset 0s
    - Uses absolute file:// URLs for media paths

    Args:
        song_name: Song name for display and filenames
        original_video_path: Path to original video file
        harmonica_video_path: Path to harmonica animation video
        tabs_video_path: Path to tabs animation video
        output_dir: Directory for FCPXML output
        video_resolution: Video dimensions as (width, height)
        frame_rate: Frame rate in fps (default: 30.0)
        duration_seconds: Clip duration in seconds (if None, default to 480)

    Returns:
        Path to generated FCPXML file

    Raises:
        FileNotFoundError: If any input video file doesn't exist
    """
    # Validate input files
    for path, name in [
        (original_video_path, "Original video"),
        (harmonica_video_path, "Harmonica video"),
        (tabs_video_path, "Tabs video"),
    ]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"{name} not found: {path}")

    os.makedirs(output_dir, exist_ok=True)

    # Get absolute paths and convert to file:// URLs
    orig_abs = os.path.abspath(original_video_path)
    harmonica_abs = os.path.abspath(harmonica_video_path)
    tabs_abs = os.path.abspath(tabs_video_path)

    orig_url = f"file://{orig_abs}"
    harmonica_url = f"file://{harmonica_abs}"
    tabs_url = f"file://{tabs_abs}"

    # Use default duration if not specified
    if duration_seconds is None:
        duration_seconds = 480

    width, height = video_resolution
    duration_str = f"{int(duration_seconds)}s"

    # Build FCPXML with nested clip structure
    xml_content = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE fcpxml>
<fcpxml version="1.8">
  <resources>
    <format id="r1" frameDuration="1/{int(frame_rate)}s" width="{int(width)}" height="{int(height)}" colorSpace="1-1-1 (Rec. 709)"/>
    <asset id="r2" name="{os.path.basename(original_video_path)}" src="{orig_url}" duration="{duration_str}" hasVideo="1" hasAudio="1" audioChannels="2" audioRate="48k"/>
    <asset id="r3" name="{os.path.basename(harmonica_video_path)}" src="{harmonica_url}" duration="{duration_str}" hasVideo="1" hasAudio="0"/>
    <asset id="r4" name="{os.path.basename(tabs_video_path)}" src="{tabs_url}" duration="{duration_str}" hasVideo="1" hasAudio="0"/>
  </resources>
  <library>
    <event name="{song_name}">
      <project name="{song_name}">
        <sequence format="r1" duration="{duration_str}" audioRate="48k">
          <spine>
            <asset-clip ref="r2" offset="0s" start="0s" duration="{duration_str}">
              <asset-clip ref="r3" lane="1" offset="0s" start="0s" duration="{duration_str}"/>
              <asset-clip ref="r4" lane="2" offset="0s" start="0s" duration="{duration_str}"/>
            </asset-clip>
          </spine>
        </sequence>
      </project>
    </event>
  </library>
</fcpxml>
"""

    # Write to file
    output_path = os.path.join(output_dir, f"{song_name}_final_cut.fcpxml")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(xml_content)

    return output_path
