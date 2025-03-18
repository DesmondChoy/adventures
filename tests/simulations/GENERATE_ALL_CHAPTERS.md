# Generate All Chapters for Learning Odyssey

This script simulates a user going through the Learning Odyssey app experience to generate ten chapters. It randomly selects a story category and lesson topic, then makes random choices for each chapter to complete the adventure.

## Features

- Generates all 10 chapters plus the summary chapter
- Makes random choices for each chapter
- Captures all chapter content, including the conclusion chapter
- Logs the complete simulation for analysis
- Saves the entire state to a JSON file for later use
- Properly handles WebSocket connections with retry logic
- Includes comprehensive error handling and logging

## Usage

```bash
python tests/simulations/generate_all_chapters.py [--category CATEGORY] [--topic TOPIC]
```

### Options

- `--category`: Specify a story category (e.g., "enchanted_forest_tales")
- `--topic`: Specify a lesson topic (e.g., "Singapore History")

If not specified, the script will randomly select a story category and lesson topic.

## Output

The script generates several output files:

1. **Log File**: `logs/simulations/chapter_generator_[TIMESTAMP]_[RUN_ID].log`
   - Contains detailed logs of the simulation process
   - Includes structured events for chapter starts, choices, and completions
   - Useful for debugging and analysis

2. **State File**: `logs/simulations/simulation_state_[TIMESTAMP]_[RUN_ID].json`
   - Contains the complete AdventureState with all chapters
   - Includes chapter content, choices, and metadata
   - Can be loaded for further analysis or processing

## How It Works

1. The script connects to the Learning Odyssey WebSocket server
2. It initializes a new adventure with a random story category and lesson topic
3. For each chapter:
   - It receives and processes the chapter content
   - It extracts the available choices
   - It randomly selects a choice and sends it to the server
   - It stores the chapter content and choice in the simulation state
4. For the conclusion chapter (Chapter 10):
   - It processes the chapter content
   - It sends the "reveal_summary" choice to generate the adventure summary
5. It processes the adventure summary and stores it as an additional chapter
6. Finally, it saves the complete state to a JSON file

## Requirements

- The Learning Odyssey app server must be running at `localhost:8000`
- Python 3.8+ with the following packages:
  - websockets
  - asyncio
  - json
  - random
  - pydantic

## Example

```bash
# Generate chapters with random story category and lesson topic
python tests/simulations/generate_all_chapters.py

# Generate chapters with specific story category and lesson topic
python tests/simulations/generate_all_chapters.py --category "enchanted_forest_tales" --topic "Singapore History"
```

## Notes

This script is the consolidated version of several previous simulation scripts (story_simulation.py, chapter_generator.py, etc.) and now serves as the primary tool for generating complete adventures for testing and analysis purposes.
