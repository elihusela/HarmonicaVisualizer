# HarmonicaTabs Project - Claude Notes

## Project Overview
Generates animated harmonica tablature videos from input videos, tab files, and harmonica models. Creates visual animations that sync audio with harmonica tab notation.

## Development Notes
- Uses Poetry for dependency management
- Has pre-commit hooks configured
- MIDI files stored in `fixed_midis/` directory
- **Test Coverage**: 99% (562 tests passing)

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
python cli.py generate-midi PianoManFullVert_KeyC_Stem.wav
python cli.py generate-midi PianoManFullVert_KeyC_Stem.wav --preset harmonica_strict --no-melodia-trick
python cli.py generate-midi PianoManFullVert_KeyC_Stem.wav --preset harmonica_strict --onset-threshold 0.25 --frame-threshold 0.18 --no-melodia-trick
python cli.py generate-midi PianoManFullVert_KeyC_Stem.wav --preset harmonica_strict --no-melodia-trick --minimum-note-length 150

# Fix MIDI in DAW → save as fixed_midis/MySong_fixed.mid

# Phase 2: WAV → Video (reuses extracted audio)
python cli.py create-video WonderfulWorldHori.MP4 WonderfulWorldHori.txt --key C --only-full-tab-video
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

## File Outputs
```
outputs/
├── MySong_harmonica.mov       # Harmonica hole animation
├── MySong_full_tabs.mov       # Continuous page-by-page tab video
└── page1_tabs.mov, page2_tabs.mov, etc.  # Individual tab pages
```

## Known TODOs / Future Enhancements

### Stretch Tasks (Low Priority)
1. **TabMatcher Improvements** (`tab_phrase_animator/tab_matcher.py`)
   - Timing-proximity scoring, chord inversion support, better error messages

2. **MIDI Bend Detection** (`tab_converter/tab_mapper.py`)
   - Auto-detect pitch bends from MIDI events → set `is_bend=True`

3. **Performance Optimization**
   - Video generation speed, MIDI parallelization, caching

## Planned Features (Not Implemented)

### High Priority (Next to Implement)

1. **MIDI Validation Tool** - Detect and report MIDI/tab file mismatches before video generation
   - Command: `python cli.py validate-midi MySong_fixed.mid MySong.txt --key G`
   - Features:
     - Compare MIDI note count vs tab file expected notes
     - Identify exact positions of mismatches (wrong notes, extra notes, missing notes)
     - Show detailed report with MIDI note numbers, hole numbers, and timestamps
     - Detect unmappable notes (notes not playable on specified harmonica key)
   - Output example:
     ```
     ✅ MIDI validation passed: 79/79 notes match

     OR

     ❌ MIDI validation failed:
        • Position 16: Extra note (hole 5, MIDI 76) at time 2739
        • Position 41: Wrong note (expected hole 4/MIDI 67, got MIDI 68)
        • Total: 80 MIDI notes, 79 expected from tab file

     Fix suggestions:
        - Delete MIDI 76 at position 16 (time 2739)
        - Change MIDI 68 to MIDI 67 at position 41 (time 5741)
     ```
   - Benefits:
     - Catch MIDI errors before running expensive video generation
     - Pinpoint exact locations of problems for quick DAW fixes
     - Prevent "-X MIDI entries unused" warnings during create-video
     - Save time by validating MIDI quality upfront

### Lower Priority

2. **Stem Splitting** - Separate harmonica from guitar/background using Demucs AI
   - Command: `python cli.py split-stems MySong.mp4 --output stems/`
   - Outputs: vocals.wav, drums.wav, bass.wav, other.wav
   - User picks best stem → `generate-midi stems/vocals.wav`

3. **Visual Gap Bug Fix** - Force gap between consecutive identical notes
   - Fix: `image_converter/animator.py:19-30` - remove overlap check, always create gap
   - Increase gap: 0.1s → 0.15s

4. **FPS Optimization** - Configurable FPS for tab/harmonica animations
   - CLI: `--tabs-fps 15 --harmonica-fps 15`
   - Default 15fps saves ~50% render time/file size

5. **Cleanup Individual Pages** - Optional deletion of page videos after compositor
   - CLI: `--no-keep-individual-pages`
   - Keeps only full video, deletes page1.mov, page2.mov, etc.

6. **Auto-Tab Generation** - Generate .txt files from MIDI automatically
   - Command: `python cli.py generate-tabs MySong.mid --output MySong.txt`
   - User edits .txt → `create-video MySong.wav MySong.txt`
   - Quick fix workflow for tab mistakes

7. **Better MIDI Libraries** - Benchmark alternatives to basic_pitch (experimental)
   - Test: Magenta mt3, crepe, pyin
   - Implement if >10% improvement found

## Quick Reference

**When implementing next feature:**
1. Check planned features list (order: MIDI Validation → Stem Split → Visual Gap → FPS → Cleanup → Auto-tabs → MIDI benchmark)
2. Follow implementation steps
3. Run tests
4. Commit with descriptive message

**Architecture locations:**
- MIDI mappings: `tab_converter/consts.py`
- Hole coordinates: `image_converter/consts.py`
- Key registry: `harmonica_pipeline/harmonica_key_registry.py`
- Pipeline configs: `harmonica_pipeline/video_creator_config.py`
