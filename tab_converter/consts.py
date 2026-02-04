"""
Harmonica MIDI mappings - All keys derived from C harmonica by transposition.

The C harmonica is the "master" mapping. All other keys are generated
by transposing the C mapping by the appropriate number of semitones.
"""

NOTE_ON_MSG = "note_on"
NOTE_OFF_MSG = "note_off"
SET_TEMPO_MSG = "set_tempo"


# =============================================================================
# C HARMONICA - THE MASTER MAPPING
# =============================================================================
# All other keys are transposed from this. Blow 1 = C4 = MIDI 60.

# Regular notes (pitch -> hole number, positive = blow, negative = draw)
_C_HARMONICA_NOTES = {
    60: 1,  # Blow 1 (C4)
    62: -1,  # Draw 1 (D4)
    64: 2,  # Blow 2 (E4)
    67: 3,  # Blow 3 (G4) - Note: Draw 2 (G4) shares pitch with Blow 3
    71: -3,  # Draw 3 (B4)
    72: 4,  # Blow 4 (C5)
    74: -4,  # Draw 4 (D5)
    76: 5,  # Blow 5 (E5)
    77: -5,  # Draw 5 (F5)
    79: 6,  # Blow 6 (G5)
    81: -6,  # Draw 6 (A5)
    84: 7,  # Blow 7 (C6)
    83: -7,  # Draw 7 (B5)
    88: 8,  # Blow 8 (E6)
    86: -8,  # Draw 8 (D6)
    91: 9,  # Blow 9 (G6)
    89: -9,  # Draw 9 (F6)
    96: 10,  # Blow 10 (C7)
    93: -10,  # Draw 10 (A6)
}

# Bend notes (pitch -> (hole number, bend notation))
# Draw bends available on holes 1-6 where draw is higher than blow
_C_HARMONICA_BENDS = {
    # Hole 1: 1 bend available (D4 draw, can bend to Db4)
    61: (-1, "'"),  # -1' = Db4
    # Hole 2: 2 bends available (G4 draw, can bend to Gb4, F4)
    66: (-2, "'"),  # -2' = Gb4
    65: (-2, "''"),  # -2'' = F4
    # Hole 3: 3 bends available (B4 draw, can bend to Bb4, A4, Ab4)
    70: (-3, "'"),  # -3' = Bb4
    69: (-3, "''"),  # -3'' = A4
    68: (-3, "'''"),  # -3''' = Ab4
    # Hole 4: 1 bend available (D5 draw, can bend to Db5)
    73: (-4, "'"),  # -4' = Db5
    # Hole 5: No bends (F5 draw is only 1 semitone above E5 blow)
    # Hole 6: 1 bend available (A5 draw, can bend to Ab5)
    80: (-6, "'"),  # -6' = Ab5
}


# =============================================================================
# KEY TRANSPOSITION
# =============================================================================
# Offset from C (semitones). Negative = lower pitch.
# Each key's Blow 1 pitch = 60 + offset

KEY_OFFSETS = {
    "C": 0,
    "C#": -11,  # C#3 (MIDI 49)
    "D": -10,  # D3 (MIDI 50)
    "EB": -9,  # Eb3 (MIDI 51)
    "E": -8,  # E3 (MIDI 52)
    "F": -7,  # F3 (MIDI 53)
    "F#": -6,  # F#3 (MIDI 54)
    "G": -5,  # G3 (MIDI 55)
    "AB": -4,  # Ab3 (MIDI 56)
    "A": -3,  # A3 (MIDI 57)
    "BB": -2,  # Bb3 (MIDI 58)
    "B": -1,  # B3 (MIDI 59)
}


def _transpose_mapping(base_mapping: dict, offset: int) -> dict:
    """Transpose a pitch->hole mapping by the given semitone offset."""
    return {pitch + offset: hole for pitch, hole in base_mapping.items()}


def _transpose_bend_mapping(base_bends: dict, offset: int) -> dict:
    """Transpose a pitch->(hole, notation) bend mapping by the given semitone offset."""
    return {pitch + offset: bend_info for pitch, bend_info in base_bends.items()}


def _expand_octaves(base_mapping: dict) -> dict:
    """Expand a mapping to include notes one octave above and below.

    This helps when pitch detection is off by an octave.
    Only adds octave variants if they don't conflict with existing mappings.
    """
    expanded = dict(base_mapping)
    for pitch, hole in base_mapping.items():
        lower = pitch - 12
        if lower >= 0 and lower not in expanded:
            expanded[lower] = hole
        higher = pitch + 12
        if higher <= 127 and higher not in expanded:
            expanded[higher] = hole
    return expanded


def _expand_octaves_bends(base_bends: dict) -> dict:
    """Expand bend mapping ONE octave DOWN only.

    Only expands downward because:
    - Pitch detection often detects harmonics (higher octaves) of low notes
    - A bent note an octave HIGHER than the actual bend is not playable
    """
    expanded = dict(base_bends)
    for pitch, bend_info in base_bends.items():
        lower = pitch - 12
        if lower >= 0 and lower not in expanded:
            expanded[lower] = bend_info
    return expanded


# =============================================================================
# GENERATE ALL KEY MAPPINGS
# =============================================================================


def _generate_key_mapping(key: str) -> dict:
    """Generate the full MIDI mapping for a harmonica key."""
    offset = KEY_OFFSETS[key]
    transposed = _transpose_mapping(_C_HARMONICA_NOTES, offset)
    return _expand_octaves(transposed)


def _generate_bend_mapping(key: str) -> dict:
    """Generate the bend mapping for a harmonica key."""
    offset = KEY_OFFSETS[key]
    transposed = _transpose_bend_mapping(_C_HARMONICA_BENDS, offset)
    return _expand_octaves_bends(transposed)


# Generate all mappings
C_HARMONICA_MAPPING = _generate_key_mapping("C")
CS_HARMONICA_MAPPING = _generate_key_mapping("C#")
D_HARMONICA_MAPPING = _generate_key_mapping("D")
EB_HARMONICA_MAPPING = _generate_key_mapping("EB")
E_HARMONICA_MAPPING = _generate_key_mapping("E")
F_HARMONICA_MAPPING = _generate_key_mapping("F")
FS_HARMONICA_MAPPING = _generate_key_mapping("F#")
G_HARMONICA_MAPPING = _generate_key_mapping("G")
AB_HARMONICA_MAPPING = _generate_key_mapping("AB")
A_HARMONICA_MAPPING = _generate_key_mapping("A")
BB_HARMONICA_MAPPING = _generate_key_mapping("BB")
B_HARMONICA_MAPPING = _generate_key_mapping("B")

# Generate all bend mappings
C_HARMONICA_BENDS = _generate_bend_mapping("C")
CS_HARMONICA_BENDS = _generate_bend_mapping("C#")
D_HARMONICA_BENDS = _generate_bend_mapping("D")
EB_HARMONICA_BENDS = _generate_bend_mapping("EB")
E_HARMONICA_BENDS = _generate_bend_mapping("E")
F_HARMONICA_BENDS = _generate_bend_mapping("F")
FS_HARMONICA_BENDS = _generate_bend_mapping("F#")
G_HARMONICA_BENDS = _generate_bend_mapping("G")
AB_HARMONICA_BENDS = _generate_bend_mapping("AB")
A_HARMONICA_BENDS = _generate_bend_mapping("A")
BB_HARMONICA_BENDS = _generate_bend_mapping("BB")
B_HARMONICA_BENDS = _generate_bend_mapping("B")


# =============================================================================
# LOOKUP DICTIONARIES
# =============================================================================

HARMONICA_MAPPINGS = {
    "C": C_HARMONICA_MAPPING,
    "C#": CS_HARMONICA_MAPPING,
    "D": D_HARMONICA_MAPPING,
    "EB": EB_HARMONICA_MAPPING,
    "E": E_HARMONICA_MAPPING,
    "F": F_HARMONICA_MAPPING,
    "F#": FS_HARMONICA_MAPPING,
    "G": G_HARMONICA_MAPPING,
    "AB": AB_HARMONICA_MAPPING,
    "A": A_HARMONICA_MAPPING,
    "BB": BB_HARMONICA_MAPPING,
    "B": B_HARMONICA_MAPPING,
}

HARMONICA_BEND_MAPPINGS = {
    "C": C_HARMONICA_BENDS,
    "C#": CS_HARMONICA_BENDS,
    "D": D_HARMONICA_BENDS,
    "EB": EB_HARMONICA_BENDS,
    "E": E_HARMONICA_BENDS,
    "F": F_HARMONICA_BENDS,
    "F#": FS_HARMONICA_BENDS,
    "G": G_HARMONICA_BENDS,
    "AB": AB_HARMONICA_BENDS,
    "A": A_HARMONICA_BENDS,
    "BB": BB_HARMONICA_BENDS,
    "B": B_HARMONICA_BENDS,
}
