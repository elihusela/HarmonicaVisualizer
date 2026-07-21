"""FCPXML generator for Final Cut Pro project automation.

Generates Final Cut Pro XML project files for assembling harmonica tab videos.
Uses correct FCPXML 1.8 schema with asset-clips and rational timing.
"""

import os
from typing import Optional
from xml.etree import ElementTree as ET
from xml.dom import minidom


class TimingValue:
    """Represents rational time values in FCPXML (numerator/denominator + unit)."""

    def __init__(self, numerator: int, denominator: int = 1, unit: str = "s"):
        self.numerator = numerator
        self.denominator = denominator
        self.unit = unit

    def __str__(self) -> str:
        """Convert to FCPXML format: '120/30s' or '0s'."""
        if self.denominator == 1:
            return f"{self.numerator}{self.unit}"
        return f"{self.numerator}/{self.denominator}{self.unit}"

    @classmethod
    def from_seconds(cls, seconds: float) -> "TimingValue":
        """Convert seconds to rational representation."""
        if seconds == 0:
            return cls(0, 1, "s")
        # Check if it's a whole number
        if seconds == int(seconds):
            return cls(int(seconds), 1, "s")
        numerator = int(seconds * 1000)
        # Simplify fraction: find GCD
        from math import gcd
        divisor = gcd(numerator, 1000)
        return cls(numerator // divisor, 1000 // divisor, "s")

    @classmethod
    def frame_duration(cls, fps: float) -> "TimingValue":
        """Get frame duration for a given frame rate."""
        if fps == 25:
            return cls(1, 25, "s")
        elif fps == 29.97:
            return cls(1001, 30000, "s")
        elif fps == 30:
            return cls(1, 30, "s")
        elif fps == 60:
            return cls(1, 60, "s")
        else:
            denominator = int(fps * 1000)
            return cls(1000, denominator, "s")


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

    Creates a valid FCPXML that:
    - Places harmonica and tabs clips on separate video lanes (lane 1, 2)
    - Original video as reference (lane 0)
    - Clips are muted on video-only layers
    - All timing uses rational format per FCPXML spec
    - No audio on harmonica/tabs clips

    Args:
        song_name: Song name for display and filenames
        original_video_path: Path to original video file
        harmonica_video_path: Path to harmonica animation video
        tabs_video_path: Path to tabs animation video
        output_dir: Directory for FCPXML output
        video_resolution: Video dimensions as (width, height)
        frame_rate: Frame rate in fps (default: 30.0)
        duration_seconds: Clip duration in seconds (if None, tries to detect)

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

    # Get absolute paths
    orig_abs = os.path.abspath(original_video_path)
    harmonica_abs = os.path.abspath(harmonica_video_path)
    tabs_abs = os.path.abspath(tabs_video_path)

    # Calculate or estimate duration (assume 8 minutes if not specified)
    if duration_seconds is None:
        duration_seconds = 480  # 8 minutes default

    # Build FCPXML
    xml_content = _build_fcpxml(
        song_name=song_name,
        orig_abs=orig_abs,
        harmonica_abs=harmonica_abs,
        tabs_abs=tabs_abs,
        video_resolution=video_resolution,
        frame_rate=frame_rate,
        duration_seconds=duration_seconds,
    )

    # Write to file
    output_path = os.path.join(output_dir, f"{song_name}_final_cut.fcpxml")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(xml_content)

    return output_path


def _build_fcpxml(
    song_name: str,
    orig_abs: str,
    harmonica_abs: str,
    tabs_abs: str,
    video_resolution: tuple,
    frame_rate: float,
    duration_seconds: float,
) -> str:
    """Build FCPXML content as a formatted string."""
    width, height = video_resolution

    # Create root element
    root = ET.Element("fcpxml")
    root.set("version", "1.8")

    # Resources section
    resources = ET.SubElement(root, "resources")

    # Format resource
    frame_duration = TimingValue.frame_duration(frame_rate)
    format_elem = ET.SubElement(resources, "format")
    format_elem.set("id", "r1")
    format_elem.set("frameDuration", str(frame_duration))
    format_elem.set("width", f"{float(width):.1f}")
    format_elem.set("height", f"{float(height):.1f}")
    format_elem.set("colorSpace", "Rec. 709")

    # Duration as timing value
    duration_timing = TimingValue.from_seconds(duration_seconds)

    # Asset resources
    asset_orig = ET.SubElement(resources, "asset")
    asset_orig.set("id", "r2")
    asset_orig.set("name", os.path.basename(orig_abs))
    asset_orig.set("src", orig_abs)
    asset_orig.set("duration", str(duration_timing))
    asset_orig.set("hasVideo", "1")
    asset_orig.set("hasAudio", "1")
    asset_orig.set("audioChannels", "2")
    asset_orig.set("audioRate", "48000")

    asset_harmonica = ET.SubElement(resources, "asset")
    asset_harmonica.set("id", "r3")
    asset_harmonica.set("name", os.path.basename(harmonica_abs))
    asset_harmonica.set("src", harmonica_abs)
    asset_harmonica.set("duration", str(duration_timing))
    asset_harmonica.set("hasVideo", "1")
    asset_harmonica.set("hasAudio", "0")

    asset_tabs = ET.SubElement(resources, "asset")
    asset_tabs.set("id", "r4")
    asset_tabs.set("name", os.path.basename(tabs_abs))
    asset_tabs.set("src", tabs_abs)
    asset_tabs.set("duration", str(duration_timing))
    asset_tabs.set("hasVideo", "1")
    asset_tabs.set("hasAudio", "0")

    # Library and project
    library = ET.SubElement(root, "library")
    event = ET.SubElement(library, "event")
    event.set("name", song_name)

    project = ET.SubElement(event, "project")
    project.set("name", song_name)

    # Sequence (timeline)
    sequence = ET.SubElement(project, "sequence")
    sequence.set("format", "r1")
    sequence.set("duration", str(duration_timing))
    sequence.set("audioRate", "48000")

    # Spine with clips stacked on lanes
    spine = ET.SubElement(sequence, "spine")

    # Lane 0: Original video (reference/background)
    clip_orig = ET.SubElement(spine, "asset-clip")
    clip_orig.set("ref", "r2")
    clip_orig.set("offset", "0s")
    clip_orig.set("duration", str(duration_timing))
    clip_orig.set("start", "0s")
    clip_orig.set("name", "Original")
    clip_orig.set("lane", "0")

    # Lane 1: Harmonica video
    clip_harmonica = ET.SubElement(spine, "asset-clip")
    clip_harmonica.set("ref", "r3")
    clip_harmonica.set("offset", "0s")
    clip_harmonica.set("duration", str(duration_timing))
    clip_harmonica.set("start", "0s")
    clip_harmonica.set("name", "Harmonica")
    clip_harmonica.set("lane", "1")

    # Lane 2: Tabs video
    clip_tabs = ET.SubElement(spine, "asset-clip")
    clip_tabs.set("ref", "r4")
    clip_tabs.set("offset", "0s")
    clip_tabs.set("duration", str(duration_timing))
    clip_tabs.set("start", "0s")
    clip_tabs.set("name", "Tabs")
    clip_tabs.set("lane", "2")

    # Pretty print
    return _prettify_xml(root)


def _prettify_xml(elem: ET.Element) -> str:
    """Return a pretty-printed XML string."""
    rough_string = ET.tostring(elem, encoding="unicode")
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ", encoding="utf-8").decode("utf-8")
