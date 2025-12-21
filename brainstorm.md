# HarmonicaTabs - Interactive Workflow Brainstorm

## Vision: Streamlined Interactive Pipeline

### Goal
Create a fully automated, interactive workflow where users drop files in a folder and the system guides them through each step with approval gates, automatic cleanup, and intelligent file management.

---

## 📊 IMPLEMENTATION PROGRESS

**Started:** 2025-12-21
**Current Phase:** Complete (Paused for review)
**Status:** ✅ 3 Phases Complete

### Completed Phases

#### ✅ Phase 2: Build Filename Parser (COMPLETE)
**Completed:** 2025-12-21 16:30
**Duration:** ~30 minutes

**Tasks Completed:**
- ✅ Created `utils/filename_parser.py` with FilenameConfig dataclass
- ✅ Implemented parse_filename() function
- ✅ Support for all 12 harmonica keys (A, Ab, B, Bb, C, C#, D, E, Eb, F, F#, G)
- ✅ Support for both notation styles (F# and FS, Bb and BB)
- ✅ Created comprehensive test suite (31 tests)
- ✅ All tests passing (618 total in suite)
- ✅ Committed changes

**Commits:**
- `7fe4296` - "feat(parser): Add filename-based configuration parser"

**Module Features:**
- FilenameConfig dataclass: song_name, key, enable_stem, fps, tab_buffer
- parse_filename(): Extract configuration from filename
- Key parsing: Supports all 12 keys, case-insensitive
- Stem flag: _Stem / _NoStem
- FPS parameter: _FPS15, _FPS30, etc. (1-60 range)
- TabBuffer parameter: _TabBuffer0.5 (0-5.0 range)
- Validation: Error handling for invalid values
- Zero integration: Completely isolated, no side effects

**Notes:**
- Completely isolated module - zero risk to existing code
- 100% test coverage with comprehensive edge case testing
- Ready for integration in Phase 4

---

#### ✅ Phase 1: Add Dependencies (COMPLETE)
**Completed:** 2025-12-21 16:00
**Duration:** ~15 minutes

**Tasks Completed:**
- ✅ Added questionary ^2.1.1 to dependencies
- ✅ Added rich ^14.2.0 to dependencies
- ✅ Ran poetry install (5 new packages installed, 6 updated)
- ✅ Verified tests still passing (587 tests ✅)
- ✅ Committed changes

**Commits:**
- `3938208` - "feat(deps): Add questionary and rich for interactive CLI"

**Dependencies Added:**
- questionary: Interactive prompts and user input
- rich: Beautiful terminal output, progress bars, panels
- Also updated: scipy, pillow, prompt-toolkit, pygments

**Notes:**
- Zero breaking changes
- All pre-commit hooks passing
- Ready for interactive CLI development

---

#### ✅ Phase 0: Preparation (COMPLETE)
**Completed:** 2025-12-21 15:45
**Duration:** ~15 minutes

**Tasks Completed:**
- ✅ Checked git status and current changes
- ✅ Committed improvements to main branch
- ✅ Created feature branch: `feature/interactive-workflow`
- ✅ Tagged stable version: `stable-before-interactive`
- ✅ Ran baseline tests: 587 tests passing ✅
- ✅ Documented baseline state

**Commits:**
- `5cbeddb` - "feat: Improve tab parsing and tune consecutive note gap"

**Baseline State:**
- Branch: `feature/interactive-workflow` (created from main)
- Tests: 587 passing, 1 warning
- Git tag: `stable-before-interactive` (rollback point)
- All pre-commit hooks passing (black, mypy, flake8, pytest)

**Notes:**
- Added debug_*.py pattern to .gitignore
- Committed tab parsing improvements and gap tuning before branching
- Clean starting point for interactive workflow development

---

### Upcoming Phases (Paused - Awaiting Review)
- **Phase 3:** Build state machine (isolated) - 🔲 Not Started
- **Phase 4:** Build workflow orchestrator - 🔲 Not Started
- **Phase 5:** Add CLI interactive command - 🔲 Not Started
- **Phase 6:** Integrate planned features - 🔲 Not Started

### Abort Plan
If things get too complicated:
```bash
# Nuclear option - back to stable
git checkout main
git branch -D feature/interactive-workflow

# Or restore to tagged version
git checkout stable-before-interactive
```

---

## Workflow Design

### File-Based Configuration
**Idea:** Encode all parameters in the video filename (manual step by user)

**Filename Convention Examples:**
```
SongName_KeyG_Stem.mp4           # G harmonica, with stem separation
PianoMan_KeyC_NoStem_FPS15.mp4   # C harmonica, no stems, 15 FPS
MyTune_KeyBb.wav                 # Bb harmonica, defaults
```

**Parsing Logic:**
- `_Key[A-G][b#]?` - Harmonica key (required)
- `_Stem` - Enable stem separation (optional)
- `_NoStem` - Skip stem separation (optional, default)
- `_FPS[0-9]+` - Set FPS (optional, default 15)
- `_TabBuffer[0-9.]+` - Tab page buffer time (optional, default 0.1)

---

## Interactive Pipeline Steps

### Step 0: File Drop
**User Action:** Drop video/audio + .txt tab file in `input/` folder

**System Action:**
- Detect new files
- Parse filename parameters
- Display parsed config for confirmation

### Step 1: Stem Separation (Conditional)
**Trigger:** If `_Stem` in filename

**System Action:**
1. Run Demucs stem separation
2. Save 4 stems to `working/stems/`
3. **WAIT FOR USER:** Present stems, ask which to use

**User Input:**
- Select: vocals.wav / drums.wav / bass.wav / other.wav
- Or: Skip, use original file

**Output:** Selected audio file for next step

---

### Step 2: MIDI Extraction
**System Action:**
1. Extract MIDI from selected audio file
2. Save to `working/MySong_generated.mid`
3. Display MIDI stats (note count, duration)

**Output:** `MySong_generated.mid`

**User Prompt:** "MIDI generated. Please fix/edit in your DAW, then press Enter to continue..."

---

### Step 3: Harmonica Video Generation (Iterative Loop)
**System Action:**
1. Load fixed MIDI from `working/MySong_fixed.mid` (or latest version)
2. Generate harmonica animation
3. Save to `working/MySong_harmonica.mov`
4. **WAIT FOR USER:** Display video path, ask for approval

**User Options:**
- ✅ **Approve** → Move to next step
- 🔄 **Re-fix MIDI** → Go back to DAW, regenerate
- ❌ **Cancel** → Abort workflow

**Loop:** Stays in this step until user approves

---

### Step 4: Full Tab Video Generation
**System Action:**
1. Generate full tab video with page compositor
2. **Auto-delete** intermediate page videos after use
3. Save to `working/MySong_full_tabs.mov`
4. Display preview/stats

**User Prompt:** "Full tab video generated. Review and approve to continue..."

**User Options:**
- ✅ **Approve** → Move to final step
- 🔄 **Regenerate** → Adjust params, regenerate
- ❌ **Cancel** → Abort workflow

---

### Step 5: Finalization & Cleanup
**System Action:**
1. **Zip outputs:** Create `MySong_KeyG_YYYYMMDD.zip` containing:
   - `MySong_harmonica.mov`
   - `MySong_full_tabs.mov`
2. Move zip to `outputs/`
3. **Archive legacy files** to `legacy/MySong_KeyG_YYYYMMDD/`:
   - `MySong_fixed.mid` (final MIDI)
   - `MySong.txt` (tab file)
4. **Delete working files:**
   - Stems
   - Generated MIDI
   - Intermediate videos
   - Processed audio
5. Display summary

**Output:**
```
outputs/
└── MySong_KeyG_20251221.zip

legacy/
└── MySong_KeyG_20251221/
    ├── MySong_fixed.mid
    └── MySong.txt
```

---

## Technical Implementation

### Library Recommendations

#### Interactive Prompts (CLI) - **RECOMMENDED**
**Primary Choice: `questionary`**
```python
import questionary

# Example: Select stem
stem_choice = questionary.select(
    "Which stem contains the best harmonica audio?",
    choices=["vocals.wav", "drums.wav", "bass.wav", "other.wav", "Skip - use original"]
).ask()

# Example: Approval gate
approved = questionary.confirm(
    "Review the harmonica video. Does it look good?"
).ask()

if not approved:
    action = questionary.select(
        "What would you like to do?",
        choices=["Re-fix MIDI", "Cancel workflow"]
    ).ask()
```

**Why questionary?**
- Beautiful, modern CLI interface
- Easy to use, minimal code
- Supports: confirm, select, text, password, checkbox
- Works in terminal (no GUI dependencies)

**Alternative: `rich`** (for pretty output + progress bars)
```python
from rich.console import Console
from rich.progress import track
from rich.panel import Panel

console = Console()

console.print(Panel.fit("🎵 Generating MIDI...", style="bold green"))

for step in track(range(100), description="Processing..."):
    # work
```

---

#### GUI Options (If CLI not enough)

**Option 1: `Gooey` (Easiest GUI)**
```python
from gooey import Gooey, GooeyParser

@Gooey(program_name="HarmonicaTabs Interactive")
def main():
    parser = GooeyParser()
    parser.add_argument('input_folder', widget='DirChooser')
    # CLI code stays the same!
```
- **Pros:** One decorator, instant GUI
- **Cons:** Less control over custom interactions

**Option 2: `streamlit` (Web-based)**
```python
import streamlit as st

st.title("HarmonicaTabs Pipeline")
if st.button("Start Processing"):
    # workflow
```
- **Pros:** Beautiful, modern web UI
- **Cons:** Overkill for this use case, requires browser

**Option 3: `tkinter` (Standard Python GUI)**
- **Pros:** Built-in, no extra dependencies
- **Cons:** More boilerplate code

---

#### File Watching (Optional - Auto-detect new files)
**Library: `watchdog`**
```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class NewFileHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.src_path.endswith(('.mp4', '.wav', '.mov')):
            print(f"New file detected: {event.src_path}")
            # Start workflow

observer = Observer()
observer.schedule(NewFileHandler(), path='input/', recursive=False)
observer.start()
```

---

### Workflow State Management

**Approach: State Machine with Session File**

```python
from enum import Enum
import json

class WorkflowState(Enum):
    INIT = "init"
    STEM_SELECTION = "stem_selection"
    MIDI_GENERATION = "midi_generation"
    MIDI_FIXING = "midi_fixing"
    HARMONICA_REVIEW = "harmonica_review"
    TAB_VIDEO_REVIEW = "tab_video_review"
    FINALIZATION = "finalization"
    COMPLETE = "complete"

class WorkflowSession:
    def __init__(self, session_file="working/.session.json"):
        self.session_file = session_file
        self.state = WorkflowState.INIT
        self.data = {}

    def save(self):
        with open(self.session_file, 'w') as f:
            json.dump({
                'state': self.state.value,
                'data': self.data
            }, f)

    def load(self):
        if os.path.exists(self.session_file):
            with open(self.session_file, 'r') as f:
                session = json.load(f)
                self.state = WorkflowState(session['state'])
                self.data = session['data']
            return True
        return False

    def transition_to(self, new_state):
        self.state = new_state
        self.save()
```

**Benefits:**
- Resume after crash/restart
- Track progress visually
- Allow "go back" functionality

---

### Filename Parameter Parsing

```python
import re
from dataclasses import dataclass
from typing import Optional

@dataclass
class VideoConfig:
    song_name: str
    key: str = "C"
    enable_stem: bool = False
    fps: int = 15
    tab_buffer: float = 0.1

def parse_filename(filename: str) -> VideoConfig:
    """
    Parse configuration from filename.

    Examples:
        SongName_KeyG_Stem.mp4 → VideoConfig(song_name="SongName", key="G", enable_stem=True)
        PianoMan_KeyC_FPS15.mp4 → VideoConfig(song_name="PianoMan", key="C", fps=15)
    """
    # Remove extension
    name = os.path.splitext(filename)[0]

    # Split by underscore
    parts = name.split('_')

    config = VideoConfig(song_name=parts[0])

    for part in parts[1:]:
        # Parse key
        if match := re.match(r'Key([A-G][b#]?)', part, re.IGNORECASE):
            config.key = match.group(1).upper()

        # Parse stem flag
        elif part.lower() == 'stem':
            config.enable_stem = True

        # Parse FPS
        elif match := re.match(r'FPS(\d+)', part, re.IGNORECASE):
            config.fps = int(match.group(1))

        # Parse tab buffer
        elif match := re.match(r'TabBuffer([\d.]+)', part, re.IGNORECASE):
            config.tab_buffer = float(match.group(1))

    return config
```

---

## Folder Structure

```
project/
├── input/                          # User drops files here
│   ├── MySong_KeyG_Stem.mp4
│   └── MySong.txt
│
├── working/                        # Temporary processing files
│   ├── .session.json              # State tracking
│   ├── stems/                     # Stem separation outputs
│   │   ├── vocals.wav
│   │   ├── drums.wav
│   │   ├── bass.wav
│   │   └── other.wav
│   ├── MySong_generated.mid       # Raw MIDI from basic_pitch
│   ├── MySong_fixed.mid           # User-edited MIDI
│   ├── MySong_harmonica.mov       # Harmonica animation
│   └── MySong_full_tabs.mov       # Full tab video
│
├── outputs/                        # Final deliverables
│   └── MySong_KeyG_20251221.zip   # Zipped outputs
│
└── legacy/                         # Archived project files
    └── MySong_KeyG_20251221/
        ├── MySong_fixed.mid
        └── MySong.txt
```

---

## Proposed CLI Design

### Main Command: Interactive Mode
```bash
# Start interactive workflow
python cli.py interactive

# Or with file watching
python cli.py interactive --watch
```

### Example Interactive Session
```
🎵 HarmonicaTabs Interactive Pipeline
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📂 Detected: MySong_KeyG_Stem.mp4 + MySong.txt

📋 Parsed Configuration:
   Song Name: MySong
   Key: G
   Stem Separation: Enabled
   FPS: 15 (default)
   Tab Buffer: 0.1s (default)

✅ Configuration correct? (Y/n): y

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Step 1/5: Stem Separation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎵 Separating audio stems with Demucs...
⏱️  Processing... [████████████████████] 100%

✅ Created 4 stems in working/stems/:
   1. vocals.wav (likely has harmonica)
   2. drums.wav
   3. bass.wav
   4. other.wav

? Which stem contains the best harmonica audio?
  > vocals.wav
    bass.wav
    other.wav
    Skip - use original file

✅ Selected: vocals.wav

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Step 2/5: MIDI Generation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎹 Generating MIDI from vocals.wav...
⏱️  Processing... [████████████████████] 100%

✅ MIDI saved to: working/MySong_generated.mid
   Notes detected: 87
   Duration: 32.5s

📝 Please fix/edit the MIDI in your DAW, then save as:
   working/MySong_fixed.mid

⏸️  Press Enter when ready to continue...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Step 3/5: Harmonica Video
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎬 Generating harmonica animation...
⏱️  Processing... [████████████████████] 100%

✅ Video saved to: working/MySong_harmonica.mov

? Does the harmonica video look good?
  > ✅ Yes - continue
    🔄 No - re-fix MIDI and regenerate
    ❌ Cancel workflow

✅ Approved!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Step 4/5: Full Tab Video
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎬 Generating full tab video with compositor...
⏱️  Processing... [████████████████████] 100%
🗑️  Deleted intermediate page videos

✅ Video saved to: working/MySong_full_tabs.mov

? Does the tab video look good?
  > ✅ Yes - finalize and export
    🔄 No - regenerate
    ❌ Cancel workflow

✅ Approved!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Step 5/5: Finalization
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📦 Creating final package...
   ✅ Zipped outputs → outputs/MySong_KeyG_20251221.zip
   ✅ Archived MIDI + tabs → legacy/MySong_KeyG_20251221/
   🗑️  Cleaned working directory

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎉 Workflow Complete!
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📂 Outputs: outputs/MySong_KeyG_20251221.zip
📂 Legacy: legacy/MySong_KeyG_20251221/

Ready for next project!
```

---

## Implementation Phases

### Phase 1: Core Interactive CLI (Recommended First)
**Dependencies:**
- `questionary` - Interactive prompts
- `rich` - Beautiful output

**Deliverables:**
1. Filename parser
2. State machine with session management
3. Interactive workflow steps 1-5
4. Basic cleanup/archival

### Phase 2: Polish & UX
**Enhancements:**
1. Progress bars for long operations
2. Better error handling
3. "Go back" functionality
4. Workflow resume after crash

### Phase 3: Optional GUI (Future)
**If CLI not sufficient:**
- Add Gooey decorator for instant GUI
- Or build custom Streamlit interface

---

## Questions to Resolve

### 1. MIDI File Naming
**Question:** How does user save edited MIDI?
- **Option A:** Fixed name `MySong_fixed.mid` (user must rename)
- **Option B:** Program watches folder, accepts any new `.mid` file
- **Option C:** User specifies path in prompt

**Recommendation:** Option A (simplest, most reliable)

### 2. File Watching vs Manual Trigger
**Question:** Auto-detect new files or manual start?
- **Option A:** User runs `python cli.py interactive` each time
- **Option B:** Program watches `input/` folder continuously

**Recommendation:** Option A for MVP, add Option B later

### 3. Error Handling
**Question:** What if stem separation fails? MIDI generation fails?
- Display error, offer retry
- Log to `working/error.log`
- Allow user to skip step or cancel

### 4. Multi-Project Workflow
**Question:** Can user start new project while one is in progress?
- **Option A:** Only one active session at a time (lock file)
- **Option B:** Support parallel sessions (separate working dirs)

**Recommendation:** Option A for MVP

---

## Success Criteria

✅ User drops video + tabs in `input/`
✅ Filename parameters parsed correctly
✅ Interactive prompts guide user through each step
✅ Approval gates prevent proceeding with bad outputs
✅ Iterative MIDI refinement loop works smoothly
✅ Final outputs zipped with descriptive name
✅ Working files cleaned automatically
✅ Legacy files archived for reference
✅ Session state saved (can resume after crash)

---

## Next Steps

1. **Decide:** CLI-only or GUI? (Recommend CLI with `questionary` + `rich`)
2. **Prototype:** Build filename parser + state machine
3. **Implement:** Interactive workflow for steps 1-5
4. **Test:** Run through full workflow with real video
5. **Polish:** Add progress bars, better error messages
6. **Document:** Update README with new workflow instructions

---

## Alternative: Makefile-Style Workflow (Simpler Option)

If full interactivity is too complex, consider a simpler "stage" approach:

```bash
# User manually runs each stage when ready
python cli.py stage1-stem MySong_KeyG_Stem.mp4      # Creates stems, user selects
python cli.py stage2-midi vocals.wav                # Creates MIDI, user fixes
python cli.py stage3-harmonica MySong_fixed.mid     # Creates harmonica video
python cli.py stage4-tabs MySong_fixed.mid tabs.txt # Creates tab video
python cli.py stage5-finalize MySong                # Zip + cleanup
```

**Pros:** Simpler, more control
**Cons:** Less automated, more manual commands

---

## Final Recommendation

**Best Approach for Your Needs:**

1. **Use `questionary` + `rich`** for beautiful CLI interactions
2. **Implement state machine** with session persistence
3. **Start with CLI-only** (no GUI for MVP)
4. **Add file watching later** if needed
5. **Focus on approval gates** - most important for quality

This gives you:
- Fast, streamlined workflow
- Visual clarity and progress tracking
- Ability to iterate until satisfied
- Clean, organized outputs
- No GUI complexity

**Estimated Effort:** 2-3 days of focused development
