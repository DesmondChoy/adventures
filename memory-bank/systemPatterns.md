# System Patterns

## Architecture Overview
```mermaid
graph TD
    Client[Web Client] <--> WSR[WebSocket Router]
    WSR <--> WSS[WebSocket Service]
    WSS <--> ASM[Adventure State Manager]
    ASM <--> AS[AdventureState]
    ASM <--> CM[Chapter Manager]
    CM <--> LLM[LLM Service]
    CM <--> DB[(Database)]

    subgraph Client Side
        LP[localStorage] <--> CSM[Client State Manager]
        CSM <--> Client
    end

    subgraph Core State
        AS
    end

    subgraph Services
        WSS
        ASM
        CM
        LLM
    end

    subgraph Routing
        WSR
    end

    subgraph Content Sources
        CSV[lessons.csv] --> CM
        LLM --> CM
    end
```

## Component Architecture

### 1. Client-Side State Management
- **AdventureStateManager Class**
  * Uses localStorage for persistence
  * Independent of cookies
  * Maintains complete chapter history
  * Enables seamless recovery
  * CRITICAL: Cannot cache future content due to LLM dependency

- **WebSocket Connection Management**
  * Exponential backoff (1s to 30s)
  * Maximum 5 reconnection attempts
  * Automatic state restoration
  * Silent recovery attempts
  * Connection health monitoring

- **Error Handling**
  * Clear user feedback
  * Graceful degradation
  * Automatic recovery attempts
  * Progress preservation
  * CRITICAL: Must maintain server connection for LLM generation

### 2. AdventureState (`app/models/story.py`)
- Centralized adventure state management.
- Chapter progression tracking.
- Adventure length handling.
- ChapterType enum management (LESSON/STORY/REASON/CONCLUSION).
- Question and answer tracking.
- Narrative continuity enforcement.
- Metadata tracking for element consistency.

### 3. WebSocket Components

#### WebSocket Router (`app/routers/websocket_router.py`)
- Core routing and connection management:
  * Handles WebSocket endpoint definition
  * Manages connection lifecycle (accept/disconnect)
  * Receives and validates client messages
  * Coordinates with WebSocket Service for processing
- State initialization and updates:
  * Works with AdventureStateManager for state handling
  * Validates state during initialization
  * Ensures state consistency across updates
  * Handles error recovery for state issues

#### WebSocket Service (`app/services/websocket_service.py`)
- Core business logic implementation:
  * Processes user choices and generates responses
  * Manages chapter content generation
  * Handles streaming of content to client
  * Coordinates state updates with AdventureStateManager
- Message handling:
  * Processes choice data
  * Generates chapter content
  * Manages streaming optimization
  * Formats and sends responses
- Error handling:
  * Manages content generation errors
  * Handles state transition issues
  * Provides fallback responses
  * Maintains connection stability

### 4. Adventure State Manager (`app/services/adventure_state_manager.py`)
- Centralized management of `AdventureState`.
- Handles initialization, updates, and retrieval of the adventure state.
- Encapsulates state manipulation logic, decoupling it from the WebSocket router.

### 5. Chapter Manager (`app/services/chapter_manager.py`)
- **Chapter Type Pattern:**
  - Adventure length selection at landing page.
  - Chapter sequence determined by ChapterManager:
    * First chapter: STORY (for setting/character development)
    * Second-to-last chapter: STORY (for pivotal choices)
    * Last chapter: CONCLUSION (for story resolution)
    * 50% of remaining chapters, rounded down: LESSON (subject to available questions)
    * **Priority Rules:**
      - No consecutive LESSON chapters allowed (highest priority)
      - At least 1 REASON chapter in every scenario (required)
      - Every LESSON assumes at least 3 questions available
      - Accept 25% of scenarios where there are two LESSON chapters (optimization tradeoff)
    * 50% of LESSON chapters, rounded down: REASON chapters
    * REASON chapters only occur immediately after a LESSON chapter
    * STORY chapters must follow REASON chapters
  - LESSON chapters limited by available questions in `lessons.csv`.
  - STORY chapters use full LLM generation with choices.
  - REASON chapters test deeper understanding of previous LESSON chapter.
  - CONCLUSION chapters use full LLM generation without choices.
  - The chapter type for each chapter during the adventure is determined using `state.planned_chapter_types`.
- Adventure flow control.
- Question availability validation.
- Error recovery mechanisms.

### 6. LLM Integration (`app/services/llm/`)
- Provider-agnostic implementation.
- **Narrative generation for all chapter types (using prompts in `app/services/llm/prompt_engineering.py`)**:
  * LESSON: Question-based narrative with educational focus
  * STORY: Choice-driven narrative with three options
  * REASON: Follow-up to LESSON chapters to test deeper understanding
    - For correct answers: Multiple challenge types to test understanding:
      * `confidence_test`: Tests if they'll stick with their original answer
      * `application`: Tests if they can apply the concept in a new scenario
      * `connection_making`: Tests if they can connect the concept to broader themes
      * `teaching_moment`: Tests if they can explain the concept to another character
    - For incorrect answers: Structured educational approach:
      * Educational reflection: Gently revealing the correct concept
      * Narrative deepening: Using the story environment to illustrate the concept
      * "Aha moment": Creating a moment where understanding clicks
      * Story-integrated choices: Testing understanding while advancing the story
    - Challenge type tracking in AdventureState metadata for debugging
    - Uses diverse storytelling techniques for reflective moments

### 7. State Management Pattern
- Centralized AdventureState:
  * Single source of truth for all state
  * Complete state serialization
  * Pre-determined chapter sequence via `planned_chapter_types`
  * Question data persistence
  * Story length constraints (5-10 chapters)
  * Recovery mechanisms
  * Metadata tracking for element consistency
  * Critical state preservation during updates:
    - selected_narrative_elements
    - selected_sensory_details
    - selected_theme
    - selected_moral_teaching
    - selected_plot_twist
    - metadata
    - planned_chapter_types
    - story_length
    - current_storytelling_phase

- **Navigation State Pattern:**
  * Separation of Concerns:
    - Sequential Tracking (`chapter_number`):
      * ChapterManager's domain
      * Handles progression logic
      * Manages chapter sequencing
      * Controls story length
    - Navigation Tracking (`current_chapter_id`):
      * WebSocket router's domain
      * Manages routing/navigation
      * Handles state restoration
      * Controls narrative branching

  * Educational Benefits:
    - Comprehensive Progress Tracking:
      * Linear progress via `chapter_number`
      * Learning paths via `current_chapter_id`
      * Student decision analysis
      * Personalized narrative branches
    - Learning Assessment:
      * Track correct/incorrect answers
      * Monitor decision patterns
      * Analyze learning strategies
      * Measure concept understanding

  * System Architecture Benefits:
    - Clear Separation of Concerns:
      * Progression logic isolated
      * Navigation handling separated
      * Clean component boundaries
      * Reduced system coupling
    - Maintainability:
      * Independent component testing
      * Simplified debugging
      * Clear responsibility boundaries
      * Easier system extensions

  * Implementation Details:
    - Sequential Tracking:
      * `chapter_number` (integer): Linear progression (1, 2, 3...)
      * Used by ChapterManager for sequence validation
      * Ensures proper chapter ordering
      * Critical for chapter type determination
    
    - Navigation Tracking:
      * `current_chapter_id` (string): User's path through content
      * Values:
        - "start": Initial state
        - "correct"/"wrongX": Lesson responses
        - "chapter_X_Y": Story choice paths
      * Critical for client-server synchronization
      * Enables branching narrative paths

  * State Synchronization:
    - WebSocket Updates:
      * Sends `current_chapter_id` for client updates
      * Validates `chapter_number` for progression
      * Maintains bidirectional state sync
      * Handles connection recovery
    - Error Recovery:
      * State reconstruction from either tracker
      * Connection interruption handling
      * Client state restoration
      * Integrity validation

  * **Important Implementation Detail:** The `story_category` and `lesson_topic` are passed as URL parameters to the WebSocket endpoint and are not included in the `validated_state`.

- Chapter Type Management:
  * Sequence determined upfront by ChapterManager
  * Stored in `AdventureState.planned_chapter_types`
  * Used consistently across all components
  * No hard-coded assumptions about chapter types
  * Maintains state integrity throughout adventure
  * The chapter type for each chapter is determined using `state.planned_chapter_types`

### 8. Question Handling Pattern
- Question Lifecycle:
  1. Sample question from `lessons.csv` (handled by `ChapterManager`)
  2. Store with chapter data
  3. Use for response creation
  4. Persist through state updates
- State Consistency:
  1. Store question on chapter creation
  2. Include in state serialization
  3. Restore from client state
  4. Use for response handling
- Error Management:
  1. Validate question data
  2. Handle missing questions
  3. Recover from errors
  4. Maintain state consistency

### 9. Content Management Pattern
- Lesson questions from `lessons.csv`.
- LLM-generated narratives (via `app/services/llm/prompt_engineering.py`).
- LLM-generated story choices (via `app/services/llm/prompt_engineering.py`).
- LLM-generated conclusions (via `app/services/llm/prompt_engineering.py`).
- Narrative continuity enforcement.
- Consequence handling.

## Story Elements Pattern
1.  Element Selection from `new_stories.yaml`:
    - Random sampling happens once at state initialization:
      * One element from each `narrative_elements` category
      * One element from each `sensory_details` category
    - Non-random elements (`name`, `description`, `tone`) are extracted and validated separately
    - CRITICAL: Selected elements stored in AdventureState
    - CRITICAL: All elements must remain consistent throughout adventure
    - CRITICAL: Validation ensures all required elements are present

2.  Plot Twist Integration:
    - Phase-specific guidance via get_plot_twist_guidance():
      * Exposition: Subtle hints and background elements only
      * Rising: Begin connecting previous hints, maintain mystery
      * Trials: Build tension and increase visibility of hints
      * Climax: Full revelation and impact of the twist
      * Return: Show aftermath and consequences
    - CRITICAL: Plot twist must evolve naturally
    - CRITICAL: Previous hints must connect logically
    - CRITICAL: Guidance stored in state metadata

3.  Element Consistency Management:
    - Metadata field in AdventureState tracks:
      * Non-random elements
      * Plot twist guidance
      * Element consistency
      * Initialization timestamp
    - CRITICAL: All elements validated during initialization
    - CRITICAL: Metadata provides consistency checks throughout adventure
    - CRITICAL: Error recovery maintains element consistency

4.  Error Handling and Validation:
    - Comprehensive validation in select_random_elements:
      * Required categories checked
      * Element types validated
      * Non-empty values ensured
    - Detailed error messages and logging
    - Proper error propagation
    - Recovery mechanisms maintain consistency
    - CRITICAL: Validation failures prevent state corruption

5.  `sensory_details` integration into build_system_prompt():
    - Visual elements for scene setting
    - Sound elements for atmosphere
    - Smell elements for immersion
    - CRITICAL: Weave naturally into narrative
    - CRITICAL: Support current story phase
    - CRITICAL: Consistent with metadata tracking

## Narrative Continuity Pattern (`app/services/llm/prompt_engineering.py`)
1. Story Elements Consistency:
   - Maintain selected setting throughout
   - Keep character archetypes consistent
   - Follow selected story rules
   - Develop chosen theme
   - Reinforce moral teaching
   - CRITICAL: Reference established elements

2. Previous Chapter Impact:
   - After LESSON Chapter (Correct or Incorrect Answer):
     * Triggers `process_consequences()` in `prompt_engineering.py`
     * This function generate appropriate story consequences based on lesson response
     * CRITICAL: Include answer in state
   
   - After STORY Chapter:
     * Continue from chosen path
     * Reference choice details
     * Show consequences
     * Maintain world state
     * CRITICAL: Include choice context
   
   - After CONCLUSION Chapter:
     * No further narrative
     * Return to Landing Page
     * CRITICAL: No state updates

3. Plot Twist Development:
   - Rising Phase:
     * Plant subtle hints
     * Create background elements
     * Maintain subtlety
     * CRITICAL: Don't reveal too much
   
   - Trials Phase:
     * Connect previous hints
     * Build tension
     * Increase visibility
     * CRITICAL: Maintain mystery
   
   - Climax Phase:
     * Reveal full twist
     * Connect all hints
     * Show impact
     * CRITICAL: Satisfying resolution

- Continuity Enforcement:
  1. LLM Prompt Engineering:
     - CRITICAL: All state properties must be in prompt
     - Complete chapter history required
     - Recent decisions/answers highlighted
     - Consequence guidelines enforced
     - Character development maintained
     - Error if state data missing
  
  2. State Management:
     - Track all chapter outcomes in AdventureState
     - Maintain complete decision history
     - Record learning progress with timestamps
     - Ensure consistent references
     - Implement state recovery for prompt failures

- Cross-Chapter Connections:
  1. Knowledge Integration:
     - Connect LESSON content to STORY events
     - Use previous LESSON content in choices
     - Build upon established concepts
     - Create learning callbacks
     - CRITICAL: Track concept relationships in state
  
  2. Character Development:
     - Consistent personality traits
     - Growth from experiences
     - Learning from mistakes
     - Decision impact on character
     - CRITICAL: Maintain character state history

- Error Recovery:
  1. Prompt Failures:
     - Log complete prompt content
     * Track missing state properties
     * Implement fallback responses
     * Maintain narrative consistency
  
  2. State Inconsistency:
     * Detect narrative discontinuity
     * Implement state recovery
     * Log recovery attempts
     * Maintain error boundaries

## Component Relationships

### Initial Flow
1. User selects topic and length at landing.
2. `ChapterManager` determines chapter sequence:
   - First chapter: STORY (for setting/character development)
   - Second-to-last chapter: STORY (for pivotal choices)
   - Last chapter: CONCLUSION (for story resolution)
   - 50% of remaining chapters, rounded down: LESSON (subject to available questions)
   - No consecutive LESSON chapters allowed
   - 50% of LESSON chapters, rounded down: REASON chapters
   - REASON chapters only occur immediately after a LESSON chapter
   - STORY chapters follow REASON chapters
3. First chapter (STORY) begins.
4. LLM generates narrative with choices.
5. State tracks progression.

### Chapter Progression
1. Content source varies by chapter type:
   - Lesson: `lessons.csv` + LLM narrative with educational focus
   - Story: Full LLM generation with three choices
   - Reason: Follow-up to LESSON chapters to test deeper understanding
     * For correct answers: Multiple challenge types (confidence_test, application, connection_making, teaching_moment)
     * For incorrect answers: Structured educational approach with "aha moment"
     * Challenge type tracking in AdventureState metadata for debugging
     * Uses creative storytelling techniques for reflective moments
   - Conclusion: Full LLM generation without choices
2. Narrative continuity maintained.
3. Previous chapter consequences reflected.
4. No repeat questions in session.
5. No consecutive LESSON chapters allowed.
6. REASON chapters only follow LESSON chapters.
7. STORY chapters follow REASON chapters.

## Technical Details and Testing
- **Question Handling:** Dynamic sampling, answer shuffling, duplicate prevention, topic management.
- **State Management:** Complete state tracking, question history, answer selections, performance metrics.
- **Testing Automation:** Question sampling tests, answer shuffling validation, flow verification, state consistency.

### Testing Framework (`tests/`)
```mermaid
graph TD
    Tests[tests/] --> Simulations[simulations/]
    Simulations --> SimScript[story_simulation.py]
    Simulations --> FuncTests[test_simulation_functionality.py]
    Simulations --> ErrorTests[test_simulation_errors.py]
    Simulations --> LogUtils[log_utils.py]
    Simulations --> Docs[Documentation Files]
    
    Docs --> TestingMD[SIMULATION_TESTING.md]
    Docs --> GuideMD[SIMULATION_GUIDE.md]
    Docs --> SummaryMD[TEST_SUMMARY.md]
```

#### Test Structure and Organization
- **Root Directory**: `tests/` contains all testing code
- **Simulation Tests**: `tests/simulations/` focuses on end-to-end testing through simulation
- **Test Files**:
  * `test_simulation_functionality.py`: Tests functional correctness of the simulation system
    - Verifies chapter sequences (STORY/LESSON/CONCLUSION ordering)
    - Validates lesson ratio (approximately 50% of flexible chapters)
    - Checks lesson success rate calculations
    - Verifies simulation metadata
    - Tests state transition consistency
  * `test_simulation_errors.py`: Tests error handling and recovery mechanisms
    - Verifies error detection and classification
    - Tests logging level configuration
    - Validates error recovery mechanisms
    - Performs comprehensive error analysis
    - Checks for absence of critical errors
- **Simulation Script**: `story_simulation.py` generates structured log data for test analysis
- **Utility Module**: `log_utils.py` provides functions for finding, parsing, and analyzing logs
- **Orchestration Script**: `run_simulation_tests.py` automates the entire testing workflow
  * Starts the FastAPI server with uvicorn
  * Runs the story simulation
  * Executes all pytest tests
  * Handles proper cleanup of all processes

#### Running Tests Before Feature Deployment

##### Using the Orchestration Script (Recommended)
```bash
# Run the complete workflow (server, simulation, tests)
python tests/simulations/run_simulation_tests.py

# Run with specific story category and lesson topic
python tests/simulations/run_simulation_tests.py --category "enchanted_forest_tales" --topic "Farm Animals"

# Skip simulation and just run tests on existing logs
python tests/simulations/run_simulation_tests.py --tests-only

# Run only the simulation without tests
python tests/simulations/run_simulation_tests.py --simulation-only
```

##### Manual Testing (Alternative)
1. **Generate Test Data**:
   ```bash
   # Run a simulation to generate log data
   python tests/simulations/story_simulation.py
   
   # Optionally specify story category and lesson topic
   python tests/simulations/story_simulation.py --category "enchanted_forest_tales" --topic "Farm Animals"
   ```

2. **Run Functionality Tests**:
   ```bash
   # Run all functionality tests
   pytest tests/simulations/test_simulation_functionality.py
   
   # Run a specific test
   pytest tests/simulations/test_simulation_functionality.py::test_chapter_sequence
   ```

3. **Run Error Handling Tests**:
   ```bash
   # Run all error handling tests
   pytest tests/simulations/test_simulation_errors.py
   
   # Run a specific test
   pytest tests/simulations/test_simulation_errors.py::test_error_recovery_mechanism
   ```

4. **Verify Test Results**:
   - All tests should pass with output similar to:
     ```
     ========================== 6 passed in 0.33s ==========================
     ```
   - If tests fail, the error message will indicate which assertion failed and provide guidance

#### When to Run Tests
- **Required**: Before pushing changes to any of these files:
  * `app/services/llm/*`
  * `app/routers/websocket_router.py`
  * `app/services/websocket_service.py`
  * `app/services/chapter_manager.py`
  * `app/models/story.py`
  * `app/init_data.py`
  * `app/data/new_stories.yaml`
  * `app/data/lessons.csv`
  * `app/templates/index.html`
- **Recommended**: After any significant changes to the codebase
- **Best Practice**: Include in CI/CD pipeline for automated verification

#### Test Documentation
- **Primary Reference**: `SIMULATION_TESTING.md` contains comprehensive documentation
- **Deprecated Files**: `SIMULATION_GUIDE.md` and `TEST_SUMMARY.md` have been merged into the primary reference

## Text Streaming Pattern
1. Content Delivery:
   - Word-by-word streaming for natural flow
   - Consistent timing between words (0.02s)
   - Paragraph breaks with longer pauses (0.1s)
   - CRITICAL: Maintain reading rhythm

2. Typography Pattern (`app/static/css/typography.css`):
   - CRITICAL: Consistent typography between streaming text and choices
   - Base Settings:
     * Font: Andika (optimized for education)
     * Size: 1.2rem for main content
     * Line height: 1.7 for readability
     * Weight: 500 for clarity
   - CSS Variables for Maintainability:
     * --font-primary
     * --font-code
     * --color-text-primary
     * --color-text-dark
     * --line-height-content
     * --font-size-content (and other size variants)
   - Standardized Application:
     * Streaming content matches choice buttons exactly
     * Consistent styling across UI elements
     * Educational focus in typography choices
   - Error Prevention:
     * Global font family fallbacks
     * Consistent text shadow application
     * Proper whitespace preservation

3. Markdown Processing:
   - Real-time parsing during stream
   - Buffer management for partial content
   - Emphasis handling (*italic*, **bold**)
   - Code block formatting
   - CRITICAL: Preserve streaming experience

4. Error Handling:
   - Graceful fallback to plain text
   - Maintain stream on parse errors
   - Clear error logging
   - State recovery
   - CRITICAL: Never break narrative flow

5. State Management:
   - Clean buffer between chapters
   - Proper cleanup on reset
   - Memory management
   - WebSocket stability
   - CRITICAL: Prevent content overlap
