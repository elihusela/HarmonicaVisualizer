# HarmonicaTabs

Generates animated harmonica tablature videos from audio/video files. Syncs harmonica tab notation with audio playback.

## Quick Start

```bash
python cli.py interactive MySong_KeyG.mp4   # Guided workflow
python cli.py generate-midi MySong.wav       # Phase 1: Audio → MIDI
python cli.py create-video MySong.mp4 tabs.txt --key G  # Phase 2: MIDI → Video
```

See [USAGE.md](USAGE.md) for full CLI reference.

## Project Health

- **Tests**: 769 passing, 99% coverage
- **Dependencies**: Poetry (`poetry install`)
- **Pre-commit**: black, mypy, flake8, pytest

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for system design, modules, and classes.

**Pipeline Overview:**
```
Audio/Video → MIDI Generation → Manual DAW Edit → Video Creation
     ↓              ↓                  ↓               ↓
  extract       basic_pitch      fix notes      animate tabs
```

## Directory Structure

```
video-files/      # Input videos/audio
tab-files/        # Tab notation text files
fixed_midis/      # Edited MIDI files (ready for video)
outputs/          # Generated videos
sessions/         # Workflow state + logs
```

## TODOs (Prioritized)

### High Priority

1. **Video Generation Speed Optimization**
   - Current: Renders every frame even when nothing changes
   - Goal: Static segment compositing (70-90% faster)
   - Approach: Split into [static clip] → [animated segment] → [static clip]
   - Files: `image_converter/animator.py`, `tab_phrase_animator/tab_phrase_animator.py`

### Low Priority

2. **TabMatcher Improvements** (experimental feature)
   - Better chord matching, timing alignment
   - File: `tab_phrase_animator/tab_matcher.py`

3. **Alternative MIDI Libraries**
   - Benchmark: Magenta mt3, crepe, pyin vs basic_pitch
   - Only if >10% accuracy improvement

## Claude Instructions

- Use Context7 MCP for library docs (moviepy, basic_pitch, matplotlib, numpy)
- Run `poetry install` for dependencies
- Run `pytest` before committing
