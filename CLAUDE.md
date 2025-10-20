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
python cli.py create-video PMH.m4v PMH.txt --only-tabs

# Create only harmonica animation (skip tab phrases)
python cli.py create-video PMH.m4v PMH.txt --only-harmonica

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

### 🧪 **Current Status: Phase 2 Core Business Logic COMPLETE ✅**
- ✅ **Phase 1 DONE**: Data models tests (TabEntry, Tabs, NoteEvent) - 17 tests
- ✅ **Phase 2 DONE**: Core business logic - 110+ tests
  - ✅ TabMapper (MIDI→Tab conversion) - 24 tests
  - ✅ MidiGenerator (Audio→MIDI pipeline) - 26 tests
  - ✅ AudioProcessor (Audio processing workflow) - 23 tests
  - ✅ TabTextParser (.txt file parsing) - 37 tests (32 passing, 5 edge case failures)
- 🚧 **NEXT SESSION STARTS HERE** 🚧

### 📁 **Test Structure (1:1 Source Mapping)**
```
Source Structure                Test Structure                        Status
─────────────────              ──────────────────                    ──────
tab_converter/                  tests/tab_converter/
├── models.py          →        ├── test_models.py                    ✅ DONE
├── tab_mapper.py      →        ├── test_tab_mapper.py                ✅ DONE
├── consts.py          →        └── conftest.py                       ✅ DONE

harmonica_pipeline/             tests/harmonica_pipeline/
├── video_creator.py   →        ├── test_video_creator.py             🚧 NEXT
├── midi_generator.py  →        ├── test_midi_generator.py            ✅ DONE
└── midi_processor.py  →        └── conftest.py                       ✅ DONE

utils/                          tests/utils/
├── audio_extractor.py →        ├── test_audio_extractor.py           🚧 NEXT
├── audio_processor.py →        ├── test_audio_processor.py           ✅ DONE
└── utils.py          →         ├── test_utils.py                     🚧 NEXT
                                └── conftest.py                       ✅ DONE

tab_phrase_animator/            tests/tab_phrase_animator/
├── tab_text_parser.py →        ├── test_tab_text_parser.py           ✅ DONE (5 edge cases)
├── tab_phrase_animator.py →    ├── test_tab_phrase_animator.py       🚧 NEXT
└── tab_matcher.py     →        ├── test_tab_matcher.py               🚧 NEXT
                                └── conftest.py                       ✅ DONE

image_converter/                tests/image_converter/                🚧 NEXT
├── animator.py        →        ├── test_animator.py                  🚧 NEW
├── consts.py          →        ├── test_consts.py                    🚧 NEW
└── ...                →        └── conftest.py                       🚧 NEW

./                              tests/
├── cli.py             →        ├── test_cli.py                       🚧 NEXT
├── main.py            →        ├── test_main.py                      🚧 NEXT
└── ...                →        ├── conftest.py                       ✅ DONE
                                └── test_integration.py                🚧 NEXT
```

### 🎯 **Remaining Implementation Plan**

#### **Step 1: Fix TabTextParser Edge Cases (1 commit) - IMMEDIATE NEXT**
- Fix 5 failing edge case tests in TabTextParser
- Issues: colon handling, hole validation timing, empty page counting
- Target: 37/37 tests passing for complete TabTextParser coverage

#### **Step 2: Phase 3 - Complex Integration & Missing Components (4-5 commits)**
1. **tests/harmonica_pipeline/test_video_creator.py** - Text-based structure ✨ (our major changes)
2. **tests/utils/test_audio_extractor.py** - Audio extraction with ffmpeg fallback
3. **tests/utils/test_utils.py** - Directory management, MIDI processing utilities
4. **tests/tab_phrase_animator/test_tab_phrase_animator.py** - Tab phrase animation
5. **tests/tab_phrase_animator/test_tab_matcher.py** - Tab timing alignment

#### **Step 3: Complete Coverage - All Remaining Files (3-4 commits)**
6. **tests/image_converter/** - Animation system (animator.py, consts.py)
7. **tests/test_cli.py** - Command-line interface testing
8. **tests/test_main.py** - Legacy main.py functionality
9. **tests/test_integration.py** - End-to-end workflow validation

#### **Step 4: 100% Coverage Analysis & Cleanup (2 commits)**
10. **Coverage analysis**: Run coverage tools to identify untested code paths
11. **Fill coverage gaps**: Add tests for any missed functions/edge cases
12. **Performance testing**: Benchmark critical paths and memory usage

#### **Step 5: TODO Review & Implementation (2-3 commits)**
13. **Review all TODOs**: Scan codebase for TODO comments added during testing
14. **Implement high-priority TODOs**: Address critical functionality gaps
15. **Document remaining TODOs**: Create GitHub issues for future work

### 🚀 **Updated Commit Strategy**
```bash
# IMMEDIATE NEXT:
1. test: Fix TabTextParser edge cases (colon handling, validation timing)

# Phase 3 - Complex Integration:
2. test: Add VideoCreator text-based structure tests
3. test: Add AudioExtractor and ffmpeg fallback tests
4. test: Add utils module tests (directory management, MIDI utilities)
5. test: Add TabPhraseAnimator and TabMatcher tests
6. test: Add ImageConverter animation system tests

# Complete Coverage:
7. test: Add CLI and main.py integration tests
8. test: Add end-to-end integration test suite
9. test: Achieve 100% code coverage and performance benchmarks

# TODO Implementation:
10. fix: Implement realistic harmonica chord validation (consecutive holes, max 2-note chords)
11. fix: Address all high-priority TODOs discovered during testing
12. docs: Document remaining TODOs and create GitHub issues
```

### 📊 **Current Testing Metrics**
- **Total Tests**: 110+ (127 collected by pytest)
- **Coverage**: ~60% estimated (core business logic complete)
- **Modules Tested**: 6/15+ source modules
- **TODOs Added**: 1 confirmed (TabTextParser chord validation)
- **Target**: 100% coverage, all TODOs addressed

### 📝 **Next Session Action Items**
1. **Fix TabTextParser edge cases** - 5 failing tests to 37/37 passing
2. **Create VideoCreator tests** - Text-based structure implementation
3. **AudioExtractor tests** - Video→audio extraction with fallbacks
4. **Utils tests** - Directory management and MIDI utilities
5. **Coverage analysis** - Identify remaining untested code paths

### 🎨 **Conftest Architecture Strategy** ✅
- **Global fixtures**: Core data structures, common utilities
- **Module fixtures**: Specific to each source module in their conftest.py
- **Hierarchical inheritance**: Module conftest inherits global automatically
- **DRY principle**: Shared fixtures prevent duplication across test files
