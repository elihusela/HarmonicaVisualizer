NOTE_ON_MSG = "note_on"
NOTE_OFF_MSG = "note_off"
SET_TEMPO_MSG = "set_tempo"


def _expand_octaves(base_mapping: dict) -> dict:
    """Expand a harmonica mapping to include notes one octave above and below.

    This allows MIDI notes that are an octave off to still map to the correct holes.
    Only adds octave variants if they don't conflict with existing base mappings.
    """
    expanded = dict(base_mapping)  # Start with base mappings (these take priority)

    for pitch, hole in base_mapping.items():
        # Add lower octave (-12 semitones) if valid MIDI and not already mapped
        lower = pitch - 12
        if lower >= 0 and lower not in expanded:
            expanded[lower] = hole
        # Add higher octave (+12 semitones) if valid MIDI and not already mapped
        higher = pitch + 12
        if higher <= 127 and higher not in expanded:
            expanded[higher] = hole

    return expanded


_C_HARMONICA_BASE = {
    60: 1,  # Blow 1
    62: -1,  # Draw 1
    64: 2,  # Blow 2
    # 67: -2,  # Draw 2
    67: 3,  # Blow 3
    71: -3,  # Draw 3
    72: 4,  # Blow 4
    74: -4,  # Draw 4
    76: 5,  # Blow 5
    77: -5,  # Draw 5
    79: 6,  # Blow 6
    81: -6,  # Draw 6
    84: 7,  # Blow 7
    83: -7,  # Draw 7
    88: 8,  # Blow 8
    86: -8,  # Draw 8
    91: 9,  # Blow 9
    89: -9,  # Draw 9
    96: 10,  # Blow 10
    93: -10,  # Draw 10
}
C_HARMONICA_MAPPING = _expand_octaves(_C_HARMONICA_BASE)

_G_HARMONICA_BASE = {
    55: 1,  # Blow 1 (G3)
    57: -1,  # Draw 1 (A3)
    59: 2,  # Blow 2 (B3)
    # 62: -2,  # Draw 2 (D4) - commented out due to collision with Blow 3
    62: 3,  # Blow 3 (D4)
    66: -3,  # Draw 3 (F#4)
    67: 4,  # Blow 4 (G4)
    69: -4,  # Draw 4 (A4)
    71: 5,  # Blow 5 (B4)
    72: -5,  # Draw 5 (C5)
    74: 6,  # Blow 6 (D5)
    76: -6,  # Draw 6 (E5)
    79: 7,  # Blow 7 (G5)
    78: -7,  # Draw 7 (F#5)
    83: 8,  # Blow 8 (B5)
    81: -8,  # Draw 8 (A5)
    86: 9,  # Blow 9 (D6)
    84: -9,  # Draw 9 (C6)
    91: 10,  # Blow 10 (G6)
    88: -10,  # Draw 10 (E6)
}
G_HARMONICA_MAPPING = _expand_octaves(_G_HARMONICA_BASE)

_BB_HARMONICA_BASE = {
    58: 1,  # Blow 1 (Bb3)
    60: -1,  # Draw 1 (C4)
    62: 2,  # Blow 2 (D4)
    # 65: -2,  # Draw 2 (F4) - commented out due to collision with Blow 3
    65: 3,  # Blow 3 (F4)
    69: -3,  # Draw 3 (A4)
    70: 4,  # Blow 4 (Bb4)
    72: -4,  # Draw 4 (C5)
    74: 5,  # Blow 5 (D5)
    75: -5,  # Draw 5 (Eb5)
    77: 6,  # Blow 6 (F5)
    79: -6,  # Draw 6 (G5)
    82: 7,  # Blow 7 (Bb5)
    81: -7,  # Draw 7 (A5)
    86: 8,  # Blow 8 (D6)
    84: -8,  # Draw 8 (C6)
    89: 9,  # Blow 9 (F6)
    87: -9,  # Draw 9 (Eb6)
    94: 10,  # Blow 10 (Bb6)
    91: -10,  # Draw 10 (G6)
}
BB_HARMONICA_MAPPING = _expand_octaves(_BB_HARMONICA_BASE)

_A_HARMONICA_BASE = {
    57: 1,  # Blow 1 (A3)
    59: -1,  # Draw 1 (B3)
    61: 2,  # Blow 2 (C#4)
    64: 3,  # Blow 3 (E4)
    68: -3,  # Draw 3 (Ab4)
    69: 4,  # Blow 4 (A4)
    71: -4,  # Draw 4 (B4)
    73: 5,  # Blow 5 (C#5)
    74: -5,  # Draw 5 (D5)
    76: 6,  # Blow 6 (E5)
    78: -6,  # Draw 6 (F#5)
    80: -7,  # Draw 7 (Ab5)
    81: 7,  # Blow 7 (A5)
    83: -8,  # Draw 8 (B5)
    85: 8,  # Blow 8 (C#6)
    86: -9,  # Draw 9 (D6)
    88: 9,  # Blow 9 (E6)
    90: -10,  # Draw 10 (F#6)
    93: 10,  # Blow 10 (A6)
}
A_HARMONICA_MAPPING = _expand_octaves(_A_HARMONICA_BASE)

_AB_HARMONICA_BASE = {
    56: 1,  # Blow 1 (Ab3)
    58: -1,  # Draw 1 (Bb3)
    60: 2,  # Blow 2 (C4)
    63: 3,  # Blow 3 (Eb4)
    67: -3,  # Draw 3 (G4)
    68: 4,  # Blow 4 (Ab4)
    70: -4,  # Draw 4 (Bb4)
    72: 5,  # Blow 5 (C5)
    73: -5,  # Draw 5 (C#5)
    75: 6,  # Blow 6 (Eb5)
    77: -6,  # Draw 6 (F5)
    79: -7,  # Draw 7 (G5)
    80: 7,  # Blow 7 (Ab5)
    82: -8,  # Draw 8 (Bb5)
    84: 8,  # Blow 8 (C6)
    85: -9,  # Draw 9 (C#6)
    87: 9,  # Blow 9 (Eb6)
    89: -10,  # Draw 10 (F6)
    92: 10,  # Blow 10 (Ab6)
}
AB_HARMONICA_MAPPING = _expand_octaves(_AB_HARMONICA_BASE)

_B_HARMONICA_BASE = {
    59: 1,  # Blow 1 (B3)
    61: -1,  # Draw 1 (C#4)
    63: 2,  # Blow 2 (Eb4)
    66: 3,  # Blow 3 (F#4)
    70: -3,  # Draw 3 (Bb4)
    71: 4,  # Blow 4 (B4)
    73: -4,  # Draw 4 (C#5)
    75: 5,  # Blow 5 (Eb5)
    76: -5,  # Draw 5 (E5)
    78: 6,  # Blow 6 (F#5)
    80: -6,  # Draw 6 (Ab5)
    82: -7,  # Draw 7 (Bb5)
    83: 7,  # Blow 7 (B5)
    85: -8,  # Draw 8 (C#6)
    87: 8,  # Blow 8 (Eb6)
    88: -9,  # Draw 9 (E6)
    90: 9,  # Blow 9 (F#6)
    92: -10,  # Draw 10 (Ab6)
    95: 10,  # Blow 10 (B6)
}
B_HARMONICA_MAPPING = _expand_octaves(_B_HARMONICA_BASE)

_CS_HARMONICA_BASE = {
    49: 1,  # Blow 1 (C#3)
    51: -1,  # Draw 1 (Eb3)
    53: 2,  # Blow 2 (F3)
    56: 3,  # Blow 3 (Ab3)
    60: -3,  # Draw 3 (C4)
    61: 4,  # Blow 4 (C#4)
    63: -4,  # Draw 4 (Eb4)
    65: 5,  # Blow 5 (F4)
    66: -5,  # Draw 5 (F#4)
    68: 6,  # Blow 6 (Ab4)
    70: -6,  # Draw 6 (Bb4)
    72: -7,  # Draw 7 (C5)
    73: 7,  # Blow 7 (C#5)
    75: -8,  # Draw 8 (Eb5)
    77: 8,  # Blow 8 (F5)
    78: -9,  # Draw 9 (F#5)
    80: 9,  # Blow 9 (Ab5)
    82: -10,  # Draw 10 (Bb5)
    85: 10,  # Blow 10 (C#6)
}
CS_HARMONICA_MAPPING = _expand_octaves(_CS_HARMONICA_BASE)

_D_HARMONICA_BASE = {
    50: 1,  # Blow 1 (D3)
    52: -1,  # Draw 1 (E3)
    54: 2,  # Blow 2 (F#3)
    57: 3,  # Blow 3 (A3)
    61: -3,  # Draw 3 (C#4)
    62: 4,  # Blow 4 (D4)
    64: -4,  # Draw 4 (E4)
    66: 5,  # Blow 5 (F#4)
    67: -5,  # Draw 5 (G4)
    69: 6,  # Blow 6 (A4)
    71: -6,  # Draw 6 (B4)
    73: -7,  # Draw 7 (C#5)
    74: 7,  # Blow 7 (D5)
    76: -8,  # Draw 8 (E5)
    78: 8,  # Blow 8 (F#5)
    79: -9,  # Draw 9 (G5)
    81: 9,  # Blow 9 (A5)
    83: -10,  # Draw 10 (B5)
    86: 10,  # Blow 10 (D6)
}
D_HARMONICA_MAPPING = _expand_octaves(_D_HARMONICA_BASE)

_E_HARMONICA_BASE = {
    52: 1,  # Blow 1 (E3)
    54: -1,  # Draw 1 (F#3)
    56: 2,  # Blow 2 (Ab3)
    59: 3,  # Blow 3 (B3)
    63: -3,  # Draw 3 (Eb4)
    64: 4,  # Blow 4 (E4)
    66: -4,  # Draw 4 (F#4)
    68: 5,  # Blow 5 (Ab4)
    69: -5,  # Draw 5 (A4)
    71: 6,  # Blow 6 (B4)
    73: -6,  # Draw 6 (C#5)
    75: -7,  # Draw 7 (Eb5)
    76: 7,  # Blow 7 (E5)
    78: -8,  # Draw 8 (F#5)
    80: 8,  # Blow 8 (Ab5)
    81: -9,  # Draw 9 (A5)
    83: 9,  # Blow 9 (B5)
    85: -10,  # Draw 10 (C#6)
    88: 10,  # Blow 10 (E6)
}
E_HARMONICA_MAPPING = _expand_octaves(_E_HARMONICA_BASE)

_EB_HARMONICA_BASE = {
    51: 1,  # Blow 1 (Eb3)
    53: -1,  # Draw 1 (F3)
    55: 2,  # Blow 2 (G3)
    58: 3,  # Blow 3 (Bb3)
    62: -3,  # Draw 3 (D4)
    63: 4,  # Blow 4 (Eb4)
    65: -4,  # Draw 4 (F4)
    67: 5,  # Blow 5 (G4)
    68: -5,  # Draw 5 (Ab4)
    70: 6,  # Blow 6 (Bb4)
    72: -6,  # Draw 6 (C5)
    74: -7,  # Draw 7 (D5)
    75: 7,  # Blow 7 (Eb5)
    77: -8,  # Draw 8 (F5)
    79: 8,  # Blow 8 (G5)
    80: -9,  # Draw 9 (Ab5)
    82: 9,  # Blow 9 (Bb5)
    84: -10,  # Draw 10 (C6)
    87: 10,  # Blow 10 (Eb6)
}
EB_HARMONICA_MAPPING = _expand_octaves(_EB_HARMONICA_BASE)

_F_HARMONICA_BASE = {
    53: 1,  # Blow 1 (F3)
    55: -1,  # Draw 1 (G3)
    57: 2,  # Blow 2 (A3)
    60: 3,  # Blow 3 (C4)
    64: -3,  # Draw 3 (E4)
    65: 4,  # Blow 4 (F4)
    67: -4,  # Draw 4 (G4)
    69: 5,  # Blow 5 (A4)
    70: -5,  # Draw 5 (Bb4)
    72: 6,  # Blow 6 (C5)
    74: -6,  # Draw 6 (D5)
    76: -7,  # Draw 7 (E5)
    77: 7,  # Blow 7 (F5)
    79: -8,  # Draw 8 (G5)
    81: 8,  # Blow 8 (A5)
    82: -9,  # Draw 9 (Bb5)
    84: 9,  # Blow 9 (C6)
    86: -10,  # Draw 10 (D6)
    89: 10,  # Blow 10 (F6)
}
F_HARMONICA_MAPPING = _expand_octaves(_F_HARMONICA_BASE)

_FS_HARMONICA_BASE = {
    54: 1,  # Blow 1 (F#3)
    56: -1,  # Draw 1 (Ab3)
    58: 2,  # Blow 2 (Bb3)
    61: 3,  # Blow 3 (C#4)
    65: -3,  # Draw 3 (F4)
    66: 4,  # Blow 4 (F#4)
    68: -4,  # Draw 4 (Ab4)
    70: 5,  # Blow 5 (Bb4)
    71: -5,  # Draw 5 (B4)
    73: 6,  # Blow 6 (C#5)
    75: -6,  # Draw 6 (Eb5)
    77: -7,  # Draw 7 (F5)
    78: 7,  # Blow 7 (F#5)
    80: -8,  # Draw 8 (Ab5)
    82: 8,  # Blow 8 (Bb5)
    83: -9,  # Draw 9 (B5)
    85: 9,  # Blow 9 (C#6)
    87: -10,  # Draw 10 (Eb6)
    90: 10,  # Blow 10 (F#6)
}
FS_HARMONICA_MAPPING = _expand_octaves(_FS_HARMONICA_BASE)
