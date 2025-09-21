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

## Latest Architecture (Sept 2024)

### 🎵 **Simplified 2-Phase Workflow:**
```bash
# Phase 1: Video/Audio → MIDI (auto-naming, WAV extraction)
python cli.py generate-midi BW.MOV  # No --output-name needed!

# Fix MIDI in DAW → save as fixed_midis/BW_fixed.mid

# Phase 2: WAV → Video (reuses extracted audio)
python cli.py create-video BW.wav BW.txt
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
- **VideoCreator**: Phase 2 video generation (unchanged)

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
