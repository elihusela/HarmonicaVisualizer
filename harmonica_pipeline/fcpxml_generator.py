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

    Creates a valid FCPXML that FCP can import with TWO projects:
    - One with English legend (r14)
    - One with Hebrew legend (r15)
    - Both in the same event, with identical clips/timing
    - Original video as primary clip in spine
    - Rectangle, harmonica, tabs, titles, legend, image overlay

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

    def _build_project(project_name: str, legend_ref: str) -> str:
        """Build a single project with specified legend."""
        ts1_attrs = (
            'font="Gveret Levin" fontSize="30" fontFace="Regular" '
            'fontColor="1 1 1 1" strokeColor="0 0 0 1" strokeWidth="-1.5" '
            'alignment="center"'
        )
        ts2_attrs = (
            'font="Instagram Sans" fontSize="30" fontColor="1 1 1 1" '
            'bold="1" strokeColor="0 0 0 1" strokeWidth="-1.5" '
            'alignment="center"'
        )
        return f"""      <project name="{project_name}">
        <sequence format="r1" duration="{duration_str}" audioRate="48k">
          <spine>
            <asset-clip ref="r2" offset="0s" start="0s" duration="{duration_str}">
              <video ref="r5" lane="1" offset="0s" name="Shapes - Rectangle" \
start="0s" duration="{duration_str}">
                <param name="Fill Color" \
key="9999/3336460347/988455508/988455699/2/353/113/111" value="0 0 0"/>
                <param name="Shape" \
key="9999/988461322/100/988461395/2/100" value="4 (Rectangle)"/>
                <param name="Outline" \
key="9999/988461322/100/988464485/2/100" value="0"/>
                <param name="Fill" \
key="9999/988461322/100/988464517/2/100" value="1"/>
                <param name="Roundness" \
key="9999/988461322/100/988467054/2/100" value="0.02975"/>
                <param name="Outline Width" \
key="9999/988461322/100/988467855/2/100" value="0.288384"/>
                <adjust-transform position="0 -13.0593" \
scale="1.06062 1.8388"/>
                <adjust-blend amount="0.95"/>
              </video>
              <asset-clip ref="r3" lane="2" offset="0s" start="0s" \
duration="{duration_str}">
                <adjust-transform position="0 -23.9472" scale="0.85 0.85"/>
              </asset-clip>
              <asset-clip ref="r4" lane="3" offset="0s" start="0s" \
duration="{duration_str}">
                <adjust-transform position="-0.0842787 -12.4764" \
scale="1.21341 1.21341"/>
              </asset-clip>
              <ref-clip ref="{legend_ref}" lane="4" offset="0s" \
name="Legend" duration="{duration_str}">
                <adjust-transform position="0 0"/>
              </ref-clip>
              <title ref="r6" lane="6" offset="0s" name="Title 1" \
start="0s" duration="3s">
                <param name="Position" \
key="9999/999166631/999166633/1/100/101" value="1.0375 350.261"/>
                <param name="Flatten" \
key="9999/999166631/999166633/2/351" value="1"/>
                <param name="Alignment" \
key="9999/999166631/999166633/2/354/999169573/401" value="1 (Center)"/>
                <text>
                  <text-style ref="ts1">{song_name}</text-style>
                </text>
                <text-style-def id="ts1">
                  <text-style {ts1_attrs}/>
                </text-style-def>
              </title>
              <title ref="r6" lane="7" offset="0s" name="Title 2" \
start="0s" duration="3s">
                <param name="Position" \
key="9999/999166631/999166633/1/100/101" value="1.0415 116.088"/>
                <param name="Flatten" \
key="9999/999166631/999166633/2/351" value="1"/>
                <param name="Alignment" \
key="9999/999166631/999166633/2/354/999169573/401" value="1 (Center)"/>
                <text>
                  <text-style ref="ts2">טאבים למפוחית</text-style>
                </text>
                <text-style-def id="ts2">
                  <text-style {ts2_attrs}/>
                </text-style-def>
              </title>
            </asset-clip>
          </spine>
        </sequence>
      </project>"""

    # Build FCPXML with both English and Hebrew projects
    r7_uid = "~/Effects.localized/BretFX Outliner Lite/BretFX Outliner Lite"
    r7_uid += "/BretFX Outliner Lite.moef"
    r7_src = (
        "file:///Users/elihu.sela/Library/Containers/"
        "com.apple.FinalCutApp/Data/Movies/Motion%20Templates.localized/"
        "Effects.localized/BretFX%20Outliner%20Lite/BretFX%20Outliner%20Lite"
        "/BretFX%20Outliner%20Lite.moef"
    )
    r8_uid = "~/Effects.localized/Tap5a/Tap5a_Quick_In-Out_Animator"
    r8_uid += "/Tap5a Quick In-Out Animator/Tap5a Quick In-Out Animator.moef"
    r8_src = (
        "file:///Users/elihu.sela/Library/Containers/"
        "com.apple.FinalCutApp/Data/Movies/Motion%20Templates.localized/"
        "Effects.localized/Tap5a/Tap5a_Quick_In-Out_Animator/"
        "Tap5a%20Quick%20In-Out%20Animator/Tap5a%20Quick%20In-Out%20Animator"
        ".moef"
    )

    xml_content = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE fcpxml>
<fcpxml version="1.8">
  <resources>
    <format id="r1" frameDuration="1/{int(frame_rate)}s" width="{int(width)}" \
height="{int(height)}" colorSpace="1-1-1 (Rec. 709)"/>
    <asset id="r2" name="{os.path.basename(original_video_path)}" \
src="{orig_url}" duration="{duration_str}" hasVideo="1" hasAudio="1" \
audioChannels="2" audioRate="48k"/>
    <asset id="r3" name="{os.path.basename(harmonica_video_path)}" \
src="{harmonica_url}" duration="{duration_str}" hasVideo="1" hasAudio="0"/>
    <asset id="r4" name="{os.path.basename(tabs_video_path)}" \
src="{tabs_url}" duration="{duration_str}" hasVideo="1" hasAudio="0"/>
    <effect id="r5" name="Shapes" \
uid="Cloud:301988DA-DE3C-4D8D-B3ED-EB4B7DC02880"/>
    <effect id="r6" name="Basic Title" \
uid=".../Titles.localized/Bumper:Opener.localized/Basic Title.localized/\
Basic Title.moti"/>
    <effect id="r7" name="BretFX Outliner Lite" uid="{r7_uid}" \
src="{r7_src}"/>
    <effect id="r8" name="Tap5a Quick In-Out Animator" uid="{r8_uid}" \
src="{r8_src}"/>
    <effect id="r9" name="Drop Shadow" \
uid="FxPlug:9C13F991-BC99-4DC8-B150-381D7CCE183B"/>
    <ref-clip id="r14" name="Tabs Legend - English" \
duration="{duration_str}"/>
    <ref-clip id="r15" name="טאבים - Hebrew" duration="{duration_str}"/>
  </resources>
  <library>
    <event name="{song_name}">
{_build_project(song_name, "r14")}
{_build_project(f"{song_name}_Hebrew", "r15")}
    </event>
  </library>
</fcpxml>
"""

    # Write to file
    output_path = os.path.join(output_dir, f"{song_name}_final_cut.fcpxml")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(xml_content)

    return output_path
