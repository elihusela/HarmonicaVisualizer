"""FCPXML generator for Final Cut Pro project automation.

Generates minimal FCPXML files for importing into Final Cut Pro.
Uses nested clip structure (harmonica/tabs nested inside original video).
All durations expressed as exact frame-count rationals to prevent audio desync.
"""

import os
import subprocess
import json
from typing import Optional, Tuple


def _probe_video(video_path: str) -> Tuple[float, int, int]:
    """Probe video for frame rate and frame count.

    Args:
        video_path: Path to video file

    Returns:
        Tuple of (fps, frame_count, rounded_fps_int)
    """
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=r_frame_rate,duration",
            "-of",
            "json",
            video_path,
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )

    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed on {video_path}: {result.stderr}")

    data = json.loads(result.stdout)
    stream = data["streams"][0]

    # Parse frame rate (can be rational like "30000/1001")
    fps_str = stream["r_frame_rate"]
    if "/" in fps_str:
        num, den = map(int, fps_str.split("/"))
        fps = num / den
    else:
        fps = float(fps_str)

    # Get duration and calculate frame count
    duration = float(stream.get("duration", 0))
    frame_count = round(duration * fps)

    return fps, frame_count, round(fps)


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

    Creates a valid FCPXML that FCP can import with one project:
    - Original video as primary clip in spine
    - Rectangle, harmonica, tabs, titles, image overlay

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

    # Probe each video for exact frame count and fps
    orig_fps, orig_frames, _ = _probe_video(original_video_path)
    harm_fps, harm_frames, _ = _probe_video(harmonica_video_path)
    tabs_fps, tabs_frames, _ = _probe_video(tabs_video_path)

    width, height = video_resolution

    # Express durations as exact rationals (frames/fps with 's' suffix)
    # This prevents audio desync caused by rounding to whole seconds
    orig_duration_str = f"{orig_frames}/{int(round(orig_fps))}s"
    harm_duration_str = f"{harm_frames}/{int(round(harm_fps))}s"
    tabs_duration_str = f"{tabs_frames}/{int(round(tabs_fps))}s"

    # Sequence duration matches original video's exact duration
    seq_duration_str = orig_duration_str

    def _build_project(project_name: str) -> str:
        """Build the project with pre-stacked clips and title."""
        ts1_id = "ts1"
        ts2_id = "ts2"
        # Main title: Artist - Song (larger, Gveret Levin)
        ts1_attrs = (
            'font="Gveret Levin" fontSize="40" fontFace="Regular" '
            'fontColor="1 1 1 1" strokeColor="0 0 0 1" strokeWidth="-1.5" '
            'alignment="center"'
        )
        # Brand label: טאבים למפוחית (smaller, Instagram Sans Bold)
        ts2_attrs = (
            'font="Instagram Sans" fontSize="24" fontFace="Bold" '
            'fontColor="1 1 1 1" strokeColor="0 0 0 1" strokeWidth="-1.5" '
            'alignment="center"'
        )
        return f"""      <project name="{project_name}">
        <sequence format="r1" duration="{seq_duration_str}" audioRate="48k">
          <spine>
            <asset-clip ref="r2" offset="0s" start="0s" \
duration="{seq_duration_str}">
              <adjust-transform>
                <param name="scale">
                  <keyframeAnimation>
                    <keyframe time="0s" value="1.08 1.08"/>
                    <keyframe time="{seq_duration_str}" value="1 1"/>
                  </keyframeAnimation>
                </param>
              </adjust-transform>
              <video ref="r5" lane="1" offset="0s" name="Shapes - Rectangle" \
start="0s" duration="{seq_duration_str}">
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
duration="{seq_duration_str}">
                <adjust-transform position="0 -23.9472" scale="0.85 0.85"/>
              </asset-clip>
              <asset-clip ref="r4" lane="3" offset="0s" start="0s" \
duration="{seq_duration_str}">
                <adjust-transform position="-0.0842787 -12.4764" \
scale="1.21341 1.21341"/>
              </asset-clip>
              <title ref="r6" lane="4" offset="0s" name="Song Title" \
start="0s" duration="3s">
                <param name="Position" \
key="9999/999166631/999166633/1/100/101" value="1.0375 280.261"/>
                <param name="Flatten" \
key="9999/999166631/999166633/2/351" value="1"/>
                <param name="Alignment" \
key="9999/999166631/999166633/2/354/999169573/401" value="1 (Center)"/>
                <text>
                  <text-style ref="{ts1_id}">artist - {song_name}</text-style>
                  <text-style ref="{ts2_id}">&#10;טאבים למפוחית</text-style>
                </text>
                <text-style-def id="{ts1_id}">
                  <text-style {ts1_attrs}/>
                </text-style-def>
                <text-style-def id="{ts2_id}">
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
src="{orig_url}" duration="{orig_duration_str}" hasVideo="1" hasAudio="1" \
audioChannels="2" audioRate="48k"/>
    <asset id="r3" name="{os.path.basename(harmonica_video_path)}" \
src="{harmonica_url}" duration="{harm_duration_str}" hasVideo="1" hasAudio="0"/>
    <asset id="r4" name="{os.path.basename(tabs_video_path)}" \
src="{tabs_url}" duration="{tabs_duration_str}" hasVideo="1" hasAudio="0"/>
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
  </resources>
  <library>
    <event name="{song_name}">
{_build_project(song_name)}
    </event>
  </library>
</fcpxml>
"""

    # Write to file
    output_path = os.path.join(output_dir, f"{song_name}_final_cut.fcpxml")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(xml_content)

    return output_path
