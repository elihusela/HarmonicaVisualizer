NOTE_ON_MSG = "note_on"
NOTE_OFF_MSG = "note_off"
SET_TEMPO_MSG = "set_tempo"
C_HARMONICA_MAPPING = {
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

G_HARMONICA_MAPPING = {
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
