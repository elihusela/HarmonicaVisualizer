"""FCPXML generator for Final Cut Pro project automation.

Generates minimal FCPXML files for importing into Final Cut Pro.
Uses simple, importable structure that FCP normalizes into full library format.
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
    """Generate a minimal FCPXML project file for Final Cut Pro.

    Creates a simple, importable FCPXML that:
    - Stacks 3 clips on lanes 0, 1, 2 (original, harmonica, tabs)
    - All synchronized at offset 0s
    - Uses rational timing format
    - Works with FCP's native import mechanism

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

    # Convert to file:// URLs for FCP compatibility
    orig_url = f"file://{orig_abs}"
    harmonica_url = f"file://{harmonica_abs}"
    tabs_url = f"file://{tabs_abs}"

    # Use default duration if not specified
    if duration_seconds is None:
        duration_seconds = 480

    width, height = video_resolution

    # Build FCPXML content
    xml_content = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE fcpxml>
<fcpxml version="1.8">
  <resources>
    <format id="r1" frameDuration="1/{int(frame_rate)}s" width="{float(width):.1f}" height="{float(height):.1f}" colorSpace="1-1-1 (Rec. 709)"/>
    <asset id="r2" name="{os.path.basename(original_video_path)}" src="{orig_url}" duration="{int(duration_seconds)}s" hasVideo="1" hasAudio="1" audioChannels="2" audioRate="48k"/>
    <asset id="r3" name="{os.path.basename(harmonica_video_path)}" src="{harmonica_url}" duration="{int(duration_seconds)}s" hasVideo="1" hasAudio="0"/>
    <asset id="r4" name="{os.path.basename(tabs_video_path)}" src="{tabs_url}" duration="{int(duration_seconds)}s" hasVideo="1" hasAudio="0"/>
  </resources>
  <library>
    <event name="{song_name}">
      <project name="{song_name}">
        <sequence format="r1" duration="{int(duration_seconds)}s" audioRate="48k">
          <spine>
            <asset-clip ref="r2" offset="0s" start="0s" duration="{int(duration_seconds)}s" lane="0"/>
            <asset-clip ref="r3" offset="0s" start="0s" duration="{int(duration_seconds)}s" lane="1"/>
            <asset-clip ref="r4" offset="0s" start="0s" duration="{int(duration_seconds)}s" lane="2"/>
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
