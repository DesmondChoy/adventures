# Story Simulations

This directory contains scripts and documentation for simulating user interactions with the Learning Odyssey application. These simulations are used for testing, debugging, and validating the application's functionality.

## Files

- `story_simulation.py`: A Python script that simulates user interaction with the story generation WebSocket API
- `simulation_plan.md`: Detailed documentation of the simulation script's implementation and usage

## Usage

1. Ensure the FastAPI application is running:
   ```bash
   uvicorn app.main:app --reload
   ```

2. Run the simulation script:
   ```bash
   python tests/simulations/story_simulation.py
   ```

## Purpose

The simulation tools in this directory serve several purposes:
1. Testing the WebSocket communication
2. Validating story generation flow
3. Debugging LLM interactions
4. Testing lesson integration
5. Verifying choice selection logic

For detailed implementation information, refer to `simulation_plan.md`. 