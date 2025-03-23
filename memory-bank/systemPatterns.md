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
    WSS <--> IMG[Image Generation Service]
    CM <--> SL[Story Loader]
    SL <--> SF[(Story Files)]
    LLM <--> PF[Paragraph Formatter]
    
    %% New React Summary Components
    Client <--> SR[Summary Router]
    SR <--> RSUM[React Summary App]
    SR <--> SAPI[Summary API]
    SAPI <--> SGEN[Summary Generator]
    SGEN <--> AS
    
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
        IMG
        PF
    end

    subgraph Content Sources
        CSV[lessons/*.csv] --> CM
        LLM --> CM
        IMG --> WSS
        SF --> SL
    end
    
    subgraph React Summary
        RSUM
        SAPI
        SGEN
    end
```

## Core Components

### 1. State Management
- **AdventureState** (`app/models/story.py`)
  * Single source of truth for all state
  * Complete state serialization
  * Pre-determined chapter sequence via `planned_chapter_types`
  * Metadata tracking for agency, elements, and challenge types
  * Critical properties preserved during updates

- **Client-Side State** (`app/templates/index.html`)
  * `AdventureStateManager` uses localStorage
  * Exponential backoff (1s to 30s) with max 5 reconnection attempts
  * Automatic state restoration on reconnect

### 2. Chapter Management
- **Chapter Sequencing** (`app/services/chapter_manager.py`)
  * First chapter: STORY
  * Second-to-last chapter: STORY
  * Last chapter: CONCLUSION
  * After CONCLUSION: SUMMARY (statistics and chapter-by-chapter recap)
  * 50% of remaining chapters: LESSON (subject to available questions)
  * 50% of LESSON chapters: REFLECT (follow LESSON)
  * No consecutive LESSON chapters
  * STORY chapters follow REFLECT chapters

- **Story Simulation Structure**
  * A complete story consists of 9 interactive chapters plus 1 conclusion chapter
  * The STORY_COMPLETE event is triggered when the chapter count equals the story length
  * The STORY_COMPLETE event contains summaries for all chapters including the CONCLUSION chapter
  * The CONCLUSION chapter is already generated when the STORY_COMPLETE event is triggered
  * The CONCLUSION chapter has no user choices
  * After the CONCLUSION chapter, users can access the SUMMARY chapter via the "Take a Trip Down Memory Lane" button
  * When the "Take a Trip Down Memory Lane" button is clicked, it's treated as a choice selection (with "reveal_summary" as the chosen_path)
  * For regular chapters, summaries are generated when a choice is made, creating a chapter response
  * For the CONCLUSION chapter, the button click creates a placeholder response (chosen_path="end_of_story", choice_text="End of story")
  * This allows the CONCLUSION chapter to go through the same summary generation process as other chapters
  * The SUMMARY chapter displays statistics and chapter-by-chapter summaries

- **Content Sources**
  * LESSON: `app/data/lessons/*.csv` files + LLM wrapper
  * STORY: Full LLM generation with choices
  * REFLECT: Narrative-driven follow-up to LESSON
  * CONCLUSION: Resolution without choices
  * SUMMARY: Statistics and chapter summaries from stored state data

### 3. Story Data Management
- **Story Loader** (`app/data/story_loader.py`)
  * Loads individual story files from `app/data/stories/` directory
  * Combines data into a consistent structure for use by Chapter Manager
  * Provides caching for performance optimization
  * Offers methods for accessing specific story categories

- **Story Files** (`app/data/stories/*.yaml`)
  * Individual YAML files for each story category
  * Consistent structure across all story files
  * Contains narrative elements, sensory details, and other story components

### 4. WebSocket Components
- **Router** (`app/routers/websocket_router.py`)
  * Handles connection lifecycle
  * Validates client messages
  * Works with AdventureStateManager for state handling

- **Service** (`app/services/websocket_service.py`)
  * Processes user choices
  * Manages chapter content generation
  * Handles streaming of content
  * Coordinates with ImageGenerationService

### 5. LLM Integration
- **Prompt Engineering** (`app/services/llm/prompt_engineering.py`)
  * `build_prompt()`: Main entry point for all chapter types
  * `build_system_prompt()`: Creates system context
  * `build_user_prompt()`: Creates chapter-specific prompts
  * `_get_phase_guidance()`: Adds phase-specific guidance

- **Provider Abstraction** (`app/services/llm/providers.py`)
  * Supports GPT-4o and Gemini
  * Standardized response handling
  * Error recovery mechanisms
  * Paragraph formatting integration

- **Paragraph Formatting** (`app/services/llm/paragraph_formatter.py`)
  * Detects text that needs paragraph formatting
  * Reformats text with proper paragraph breaks
  * Multiple retry attempts with progressive prompting
  * Buffer-based approach for streaming optimization

### 6. Image Generation
- **Service** (`app/services/image_generation_service.py`)
  * Asynchronous processing with `generate_image_async()`
  * 5 retries with exponential backoff
  * Base64 encoding for WebSocket transmission
  * Progressive enhancement (text first, images as available)
  * Enhanced prompt construction with `enhance_prompt()`

- **Dual-Purpose Content Generation**
  * **Chapter Summaries** (`generate_chapter_summary()`)
    - Focus on narrative events and character development
    - 70-100 words covering key events and educational content
    - Used for SUMMARY chapter and adventure recap
    - Written in third person, past tense narrative style
    - Template: `SUMMARY_CHAPTER_PROMPT` in `prompt_templates.py`
  
  * **Image Scenes** (`generate_image_scene()`)
    - Focus on the most visually striking moment from a chapter
    - 20-30 words of pure visual description
    - Used exclusively for image generation
    - Describes specific dramatic action or emotional peak
    - Template: `IMAGE_SCENE_PROMPT` in `prompt_templates.py`

## Key Patterns

### 1. Singleton Pattern for State Storage
- **StateStorageService** (`app/services/state_storage_service.py`)
  * Ensures all instances share the same memory cache
  * Implemented with class variables and `__new__` method
  * Prevents state loss between different service instances
  * Critical for "Take a Trip Down Memory Lane" button functionality
  ```python
  class StateStorageService:
      _instance = None
      _memory_cache = {}  # Shared memory cache across all instances
      _initialized = False

      def __new__(cls):
          if cls._instance is None:
              cls._instance = super(StateStorageService, cls).__new__(cls)
          return cls._instance

      def __init__(self):
          if not StateStorageService._initialized:
              StateStorageService._initialized = True
              logger.info("Initializing StateStorageService singleton")
  ```

### 2. Case Sensitivity Handling Pattern
- **AdventureStateManager** (`app/services/adventure_state_manager.py`)
  * Converts uppercase chapter types to lowercase during state reconstruction
  * Ensures compatibility between stored state and AdventureState model
  * Special handling for the last chapter to ensure it's always a CONCLUSION chapter
  * Robust error handling and logging for debugging
  ```python
  # Convert chapter_type to lowercase
  if isinstance(chapter["chapter_type"], str):
      chapter["chapter_type"] = chapter["chapter_type"].lower()
      logger.debug(f"Converted chapter_type to lowercase: {chapter['chapter_type']}")
  ```

### 3. React-based Summary Architecture
- **TypeScript Interfaces** (`app/static/summary-chapter/src/lib/types.ts`)
  * Defines structured data interfaces for the summary components
  * `ChapterSummary`: Chapter number, title, summary, and chapter type
  * `EducationalQuestion`: Question, user answer, correctness, and explanation
  * `AdventureStatistics`: Metrics about the adventure (chapters completed, questions answered, correct answers, time spent)
  * `AdventureSummaryData`: Container for all summary data

- **React Components** (`app/static/summary-chapter/src/pages/AdventureSummary.tsx`)
  * Fetches data from API endpoint
  * Displays chapter summaries in a timeline format
  * Shows educational questions with correct/incorrect indicators
  * Presents statistics about the adventure
  * Includes animations and visual enhancements
  * Mobile-optimized scrolling for chapter cards

- **FastAPI Integration** (`app/routers/summary_router.py`)
  * `/adventure/summary`: Serves the React app
  * `/adventure/api/adventure-summary`: Provides the summary data
  * Error handling and logging for API endpoints
  * Integration with main FastAPI application
  * Robust fallback mechanisms for missing data
  * Case sensitivity handling for chapter types
  * Special handling for the last chapter to ensure it's always treated as a CONCLUSION chapter

- **Data Generation and Processing**
  * `extract_chapter_summaries()`: Extracts chapter summaries with robust fallbacks
  * `extract_educational_questions()`: Extracts questions from LESSON chapters
  * `calculate_adventure_statistics()`: Calculates statistics with safety checks
  * `format_adventure_summary_data()`: Transforms AdventureState into React-compatible data
  * Fallback mechanisms for missing chapter summaries and educational questions

### 2. Frontend Component Architecture
- **CSS Organization** (`app/static/css/`)
  * Organized by purpose and responsibility:
    - `layout.css`: Structural elements, containers, screen transitions
    - `components.css`: Reusable UI components
    - `carousel-component.css`: Specialized carousel component styles
    - `theme.css`: Color schemes, theme variables, and visual enhancements
    - `typography.css`: Text styling and formatting with CSS variables

- **Carousel Component** (`app/static/js/carousel-manager.js`)
  * Reusable class for 3D carousel functionality
  * Configuration via constructor options
  * Methods for rotation, selection, and event handling
  * Event handling for keyboard, touch, and click interactions

- **Font Size Manager** (`app/static/js/font-size-manager.js`)
  * Controls text size adjustments for mobile users
  * Persists preferences in localStorage
  * Shows/hides controls on scroll

### 2. Agency Pattern
- **First Chapter Choice**
  * Four categories: Items, Companions, Roles, Abilities
  * Stored in `state.metadata["agency"]`
  * Referenced throughout all chapters

- **Agency Evolution**
  * REFLECT chapters: Agency evolves based on answers
  * CLIMAX phase: Agency plays pivotal role
  * CONCLUSION: Agency has meaningful resolution

### 3. Narrative Continuity
- **Story Elements Consistency**
  * Setting, characters, theme maintained
  * Plot twist development across phases
  * Agency references in all chapters

- **Previous Chapter Impact**
  * LESSON: `process_consequences()` generates appropriate story consequences
  * STORY: Continue from chosen path with consequences
  * REFLECT: Build on previous lesson understanding

### 4. Text Streaming
- **Content Delivery**
  * Word-by-word streaming (0.02s delay)
  * Paragraph breaks (0.1s delay)
  * Markdown formatting support
  * Buffer management for partial content
  * "Chapter" prefix removal with regex pattern `r"^Chapter(?:\s+\d+)?:?\s*"`

### 5. Prompt Engineering Pattern
- **Prompt Structure and Organization**:
  * Modular template design with separate templates for different chapter types
  * Consistent section ordering across templates
  * Clear delineation between system and user prompts
  * Hierarchical organization for improved readability

- **Format Example Pattern**:
  * Providing both incorrect and correct examples in prompts
  * Showing the incorrect example first to highlight what to avoid
  * Following with the correct example to demonstrate desired format
  * Using clear section headers like "INCORRECT FORMAT (DO NOT USE)" and "CORRECT FORMAT (USE THIS)"
  * Explicitly instructing the LLM to use exact section headers
  * Example implementation in `SUMMARY_CHAPTER_PROMPT` for title and summary extraction

### 6. Mobile-Optimized Scrolling Pattern
- **Fixed Height with Dynamic Content**:
  * Using fixed container heights with scrollable content areas
  * Explicit height containers with proper overflow handling
  * Conditional rendering based on device type using the `useIsMobile` hook
  * Different scroll behavior for mobile vs. desktop

- **Touch-Optimized Scroll Areas**:
  * Enhanced ScrollArea component with mobile-specific properties
  * Custom CSS classes for touch device optimization
  * Properties like `touch-auto`, `overflow-auto`, and `overscroll-contain`
  * Wider scrollbars for better touch interaction
  * Visual indicators (fade effects) to show scrollable content

- **Transition Management**:
  * Careful management of CSS transitions to avoid interference with scrolling
  * Using `transition-opacity` instead of `transition-all` for scrollable content
  * Maintaining smooth animations while ensuring scrollability
  * Example implementation in `ChapterCard.tsx` for summary cards

### 7. Simulation and Testing Pattern
- **Standardized Logging**:
  * Consistent event prefixes (e.g., `EVENT:CHAPTER_SUMMARY`, `EVENT:CHOICE_SELECTED`)
  * Source tracking for debugging (e.g., `source="chapter_update"`, `source="verification"`)
  * Structured data in log entries with standardized fields
  * Multiple verification points to ensure complete data capture

- **Error Handling and Recovery**:
  * Specific error types for different failure scenarios
  * Exponential backoff for retries with configurable parameters
  * Graceful degradation when services are unavailable
  * Comprehensive logging of error states and recovery attempts

- **Helper Functions for Common Operations**:
  * `log_chapter_summary()`: Standardized chapter summary logging
  * `verify_chapter_summaries()`: Verification of complete chapter summaries
  * `establish_websocket_connection()`: Connection with retry logic
  * `send_message()`: Standardized message sending
