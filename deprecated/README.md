# Deprecated Files

This directory contains files that have been replaced by the new two-phase CLI architecture.

## Deprecated Files:

### `main.py`
- **Replaced by**: `cli.py`
- **Reason**: Old single-file interface, replaced by modern two-phase CLI
- **Date deprecated**: September 2024

### `harmonica_pipeline.py`
- **Replaced by**: `harmonica_pipeline/midi_generator.py` + `harmonica_pipeline/video_creator.py`
- **Reason**: Monolithic class split into Phase 1 (MIDI generation) and Phase 2 (video creation)
- **Date deprecated**: September 2024

### `tests/harmonica_pipeline/`
- **Status**: Tests for deprecated `HarmonicaTabsPipeline` class
- **Note**: New tests should be written for the refactored components

## Migration Notes:

**Old way:**
```bash
python main.py video.mp4 tabs.txt harmonica.png output.mov tabs_output.mov midi.mid
```

**New way:**
```bash
# Phase 1: Generate MIDI
python cli.py generate-midi video.mp4

# Edit MIDI in DAW, then...

# Phase 2: Create video
python cli.py create-video video.wav tabs.txt
```
