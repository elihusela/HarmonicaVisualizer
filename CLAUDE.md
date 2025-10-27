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
python cli.py generate-midi MySong.MOV  # No --output-name needed!

# Fix MIDI in DAW → save as fixed_midis/MySong_fixed.mid

# Phase 2: WAV → Video (reuses extracted audio)
python cli.py create-video MySong.wav MySong.txt

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
python cli.py create-video MySong.wav MySong.txt

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

## Next Session Tasks - Phase 2 Refactoring

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
