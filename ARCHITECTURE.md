# Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           HarmonicaTabs Pipeline                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────────┐   │
│  │  Phase 1     │    │  Manual      │    │  Phase 2                 │   │
│  │  MIDI Gen    │───▶│  DAW Edit    │───▶│  Video Creation          │   │
│  └──────────────┘    └──────────────┘    └──────────────────────────┘   │
│         │                                          │                     │
│         ▼                                          ▼                     │
│  ┌──────────────┐                         ┌──────────────────────────┐   │
│  │ fixed_midis/ │                         │ outputs/                 │   │
│  │ *_fixed.mid  │                         │ *_harmonica.mov          │   │
│  └──────────────┘                         │ *_full_tabs.mov          │   │
│                                           └──────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

## Module Structure

```
harmonica_pipeline/     # Core pipeline orchestration
├── midi_generator.py       # Phase 1: Audio → MIDI (basic_pitch)
├── midi_processor.py       # MIDI loading, overlap fixing
├── video_creator.py        # Phase 2: Main video creation orchestrator
├── video_creator_config.py # Configuration dataclass
└── harmonica_key_registry.py # Key definitions (all 12 keys)

tab_converter/          # MIDI → Harmonica notation
├── consts.py              # Pitch mappings, bend definitions per key
├── models.py              # TabEntry dataclass
├── tab_mapper.py          # Converts MIDI events → TabEntry objects
└── tab_generator.py       # Generates tab text from MIDI

image_converter/        # Harmonica animation
├── animator.py            # FuncAnimation for hole highlighting
├── figure_factory.py      # Matplotlib figure setup
├── harmonica_layout.py    # Hole positions on image
├── color_scheme.py        # Draw/blow colors
├── consts.py              # Hole coordinates per key
└── video_processor.py     # MoviePy video composition

tab_phrase_animator/    # Tab page animations
├── tab_phrase_animator.py     # Page-by-page tab video
├── tab_text_parser.py         # Parse tab notation files
├── tab_matcher.py             # Match text tabs to MIDI timing (experimental)
└── full_tab_video_compositor.py # Stitch pages into single video

interactive_workflow/   # Guided CLI workflow
├── orchestrator.py        # State machine runner
└── state_machine.py       # Workflow states and transitions

utils/                  # Shared utilities
├── audio_extractor.py     # FFmpeg audio extraction
├── audio_processor.py     # Mono conversion, filtering
├── filename_parser.py     # Parse SongName_KeyX_Stem.mp4 format
├── midi_validator.py      # Compare MIDI to tab file
├── stem_separator.py      # Demucs stem separation
└── utils.py               # Paths, temp dirs, helpers

cli.py                  # Main CLI entry point (argparse)
```

## Key Classes

### Pipeline Core

| Class | File | Purpose |
|-------|------|---------|
| `MidiGenerator` | `harmonica_pipeline/midi_generator.py` | Runs basic_pitch on audio, outputs MIDI |
| `MidiProcessor` | `harmonica_pipeline/midi_processor.py` | Loads MIDI, fixes overlaps, extracts note events |
| `VideoCreator` | `harmonica_pipeline/video_creator.py` | Orchestrates Phase 2 video generation |
| `VideoCreatorConfig` | `harmonica_pipeline/video_creator_config.py` | Configuration for VideoCreator |

### Tab Conversion

| Class | File | Purpose |
|-------|------|---------|
| `TabMapper` | `tab_converter/tab_mapper.py` | MIDI pitch → harmonica hole number |
| `TabEntry` | `tab_converter/models.py` | Single note: hole, timing, bend info |
| `TabGenerator` | `tab_converter/tab_generator.py` | Generate tab text files from MIDI |

### Animation

| Class | File | Purpose |
|-------|------|---------|
| `Animator` | `image_converter/animator.py` | Harmonica hole highlighting animation |
| `FigureFactory` | `image_converter/figure_factory.py` | Setup matplotlib figures |
| `HarmonicaLayout` | `image_converter/harmonica_layout.py` | Hole positions on harmonica image |
| `TabPhraseAnimator` | `tab_phrase_animator/tab_phrase_animator.py` | Tab page animations with glow |
| `FullTabVideoCompositor` | `tab_phrase_animator/full_tab_video_compositor.py` | Stitch pages together |

### Interactive Workflow

| Class | File | Purpose |
|-------|------|---------|
| `WorkflowOrchestrator` | `interactive_workflow/orchestrator.py` | Runs guided workflow |
| `WorkflowState` | `interactive_workflow/state_machine.py` | Enum of workflow states |

## Data Flow

### Phase 1: MIDI Generation

```
Input Video/Audio
       │
       ▼
┌─────────────────┐
│ AudioExtractor  │  FFmpeg: extract WAV
└────────┬────────┘
         ▼
┌─────────────────┐
│ AudioProcessor  │  Mono, bandpass filter, noise reduction
└────────┬────────┘
         ▼
┌─────────────────┐
│  basic_pitch    │  Spotify AI model for pitch detection
└────────┬────────┘
         ▼
   fixed_midis/*.mid
```

### Phase 2: Video Creation

```
fixed_midis/*.mid + tab-files/*.txt
              │
              ▼
     ┌─────────────────┐
     │  MidiProcessor  │  Load note events, fix overlaps
     └────────┬────────┘
              ▼
     ┌─────────────────┐
     │   TabMapper     │  MIDI pitch → hole numbers
     └────────┬────────┘
              ▼
     ┌─────────────────┐
     │  TabTextParser  │  Parse tab file pages
     └────────┬────────┘
              │
       ┌──────┴──────┐
       ▼             ▼
┌────────────┐ ┌──────────────────┐
│  Animator  │ │TabPhraseAnimator │
│ (harmonica)│ │   (tab pages)    │
└─────┬──────┘ └────────┬─────────┘
      ▼                 ▼
*_harmonica.mov    *_full_tabs.mov
```

## Harmonica Key System

All 12 keys supported via transposition from C:

```python
KEY_OFFSETS = {
    "C": 0, "C#": 1, "D": 2, "EB": 3, "E": 4, "F": 5,
    "F#": 6, "G": 7, "AB": 8, "A": 9, "BB": 10, "B": 11
}
```

Each key has:
- **Pitch mapping**: MIDI note → hole number (`tab_converter/consts.py`)
- **Bend mapping**: Extra notes via draw bends (`tab_converter/consts.py`)
- **Model image**: `harmonica-models/{key}.png`
- **Hole coordinates**: Pixel positions (`image_converter/consts.py`)

## Configuration

### VideoCreatorConfig Options

| Option | Default | Purpose |
|--------|---------|---------|
| `harmonica_key` | "C" | Which harmonica key |
| `fps` | 15 | Video frame rate |
| `fix_overlaps` | False | Auto-fix overlapping MIDI notes |
| `chord_threshold_ms` | 50.0 | Overlap threshold for chord detection |
| `produce_tabs` | True | Generate tab animations |
| `only_full_tab_video` | False | Skip individual page videos |

### MIDI Generation Thresholds

| Parameter | Default | Effect |
|-----------|---------|--------|
| `onset_threshold` | 0.4 | Lower = more note starts detected |
| `frame_threshold` | 0.3 | Lower = quieter notes detected |
| `minimum_note_length` | 127ms | Filter very short notes |
| `melodia_trick` | True | Helps with single-note melodies |
