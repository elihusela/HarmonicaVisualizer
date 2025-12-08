# HarmonicaTabs Project - Claude Notes

## Project Overview
Generates animated harmonica tablature videos from input videos, tab files, and harmonica models. Creates visual animations that sync audio with harmonica tab notation.

## Current Workflow Issues
- **Manual MIDI intervention**: Code stops, requires manual MIDI fixing in Ableton, then restart
- **Cumbersome arguments**: Each new video requires many command-line arguments
- **Slow video generation**: Performance could be improved
- **No tests**: Makes refactoring risky and scary

## Main Goals
### 1. Split the Pipeline into Two Phases
- **Phase 1**: Generate MIDI file, then stop
- **Phase 2**: Take fixed MIDI file and generate final video
- **Testing mode**: Option to connect both phases for automated testing

### 2. Improve Developer Experience
- Simplify command-line interface
- Add configuration files or better argument handling
- Speed up video generation process

### 3. Add Testing
- Create test suite to enable confident refactoring
- Test individual components and full pipeline

### 4. Refactor Codebase
- Extract pipeline logic from main.py into proper classes
- Improve code organization and separation of concerns
- Better error handling and validation
- More maintainable and extensible architecture

## Current Technical Debt
- Single monolithic pipeline in `main.py`
- Hard-coded file paths and arguments
- No separation between MIDI generation and video creation
- Missing error handling and validation

## Next Steps
1. Analyze current pipeline structure
2. Design two-phase architecture
3. Add basic testing framework
4. Refactor main.py into separate phases
5. Improve CLI interface

## Development Notes
- Uses Poetry for dependency management
- Has pre-commit hooks configured
- Current entry point: `main.py` with 6+ arguments
- MIDI files stored in `fixed_midis/` directory

## Context7 MCP Server - Library Documentation
**IMPORTANT**: Always use the context7 MCP server when working with external libraries or when documentation is needed.

### When to Use Context7
- Need up-to-date API documentation for any library (moviepy, numpy, matplotlib, etc.)
- Working with unfamiliar library features or methods
- Need code examples for specific library functionality
- Debugging library-specific issues
- Verifying correct usage patterns before implementation

### How to Use
1. **First**: Call `resolve-library-id` to get the Context7-compatible library ID
2. **Then**: Call `get-library-docs` with the library ID and optional topic

### Examples
```python
# When working with moviepy video editing
# 1. Resolve: mcp__context7__resolve-library-id(libraryName="moviepy")
# 2. Get docs: mcp__context7__get-library-docs(context7CompatibleLibraryID="/Zulko/moviepy", topic="concatenate videos")

# When working with basic_pitch for MIDI generation
# 1. Resolve: mcp__context7__resolve-library-id(libraryName="basic-pitch")
# 2. Get docs: mcp__context7__get-library-docs(context7CompatibleLibraryID="/spotify/basic-pitch", topic="thresholds")

# When working with matplotlib for figure rendering
# 1. Resolve: mcp__context7__resolve-library-id(libraryName="matplotlib")
# 2. Get docs: mcp__context7__get-library-docs(context7CompatibleLibraryID="/matplotlib/matplotlib", topic="transparent background")
```

### Guidelines
- Always fetch docs BEFORE implementing new library features
- Use specific topics to get targeted documentation
- Verify API usage against latest docs (knowledge cutoff: Jan 2025)
- Especially important for: moviepy, basic_pitch, matplotlib, numpy, PIL

## Technical Architecture & Components

### Harmonica Note Mappings
- **Location**: `tab_converter/consts.py` → `C_HARMONICA_MAPPING`
- **MIDI Range**: Notes 60-96 (C4 to C7) mapped to harmonica holes 1-10
- **Format**: Positive = blow notes, Negative = draw notes
- **Visual Mapping**: `image_converter/consts.py` → hole coordinates for animation
- **Coverage**: 19 mapped notes, some holes like Draw 2 commented out

### Two-Phase Pipeline Architecture
```
Phase 1 (generate-midi): Video/Audio → MIDI Generation
├── AudioExtractor → WAV extraction
├── basic_pitch → Raw MIDI (all notes)
└── Output: temp/*_generated.mid for manual editing

Phase 2 (create-video): Fixed MIDI → Harmonica Animation
├── MIDI Loading → Note events
├── TabMapper → Harmonica tabs (filtered by C_HARMONICA_MAPPING)
├── TabMatcher → Tab timing alignment
└── Animator → Final harmonica video
```

### Key Processing Components
1. **MIDI Processing**: `harmonica_pipeline/midi_generator.py`
   - Uses Spotify's basic_pitch AI model
   - Thresholds: onset=0.2, frame=0.2
   - Now supports WAV files directly

2. **Tab Conversion**: `tab_converter/tab_mapper.py`
   - Core mapping logic using `C_HARMONICA_MAPPING`
   - Filters out unmapped MIDI notes silently
   - Converts MIDI notes to harmonica hole numbers

3. **Animation**: `image_converter/animator.py`
   - Creates visual harmonica hole animations
   - Uses coordinate mappings for precise positioning

### Current Filtering Mechanisms
- **Mapping-based**: Only notes in `C_HARMONICA_MAPPING` processed
- **Pitch bend removal**: All MIDI pitch bends stripped
- **Range filtering**: Implicit through mapping dictionary (60-96)
- **Confidence thresholds**: basic_pitch onset/frame filtering

### Data Flow
```
Video/Audio → AudioExtractor → basic_pitch → Raw MIDI →
Manual Edit → Fixed MIDI → TabMapper (C_HARMONICA_MAPPING filter) →
TabMatcher → Animator → Final Video
```

### Optimal MIDI Filtering Integration Points
1. **TabMapper.note_events_to_tabs()** (Recommended)
   - Location: `tab_converter/tab_mapper.py:18`
   - Current: `if event.pitch in self._mapping:`
   - Enhancement: Add range filtering before mapping check

2. **MIDI Loading Functions**
   - Add filtering during note event parsing
   - Configurable per harmonica model

## Recent Improvements
- ✅ WAV file support added to generate-midi command
- ✅ Two-phase CLI architecture implemented
- ✅ Separated MIDI generation from video creation
- ✅ **3-step audio processing flow implemented**
- ✅ **OOP architecture with AudioProcessor class**
- ✅ **Enhanced AudioExtractor with ffmpeg fallback**
- ✅ **Simplified workflow (auto-naming, WAV reuse)**
- ✅ HarmonicaTabs Claude Code agent created (harmonica-dev subagent)
- ✅ **Tab phrase animation bug fixed** (multiple pages now generated)
- ✅ **Selective generation options** (--only-tabs, --only-harmonica)
- ✅ **Text-based structure implementation** (.txt file page/line organization preserved)
- ✅ **Chronological MIDI timing** (left-to-right note lighting order fixed)
- ✅ **TabEntry constructor fixes** (confidence parameter added)
- ✅ **All 12 harmonica keys supported** (--key CLI flag with A, Ab, B, Bb, C, C#, D, E, Eb, F, F#, G)

## Latest Architecture (Sept 2024)

### 🎵 **Simplified 2-Phase Workflow:**
```bash
# Phase 1: Video/Audio → MIDI (auto-naming, WAV extraction)
python cli.py generate-midi LOD_C.wav

# Fix MIDI in DAW → save as fixed_midis/MySong_fixed.mid

# Phase 2: WAV → Video (reuses extracted audio)
python cli.py create-video LOD_C.m4v LMD.txt --key C --only-full-tab-vide

# With different harmonica keys:
python cli.py create-video AMEDI_Bb.m4v AMEDI.txt --key Bb
python cli.py create-video song.wav song.txt --key F#   # F-sharp harmonica
python cli.py create-video song.wav song.txt --key D    # D harmonica

# Selective Generation Options:
python cli.py create-video MySong.wav MySong.txt --only-tabs        # Only tab phrase animations
python cli.py create-video MySong.wav MySong.txt --only-harmonica   # Only harmonica animation
```

### 🏗️ **OOP Audio Processing Architecture:**
```
utils/
├── audio_extractor.py     # VideoExtractor → WAV (MoviePy + ffmpeg fallback)
├── audio_processor.py     # AudioProcessor class (kaki.sh logic)
└── audio_processor.sh     # Original kaki.sh (documentation)
```

### 🎛️ **Audio Processing Pipeline (kaki.sh integration):**
1. **Video → WAV**: Extract with fallback (complex iPhone videos supported)
2. **WAV → Processed**: Mono + 200-5000Hz filter + noise reduction + loudnorm
3. **Processed → MIDI**: basic_pitch with optimized thresholds (0.4/0.3)
4. **WAV Reuse**: Auto-saved to video-files/ for Phase 2

### 📊 **Quality Results:**
- **Before processing**: 236 note events (noisy)
- **After kaki.sh processing**: 113 note events (52% noise reduction)
- **iPhone 16 Pro Max support**: HEVC, multiple audio streams handled

### 🎯 **Key OOP Components:**
- **MidiGenerator**: 3-step pipeline orchestration
- **AudioExtractor**: Robust video→audio with fallbacks
- **AudioProcessor**: Configurable kaki.sh logic with presets
- **VideoCreator**: Phase 2 video generation with selective creation support

### 🎭 **Selective Generation Options (Latest Feature):**
New CLI options for targeted video creation:

```bash
# Create both animations (default behavior)
python cli.py create-video PMV.wav PMV.txt

# Create only tab phrase animations (skip harmonica)
python cli.py create-video PMV.m4v PMV.txt --only-tabs

# Create only harmonica animation (skip tab phrases)
python cli.py create-video PMV.m4v PMV.txt --only-harmonica

# Skip all tab generation (original option)
python cli.py create-video MySong.wav MySong.txt --no-produce-tabs

# Error: Cannot use both selective options
python cli.py create-video MySong.wav MySong.txt --only-tabs --only-harmonica
# ❌ Error: Cannot specify both --only-tabs and --only-harmonica
```

**Use Cases:**
- **Development**: Test individual components separately
- **Performance**: Skip slow animations when iterating
- **Debugging**: Isolate issues to specific animation types
- **Workflow**: Generate harmonica first, then tabs after review

---

## 🎯 NEXT FEATURE: Full Tab Video Compositor

### **Feature Overview**
Create a **single continuous video** where tab pages appear/disappear in sync with the audio, with individual notes lighting up precisely as they play. This stitches together all tab pages into one video for easy Final Cut Pro compositing.

### **Current State**
- ✅ TabPhraseAnimator generates **separate** page videos (`page1_tabs.mov`, `page2_tabs.mov`, etc.)
- ✅ Each page video has notes lighting up in sync with timing
- ✅ Works great, but requires manual stitching in editing software

### **What We're Building**
**Output:** `MySong_full_tabs.mov` - One continuous video file where:
1. **Page-by-page display** (NOT scrolling)
2. **Pages appear/disappear** at exact times based on note timing
3. **Notes light up individually** within each visible page
4. **Transparent background** (for compositing on original video)
5. **Synced to audio duration** (precise timing)

### **Visual Behavior**
```
Timeline Example (song.wav = 30 seconds):
[0.0-0.1s]   Blank (transparent)
[0.1-10.2s]  Page 1 visible, notes glow as they play (first note at 0.1s, last at 10.1s)
[10.2-10.3s] Blank transition
[10.3-20.1s] Page 2 visible, notes glow as they play
[20.1-20.2s] Blank transition
[20.2-30.0s] Page 3 visible, notes glow as they play
```

### **Page Timing Logic**
Each page visibility window calculated from note timings:
- `page_start = first_note_time - 0.1s` (small padding before)
- `page_end = last_note_time + 0.1s` (small padding after)
- **Instant cut** between pages (no fade)
- **Blank (transparent) frames** during gaps

### **Requirements (Clarified)**
✅ **Don't touch harmonica animation** - stays separate for manual Final Cut compositing
✅ **Same rendering style** - reuse existing tab page rendering
✅ **Transparent background** - for video overlay
✅ **Same note glow effect** - as current TabPhraseAnimator
✅ **Page always visible** - notes glow individually, page stays on screen
✅ **Instant transitions** - no fade, just cut between pages

### **Architecture Decision**

#### **New Module:** `tab_phrase_animator/full_tab_video_compositor.py`

**Class:** `FullTabVideoCompositor`

**Approach: Reuse Existing Page Videos** (Option A - Recommended)
- Leverage already-generated page videos from `TabPhraseAnimator`
- Read `page1_tabs.mov`, `page2_tabs.mov`, etc.
- Calculate precise timing windows from note data
- Stitch videos with blank (transparent) frames in between
- Faster iteration, reuses existing work

**Alternative: Generate Fresh** (Option B - Cleaner but slower)
- Similar to TabPhraseAnimator but render all pages into ONE video
- More control but duplicate work

### **CLI Integration**

```bash
# Default: Generate individual pages + full video
python cli.py create-video BDAY.mov BDAY.txt

# Skip full video (only individual pages)
python cli.py create-video song.wav song.txt --no-full-tab-video

# Only full video (skip individual pages)
python cli.py create-video HOG_G.m4v HOG_G.txt --key G --only-full-tab-video

# Existing flags still work
python cli.py create-video song.wav song.txt --only-tabs  # No harmonica, yes tabs
```

### **File Outputs**
```
outputs/
├── MySong_harmonica.mov       (unchanged - harmonica hole animation)
├── MySong_tabs.mov            (existing - individual tab pages stitched)
└── MySong_full_tabs.mov       (NEW - continuous page-by-page video)
```

### **Implementation Steps**

#### **Phase 1: Core Compositor Class**
1. Create `tab_phrase_animator/full_tab_video_compositor.py`
2. Implement `FullTabVideoCompositor` class:
   - Constructor: takes page videos, note timing data, audio duration
   - `calculate_page_windows()` - determine when each page appears/disappears
   - `create_blank_frame()` - generate transparent frame
   - `stitch_videos()` - concatenate page videos with blank frames
   - `generate()` - main entry point, outputs full video

#### **Phase 2: VideoCreator Integration**
1. Add flag to `VideoCreatorConfig`: `produce_full_tab_video` (default: `True`)
2. Modify `VideoCreator.create()`:
   - After generating individual pages
   - If `produce_full_tab_video` enabled
   - Call `FullTabVideoCompositor.generate()`
3. Pass through all necessary data (page videos, timing, audio length)

#### **Phase 3: CLI Flags**
1. Add `--no-full-tab-video` flag to `cli.py`
2. Add `--only-full-tab-video` flag to `cli.py`
3. Update help text and documentation

#### **Phase 4: Testing**
1. Create `tests/tab_phrase_animator/test_full_tab_video_compositor.py`
2. Test timing calculations
3. Test video stitching logic
4. Integration test with real page videos

### **Technical Considerations**

**Video Library:** Use `moviepy` (already in dependencies)
```python
from moviepy.editor import VideoFileClip, concatenate_videoclips, ColorClip

# Read existing page videos
page1 = VideoFileClip("page1_tabs.mov")
page2 = VideoFileClip("page2_tabs.mov")

# Create blank (transparent) frames
blank = ColorClip(size=(1920, 1080), color=(0,0,0,0), duration=0.1)

# Concatenate with timing
final = concatenate_videoclips([blank, page1, blank, page2, ...])
```

**Timing Data Source:** Use existing `TabMatcher` output or MIDI timing

**Precision:** Use MIDI timing data (already accurate to milliseconds)

### **Success Criteria**
✅ Single video file generated
✅ Pages appear/disappear at correct times
✅ Notes light up in sync with audio
✅ Transparent background maintained
✅ Total video duration matches audio duration
✅ Instant cuts between pages (no fade)
✅ CLI flags work as expected
✅ Tests passing

### **Next Session: Start Here** 🚀
1. Create `tab_phrase_animator/full_tab_video_compositor.py`
2. Implement `FullTabVideoCompositor` class skeleton
3. Write timing calculation logic
4. Test with one song's page videos

---

## 🎹 Harmonica Key Selection (--key flag) ✅ COMPLETED

### **Overview**
All 12 harmonica keys are fully supported via the `--key` CLI flag. The system automatically selects the correct:
- Harmonica model image (PNG)
- MIDI note mapping (pitch → hole number)
- Hole coordinate mapping (for animation)

### **Supported Keys (12 total)**
| Key | Model Image | Notes |
|-----|-------------|-------|
| A   | A.png       | 19 MIDI notes |
| Ab  | Ab.png      | 19 MIDI notes |
| B   | b.png       | 19 MIDI notes |
| Bb  | Bb.png      | 19 MIDI notes |
| C   | c.png | 19 MIDI notes (default) |
| C#  | c#.png      | 19 MIDI notes |
| D   | D.png       | 19 MIDI notes |
| E   | E.png       | 19 MIDI notes |
| Eb  | Eb.png      | 19 MIDI notes |
| F   | F.png       | 19 MIDI notes |
| F#  | F#.png      | 19 MIDI notes |
| G   | G.png       | 19 MIDI notes |

### **CLI Usage**
```bash
# Default: Use C harmonica
python cli.py create-video song.wav song.txt

# Specify a key (case-insensitive)
python cli.py create-video song.wav song.txt --key G
python cli.py create-video song.wav song.txt --key Bb
python cli.py create-video song.wav song.txt --key F#
python cli.py create-video song.wav song.txt --key Ab

# Works with full pipeline too
python cli.py full song.mp4 song.txt --key D

# Key aliases work (F# = FS, C# = CS, etc.)
python cli.py create-video song.wav song.txt --key f#   # Same as --key FS
```

### **Key Features**
- ✅ **Case-insensitive**: `C`, `c`, `G`, `g` all work
- ✅ **Common aliases**: `F#` → FS, `C#` → CS, `Bb` → BB, `Ab` → AB, `Eb` → EB
- ✅ **Auto-selection**: Model image, MIDI mapping, and hole coordinates selected automatically
- ✅ **Validation**: Clear error messages for unsupported keys
- ✅ **Override option**: Can still use `--harmonica-model` for custom images

### **Architecture**
```
harmonica_pipeline/
├── harmonica_key_registry.py   # Central registry for all keys
│   ├── HarmonicaKeyConfig      # Dataclass for key configuration
│   ├── HARMONICA_KEY_REGISTRY  # Dict mapping key → config
│   ├── get_harmonica_config()  # Lookup with validation + aliases
│   └── get_supported_keys()    # List all available keys

tab_converter/
└── consts.py                   # MIDI mappings for all 12 keys
    ├── C_HARMONICA_MAPPING
    ├── G_HARMONICA_MAPPING
    ├── BB_HARMONICA_MAPPING
    ├── ... (all 12 keys)

image_converter/
└── consts.py                   # Hole coordinate mappings
    ├── C_NEW_MODEL_HOLE_MAPPING
    ├── G_MODEL_HOLE_MAPPING
    ├── STANDARD_MODEL_HOLE_MAPPING
    └── ... (aliases for all keys)
```

### **Error Handling**
```bash
# Invalid key shows helpful error
python cli.py create-video song.wav song.txt --key X
# ❌ Error: Unsupported harmonica key: X. Supported keys: A, AB, B, BB, C, CS, D, E, EB, F, FS, G
```

---

## Next Session Tasks - Phase 2 Refactoring (OUTDATED)

### 1. Phase 2 Code Review & Simplification
- **VideoCreator class**: Review for OOP improvements
- **TabMapper/TabMatcher**: Evaluate for refactoring opportunities
- **Animation pipeline**: Optimize performance and readability
- **Error handling**: Add robust error handling throughout Phase 2

### 2. Testing & Validation
- **Unit tests**: Create tests for AudioProcessor, MidiGenerator
- **Integration tests**: End-to-end pipeline testing
- **Performance testing**: Benchmark video generation speed
- **Edge case handling**: Complex videos, missing files, corrupted data

### 3. Code Quality Improvements
- **Type hints**: Add comprehensive type annotations
- **Documentation**: Improve docstrings and inline comments
- **Logging**: Replace print statements with proper logging
- **Configuration**: Externalize hardcoded values

### 4. Commit & Version Control
- **Git commit**: Save all Phase 1 improvements
- **Branch strategy**: Consider feature branches for Phase 2 work
- **Changelog**: Document breaking changes and new features

## Testing Strategy - Bottom-Up Implementation Plan

### 🧪 **Current Status: Phase 3 COMPLETE! ✅ 502/502 Tests Passing**
- ✅ **Phase 1 DONE**: Data models tests (TabEntry, Tabs, NoteEvent) - 17 tests
- ✅ **Phase 2 DONE**: Core business logic - 120 tests
  - ✅ TabMapper (MIDI→Tab conversion) - 24 tests
  - ✅ MidiGenerator (Audio→MIDI pipeline) - 26 tests
  - ✅ AudioProcessor (Audio processing workflow) - 23 tests
  - ✅ TabTextParser (.txt file parsing) - 53 tests ✨ All edge cases fixed!
- ✅ **Phase 3 DONE**: Complex Integration & Components - 365 tests
  - ✅ VideoCreator (text-based structure) - 40 tests
  - ✅ AudioExtractor (audio extraction) - 54 tests
  - ✅ Utils (directory management, MIDI) - 33 tests
  - ✅ TabPhraseAnimator - 36 tests
  - ✅ TabMatcher (tab timing alignment) - 28 tests
  - ✅ Animator (animation system) - 39 tests
  - ✅ ColorScheme - 18 tests
  - ✅ Consts - 14 tests
  - ✅ FigureFactory - 29 tests
  - ✅ HarmonicaLayout - 35 tests
  - ✅ VideoProcessor - 33 tests
- 🚧 **NEXT: Final Testing Phase** 🚧

### 📁 **Test Structure (1:1 Source Mapping)**
```
Source Structure                Test Structure                        Status
─────────────────              ──────────────────                    ──────
tab_converter/                  tests/tab_converter/
├── models.py          →        ├── test_models.py                    ✅ DONE (17 tests)
├── tab_mapper.py      →        ├── test_tab_mapper.py                ✅ DONE (24 tests)
├── consts.py          →        └── conftest.py                       ✅ DONE

harmonica_pipeline/             tests/harmonica_pipeline/
├── video_creator.py   →        ├── test_video_creator.py             ✅ DONE (40 tests)
├── midi_generator.py  →        ├── test_midi_generator.py            ✅ DONE (26 tests)
└── midi_processor.py  →        └── conftest.py                       ✅ DONE

utils/                          tests/utils/
├── audio_extractor.py →        ├── test_audio_extractor.py           ✅ DONE (54 tests)
├── audio_processor.py →        ├── test_audio_processor.py           ✅ DONE (23 tests)
└── utils.py          →         ├── test_utils.py                     ✅ DONE (33 tests)
                                └── conftest.py                       ✅ DONE

tab_phrase_animator/            tests/tab_phrase_animator/
├── tab_text_parser.py →        ├── test_tab_text_parser.py           ✅ DONE (53 tests)
├── tab_phrase_animator.py →    ├── test_tab_phrase_animator.py       ✅ DONE (36 tests)
└── tab_matcher.py     →        ├── test_tab_matcher.py               ✅ DONE (28 tests)
                                └── conftest.py                       ✅ DONE

image_converter/                tests/image_converter/
├── animator.py        →        ├── test_animator.py                  ✅ DONE (39 tests)
├── color_scheme.py    →        ├── test_color_scheme.py              ✅ DONE (18 tests)
├── consts.py          →        ├── test_consts.py                    ✅ DONE (14 tests)
├── figure_factory.py  →        ├── test_figure_factory.py            ✅ DONE (29 tests)
├── harmonica_layout.py →       ├── test_harmonica_layout.py          ✅ DONE (35 tests)
├── video_processor.py →        ├── test_video_processor.py           ✅ DONE (33 tests)
└── ...                →        └── conftest.py                       ✅ DONE

./                              tests/
├── cli.py             →        ├── test_cli.py                       📝 TODO
└── ...                →        ├── conftest.py                       ✅ DONE
                                └── test_integration.py                📝 TODO
```

### 🎯 **Final Testing Phase - Remaining Work**

#### **Phase 4: Coverage Analysis & CLI Testing (2-3 commits)**
1. **test_cli.py** - Command-line interface testing (generate-midi, create-video commands)
2. **test_integration.py** - End-to-end workflow validation
3. **Coverage analysis** - Run pytest-cov to identify untested code paths
4. **Fill coverage gaps** - Add tests for missed functions/edge cases

#### **Phase 5: Code Quality & Cleanup (2-3 commits)**
5. **TODO review** - Scan codebase for TODO comments, prioritize fixes
6. **Performance testing** - Benchmark critical paths and memory usage
7. **Documentation** - Update docstrings, add inline comments where needed
8. **Type hints** - Ensure comprehensive type annotations

### 🚀 **Updated Commit Strategy**
```bash
# Phase 4 - Final Testing:
1. test: Add CLI integration tests (generate-midi, create-video commands)
2. test: Add end-to-end integration test suite
3. test: Achieve 90%+ code coverage with gap-filling tests

# Phase 5 - Quality & Cleanup:
4. fix: Address high-priority TODOs discovered during testing
5. perf: Add performance benchmarking and optimization
6. docs: Update documentation, docstrings, and type hints
7. docs: Create GitHub issues for remaining TODOs
```

### 📊 **Current Testing Metrics** ✅ COMPLETE!
- **Total Tests**: 562 tests (ALL PASSING ✅)
- **Coverage**: **99%** (all major components tested)
- **Modules Tested**: 17/17 source modules (cli.py ✅, midi_processor.py ✅)
- **Test Files**: 17 test modules across 5 packages
- **Achievement**: 99% coverage achieved! 🎉

### ✅ **Completed Testing Phase**
1. ✅ **Coverage analysis** - 99% achieved
2. ✅ **test_cli.py** - 45 tests, 99% coverage
3. ✅ **test_midi_processor.py** - 15 tests, 100% coverage
4. ✅ **TODO review** - Documented in stretch tasks below
5. ✅ **Test isolation fixes** - matplotlib backend + early imports

### 🎨 **Conftest Architecture Strategy** ✅
- **Global fixtures**: Core data structures, common utilities
- **Module fixtures**: Specific to each source module in their conftest.py
- **Hierarchical inheritance**: Module conftest inherits global automatically
- **DRY principle**: Shared fixtures prevent duplication across test files

## 🚀 Stretch Tasks / Future Enhancements

### Integration Testing (Optional)
**Priority:** Low
**Status:** Not required - unit/component tests provide 99% coverage

**Potential test_integration.py coverage:**
- End-to-end: Video → MIDI → Fixed MIDI → Final Video
- Full pipeline workflow validation
- Real file I/O with sample data
- Performance benchmarking

**Why it's optional:**
- Current unit tests thoroughly cover all components
- Component integration is tested via existing tests
- Would add ~50+ tests but minimal coverage gain
- Better ROI on feature development vs. integration tests

### Codebase TODOs (Documented)

#### 1. TabMatcher Algorithm Improvements
**Location:** `tab_phrase_animator/tab_matcher.py` (lines 30-35, 150-154, 161)
**Priority:** Medium
**Status:** Experimental feature working, marked for future enhancement

**Current Limitations:**
- Simple first-match strategy
- No timing proximity scoring
- No chord inversion support
- Basic error handling

**Suggested Improvements:**
- Implement timing-proximity scoring algorithm
- Support for different time signatures
- Grace note and ornament handling
- More robust chord matching
- Better error messages with match statistics

**When to implement:** If users report tab matching accuracy issues

#### 2. MIDI Bend Detection
**Location:** `tab_converter/tab_mapper.py` (line 113)
**Priority:** Low
**Status:** Feature request, not critical

**Description:**
Currently, bend notation only supported in `.txt` files. Future enhancement
could detect pitch bends from MIDI pitch bend events and automatically set
`is_bend=True` for bent notes.

**Implementation Notes:**
- Analyze MIDI pitch bend messages
- Correlate with note events
- Infrastructure already exists (`is_bend` field in `TabEntry`)
- Would enhance automation but not essential for workflow

**When to implement:** User feature request or when adding advanced MIDI analysis

#### 3. Performance Optimization
**Priority:** Low
**Status:** Not critical, current performance acceptable

**Potential Optimizations:**
- Video generation speed improvements
- MIDI processing parallelization
- Caching strategies for repeated operations
- Memory usage profiling and optimization

**When to implement:** If users report performance issues with long videos

---

## 🎯 NEXT FEATURES - Performance & Auto-Tab Generation

### **Implementation Order (USER REQUESTED - Updated Priority):**
1. 🔲 **Stem Splitting** - Separate harmonica from guitar/background (Demucs) - HIGH PRIORITY
2. 🔲 **Visual Gap Bug Fix** - Force gap between consecutive identical notes (~5 min fix)
3. 🔲 **FPS Optimization** - Reduce tab/harmonica FPS to 15 (50% speed/size improvement)
4. 🔲 **Cleanup Individual Pages** - Add flag to delete page videos after compositor
5. 🔲 **Auto-Tab Generation** - Generate .txt from MIDI automatically (with quick-fix capability)
6. 🔲 **Better MIDI Libraries** - Benchmark alternatives to basic_pitch (experimental - LOW PRIORITY)

---

### **Feature 1: Stem Splitting - Separate Harmonica from Background (DO FIRST)**

#### **Goal:**
Reduce rendering time and file sizes by ~50% using lower FPS for tab/harmonica animations.

#### **What to Do:**
1. **Add CLI flags** to `cli.py`:
   ```bash
   python cli.py create-video song.wav song.txt --tabs-fps 15 --harmonica-fps 15
   ```
   - `--tabs-fps`: FPS for tab phrase animations (default: 15, previously hardcoded 30)
   - `--harmonica-fps`: FPS for harmonica animation (default: 15, previously hardcoded 15)

2. **Modify `VideoCreatorConfig`** (`harmonica_pipeline/video_creator_config.py`):
   - Add fields: `tabs_fps: int = 15` and `harmonica_fps: int = 15`
   - Pass to animators

3. **Update `VideoCreator`** (`harmonica_pipeline/video_creator.py`):
   - Pass `config.harmonica_fps` to `animator.create_animation(fps=...)`
   - Pass `config.tabs_fps` to `tab_phrase_animator.create_animations(fps=...)`

4. **Test:**
   - Generate video with default FPS (15)
   - Generate video with `--tabs-fps 30` (backwards compat)
   - Verify 15fps looks good, renders faster

#### **Files to Modify:**
- `cli.py` - Add `--tabs-fps` and `--harmonica-fps` arguments
- `harmonica_pipeline/video_creator_config.py` - Add fps fields
- `harmonica_pipeline/video_creator.py` - Pass fps to animators

#### **Success Criteria:**
✅ CLI accepts fps flags
✅ Videos render with specified FPS
✅ 15fps default saves ~50% time/size
✅ All tests pass

---

### **Feature 3: FPS Optimization (DO THIRD)**

#### **Goal:**
Save disk space by optionally deleting individual page videos after full compositor runs.

#### **What to Do:**
1. **Add CLI flag** to `cli.py`:
   ```bash
   python cli.py create-video song.wav song.txt --no-keep-individual-pages
   ```
   - Generates full video, then deletes `page1.mov`, `page2.mov`, etc.
   - Only keeps `MySong_full_tabs.mov`

2. **Modify `VideoCreatorConfig`**:
   - Add field: `keep_individual_pages: bool = True` (default keeps them)

3. **Update `VideoCreator._create_tab_animations()`**:
   - Already has cleanup logic for `--only-full-tab-video` (lines 527-534)
   - Rename/extend to handle `--no-keep-individual-pages`

4. **Test:**
   - Run with flag, verify individual pages deleted
   - Run without flag, verify pages kept
   - Verify full video still correct

#### **Files to Modify:**
- `cli.py` - Add `--no-keep-individual-pages` argument
- `harmonica_pipeline/video_creator_config.py` - Add `keep_individual_pages` field
- `harmonica_pipeline/video_creator.py` - Use existing cleanup logic

#### **Success Criteria:**
✅ CLI accepts flag
✅ Individual pages deleted when flag set
✅ Individual pages kept when flag not set
✅ Full video unaffected
✅ All tests pass

---

### **Feature 4: Cleanup Individual Pages (DO FOURTH)**

#### **Goal:**
Auto-generate tab `.txt` files from MIDI, with easy manual correction workflow.

#### **Workflow:**
```bash
# Option A: Two-step (user can edit .txt between steps)
python cli.py generate-tabs MySong.mid --output MySong.txt
# User edits MySong.txt if needed (QUICK FIXES!)
python cli.py create-video MySong.wav MySong.txt

# Option B: One-shot (auto-generates, saves .txt, uses it)
python cli.py create-video MySong.wav MySong.mid --auto-tabs
# Creates MySong_auto.txt automatically
```

#### **What to Do:**

**Step 1: Create TabTextGenerator class**
1. **New file:** `tab_converter/tab_text_generator.py`
2. **Class:** `TabTextGenerator`
3. **Input:** `List[TabEntry]` (from MIDI)
4. **Output:** Formatted `.txt` string (same format as current .txt files)

**Logic:**
- **Page breaks:** Timing gap >2s = new page
- **Line breaks:** ~8-12 notes per line, max 4-6 lines per page
- **Chord detection:** Notes within 50ms = single chord
- **Format:** Match existing .txt format exactly (backwards compatible)

**Example Output:**
```
Page 1
-45 -4 5 6 -6
6 -5 5 -4 -45'
6 7 -7 7 -8

Page 2
8 -8 8 7 -7
7 6 -6 6 5
```

**Step 2: Add CLI commands**
1. **New command:** `generate-tabs` in `cli.py`
   ```bash
   python cli.py generate-tabs MySong.mid --output MySong.txt
   ```
2. **New flag:** `--auto-tabs` to `create-video` command
   ```bash
   python cli.py create-video MySong.wav MySong.mid --auto-tabs
   ```

**Step 3: Integration**
- `generate-tabs` command:
  1. Load MIDI → `MidiProcessor.load_note_events()`
  2. Convert to tabs → `TabMapper.note_events_to_tabs()`
  3. Generate text → `TabTextGenerator.generate(tabs)`
  4. Save to file

- `create-video --auto-tabs`:
  1. Generate .txt file (as above)
  2. Use existing flow with generated .txt

**Step 4: Testing**
- Generate .txt from various MIDIs
- Verify format matches existing .txt parser
- Test quick fixes (edit .txt, regenerate video)
- Ensure backwards compatibility

#### **Files to Create/Modify:**
- **NEW:** `tab_converter/tab_text_generator.py` - TabTextGenerator class
- **NEW:** `tests/tab_converter/test_tab_text_generator.py` - Tests
- **MODIFY:** `cli.py` - Add `generate-tabs` command and `--auto-tabs` flag
- **MODIFY:** `harmonica_pipeline/video_creator.py` - Handle MIDI input with auto-tabs

#### **Success Criteria:**
✅ `generate-tabs` command works
✅ Generated .txt matches existing format
✅ `--auto-tabs` flag creates video from MIDI
✅ User can edit .txt for quick fixes
✅ Existing .txt workflow unchanged
✅ All tests pass

---

### **Quick Reference for Claude:**

**When user says "implement the next planned feature":**
1. Check which features are marked 🔲 (not done)
2. Implement in order: FPS → Cleanup → Auto-tabs
3. Follow the "What to Do" steps precisely
4. Mark feature ✅ when complete
5. Run tests, commit

**When user says "I want to fix tab mistakes quickly":**
- This is the **auto-tabs feature (#3)**
- Solution: Generate .txt file, user edits it, re-run video creation
- Easy workflow: `generate-tabs → edit .txt → create-video`

---

### **Feature 5: Auto-Tab Generation (DO FIFTH)**

#### **Goal:**
Isolate harmonica audio from guitar/background instruments using AI source separation for cleaner MIDI generation.

#### **Library: Demucs (Meta AI)**
- State-of-the-art audio source separation
- Splits into: vocals, drums, bass, other
- Harmonica typically in "vocals" or "other" stem
- Quality over speed (OK for <1min recordings)

#### **Workflow:**
```bash
# Step 1: Split stems (separate command)
python cli.py split-stems MySong.mp4 --output stems/
# Creates: stems/vocals.wav, stems/drums.wav, stems/bass.wav, stems/other.wav
# User sees: "✅ Created 4 stems in stems/ - listen and pick best one"

# Step 2: User manually listens to each stem, picks best (e.g., vocals.wav)

# Step 3: Generate MIDI from chosen stem
python cli.py generate-midi stems/vocals.wav
# Rest of workflow unchanged
```

#### **What to Do:**

**Step 1: Install and test Demucs**
1. Add dependency: `demucs` to `pyproject.toml`
2. Test on sample harmonica+guitar recording
3. Verify output quality manually

**Step 2: Create StemSplitter class**
1. **New file:** `utils/stem_splitter.py`
2. **Class:** `StemSplitter`
3. **Input:** Audio/video file path
4. **Output:** 4 WAV files (vocals, drums, bass, other)

**Core logic:**
```python
import demucs.api

class StemSplitter:
    def split(self, input_path: str, output_dir: str) -> dict:
        # Extract audio if video
        # Run Demucs separation
        # Save 4 stems to output_dir
        # Return dict: {"vocals": "path", "drums": "path", ...}
```

**Step 3: Add CLI command**
1. New command: `split-stems` in `cli.py`
   ```bash
   python cli.py split-stems MySong.mp4 --output stems/
   ```
2. Arguments:
   - `input`: Video/audio file
   - `--output`: Output directory (default: `stems/`)
   - Optional: `--model htdemucs` (Demucs model variant)

**Step 4: Integration**
- Works as standalone command (NOT integrated into generate-midi)
- User workflow: `split-stems → listen → pick best → generate-midi`
- Clear user guidance printed after splitting

**Step 5: Testing**
1. Manual test: harmonica+guitar recording
2. Verify all 4 stems created correctly
3. Check processing time (<1min for 30s audio)
4. Quality check: is harmonica isolated?

#### **Files to Create/Modify:**
- **NEW:** `utils/stem_splitter.py` - StemSplitter class
- **NEW:** `tests/utils/test_stem_splitter.py` - Tests
- **MODIFY:** `cli.py` - Add `split-stems` command
- **MODIFY:** `pyproject.toml` - Add demucs dependency

#### **Success Criteria:**
✅ `split-stems` command works
✅ Creates 4 clean WAV files
✅ Processing time reasonable (<2min for 1min audio)
✅ Harmonica isolated from guitar in output stems
✅ Clear user instructions printed
✅ Tests passing

#### **Example Output:**
```
🎵 Splitting stems from MySong.mp4...
⏱️  Processing with Demucs (this may take 30-60 seconds)...
✅ Created 4 stems in stems/:
   - vocals.wav (likely has harmonica)
   - drums.wav
   - bass.wav
   - other.wav

👂 Listen to each stem and pick the best one
💡 Then run: python cli.py generate-midi stems/vocals.wav
```

---

### **Feature 6: Better MIDI Libraries - Benchmark Alternatives (DO SIXTH)**

#### **Goal:**
Research and benchmark alternative audio-to-MIDI libraries to potentially improve note accuracy vs basic_pitch.

#### **Status:** Experimental - may not yield improvement

#### **Libraries to Test:**
1. **Magenta mt3** (Google) - Multi-track transcription, state-of-the-art
2. **crepe** - Monophonic pitch tracking (good for single instruments)
3. **pyin** - Probabilistic YIN algorithm (lightweight)

#### **What to Do:**

**Step 1: Create benchmark framework**
1. **New file:** `tests/experiments/benchmark_midi_libraries.py`
2. Prepare 3-5 test audio files with known ground truth tabs
3. Run all libraries on same samples
4. Compare outputs to ground truth

**Metrics:**
- Note accuracy (precision/recall vs ground truth)
- Timing precision (how close to actual note timing)
- False positive rate
- Processing time

**Step 2: Test each library**
```python
# Benchmark script structure
def test_library(library_name, audio_path, ground_truth_tabs):
    # Run library
    midi_output = library.transcribe(audio_path)

    # Compare to ground truth
    precision = calculate_precision(midi_output, ground_truth_tabs)
    recall = calculate_recall(midi_output, ground_truth_tabs)

    # Return metrics
    return {
        "precision": precision,
        "recall": recall,
        "f1_score": f1,
        "processing_time": time
    }
```

**Step 3: Analyze results**
- Create comparison table
- If any library shows >10% improvement: implement it
- If no clear winner: stick with basic_pitch

**Step 4: Implementation (only if better library found)**
- Add new library to MidiGenerator as option
- CLI flag: `--midi-engine [basic_pitch|mt3|crepe]`
- Default stays basic_pitch

#### **Files to Create:**
- **NEW:** `tests/experiments/benchmark_midi_libraries.py`
- **NEW:** `tests/experiments/test_samples/` - Ground truth audio + tabs
- **MODIFY:** `harmonica_pipeline/midi_generator.py` (only if better library found)

#### **Success Criteria:**
✅ Benchmark framework runs on all libraries
✅ Clear metrics comparison table generated
✅ Decision made: switch library or keep basic_pitch
✅ If switch: new library integrated with tests passing

#### **Decision Point:**
- **If no library >10% better:** Document findings, keep basic_pitch
- **If library significantly better:** Implement as new default or optional flag

---

### **Quick Reference for Claude:**

**When user says "implement the next planned feature":**
1. Check which features are marked 🔲 (not done)
2. Implement in order: FPS → Cleanup → Auto-tabs → Stem-split → MIDI-benchmark
3. Follow the "What to Do" steps precisely
4. Mark feature ✅ when complete
5. Run tests, commit

---

## 🐛 BUG FIXES / IMPROVEMENTS

### **Bugfix: Force Visual Gap Between Consecutive Identical Notes**

#### **Problem:**
Currently, harmonica squares stay lit continuously for consecutive identical notes (e.g., two "4" holes played back-to-back), making it hard to see individual note attacks. User must manually edit MIDI to add gaps.

#### **Current Behavior** (`image_converter/animator.py:19-30`)
```python
def adjust_consecutive_identical_notes(
    flat_entries: List[TabEntry], gap: float = 0.1
) -> List[TabEntry]:
    for i in range(len(flat_entries) - 1):
        current = flat_entries[i]
        next_entry = flat_entries[i + 1]

        if current.tab == next_entry.tab:
            end_time = current.time + current.duration
            if end_time >= next_entry.time:  # ❌ ONLY creates gap if overlapping
                current.duration = max(0, next_entry.time - current.time - gap)
    return flat_entries
```

**Issue:** Gap only created if notes **overlap**. If notes are back-to-back (touching but not overlapping), no gap is created → square stays lit continuously.

**Example:**
```
Note 1: time=4.5, duration=0.5 (ends at 5.0)
Note 2: time=5.0, duration=0.5 (starts at 5.0)
Result: No gap → square stays lit from 4.5 to 5.5
Desired: Gap → square blinks off briefly between notes
```

#### **Solution:**
Always create a visual gap for consecutive identical notes, regardless of overlap.

#### **What to Do:**

**Step 1: Remove overlap check**
```python
def adjust_consecutive_identical_notes(
    flat_entries: List[TabEntry], gap: float = 0.15  # Increased from 0.1
) -> List[TabEntry]:
    for i in range(len(flat_entries) - 1):
        current = flat_entries[i]
        next_entry = flat_entries[i + 1]

        if current.tab == next_entry.tab:
            # ✅ ALWAYS create gap (removed overlap check)
            current.duration = max(0, next_entry.time - current.time - gap)
    return flat_entries
```

**Changes:**
1. Line 28: Remove `if end_time >= next_entry.time:` check
2. Line 29: Unindent to always execute
3. Line 20: Increase default gap from `0.1` → `0.15` (more visible)

**Step 2: Test**
1. Use MIDI with consecutive identical notes (no gaps)
2. Generate harmonica video
3. Verify squares now blink/disappear between same notes

**Step 3: Optional - Make gap configurable**
If user wants control over gap size:
```python
# In VideoCreatorConfig
visual_note_gap: float = 0.15  # Configurable

# CLI
python cli.py create-video song.wav song.txt --visual-gap 0.2
```

#### **Files to Modify:**
- `image_converter/animator.py` - Lines 19-30 (adjust_consecutive_identical_notes function)

#### **Success Criteria:**
✅ Consecutive identical notes show visual gap
✅ User no longer needs to manually edit MIDI for clarity
✅ Default gap (0.15s) is visible but not too jarring
✅ All tests pass

#### **Edge Cases:**
- ⚠️ If notes are very close (< gap), duration becomes 0 → OK (max(0, ...))
- ⚠️ Different notes (e.g., 4 → 5) → no gap needed (correct)
- ⚠️ Same note with existing gap → gap stays same (correct)

---

### **Quick Reference for Claude:**

**When user says "fix the consecutive notes bug":**
1. Open `image_converter/animator.py`
2. Go to line 28
3. Remove the `if end_time >= next_entry.time:` check
4. Unindent line 29
5. Change `gap: float = 0.1` to `gap: float = 0.15`
6. Test with MIDI file that has consecutive identical notes
7. Commit: "fix: Force visual gap between consecutive identical notes"
