# Active Context

## Architecture and Implementation

The project is focused on implementing core Learning Odyssey features, including:

1.  **Adventure Flow Implementation:**
    *   Landing page topic and length selection (`app/routers/web.py`).
    *   ChapterType determination (LESSON/STORY/REASON/CONCLUSION) in `app/services/chapter_manager.py`.
    *   Content source integration in `app/services/llm/prompt_engineering.py`:
        *   LESSON chapters: `lessons.csv` + LLM narrative wrapper.
        *   STORY chapters: Full LLM generation with choices.
        *   REASON chapters: Follow-up to LESSON chapters to test deeper understanding.
            * For correct answers: Multiple challenge types (confidence_test, application, connection_making, teaching_moment)
            * For incorrect answers: Structured educational reflection with "aha moment"
            * Challenge type tracking in AdventureState metadata for debugging
        *   CONCLUSION chapters: Full LLM generation without choices.
    *   Narrative continuity via prompt engineering.

2.  **Content Management (`app/data/`):**
    *   `lessons.csv` integration for LESSON chapters.
    *   `new_stories.yaml` templates for STORY chapters.
    *   LLM response validation.
    *   History tracking in `AdventureState`.
    *   Element consistency tracking via metadata.

3.  **Chapter Sequencing (`app/services/chapter_manager.py`):**
    *   First chapter: Always STORY (changed from first two chapters).
    *   Second-to-last chapter: Always STORY.
    *   Last chapter: Always CONCLUSION.
    *   50% of remaining chapters, rounded down: LESSON (subject to available questions).
    *   No consecutive LESSON chapters allowed.
    *   50% of LESSON chapters, rounded down: REASON chapters.
    *   REASON chapters only occur immediately after a LESSON chapter.
    *   STORY chapters must follow REASON chapters.

4.  **Testing Strategy (`tests/simulations/`):**
    *   Story simulation framework.
    *   Response validation.
    *   State verification.
    *   Error handling coverage.
    *   Element consistency validation.

5. **User Experience (`app/routers/web.py`):**
    * Topic selection interface.
    * Adventure length selection.
    * Real-time feedback system.
    * WebSocket state updates.
    * Progress tracking visualization.

## Recent Changes

### Enhanced REASON Chapter Implementation (2025-02-27)
- Improved `build_reason_chapter_prompt()` in `app/services/llm/prompt_engineering.py`:
  * Added variety to correct answer handling with different challenge types:
    - `confidence_test`: Tests if they'll stick with their original answer
    - `application`: Tests if they can apply the concept in a new scenario
    - `connection_making`: Tests if they can connect the concept to broader themes
    - `teaching_moment`: Tests if they can explain the concept to another character
  * Restructured incorrect answer handling with a more educational approach
  * Added challenge type tracking in AdventureState metadata:
    - Structured history in `state.metadata["reason_challenge_history"]`
    - Quick access via `state.metadata["last_reason_challenge_type"]`
    - Debug logging for selected challenge types

See progress.md for detailed change history.

## Current Considerations

### State Management System (`app/services/adventure_state_manager.py`)
- Primary focus:
  * Robust choice validation
  * State consistency preservation
  * Error recovery mechanisms
  * Comprehensive logging
- Current status:
  * Successfully handles choice extraction
  * Maintains state consistency
  * Provides fallback mechanisms
  * Generates default choices when needed
  * Implements proper error handling

### Metadata Usage
- The AdventureState metadata field is now used for:
  * Non-random elements tracking
  * Plot twist guidance
  * Story category tracking
  * Initialization timestamp
  * Element consistency tracking
  * Previous hints tracking
  * REASON challenge type tracking (new)
- This provides a flexible way to store additional information without changing the core data model

### Simulation Framework (`tests/simulations/story_simulation.py`)
- Dual purpose:
  * **Primary: Data Generation Tool**
    - Produces structured log data for subsequent test analysis
    - Captures complete user journeys through the application
    - Generates consistent output that dedicated test files will analyze
  * **Secondary: End-to-End Verification**
    - Verifies that the complete workflow executes successfully
    - Acts as a basic smoke test for the integrated system
    - Validates that all components can work together

### Test Files
- Two complementary test files:
  * **`test_simulation_functionality.py`**: Tests the functional correctness of the simulation system
    - Verifies chapter sequences (ensuring proper STORY/LESSON/CONCLUSION ordering)
    - Validates lesson ratio (approximately 50% of flexible chapters)
    - Checks lesson success rate calculations
    - Verifies simulation metadata
    - Tests state transition consistency
  * **`test_simulation_errors.py`**: Tests error handling and recovery mechanisms
    - Verifies error detection and classification
    - Tests logging level configuration
    - Validates error recovery mechanisms
    - Performs comprehensive error analysis
    - Checks for absence of critical errors

- Current status:
  * Successfully generates structured log data with standardized prefixes
  * Captures all state transitions throughout user journeys
  * Maintains WebSocket communication with proper error handling
  * Implements robust retry logic for connection failures
  * Functions as intended for both data generation and basic verification
  * Validates element consistency and tracks plot twist development

- Recent optimizations (2025-02-25):
  * Fixed story length to match codebase (constant 10 chapters)
  * Removed real-time content streaming for testing efficiency
  * Enhanced logging with standardized prefixes for automated parsing:
    - `CHAPTER_TYPE:` - Logs chapter types (STORY, LESSON, CONCLUSION)
    - `CHOICE:` - Logs user choice selections
    - `LESSON:` - Logs lesson answer correctness
    - `STATS:` - Logs story completion statistics
  * Added content preview logging for better traceability
  * Updated documentation with detailed implementation information
  * Renamed README.md to SIMULATION_GUIDE.md for clarity
  * Clarified the simulation's role as a data generation tool rather than a test suite

- Test integration:
  * Both test files analyze the simulation output from different perspectives
  * Tests verify specific behaviors and requirements:
    - Process sequence validation (e.g., `process_consequences()` after LESSON chapters)
    - Chapter type sequence verification
    - Phase assignment validation
    - Content loading and sampling verification
    - State transition consistency checks
    - Error handling and recovery mechanisms
