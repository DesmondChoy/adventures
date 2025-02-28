# Active Context

## Architecture and Implementation

The project is focused on implementing core Learning Odyssey features, including:

1.  **Adventure Flow Implementation:**
    *   Landing page topic and length selection (`app/routers/web.py`).
    *   ChapterType determination (LESSON/STORY/REFLECT/CONCLUSION) in `app/services/chapter_manager.py`.
    *   Content source integration in `app/services/llm/prompt_engineering.py`:
        *   LESSON chapters: `lessons.csv` + LLM narrative wrapper.
        *   STORY chapters: Full LLM generation with choices.
        *   REFLECT chapters: Follow-up to LESSON chapters to test deeper understanding.
            * Unified narrative-driven approach for both correct and incorrect answers
            * Story-driven choices without labeling any as "correct" or "wrong"
            * Uses Socratic method to guide deeper understanding through questions
            * Approach tracking in AdventureState metadata for debugging
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
    *   **Priority Rules:**
        * No consecutive LESSON chapters allowed (highest priority).
        * At least 1 REFLECT chapter in every scenario (required).
        * Every LESSON assumes at least 3 questions available.
        * Accept 25% of scenarios where there are two LESSON chapters (optimization tradeoff).
    *   50% of LESSON chapters, rounded down: REFLECT chapters.
    *   REFLECT chapters only occur immediately after a LESSON chapter.
    *   STORY chapters must follow REFLECT chapters.

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

### REFLECT Chapter Refactoring for Narrative Integration (2025-02-28)
- Refactored the REFLECT chapter implementation in `app/services/llm/prompt_templates.py` and `app/services/llm/prompt_engineering.py`:
  * Created a unified narrative-driven approach for both correct and incorrect answers
  * Updated `REFLECT_CHOICE_FORMAT` to remove the "correct/incorrect" structure
  * Created a unified template (`REFLECT_TEMPLATE`) with configuration objects for different answer types
  * Made all choices story-driven without labeling any as "correct" or "wrong"
  * Used the Socratic method to guide deeper understanding through questions
  * Updated metadata tracking to use the new approach
  * This makes REFLECT chapters feel like a natural part of the character's journey rather than a separate educational module

### Removed Obsolete CHOICE_FORMAT_INSTRUCTIONS (2025-02-28)
- Removed the obsolete `CHOICE_FORMAT_INSTRUCTIONS` constant:
  * Removed the import from `prompt_engineering.py`
  * Removed the constant definition from `prompt_templates.py`
  * Verified no other references existed in the codebase
  * The code was already using the more dynamic `get_choice_instructions(story_phase)` function
  * This improves code maintainability by removing unused code

### UI Fix - Hide "Swipe to explore" Tip on Desktop (2025-02-28)
- Fixed an issue where the "Swipe to explore" tip was showing on desktop devices in `app/static/css/carousel.css`:
  * Added a media query to hide the swipe tip on desktop devices (screen width > 768px)
  * Kept the tip visible on mobile devices where swiping is a relevant interaction
  * Maintained the existing functionality where the tip fades out after a few seconds or on user interaction
  * This improves the user experience by only showing interaction hints that are relevant to the user's device

### Lesson Chapter Prompt Improvement with Story Object Method (2025-02-28)
- Improved the lesson chapter generation prompt in `app/services/llm/prompt_templates.py` and `app/services/llm/prompt_engineering.py`:
  * Condensed the CRITICAL RULES to three succinct points for better LLM comprehension
  * Implemented the "Story Object Method" for creating more intuitive narrative bridges
  * Added requirement to include the exact question verbatim in the narrative
  * Provided more flexibility in where the question can appear for more natural flow
  * Updated the USER_PROMPT_TEMPLATE to be consistent with the new approach
  * Modified the `_build_chapter_prompt` function to replace the [Core Question] placeholder with the actual question
  * This addresses issues where the narrative didn't explicitly reference the question being asked, making it difficult for users to answer correctly

### Phase-Specific Choice Instructions Implementation (2025-02-27)
- Implemented phase-specific choice instructions in `app/services/llm/prompt_templates.py` and `app/services/llm/prompt_engineering.py`:
  * Created `BASE_CHOICE_FORMAT` with common choice format instructions
  * Added `CHOICE_PHASE_GUIDANCE` dictionary with appropriate guidance for each phase:
    - Exposition: "Character Establishment: Choices should reveal character traits and establish initial direction"
    - Rising: "Plot Development: Choices should subtly hint at the emerging plot twist"
    - Trials: "Challenge Response: Choices should show different approaches to mounting challenges"
    - Climax: "Critical Decision: Choices should represent pivotal decisions with significant consequences"
    - Return: "Resolution: Choices should reflect the character's growth and transformation"
  * Implemented `get_choice_instructions(phase)` function to get appropriate instructions for a given phase
  * Updated `prompt_engineering.py` to use phase-specific instructions
  * Created a test script to verify the implementation
  * Fixed inconsistency where plot twist guidance was incorrectly appearing in Exposition phase
  * Ensured plot twist guidance only appears in appropriate phases (Rising, Trials, Climax)

### LLM Prompt Optimization with Markdown Structure (2025-02-27)
- Restructured LLM prompts in `app/services/llm/prompt_templates.py` and `app/services/llm/prompt_engineering.py`:
  * Implemented markdown-based structure for better organization and readability
  * Created clear visual hierarchy with headings and subheadings
  * Enhanced formatting for lesson answers and lesson history
  * Fixed continuity guidance formatting issue that was causing empty bullet points
  * Created a test script to verify the new prompt structure
  * Improved the overall clarity and effectiveness of prompts for all chapter types

### Enhanced REFLECT Chapter Implementation (2025-02-27)
- Improved `build_reflect_chapter_prompt()` in `app/services/llm/prompt_engineering.py`:
  * Added variety to correct answer handling with different challenge types:
    - `confidence_test`: Tests if they'll stick with their original answer
    - `application`: Tests if they can apply the concept in a new scenario
    - `connection_making`: Tests if they can connect the concept to broader themes
    - `teaching_moment`: Tests if they can explain the concept to another character
  * Restructured incorrect answer handling with a more educational approach
  * Added challenge type tracking in AdventureState metadata:
    - Structured history in `state.metadata["reflect_challenge_history"]`
    - Quick access via `state.metadata["last_reflect_challenge_type"]`
    - Debug logging for selected challenge types

See progress.md for detailed change history.

## Current Considerations

### Agency Implementation
The adventure now includes a form of agency through a pivotal choice made in the first chapter:

1. **First Chapter Agency Choice**
   - User selects from one of four categories in the first chapter:
     * Magical Item to Craft (lantern, rope, amulet, map, watch, potion)
     * Companion to Choose (owl, fox, squirrel, deer, otter, turtle)
     * Role or Profession (healer, scholar, guardian, pathfinder, diplomat, craftsperson)
     * Special Ability (animal whisperer, puzzle master, storyteller, element bender, dream walker, pattern seer)
   - Choice is stored in `state.metadata["agency"]` with:
     * Type (item, companion, role, ability)
     * Name (specific choice made)
     * Description (full choice text)
     * Properties (for tracking evolution)
     * Growth history (for tracking changes)
     * References (chapters where it appears)

2. **Agency Continuity**
   - The agency element is referenced throughout all chapters
   - In REFLECT chapters, agency evolves based on correct/incorrect answers:
     * Correct answers: Agency is empowered or reveals new capabilities
     * Incorrect answers: Agency adapts to incorporate new knowledge
   - In CLIMAX phase, agency plays a pivotal role with choices reflecting different ways to use it
   - In CONCLUSION chapter, agency has a meaningful resolution showing its evolution

3. **Technical Implementation**
   - `websocket_service.py`: Detects and stores agency choice from first chapter
   - `adventure_state_manager.py`: Tracks agency references throughout chapters
   - `prompt_engineering.py`: Incorporates agency into chapter prompts
   - `prompt_templates.py`: Provides templates for agency guidance

4. **Agency Evolution**
   - Agency element grows stronger through correct answers
   - Agency element adapts through incorrect answers
   - Agency element plays a crucial role in the climax
   - Agency element has a satisfying resolution in the conclusion

### Prompt Engineering Improvements
- The Story Object Method provides a more concrete approach to creating narrative bridges:
  * Uses a single visually interesting story object to connect to the educational question
  * Makes the connection between story world and educational content more intuitive
  * Provides open-ended guidance for different question types (historical, scientific, mathematical, geographical)
  * Ensures the exact question appears verbatim in the narrative
  * Allows more flexibility in where the question appears for more natural narrative flow

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
  * REFLECT challenge type tracking
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

- Test integration:
  * Both test files analyze the simulation output from different perspectives
  * Tests verify specific behaviors and requirements:
    - Process sequence validation (e.g., `process_consequences()` after LESSON chapters)
    - Chapter type sequence verification
    - Phase assignment validation
    - Content loading and sampling verification
    - State transition consistency checks
    - Error handling and recovery mechanisms
