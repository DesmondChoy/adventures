# Chapter Summary Generator

A utility script for generating consistent chapter summaries for all chapters in a Learning Odyssey adventure.

## Overview

The Chapter Summary Generator extracts chapter content from simulation log files and generates summaries for all chapters using the same prompt template and approach. This ensures consistency across all chapter summaries, including the CONCLUSION chapter.

## Features

- Extracts chapter content from simulation log files
- Generates summaries using the same prompt template for all chapters
- Uses the same function to generate summaries for all chapters (no special cases)
- Handles missing chapters gracefully by continuing to process available chapters
- Provides both standard and compact output formats
- Supports skipping JSON file creation with `--no-json` flag
- Includes detailed error handling and logging

## Usage

```bash
# Using the latest simulation log file
python tests/simulations/generate_chapter_summaries.py

# Specifying a particular log file
python tests/simulations/generate_chapter_summaries.py logs/simulations/simulation_2025-03-17_12345678.log

# Using compact output format
python tests/simulations/generate_chapter_summaries.py --compact

# Save to JSON file (by default, no JSON is saved)
python tests/simulations/generate_chapter_summaries.py --save-json

# Combining options
python tests/simulations/generate_chapter_summaries.py --compact --save-json
```

## Output Formats

### Standard Format

The standard output format includes detailed formatting with headers and separators:

```
================================================================================
CHAPTER SUMMARIES
================================================================================

Chapter 1 (STORY):
[Summary text for chapter 1]
----------------------------------------

Chapter 2 (LESSON):
[Summary text for chapter 2]
----------------------------------------

... and so on
```

### Compact Format

The compact output format provides a more concise display with one line per chapter:

```
CHAPTER SUMMARIES

CHAPTER 1 (STORY): [Summary text for chapter 1]
CHAPTER 2 (LESSON): [Summary text for chapter 2]
...
```

## Error Handling

The script includes robust error handling that allows it to continue processing even if some chapters are missing from the log file. If a chapter is not found, the script will:

1. Log a warning message
2. Skip the missing chapter
3. Continue processing the remaining chapters
4. Display summaries for all successfully processed chapters
5. Save summaries to JSON file only if explicitly requested with `--save-json`

This makes the script more resilient when working with incomplete simulation logs.

## Implementation Details

- Uses direct API call to Gemini with fallback to streaming approach
- Implements retry logic with exponential backoff for reliability
- Standardizes summary generation across all chapter types
- Maintains consistent parameters for all chapters
- Provides detailed logging for debugging and monitoring

## Integration with Other Tools

This script complements the existing simulation tools:

- `run_simulation_tests.py`: Runs simulations and generates log files
- `show_summary_from_log.py`: Displays the summary chapter from a log file
- `story_simulation.py`: Core simulation logic

The Chapter Summary Generator provides a way to generate consistent summaries for all chapters, which can be useful for testing and debugging the summary chapter functionality.
