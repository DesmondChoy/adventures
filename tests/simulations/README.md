# Adventure Simulation Suite

The scripts in this directory exercise the production adventure flow through
the live WebSocket endpoint and the summary pipeline. They are useful for
smoke tests, log-based anomaly detection, reusable state generation, and
summary debugging without reimplementing application logic.

## Prerequisites

- Run commands from the repository root.
- Activate `.venv` before running Python commands:

  ```bash
  source .venv/bin/activate
  ```

- For scripts other than `run_test_analysis.py`, start the application first:

  ```bash
  python -m uvicorn app.main:app --reload
  ```

## Script Overview

| Script | Purpose | Key options |
| --- | --- | --- |
| `run_test_analysis.py` | Runs adventure simulations, manages the server lifecycle if needed, and analyzes the newest test log. | `--runs`, `--category`, `--topic`, `--host`, `--port`, `--analyze-only`, `--no-server` |
| `adventure_test_runner.py` | Runs one or more end-to-end WebSocket adventures against an existing server. | `--runs`, `--category`, `--topic`, `--host`, `--port` |
| `log_analyzer.py` | Analyzes one test log file for errors and app-specific anomalies. | `<log_file>`, `--output` |
| `generate_all_chapters.py` | Generates a single full adventure, reveals the summary, and saves a reusable state JSON file. | `--category`, `--topic` |
| `generate_chapter_summaries.py` | Produces chapter summaries or React-compatible summary data from a saved simulation state JSON file. | `[state_file]`, `--output`, `--save-json`, `--compact`, `--delay`, `--react-json`, `--react-output` |

## Quick Start

### End-to-end automated run

This is the fastest way to validate the app from the outside:

```bash
python tests/simulations/run_test_analysis.py --runs 3
```

That command:

- starts `uvicorn` automatically if port `8000` is free
- runs the requested number of WebSocket playthroughs
- finds the newest `adventure_test_*.log`
- runs `log_analyzer.py` against that log
- writes an `analysis_report_*.txt` file under `logs/simulations/`

Useful variants:

```bash
# Reuse an already running local server
python tests/simulations/run_test_analysis.py --runs 3 --no-server

# Only analyze the newest log file
python tests/simulations/run_test_analysis.py --analyze-only

# Lock the run to a specific world and topic
python tests/simulations/run_test_analysis.py \
  --runs 2 \
  --category enchanted_forest_tales \
  --topic "Singapore History"
```

### Raw WebSocket simulations

Use the raw runner when you want repeated playthroughs without the analysis
wrapper:

```bash
python tests/simulations/adventure_test_runner.py --runs 5
python tests/simulations/adventure_test_runner.py \
  --category festival_of_lights_and_colors \
  --topic "Human Body" \
  --host localhost \
  --port 8000
```

### Generate a reusable full-adventure state file

`generate_all_chapters.py` is the handiest way to create a state JSON file that
can be reused by summary tools:

```bash
python tests/simulations/generate_all_chapters.py
python tests/simulations/generate_all_chapters.py \
  --category clockwork_sky_city \
  --topic "Astronomy"
```

This script connects to `localhost:8000`, runs the full 10-chapter flow, sends
`"reveal_summary"` after the conclusion chapter, and writes a
`simulation_state_*.json` file under `logs/simulations/`.

### Turn a saved state into summary data

`generate_chapter_summaries.py` works from simulation state JSON files, not
from raw logs:

```bash
# Use the latest simulation_state_*.json file and print summaries only
python tests/simulations/generate_chapter_summaries.py --compact

# Use a specific state file and save JSON output
python tests/simulations/generate_chapter_summaries.py \
  logs/simulations/simulation_state_2026-04-14_12:34_abcd1234.json \
  --save-json \
  --output chapter_summaries.json

# Generate React-compatible summary data
python tests/simulations/generate_chapter_summaries.py \
  --react-json \
  --react-output tests/summary_data.json
```

## Output Files

### Adventure test logs

- Location: `logs/simulations/`
- Pattern: `adventure_test_{timestamp}_{run_id}.log`
- Created by: `adventure_test_runner.py` and `run_test_analysis.py`

### Analysis reports

- Location: `logs/simulations/`
- Pattern: `analysis_report_{timestamp}_{run_id}.txt`
- Created by: `run_test_analysis.py`

### Full simulation state files

- Location: `logs/simulations/`
- Pattern: `simulation_state_{timestamp}_{run_id}.json`
- Created by: `generate_all_chapters.py`

### Full-adventure generation logs

- Location: `logs/simulations/`
- Pattern: `generate_all_chapters_{timestamp}_{run_id}.log`
- Created by: `generate_all_chapters.py`

## Log Analyzer Coverage

`log_analyzer.py` looks for application-specific issues rather than generic
grep-style errors. It detects:

- critical error and exception lines
- performance problems such as slow operations and streaming issues
- state management issues such as `[STATE CORRUPTION]` and storage failures
- WebSocket connection and message-processing failures
- LLM generation and prompt-related errors
- incomplete adventure or summary-generation failures

Run it directly when you want to inspect a specific log:

```bash
python tests/simulations/log_analyzer.py \
  logs/simulations/adventure_test_2026-04-14_12:34_abcd1234.log \
  --output logs/simulations/manual_analysis.txt
```

## Command Reference

### `adventure_test_runner.py`

```text
--runs RUNS
--category CATEGORY
--topic TOPIC
--port PORT
--host HOST
```

### `run_test_analysis.py`

```text
--runs RUNS
--category CATEGORY
--topic TOPIC
--port PORT
--host HOST
--analyze-only
--no-server
```

### `generate_all_chapters.py`

```text
--category CATEGORY
--topic TOPIC
```

### `generate_chapter_summaries.py`

```text
[state_file]
--output OUTPUT
--save-json
--compact
--delay DELAY
--react-json
--react-output REACT_OUTPUT
```

## Recommended Workflow

1. Use `run_test_analysis.py` for routine smoke coverage.
2. Use `generate_all_chapters.py` when you need a reusable adventure state.
3. Use `generate_chapter_summaries.py` and `tests/test_summary_chapter.py`
   when working on the summary experience.
4. Use `log_analyzer.py` directly when investigating a specific failure.
