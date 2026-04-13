# Generate All Chapters

`generate_all_chapters.py` runs a single end-to-end adventure against the live
WebSocket server, makes choices automatically, reveals the summary, and writes
the resulting `AdventureState` to a reusable JSON file.

## Requirements

- Activate `.venv`
- Run the command from the repository root
- Start the application at `localhost:8000`

```bash
source .venv/bin/activate
python -m uvicorn app.main:app --reload
```

## Usage

```bash
python tests/simulations/generate_all_chapters.py
python tests/simulations/generate_all_chapters.py \
  --category enchanted_forest_tales \
  --topic "Singapore History"
```

### Options

- `--category`: specific story category ID
- `--topic`: specific lesson topic

If neither option is supplied, the script randomly selects both values from
the current content library.

## What the Script Does

1. Connects to `/ws/story/{story_category}/{lesson_topic}` on
   `localhost:8000`
2. Sends the initial `"start"` choice with a planned 10-chapter structure
3. Streams all generated chapters and chooses from available options
4. Processes the conclusion chapter
5. Sends `"reveal_summary"` to trigger the summary flow
6. Appends the summary chapter to the in-memory simulation state
7. Writes the resulting state to disk for reuse by summary tools

## Output Files

- Log file:
  `logs/simulations/generate_all_chapters_{timestamp}_{run_id}.log`
- State file:
  `logs/simulations/simulation_state_{timestamp}_{run_id}.json`

The saved state file is the primary input for:

- `tests/simulations/generate_chapter_summaries.py`
- `tests/test_summary_chapter.py`
- `tests/test_summary_button_flow.py`

## Notes

- This script talks to the running app and uses the production WebSocket flow.
- It does not accept custom host or port arguments.
- The saved JSON captures the generated chapters, lesson data, chapter
  summaries, metadata, and the appended summary chapter from the run.
