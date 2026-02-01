"""
MIDI Validator - Validates MIDI files against tab files before video generation.

Detects mismatches between MIDI note events and expected tab file structure.
"""

from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass

from harmonica_pipeline.midi_processor import MidiProcessor
from harmonica_pipeline.harmonica_key_registry import get_harmonica_config
from tab_converter.tab_mapper import TabMapper
from tab_phrase_animator.tab_text_parser import TabTextParser
from utils.utils import TEMP_DIR


@dataclass
class ValidationIssue:
    """Represents a single validation issue."""

    position: int
    issue_type: str  # "extra", "missing", "wrong", "unmappable"
    description: str
    midi_note: Optional[int] = None
    expected_note: Optional[int] = None
    time_ms: Optional[int] = None
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of MIDI validation."""

    passed: bool
    total_midi_notes: int
    total_expected_notes: int
    issues: List[ValidationIssue]

    def get_summary(self) -> str:
        """Get a human-readable summary of the validation result."""
        if self.passed:
            return f"✅ MIDI validation passed: {self.total_midi_notes}/{self.total_expected_notes} notes match"

        lines = ["❌ MIDI validation failed:"]
        for issue in self.issues:
            lines.append(f"   • {issue.description}")

        lines.append(
            f"\n   Total: {self.total_midi_notes} MIDI notes, {self.total_expected_notes} expected from tab file"
        )

        if any(issue.suggestion for issue in self.issues):
            lines.append("\nFix suggestions:")
            for issue in self.issues:
                if issue.suggestion:
                    lines.append(f"   - {issue.suggestion}")

        return "\n".join(lines)


class MidiValidator:
    """Validates MIDI files against tab files."""

    def __init__(self, midi_path: str, tab_path: str, harmonica_key: str):
        """
        Initialize MIDI validator.

        Args:
            midi_path: Path to MIDI file
            tab_path: Path to tab text file
            harmonica_key: Harmonica key (C, G, etc.)
        """
        self.midi_path = midi_path
        self.tab_path = tab_path
        self.harmonica_key = harmonica_key

        # Get key configuration
        try:
            key_config = get_harmonica_config(harmonica_key)
        except ValueError as e:
            raise ValueError(f"Invalid harmonica key '{harmonica_key}': {e}")

        # Store the MIDI mapping for unmappable note detection
        self.midi_mapping = key_config.midi_mapping

        # Initialize processors
        self.midi_processor = MidiProcessor(midi_path)
        self.tab_mapper = TabMapper(key_config.midi_mapping, TEMP_DIR)
        self.tab_text_parser = TabTextParser(tab_path)

    def validate(self) -> ValidationResult:
        """
        Validate MIDI file against tab file.

        Returns:
            ValidationResult with all detected issues
        """
        # Load MIDI note events
        midi_events = self.midi_processor.load_note_events()
        total_midi_notes = len(midi_events)

        # Parse tab file to count expected notes
        parsed_pages = self.tab_text_parser.get_pages()
        total_expected_notes = self._count_expected_notes(parsed_pages)

        # Convert MIDI to tabs to check if notes are mappable
        _ = self.tab_mapper.note_events_to_tabs(midi_events)

        # Detect issues
        issues = []

        # Check for count mismatch
        if total_midi_notes != total_expected_notes:
            if total_midi_notes > total_expected_notes:
                extra_count = total_midi_notes - total_expected_notes
                issues.append(
                    ValidationIssue(
                        position=-1,
                        issue_type="extra",
                        description=f"Found {extra_count} extra MIDI note(s)",
                        suggestion=f"Remove {extra_count} note(s) from MIDI file to match tab file",
                    )
                )
            else:
                missing_count = total_expected_notes - total_midi_notes
                issues.append(
                    ValidationIssue(
                        position=-1,
                        issue_type="missing",
                        description=f"Missing {missing_count} MIDI note(s)",
                        suggestion=f"Add {missing_count} note(s) to MIDI file to match tab file",
                    )
                )

        # Check for unmappable notes (notes not in harmonica key mapping)
        unmappable_notes = self._find_unmappable_notes(midi_events)
        for idx, (
            start_time,
            end_time,
            pitch,
            velocity,
            confidence,
        ) in unmappable_notes:
            time_ms = int(start_time * 1000)  # Convert to milliseconds
            issues.append(
                ValidationIssue(
                    position=idx,
                    issue_type="unmappable",
                    description=f"Position {idx}: Unmappable note (MIDI {pitch}) at time {time_ms}ms",
                    midi_note=pitch,
                    time_ms=time_ms,
                    suggestion=(
                        f"Change MIDI note {pitch} at position {idx} "
                        f"to a note playable on {self.harmonica_key} harmonica"
                    ),
                )
            )

        # Validation passes if no issues found
        passed = len(issues) == 0

        return ValidationResult(
            passed=passed,
            total_midi_notes=total_midi_notes,
            total_expected_notes=total_expected_notes,
            issues=issues,
        )

    def _count_expected_notes(self, parsed_pages: Dict[str, List[List[List]]]) -> int:
        """
        Count expected number of notes from parsed tab pages.

        Args:
            parsed_pages: Parsed tab file pages (Dict[str, List[List[List[ParsedNote]]]])

        Returns:
            Total count of expected notes
        """
        total_notes = 0

        for page_name, lines in parsed_pages.items():
            for line in lines:
                for chord in line:
                    # Each chord is a list of ParsedNote objects
                    # Count the number of notes in each chord
                    total_notes += len(chord)

        return total_notes

    def _find_unmappable_notes(
        self, midi_events: List[Tuple[float, float, int, float, float]]
    ) -> List[Tuple[int, Tuple[float, float, int, float, float]]]:
        """
        Find MIDI notes that cannot be mapped to the harmonica key.

        Args:
            midi_events: List of MIDI note events (start_time, end_time, pitch, velocity, confidence)

        Returns:
            List of (index, event) tuples for unmappable notes
        """
        unmappable = []

        for idx, event in enumerate(midi_events):
            start_time, end_time, pitch, velocity, confidence = event

            # Check if pitch exists in the harmonica key mapping
            if pitch not in self.midi_mapping:
                unmappable.append((idx, event))

        return unmappable


def validate_midi(
    midi_path: str, tab_path: str, harmonica_key: str
) -> ValidationResult:
    """
    Convenience function to validate MIDI against tab file.

    Args:
        midi_path: Path to MIDI file
        tab_path: Path to tab text file
        harmonica_key: Harmonica key (C, G, etc.)

    Returns:
        ValidationResult
    """
    validator = MidiValidator(midi_path, tab_path, harmonica_key)
    return validator.validate()
