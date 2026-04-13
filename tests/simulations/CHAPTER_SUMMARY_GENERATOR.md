# Chapter Summary Generator

`generate_chapter_summaries.py` reads a saved
`logs/simulations/simulation_state_*.json` file and produces chapter summaries
using the same summary-generation path across all chapter types. It can also
emit a React-compatible payload for the summary front-end.

This script works from simulation state JSON files, not from raw log files.

## Inputs

The script accepts either:

- an explicit `simulation_state_*.json` path
- no positional argument, in which case it automatically picks the latest
  `simulation_state_*.json` file from `logs/simulations/`

The state files are normally created by
`tests/simulations/generate_all_chapters.py`.

## Usage

```bash
# Use the latest simulation state file and print concise output
python tests/simulations/generate_chapter_summaries.py --compact

# Use a specific simulation state file
python tests/simulations/generate_chapter_summaries.py \
  logs/simulations/simulation_state_2026-04-14_12:34_abcd1234.json

# Save the chapter-summary JSON payload
python tests/simulations/generate_chapter_summaries.py \
  --save-json \
  --output chapter_summaries.json

# Generate React-compatible summary data without writing a file
python tests/simulations/generate_chapter_summaries.py --react-json

# Generate React-compatible summary data and save it to disk
python tests/simulations/generate_chapter_summaries.py \
  --react-json \
  --react-output tests/summary_data.json

# Slow down LLM calls between chapters
python tests/simulations/generate_chapter_summaries.py \
  --delay 1.0 \
  --compact
```

## Options

- `state_file`: optional path to a simulation state JSON file
- `--output OUTPUT`: output path for saved chapter-summary JSON
  (default: `chapter_summaries.json`)
- `--save-json`: writes the chapter-summary JSON file
- `--compact`: prints one concise block per chapter
- `--delay DELAY`: pause between chapter requests in seconds
  (default: `2.0`)
- `--react-json`: generates React-compatible summary data instead of the raw
  chapter-summary list
- `--react-output REACT_OUTPUT`: optional output path for the React-compatible
  JSON payload

## Output Behavior

### Default mode

Without `--save-json` or `--react-json`, the script prints generated summaries
to the console and does not write a file.

### Saved chapter-summary JSON

When `--save-json` is provided, the script writes a list of chapter summary
objects to `--output`. Each object contains:

- `chapter_number`
- `chapter_type`
- `title`
- `summary`

### React-compatible summary JSON

When `--react-json` is provided, the script returns the shape expected by the
summary front-end, including:

- `chapterSummaries`
- `educationalQuestions`
- `statistics`

If `--react-output` is also provided, that payload is written to disk.

## Typical Workflow

1. Generate a full simulation state:

   ```bash
   python tests/simulations/generate_all_chapters.py
   ```

2. Turn that state into summary data:

   ```bash
   python tests/simulations/generate_chapter_summaries.py \
     --react-json \
     --react-output tests/summary_data.json
   ```

3. Preview the summary UI against that data:

   ```bash
   python tests/test_summary_chapter.py \
     --state-file logs/simulations/simulation_state_<timestamp>_<run_id>.json
   ```

## Notes

- The script uses the same summary-generation path for story, lesson, reflect,
  and conclusion chapters.
- Missing chapter content is skipped rather than aborting the entire run.
- React payload generation is useful when debugging the front-end summary page
  without replaying a whole adventure in the browser.
