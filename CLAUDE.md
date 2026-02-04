# HarmonicaTabs Project - Claude Notes

## Project Overview
Generates animated harmonica tablature videos from input videos, tab files, and harmonica models. Creates visual animations that sync audio with harmonica tab notation.

## Development Notes
- Uses Poetry for dependency management
- Has pre-commit hooks configured
- MIDI files stored in `fixed_midis/` directory
- **Test Coverage**: 99% (738 tests passing)

---

## Active Development Branches

### `feature/auto-tab-generation`
**Purpose:** Generate .txt tab files from MIDI automatically

**Command:** `python cli.py generate-tabs TimeofYourLife_fixed.mid --key G`

**Status:** Complete - ready to merge

**Progress:**
- [x] Design tab file output format (pages, lines, chords)
- [x] Implement MIDI → hole number mapping using existing TabMapper
- [x] Add CLI command `generate-tabs`
- [x] Handle page breaks (auto or configurable notes per page)
- [x] Add 20 tests for TabGenerator
- [x] Chord detection (simultaneous notes → 56, -4-5)

**CLI Options:**
```bash
python cli.py generate-tabs MySong_fixed.mid --key G
python cli.py generate-tabs MySong_fixed.mid --key G --output CustomName.txt
python cli.py generate-tabs MySong_fixed.mid --key G --notes-per-line 5
python cli.py generate-tabs MySong_fixed.mid --key G --notes-per-page 20
```

**Use case:** Quick starting point - generates structure from MIDI, user fixes mistakes

---

### `feature/stem-splitting`
**Purpose:** Separate harmonica from guitar/background using Demucs AI

**Status:** Complete - ready to merge

**How it works:**
When running `python cli.py interactive MySong_KeyC_Stem.mp4`:
1. Workflow detects `_Stem` flag and asks "Run Demucs stem separation?"
2. If Yes → Runs Demucs 6-stem model → Auto-uses "other.mp3" (where harmonica ends up)
3. If No → Manual file selection from video-files/
4. Continues with MIDI generation from the selected audio

**CLI Command:** `python cli.py split-stems` - Standalone stem separation
```bash
python cli.py split-stems MySong.mp4                    # Separate into 6 stems
python cli.py split-stems MySong.mp4 --output-dir my_stems  # Custom output dir
python cli.py split-stems MySong.mp4 --stem vocals      # Highlight vocals instead of other
```

**Test Script:** `scripts/test_demucs.py` - Standalone script to test Demucs
```bash
python scripts/test_demucs.py --check-gpu           # Check GPU availability
python scripts/test_demucs.py video-files/MySong.mp4  # Run 6-stem separation
```

**Progress:**
- [x] Create standalone Demucs test script (scripts/test_demucs.py)
- [x] Test Demucs on sample files (pianoman worked well)
- [x] Implement StemSeparator class (utils/stem_separator.py)
- [x] Handle GPU/CPU fallback (CUDA > MPS > CPU)
- [x] Integrate with interactive workflow
- [x] Add 21 tests for stem separator
- [x] Add Demucs dependency to pyproject.toml
- [x] Add standalone CLI command `split-stems`

**Technical details:**
- Model: `htdemucs_6s` (6 stems: vocals, drums, bass, guitar, piano, other)
- Output: MP3 format (workaround for torchcodec compatibility)
- GPU: Auto-detects CUDA/MPS, falls back to CPU
- Harmonica typically ends up in "other" stem

**Use case:** One-stop workflow - no external tools needed for stem separation

---

### Archived Branches
| Branch | Merged To | Date | Summary |
|--------|-----------|------|---------|
| `feature/interactive-workflow` | `main` | 2026-01-21 | Interactive workflow, MIDI validation, parallel support, 3-note chords |

**Archived brainstorm files:** `archive/brainstorm_interactive-workflow.md`

---

## Context7 MCP Server - Library Documentation
**IMPORTANT**: Always use the context7 MCP server when working with external libraries.

### When to Use
- Need up-to-date API documentation (moviepy, numpy, matplotlib, basic_pitch, etc.)
- Working with unfamiliar library features
- Verifying correct usage patterns

### How to Use
1. Call `resolve-library-id` to get the Context7-compatible library ID
2. Call `get-library-docs` with the library ID and optional topic

**Key libraries**: moviepy, basic_pitch, matplotlib, numpy, PIL

## Technical Architecture

### Two-Phase Pipeline
```
Phase 1 (generate-midi): Video/Audio → MIDI Generation
├── AudioExtractor → WAV extraction
├── AudioProcessor → Mono + filter + noise reduction
├── basic_pitch → Raw MIDI (onset=0.4, frame=0.3)
└── Output: temp/*_generated.mid for manual editing

Phase 2 (create-video): Fixed MIDI → Harmonica Animation
├── MIDI Loading → Note events
├── TabMapper → Harmonica tabs (filtered by C_HARMONICA_MAPPING)
├── TabMatcher → Tab timing alignment
└── Animator → Final harmonica + tab videos
```

### Key Components
1. **MIDI Processing**: `harmonica_pipeline/midi_generator.py` - Spotify's basic_pitch AI model
2. **Tab Conversion**: `tab_converter/tab_mapper.py` - MIDI notes → harmonica hole numbers
3. **Animation**: `image_converter/animator.py` - Visual harmonica hole animations
4. **Tab Phrase**: `tab_phrase_animator/` - Page-by-page tab animations with note glow

### Harmonica Key Support
- **All 12 keys supported**: A, Ab, B, Bb, C, C#, D, E, Eb, F, F#, G
- **Mappings**: `tab_converter/consts.py` - MIDI pitch → harmonica holes for each key
- **Coordinates**: `image_converter/consts.py` - Hole coordinates for animation
- **Registry**: `harmonica_pipeline/harmonica_key_registry.py` - Central key configuration

## Current Workflow

### Simplified 2-Phase Workflow
```bash
# Phase 1: Video/Audio → MIDI (auto-naming, WAV extraction)
python cli.py generate-midi StandByMe_KeyA_Stem.wav
python cli.py generate-midi StandByMe_KeyA_Stem.wav --preset harmonica_strict --no-melodia-trick
python cli.py generate-midi PianoManFullVert_KeyC_Stem.wav --preset harmonica_strict --onset-threshold 0.25 --frame-threshold 0.18 --no-melodia-trick
python cli.py generate-midi PianoManFullVert_KeyC_Stem.wav --preset harmonica_strict --no-melodia-trick --minimum-note-length 150

# Fix MIDI in DAW → save as fixed_midis/MySong_fixed.mid

# Phase 2: WAV → Video (reuses extracted audio)
python cli.py create-video StandByMe_KeyA_Stem.MP4 StandByMe.txt --key A --only-full-tab-video
python cli.py validate-midi StandByMe_KeyA_Stem_fixed.mid StandByMe.txt --key A

python cli.py create-video BrokenWindowGarden.m4v BROKEN_WINDOW_C.txt --key C --only-full-tab-video
python cli.py create-video MySong.m4v MySong.txt --key G --only-harmonica
python cli.py create-video MySong.m4v MySong.txt --key Bb --only-full-tab-video
```

### CLI Options
```bash
# Key selection (all 12 harmonica keys)
--key [A|Ab|B|Bb|C|C#|D|E|Eb|F|F#|G]

# Selective generation
--only-tabs              # Only tab phrase animations
--only-harmonica         # Only harmonica animation
--only-full-tab-video    # Only full continuous tab video
--no-produce-tabs        # Skip all tab generation
```

### Interactive Workflow (NEW)
```bash
# Full guided workflow - select file from menu
python cli.py interactive

# Full guided workflow - specify file directly
python cli.py interactive theriver_KeyG_Stem.MP4

# Explicit tab file (if different name)
python cli.py interactive MySong_KeyG.mp4 CustomTabs.txt

# Auto-approve mode (for testing)
python cli.py interactive MySong_KeyG.mp4 --auto-approve

# With stem separation (manual) - prompts for stem file
python cli.py interactive MySong_KeyBb_Stem.mp4

# Filename encodes config: SongName_Key[X]_[Stem]_[FPS##].ext
python cli.py interactive MySong_KeyBb_Stem_FPS10.mp4

# Clean/reset existing session and start fresh
python cli.py interactive MySong_KeyG.mp4 --clean

# Skip to specific stage (when you already have MIDI/videos ready)
python cli.py interactive MySong_KeyG.mp4 --skip-to tabs           # Regenerate tab video only
python cli.py interactive MySong_KeyG.mp4 --skip-to harmonica      # Regenerate harmonica video
python cli.py interactive MySong_KeyG.mp4 --skip-to midi-fixing    # Have MIDI, need to fix/validate
python cli.py interactive MySong_KeyG.mp4 --skip-to tab-generation # Generate tabs from MIDI
python cli.py interactive MySong_KeyG.mp4 --skip-to finalize       # Just create ZIP/archive
```

**Skip-to Options:**
- `midi-fixing` - Already have MIDI, skip to fixing/validation step
- `tab-generation` - Generate tabs from MIDI (if no tab file exists)
- `harmonica` - Regenerate harmonica video (needs MIDI)
- `tabs` - Regenerate tab video only (needs MIDI)
- `finalize` - Just create ZIP and archive (needs existing videos)

**Stem Separation Flow** (when `_Stem` in filename):
1. Workflow detects `_Stem` flag and pauses
2. You separate stems offline using Demucs, iZotope RX, etc.
3. Save the best stem (e.g., `MySong_vocals.wav`) to `video-files/`
4. Enter the stem filename when prompted
5. MIDI is generated from that stem instead of the full mix

**Workflow Steps:**
1. Parse config from filename (key, stem flag, FPS)
2. Generate MIDI → pause for DAW editing → opens `fixed_midis/` folder
3. **Tab Generation** (optional) - If no tab file exists, offers to generate from MIDI
4. **Validate MIDI** (auto-runs, shows mismatches)
5. Select FPS (5-30, lower = faster render)
6. Generate harmonica video → opens `outputs/` → approval gate
7. Generate tab video → opens `outputs/` → approval gate
8. Finalize (ZIP outputs, archive to legacy/)

**Session Resume:** If interrupted, re-run same command to resume from last step.

### Validation Command
```bash
# Standalone MIDI validation
python cli.py validate-midi MySong_fixed.mid MySong.txt --key G
```

## File Outputs
```
outputs/
├── MySong_harmonica.mov       # Harmonica hole animation
├── MySong_full_tabs.mov       # Continuous page-by-page tab video
└── page1_tabs.mov, page2_tabs.mov, etc.  # Individual tab pages

sessions/
├── workflow.log               # Warnings/errors from libraries (MoviePy, TensorFlow, etc.)
└── MySong_session.json        # Session state for resume
```

**Log File**: Third-party library warnings (scikit-learn, TensorFlow, MoviePy, FFmpeg) are redirected to `sessions/workflow.log` to keep terminal output clean. Check this file for debugging.

## Video Optimization Plan (Future)

### Problem: Long Videos with Sparse Notes
For 2+ minute videos with few notes, current approach renders every frame:
- Harmonica: 15 FPS × 120s = 1,800 frames
- Tabs: 30 FPS × 120s = 3,600 frames

Most frames are identical (static harmonica/tabs between notes).

### Current Solution: FPS Selection ✅
Interactive workflow now asks user to select FPS before video generation:
- 5 FPS: Fastest render, minimal animation (sparse notes)
- 10 FPS: Fast render, smooth enough for most cases (Recommended)
- 15 FPS: Balanced quality and speed
- 20-30 FPS: Higher quality, slower render (dense notes)

### Future Optimization: Static Segment Compositing
Split video into segments for 70-90% render time reduction:
```
[static 0-15s] → [animated 15-16s] → [static 16-45s] → [animated 45-46s] → ...
```
- Static segments: Single frame ImageClip with duration (1 frame, not 450)
- Animated segments: Normal FuncAnimation for note transitions
- Concatenate with MoviePy

**Implementation locations:**
- Harmonica: `image_converter/animator.py` - `FuncAnimation` callback
- Tabs: `tab_phrase_animator/tab_phrase_animator.py` - `FuncAnimation` callback
- Key optimization: Replace frame-by-frame with segment-based rendering

## Known TODOs / Future Enhancements

### Stretch Tasks (Low Priority)
1. **TabMatcher Improvements** (`tab_phrase_animator/tab_matcher.py`)
   - Timing-proximity scoring, chord inversion support, better error messages

2. **MIDI Bend Detection** (`tab_converter/tab_mapper.py`)
   - Auto-detect pitch bends from MIDI events → set `is_bend=True`

3. **Performance Optimization**
   - Video generation speed, MIDI parallelization, caching

4. **Handle Overlapping MIDI Notes**
   - Detect and handle overlapping notes in MIDI files
   - Options: merge into chords, truncate earlier note, or warn user
   - Affects: `harmonica_pipeline/midi_processor.py`, `tab_converter/tab_mapper.py`

## Implemented Features

### MIDI Validation Tool ✅
- **CLI Command:** `python cli.py validate-midi MySong_fixed.mid MySong.txt --key G`
- **Interactive Workflow:** Automatically runs after MIDI fixing step
- Detects: extra notes, missing notes, unmappable notes
- Shows fix suggestions with MIDI note numbers and timestamps

## Planned Features (Not Implemented)

### Lower Priority

1. **Stem Splitting** - Separate harmonica from guitar/background using Demucs AI
   - Command: `python cli.py split-stems MySong.mp4 --output stems/`
   - Outputs: vocals.wav, drums.wav, bass.wav, other.wav
   - User picks best stem → `generate-midi stems/vocals.wav`

2. **Visual Gap Bug Fix** - Force gap between consecutive identical notes
   - Fix: `image_converter/animator.py:19-30` - remove overlap check, always create gap
   - Increase gap: 0.1s → 0.15s

3. **FPS Optimization** - Configurable FPS for tab/harmonica animations
   - CLI: `--tabs-fps 15 --harmonica-fps 15`
   - Default 15fps saves ~50% render time/file size

4. **Cleanup Individual Pages** - Optional deletion of page videos after compositor
   - CLI: `--no-keep-individual-pages`
   - Keeps only full video, deletes page1.mov, page2.mov, etc.

5. **Auto-Tab Generation** - Generate .txt files from MIDI automatically
   - Command: `python cli.py generate-tabs isntshelovelytwins_fixed.mid`
   - User edits .txt → `create-video MySong.wav MySong.txt`
   - Quick fix workflow for tab mistakes

6. **Better MIDI Libraries** - Benchmark alternatives to basic_pitch (experimental)
   - Test: Magenta mt3, crepe, pyin
   - Implement if >10% improvement found

## Quick Reference

**When implementing next feature:**
1. Check planned features list (order: Stem Split → Visual Gap → FPS → Cleanup → Auto-tabs → MIDI benchmark)
2. Follow implementation steps
3. Run tests
4. Commit with descriptive message

**Architecture locations:**
- MIDI mappings: `tab_converter/consts.py`
- Hole coordinates: `image_converter/consts.py`
- Key registry: `harmonica_pipeline/harmonica_key_registry.py`
- Pipeline configs: `harmonica_pipeline/video_creator_config.py`
