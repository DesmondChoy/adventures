# Active Context

## Current Focus
The project is implementing core Learning Odyssey features:

1. Adventure Flow Implementation
   - Landing page topic and length selection
   - **`app/services/chapter_manager.py`**: ChapterType determination (LESSON/STORY/CONCLUSION)
   - **`app/services/llm/prompt_engineering.py`**: Content source integration:
     - LESSON chapters: lessons.csv + LLM narrative wrapper
     - STORY chapters: Full LLM generation with choices
     - CONCLUSION chapters: Full LLM generation without choices
   - Narrative continuity via prompt engineering

2. Content Management (`app/data/`)
   - lessons.csv integration for LESSON chapters
   - stories.yaml templates for STORY chapters
   - LLM response validation
   - History tracking in AdventureState

## Recent Changes

### Journey Quest Implementation
- Initial implementation of Journey Quest pacing:
  * Added `current_storytelling_phase` to `AdventureState` to track phases
  * Added `determine_story_phase` static method to `ChapterManager`
  * Updated `initialize_adventure_state` with initial "Exposition" phase
  * Modified `websocket_service.py` for phase updates
  * Enhanced `_get_phase_guidance` with detailed phase-specific guidance
  * Updated `_build_base_prompt` to use state-based phase
  * Added required math imports

### Story Phase Timing Fix
- Fixed incorrect story phase progression:
  * Moved phase update before chapter generation in `websocket_service.py`
  * Ensures correct phase (e.g., "Rising" for Chapter 2)
  * Maintains proper Journey Quest structure (Exposition -> Rising -> Trials -> Climax -> Return)
  * Improves narrative coherence by using correct phase guidance in prompts
  * Fixed timing issue where LLM was seeing old phase value

### Chapter Logic Refactor
- Implemented new chapter sequencing:
  * First two chapters: Always STORY (for setting/character development)
  * Second-to-last chapter: Always STORY (for pivotal choices)
  * Last chapter: Always CONCLUSION (for story resolution)
  * Remaining chapters: 50% LESSON (subject to available questions)
- Added CONCLUSION chapter type:
  * No choices presented
  * Provides satisfying story resolution
  * Return to Landing Page button
- Enhanced prompt engineering:
  * Added CONCLUSION-specific prompts
  * Improved narrative resolution
  * Better story arc completion
- Fixed random.sample error:
  * Added validation for available questions
  * Improved error handling
  * Better logging for debugging

### Progress Tracking (`app/templates/index.html`)
- Implemented visual progress tracking:
  * Current chapter and total chapters display
  * Progress bar with indigo color scheme
  * Smooth transitions using Tailwind
  * Responsive to state changes
- Enhanced state integration:
  * Updates based on chapter_number
  * Syncs with story_length
  * Persists across page reloads
  * Handles backwards navigation
- UI/UX improvements:
  * Positioned at top of story container
  * Consistent styling with app theme
  * Clear visual feedback
  * Smooth animations

### State Management (`app/models/story.py`)
- Enhanced state tracking system:
  * Sequential progression via chapter_number
  * Navigation paths via current_chapter_id
  * Clear separation of concerns:
    - ChapterManager uses chapter_number
    - WebSocket router uses current_chapter_id
  * Improved state serialization
  * Better error recovery

- Added planned_chapter_types to AdventureState:
  * Pre-determined sequence of chapter types
  * Stored during state initialization
  * Single source of truth for chapter progression
  * Maintains complete state serialization

### WebSocket Architecture Refactoring
- Split WebSocket handling into two components:
  * **`app/routers/websocket_router.py`**:
    - Focused on routing and connection management
    - Handles WebSocket lifecycle (accept/disconnect)
    - Manages initial state setup and updates
    - Routes messages to appropriate service functions
  * **`app/services/websocket_service.py`**:
    - Contains core business logic
    - Processes user choices
    - Generates chapter content
    - Manages streaming and message sending
- Benefits of this separation:
  * Clearer separation of concerns
  * More maintainable codebase
  * Easier testing and debugging
  * Better error handling isolation

### Chapter Management (`app/services/chapter_manager.py`)
- Enhanced state initialization:
  * Store chapter type sequence in AdventureState
  * Maintain sequence through entire adventure
  * Improved state consistency
  * Better error handling

### State Management (`app/services/adventure_state_manager.py`)
- Created `AdventureStateManager` class to encapsulate state management logic.
- Implemented methods for:
    - Initializing state (`initialize_state`)
    - Retrieving current state (`get_current_state`)
    - Updating state from client data (`update_state_from_client`)
    - Appending new chapters (`append_new_chapter`)
- Refactored state management logic from `websocket.py` into `AdventureStateManager`.

### Prompt Engineering (`app/services/llm/prompt_engineering.py`)
- Enhanced world-building system:
    * Uses topic/subtopic for thematic world creation
    * Improved data structures in LessonQuestion
    * Better narrative coherence through subject connections
    * More meaningful fantasy world generation
- Improved narrative continuity:
    * Use planned_chapter_types for accurate chapter type info
    * Removed hard-coded chapter type assumptions
    * Enhanced state-driven progression
    * Better state consistency in prompts
- Simplified process_consequences():
    * Removed hardcoded chapter number checks
    * Logic now based purely on is_correct state
    * Maintains high-quality narrative guidance
    * Follows state-driven pattern

### Story Length Fixes
- Updated `index.html` to offer story lengths of 5, 8, and 10 chapters.
- Modified `app/models/story.py` to allow story lengths up to 10 chapters (changed `story_length` field constraint).

### Chapter 1 Choices Fix
- Removed the `is_opening` special case in `app/services/llm/prompt_engineering.py` to ensure the first two chapters (STORY type) include choices.

### "Chapter X:" Prefix Fix
- Added an instruction to the system prompt (`app/services/llm/prompt_engineering.py`) to prevent the LLM from generating chapter prefixes.
- Added debug logging to `app/services/websocket_service.py` to track chapter content.
- Improved the regex in `app/services/websocket_service.py` to reliably remove any "Chapter X:" prefixes.
- Ensured the stripped content is used consistently for streaming, state updates, and storing chapter data.
- Fixed duplicate parameter and docstring issues in `app/services/websocket_service.py`.

## Active Decisions

### Architecture
1. Content Flow
    - **`app/services/chapter_manager.py`**:
        - Determines ChapterType (LESSON/STORY/CONCLUSION)
        - First two chapters: Always STORY
        - Second-to-last chapter: Always STORY
        - Last chapter: Always CONCLUSION
        - 50% of remaining chapters: LESSON (subject to available questions)
    - **`app/services/llm/prompt_engineering.py`**:
        - LESSON chapters:
            * Questions from lessons.csv
            * LLM narrative wrapper
            * Response validation
        - STORY chapters:
            * Full LLM generation
            * Three choices per chapter
        - CONCLUSION chapters:
            * Full LLM generation
            * No choices
            * Story resolution
    - Outcome tracking in AdventureState
    - Narrative continuity via prompts

2. Testing Strategy (`tests/simulations/`)
   - Story simulation framework
   - Response validation
   - State verification
   - Error handling coverage

### Implementation
1. User Experience (`app/routers/web.py`)
   - Topic selection interface
   - Adventure length selection
   - Real-time feedback system
   - WebSocket state updates
   - Progress tracking visualization

2. Flow Control (`app/services/chapter_manager.py`)
   - New chapter type sequencing
   - Dynamic content sampling
   - Error recovery mechanisms
   - Question availability validation

## Current Considerations

### Testing Framework (`tests/simulations/story_simulation.py`)
- Primary purpose:
  * Generate test data through random adventure progression
  * Provide comprehensive logs for test validation
  * Support testing requirements when core components change
- Current status:
  * Successfully generates required DEBUG level logs
  * Captures all state changes and responses
  * Maintains WebSocket communication
  * Implements robust error handling
  * Functions as intended for test data generation

### Technical
1. Performance
   - LLM response times
   - WebSocket latency
   - State synchronization speed
   - Error recovery time
   - Progress updates smoothness

2. Reliability
   - WebSocket connection stability
   - LLM service availability
   - State consistency
   - Error handling coverage
   - Progress tracking accuracy

### Product
1. User Experience
   - Topic relevance
   - Narrative engagement
   - Learning effectiveness
   - Error feedback clarity
   - Progress visualization clarity

2. Content Quality
   - Question appropriateness
   - Narrative coherence
   - Choice meaningfulness
   - Learning progression
   - Progress feedback effectiveness
