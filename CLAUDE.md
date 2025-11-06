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

## Latest Architecture (Sept 2024)

### 🎵 **Simplified 2-Phase Workflow:**
```bash
# Phase 1: Video/Audio → MIDI (auto-naming, WAV extraction)
python cli.py generate-midi BLCKBRD.m4v

# Fix MIDI in DAW → save as fixed_midis/MySong_fixed.mid

# Phase 2: WAV → Video (reuses extracted audio)
python cli.py create-video BLCKBRD.m4v BLCKBRD.txt --only-tabs

# Selective Generation Options (NEW):
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
python cli.py create-video BLCKBRD.m4v BLCKBRD.txt --only-full-tab-video

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

## 🎹 NEXT FEATURE: Configurable Harmonica Key

### **Feature Overview**
Add CLI argument to specify harmonica key (C, D, G, etc.), automatically selecting the correct harmonica model image and MIDI mapping for that key. This replaces hardcoded key selection with flexible runtime configuration.

### **Current State**
- ✅ G harmonica model and mapping exist (G_HARMONICA_MAPPING, G_MODEL_HOLE_MAPPING)
- ✅ C harmonica model and mapping exist (C_HARMONICA_MAPPING, C_NEW_MODEL_HOLE_MAPPING)
- ❌ Key is hardcoded in VideoCreator (currently using G)
- ❌ No CLI argument to select key
- ❌ No registry/mapping system for keys

### **What We're Building**
Add `--key` argument to CLI commands that:
1. Accepts single letter (C, D, G, etc.)
2. Defaults to C (standard harmonica)
3. Automatically selects correct harmonica model image
4. Automatically selects correct MIDI mapping
5. Validates key is supported (error if mapping doesn't exist)

### **CLI Usage**
```bash
# Default: Use C harmonica (existing behavior after reverting G commit)
python cli.py create-video song.wav song.txt

# Explicit C harmonica
python cli.py create-video song.wav song.txt --key C

# Use G harmonica
python cli.py create-video song.wav song.txt --key G

# Use D harmonica (future)
python cli.py create-video song.wav song.txt --key D

# Works with all commands
python cli.py generate-midi song.mov --key G
python cli.py full song.mov song.txt --key D
```

### **Implementation Architecture**

#### **1. Key Registry System**
Create centralized registry mapping keys to their resources:

**Location:** `harmonica_pipeline/harmonica_key_registry.py`
```python
from dataclasses import dataclass
from typing import Dict

@dataclass
class HarmonicaKeyConfig:
    """Configuration for a specific harmonica key."""
    key: str  # "C", "G", "D", etc.
    model_image: str  # Path to PNG file
    midi_mapping: Dict[int, int]  # MIDI note -> harmonica hole
    hole_mapping: Dict[int, Dict]  # Hole -> coordinates

# Registry of supported keys
HARMONICA_KEY_REGISTRY: Dict[str, HarmonicaKeyConfig] = {
    "C": HarmonicaKeyConfig(
        key="C",
        model_image="CNewModel.png",
        midi_mapping=C_HARMONICA_MAPPING,
        hole_mapping=C_NEW_MODEL_HOLE_MAPPING,
    ),
    "G": HarmonicaKeyConfig(
        key="G",
        model_image="harmonica_4_G.png",
        midi_mapping=G_HARMONICA_MAPPING,
        hole_mapping=G_MODEL_HOLE_MAPPING,
    ),
    # Future: Add D, A, etc.
}

def get_harmonica_config(key: str) -> HarmonicaKeyConfig:
    """Get configuration for harmonica key, with validation."""
    key = key.upper()
    if key not in HARMONICA_KEY_REGISTRY:
        supported = ", ".join(HARMONICA_KEY_REGISTRY.keys())
        raise ValueError(f"Unsupported harmonica key: {key}. Supported: {supported}")
    return HARMONICA_KEY_REGISTRY[key]
```

#### **2. VideoCreatorConfig Update**
Add `harmonica_key` field:

**Location:** `harmonica_pipeline/video_creator_config.py`
```python
@dataclass
class VideoCreatorConfig:
    # ... existing fields ...
    harmonica_key: str = "C"  # Default to C harmonica

    def __post_init__(self):
        # Validate key and get config
        from harmonica_pipeline.harmonica_key_registry import get_harmonica_config
        self.key_config = get_harmonica_config(self.harmonica_key)

        # Override harmonica_path if not explicitly set
        if self.harmonica_path == "default":
            self.harmonica_path = f"harmonica-models/{self.key_config.model_image}"
```

#### **3. VideoCreator Update**
Use key config instead of hardcoded mappings:

**Location:** `harmonica_pipeline/video_creator.py`
```python
class VideoCreator:
    def __init__(self, config: VideoCreatorConfig):
        # Get key configuration
        key_config = config.key_config

        # Use key-specific mappings
        self.tab_mapper = TabMapper(key_config.midi_mapping, TEMP_DIR)

        # Use key-specific hole mapping
        harmonica_layout = HarmonicaLayout(
            config.harmonica_path, key_config.hole_mapping
        )
```

#### **4. CLI Integration**

**Location:** `cli.py`
```python
# Add to video_parser
video_parser.add_argument(
    "--key",
    type=str,
    default="C",
    help="Harmonica key (C, G, D, etc.). Default: C",
)

# Add to full_parser
full_parser.add_argument(
    "--key",
    type=str,
    default="C",
    help="Harmonica key (C, G, D, etc.). Default: C",
)

# Update create_video_phase signature
def create_video_phase(
    video: str,
    tabs: str,
    harmonica_model: Optional[str] = None,
    harmonica_key: str = "C",  # NEW
    # ... other params ...
):
    # Pass key to config
    config = VideoCreatorConfig(
        # ... existing params ...
        harmonica_key=harmonica_key,
    )
```

### **Migration Strategy**
1. **Add registry** - Create centralized key registry
2. **Update config** - Add harmonica_key field with validation
3. **Update VideoCreator** - Use key config instead of hardcoded imports
4. **Add CLI args** - Add --key to all commands
5. **Update tests** - Test key validation and selection
6. **Revert G commit** - Change default back to C
7. **Documentation** - Update README with --key usage

### **Validation & Error Handling**
```python
# Invalid key
python cli.py create-video song.wav song.txt --key Z
# ❌ Error: Unsupported harmonica key: Z. Supported: C, G

# Case insensitive
python cli.py create-video song.wav song.txt --key g
# ✅ Works, normalized to G

# Override model path (advanced usage)
python cli.py create-video song.wav song.txt --key G --harmonica-model custom.png
# ✅ Uses G mapping but custom image
```

### **Testing Requirements**
1. **test_harmonica_key_registry.py** - Registry validation, key lookup
2. **test_video_creator_config.py** - Key config integration
3. **test_cli.py** - CLI argument parsing and validation
4. **Integration test** - Full pipeline with different keys

### **Success Criteria**
✅ CLI accepts --key argument (C, G, D, etc.)
✅ Default key is C (standard harmonica)
✅ Key determines model image automatically
✅ Key determines MIDI mapping automatically
✅ Invalid keys show clear error message
✅ Case-insensitive key handling
✅ Tests passing for all supported keys
✅ Documentation updated

### **Future Enhancements**
- Auto-detect key from MIDI file pitch analysis
- Support for chromatic harmonicas
- Custom key configurations via config file
- Key transposition (play C tabs on G harmonica)

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
