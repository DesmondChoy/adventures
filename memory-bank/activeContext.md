# Active Context

## Core Architecture

1. **Adventure Flow (`app/routers/web.py`, `app/services/chapter_manager.py`):**
   * ChapterType enum: LESSON, STORY, REFLECT, CONCLUSION
   * Content sources in `prompt_engineering.py`:
     - LESSON: `lessons.csv` + LLM wrapper
     - STORY: Full LLM generation with choices
     - REFLECT: Narrative-driven follow-up to LESSON
     - CONCLUSION: Resolution without choices

2. **Chapter Sequencing (`chapter_manager.py`):**
   * First chapter: STORY
   * Second-to-last: STORY
   * Last chapter: CONCLUSION
   * 50% of remaining: LESSON (subject to available questions)
   * 50% of LESSON chapters: REFLECT (follow LESSON)
   * STORY chapters follow REFLECT chapters
   * No consecutive LESSON chapters

3. **State Management (`adventure_state_manager.py`):**
   * Robust choice validation
   * State consistency preservation
   * Error recovery mechanisms
   * Metadata tracking for agency, elements, and challenge types

## Recent Changes

### Streamlined Prompts for All Chapters (2025-03-01)
- Extended streamlined approach to all chapter types in `prompt_templates.py` and `prompt_engineering.py`
- Created unified `build_prompt()` function for all chapter types
- Removed redundant files and conditional checks in `providers.py`
- Reduced token usage while preserving essential guidance

### Enhanced Image Generation (2025-03-01)
- Increased retries from 2 to 5 in `generate_image_async()` and `_generate_image()`
- Added robust null checking to prevent "NoneType has no len()" errors
- Standardized to use `GOOGLE_API_KEY` environment variable
- Implemented graceful fallbacks for failed image generation

### Agency Implementation (2025-02-28)
- First chapter agency choice from four categories stored in `state.metadata["agency"]`
- Agency evolution in REFLECT chapters based on correct/incorrect answers
- Agency tracking in `update_agency_references()` in `adventure_state_manager.py`
- Agency guidance templates in `prompt_templates.py`

### Narrative Improvements (2025-02-28)
- Story Object Method in `build_lesson_chapter_prompt()` for intuitive narrative bridges
- Unified REFLECT chapter approach in `build_reflect_chapter_prompt()`
- Phase-specific choice instructions via `get_choice_instructions(phase)`
- Markdown-based prompt structure for better organization

## Testing Framework

- **Simulation (`tests/simulations/story_simulation.py`):**
  * Generates structured log data with standardized prefixes
  * Verifies complete workflow execution
  * Validates component integration

- **Test Files:**
  * `test_simulation_functionality.py`: Verifies chapter sequences, ratios, state transitions
  * `test_simulation_errors.py`: Tests error handling, recovery, logging configuration
  * `run_simulation_tests.py`: Orchestrates server, simulation, and test execution
