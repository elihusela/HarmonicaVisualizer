# Usage Guide

## Interactive Workflow (Recommended)

The guided workflow handles the full pipeline with prompts and session resume:

```bash
# Start workflow - select file from menu
python cli.py interactive

# Start with specific file
python cli.py interactive MySong_KeyG.mp4

# Specify tab file explicitly
python cli.py interactive MySong_KeyG.mp4 CustomTabs.txt

# Reset and start fresh
python cli.py interactive MySong_KeyG.mp4 --clean

# Skip to a specific stage
python cli.py interactive MySong_KeyG.mp4 --skip-to tabs
python cli.py interactive MySong_KeyG.mp4 --skip-to harmonica
python cli.py interactive MySong_KeyG.mp4 --skip-to midi-fixing
python cli.py interactive MySong_KeyG.mp4 --skip-to finalize
```

### Filename Convention

Encode settings in the filename: `SongName_Key[X]_[Stem]_[FPS##].ext`

| Part | Example | Meaning |
|------|---------|---------|
| Key | `_KeyG` | Use G harmonica |
| Stem | `_Stem` | Pause for stem separation |
| FPS | `_FPS10` | Render at 10 FPS |

Examples:
- `Layla_KeyC.mp4` → C harmonica
- `StandByMe_KeyA_Stem.wav` → A harmonica, will prompt for stem file
- `River_KeyG_FPS5.mp4` → G harmonica, 5 FPS render

### Workflow Steps

1. **Parse config** from filename
2. **Generate MIDI** → pause for DAW editing
3. **Validate MIDI** against tab file
4. **Select FPS** (5-30, lower = faster)
5. **Generate harmonica video** → approval gate
6. **Generate tab video** → approval gate
7. **Finalize** (ZIP, archive)

Session auto-saves. If interrupted, re-run to resume.

---

## Manual Commands

### Phase 1: Generate MIDI

```bash
# Basic
python cli.py generate-midi MySong.wav

# With tuning for more notes
python cli.py generate-midi MySong.wav \
  --onset-threshold 0.25 \
  --frame-threshold 0.18

# With preset
python cli.py generate-midi MySong.wav --preset harmonica_strict

# Filter short notes
python cli.py generate-midi MySong.wav --minimum-note-length 150

# Disable melodia (helps with chords)
python cli.py generate-midi MySong.wav --no-melodia-trick
```

**Output:** `fixed_midis/MySong_fixed.mid`

Edit in DAW, then save in place.

### Phase 2: Create Video

```bash
# Basic
python cli.py create-video MySong.mp4 MySong.txt --key G

# Only harmonica animation
python cli.py create-video MySong.mp4 MySong.txt --key G --only-harmonica

# Only tab video
python cli.py create-video MySong.mp4 MySong.txt --key G --only-full-tab-video

# Fix MIDI overlaps automatically
python cli.py create-video MySong.mp4 MySong.txt --key G --fix-overlaps

# Custom chord threshold (ms)
python cli.py create-video MySong.mp4 MySong.txt --key G \
  --fix-overlaps --chord-threshold 100
```

**Output:** `outputs/MySong_harmonica.mov`, `outputs/MySong_full_tabs.mov`

### Validate MIDI

Check MIDI matches tab file before video generation:

```bash
python cli.py validate-midi MySong_fixed.mid MySong.txt --key G
```

### Generate Tabs from MIDI

Create tab file from MIDI (if you don't have one):

```bash
python cli.py generate-tabs MySong_fixed.mid --key G
```

**Output:** `tab-files/MySong.txt`

---

## CLI Options Reference

### Harmonica Keys

```bash
--key [A|Ab|B|Bb|C|C#|D|E|Eb|F|F#|G]
```

### Video Generation

| Flag | Effect |
|------|--------|
| `--only-tabs` | Only tab phrase animations |
| `--only-harmonica` | Only harmonica animation |
| `--only-full-tab-video` | Only continuous tab video |
| `--no-produce-tabs` | Skip all tab generation |
| `--fix-overlaps` | Auto-fix overlapping notes |
| `--chord-threshold N` | Chord detection threshold (ms) |
| `--tab-page-buffer N` | Buffer time around notes (seconds) |

### MIDI Generation

| Flag | Default | Effect |
|------|---------|--------|
| `--onset-threshold` | 0.4 | Lower = catch softer note starts |
| `--frame-threshold` | 0.3 | Lower = catch quieter sustained notes |
| `--minimum-note-length` | 127 | Filter notes shorter than N ms |
| `--preset` | none | `harmonica_strict` for clean output |
| `--no-melodia-trick` | off | Better chord detection |

---

## File Locations

| Directory | Contents |
|-----------|----------|
| `video-files/` | Input videos and audio files |
| `tab-files/` | Tab notation text files |
| `fixed_midis/` | Edited MIDI files |
| `outputs/` | Generated videos |
| `sessions/` | Workflow state and logs |
| `harmonica-models/` | Harmonica images per key |
| `temp/` | Working files (auto-cleaned) |

---

## Output Files

```
outputs/
├── MySong_harmonica.mov     # Harmonica hole animation
├── MySong_full_tabs.mov     # Continuous tab video
└── MySong_outputs.zip       # Archive of both (from interactive)

sessions/
├── MySong_session.json      # Workflow state for resume
└── workflow.log             # Library warnings (FFmpeg, TensorFlow, etc.)
```

---

## Stem Separation

For cleaner MIDI from mixed audio:

1. Name file with `_Stem`: `MySong_KeyG_Stem.mp4`
2. Run interactive workflow
3. When prompted, separate stems externally (Demucs, iZotope RX)
4. Save stem to `video-files/` (e.g., `MySong_vocals.wav`)
5. Enter stem filename when prompted

Or use CLI directly:
```bash
python cli.py split-stems MySong.wav
# Output: stems/MySong_vocals.wav, stems/MySong_drums.wav, etc.
```
