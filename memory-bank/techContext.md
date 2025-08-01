# Technical Context

## Technology Stack

### Backend
- **FastAPI Framework**
  * Real-time WebSocket communication
  * Structured logging system
  * Middleware stack for request tracking
  * State management and synchronization
- **Authentication & Authorization**
  * `PyJWT[crypto]` library for JWT decoding.
  * Supabase Auth for user management (Google & Anonymous providers).
  * JWTs passed via WebSocket query parameters (`token`).
  * Backend validation of JWTs using `SUPABASE_JWT_SECRET`.
  * Row-Level Security (RLS) policies in Supabase for data access control.
  * `app/auth/dependencies.py` for FastAPI JWT verification dependency (though primarily WebSocket auth is used for core adventure flow).

### AI Integration
- **Dual-Model LLM Architecture**
  * `app/services/llm/factory.py`: Factory pattern for optimal model selection
  * `app/services/llm/providers.py`: Supports GPT-4o/Gemini 2.5 Flash/Flash Lite with centralized configuration
  * **Cost-Optimized Model Routing:**
    - Gemini 2.5 Flash (`gemini-2.5-flash`): Complex reasoning (story generation, image scenes)
    - Gemini 2.5 Flash Lite (`gemini-2.5-flash-lite-preview-06-17`): Simple processing (summaries, formatting, JSON extraction)
  * `app/services/image_generation_service.py`: Gemini Imagen API with Flash Lite for prompt synthesis
  * Centralized model configuration in `ModelConfig` class with thinking budget support
  * **~50% cost reduction** through strategic Flash Lite usage on 6/8 LLM processes
  * Environment variables:
    ```
    GOOGLE_API_KEY=your_google_key  # Used for both LLM and image generation
    OPENAI_API_KEY=your_openai_key  # Optional alternative for LLM only
    SUPABASE_JWT_SECRET=your_supabase_jwt_secret # For backend JWT validation
    ```

### Frontend
- **Modular JavaScript Architecture**
  * ES6 modules for clean dependency management (`app/static/js/`)
  * `authManager.js`: Supabase authentication, session management, and user status UI updates
  * `adventureStateManager.js`: localStorage operations for adventure state persistence
  * `webSocketManager.js`: WebSocket connections, reconnection logic, and message handling
  * `stateManager.js`: Adventure state operations and state transitions
  * `uiManager.js`: DOM manipulation, UI updates, story content rendering, and user interface functions
  * `main.js`: Main entry point, coordinates all modules, and handles application initialization

- **State Management**
  ```javascript
  // app/static/js/adventureStateManager.js
  export class AdventureStateManager {
      STORAGE_KEY = 'adventure_state';
      CLIENT_UUID_KEY = 'learning_odyssey_user_uuid';
      // Uses localStorage for persistence
      // Maintains complete chapter history
  }
  ```

- **Connection Management**
  ```javascript
  // app/static/js/webSocketManager.js
  export class WebSocketManager {
      reconnectAttempts = 0;
      maxReconnectAttempts = 5;
      
      calculateBackoff() {
          // Exponential: 1s to 30s
      }
  }
  ```

- **Template Structure**
  * Modular organization with component separation
  * Inheritance-based template system
  * `components/scripts.html`: Module loading and configuration bridge between server-side data and client-side modules

- **UI Components**
  * Modular CSS organization (`app/static/css/`)
  * Typography system with educational focus
  * Word-by-word content streaming with Markdown support
  * Progressive enhancement for images

## Core Data Structures

### StateStorageService
- **Implementation:** `app/services/state_storage_service.py`
- **Description:** Provides persistent storage for `AdventureState` using a Supabase backend. Handles state creation, retrieval, updates (upsert), and retrieval of active adventures for resumption. `user_id` (if present) is converted to a string before database operations to prevent serialization errors. See `memory-bank/systemPatterns.md` for the Supabase Persistence Pattern details.

### TelemetryService
- **Implementation:** `app/services/telemetry_service.py`
- **Description:** Logs telemetry events to a Supabase backend. `user_id` (if present) is converted to a string before database operations.

### AdventureState
```python
class AdventureState:
    # Core properties
    story_length: int
    current_chapter_number: int
    planned_chapter_types: List[ChapterType]
    current_storytelling_phase: str
    
    # Content elements
    selected_narrative_elements: Dict[str, str]
    selected_sensory_details: Dict[str, str]
    selected_theme: str
    selected_moral_teaching: str
    selected_plot_twist: str
    protagonist_description: str # Base visual description of the protagonist
    
    # Summary chapter data
    chapter_summaries: List[str]  # Summaries for SUMMARY chapter
    summary_chapter_titles: List[str]  # Titles for SUMMARY chapter
    lesson_questions: List[Dict[str, Any]]  # Educational questions
    
    # Performance optimization fields
    summary_lock: asyncio.Lock  # Thread-safe lock for background summary operations
    pending_summary_tasks: List[asyncio.Task]  # Tracks background tasks for synchronization
    deferred_summary_tasks: List[Callable]  # Task factories for deferred execution after streaming
    
    # Tracking
    metadata: Dict[str, Any]  # Stores agency, challenge history, etc.
    chapters: List[ChapterData]
    character_visuals: Dict[str, str] # Stores current visual descriptions for all characters
```

### ChapterType Enum
```python
class ChapterType(str, Enum):
    LESSON = "lesson"
    STORY = "story"
    CONCLUSION = "conclusion"
    REFLECT = "reflect"
    SUMMARY = "summary"
```

## Key Services

### Chapter Manager
- Determines chapter sequence based on rules
- Enforces chapter type constraints
- Samples questions from lesson files
- Validates question availability

### WebSocket Service Structure
- **Core Module** (`core.py`): Central coordination
- **Choice Processor** (`choice_processor.py`): Handles user choices, triggers character visual updates (via `_update_character_visuals`).
- **Content Generator** (`content_generator.py`): Creates chapter content
- **Stream Handler** (`stream_handler.py`): Manages content streaming
- **Image Generator** (`image_generator.py`): Handles image generation, incorporating synthesized prompts.
- **Summary Generator** (`summary_generator.py`): Manages summary content

### LLM Integration
- **Prompt Engineering**
  * `build_prompt()`: Main entry point
  * `build_system_prompt()`: Creates system context
  * `build_user_prompt()`: Creates chapter-specific prompts
  * `_get_phase_guidance()`: Adds phase-specific guidance

- **Dual-Model Provider Architecture**
  * Factory pattern (`LLMServiceFactory`) for automatic model selection based on use case complexity
  * Supports GPT-4o and Gemini 2.5 Flash/Flash Lite using unified `google-genai` SDK
  * **Model Assignment Strategy:**
    - Flash: `story_generation`, `image_scene_generation` (29% of operations)
    - Flash Lite: `summary_generation`, `paragraph_formatting`, `character_visual_processing`, `image_prompt_synthesis`, `chapter_summaries`, `fallback_summaries` (71% of operations)
  * Centralized model configuration with `ModelConfig` class
  * 1024 token thinking budget for enhanced reasoning across all Gemini operations
  * Standardized response handling across providers
  * Error recovery mechanisms
  * Paragraph formatting integration with Flash Lite optimization
  * Migrated from deprecated `google-generativeai` to `google-genai`

### Image Generation
- Implements a **two-step image prompt synthesis pattern**:
  1. Generates a concise scene description from chapter content (`IMAGE_SCENE_PROMPT`).
  2. Uses `ImageGenerationService.synthesize_image_prompt` with an LLM (Gemini Flash) and `IMAGE_SYNTHESIS_PROMPT` to combine the scene description, protagonist base look (`state.protagonist_description`), agency details, story sensory visuals, and evolved character visuals (`state.character_visuals`) into a final, rich prompt.
- Asynchronous image generation (`generate_image_async()`) using the synthesized prompt.
- 5 retries with exponential backoff.
- Base64 encoding for WebSocket transmission.
- Progressive enhancement (text first, images as available).

### Adventure State Manager (`app/services/adventure_state_manager.py`)
- Manages `AdventureState` updates.
- Includes `update_character_visuals` method to intelligently merge new character visual information into `state.character_visuals`, preserving existing descriptions unless changes are detected.
- Handles agency reference tracking (see Agency Implementation).

### Summary Service Architecture
- **Modular Package** (`app/services/summary/`)
  * `service.py`: Main service orchestrator
  * `chapter_processor.py`: Chapter-related processing
  * `question_processor.py`: Question extraction
  * `stats_processor.py`: Statistics calculation
  * `dto.py`: Data transfer objects
  * `helpers.py`: Utility functions
  * `exceptions.py`: Custom exception classes

- **React Integration**
  * `summary_router.py`: Serves React app and API endpoints
  * TypeScript interfaces for structured data
  * API endpoint for data retrieval
  * Case conversion for naming conventions

## Agency Implementation

### Categories
- Four categories in `prompt_templates.py`:
  * Magical Items to Craft
  * Companions to Choose
  * Roles or Professions
  * Special Abilities

### Tracking
```python
# app/services/adventure_state_manager.py
def update_agency_references(self, chapter_data: ChapterData) -> None:
    # Tracks references to agency element in chapters
    # Warns if no reference found
```

### Evolution
- STORY chapters: Agency provides special abilities
- REFLECT chapters: Agency evolves based on answers
- CLIMAX phase: Agency plays pivotal role
- CONCLUSION: Agency has meaningful resolution

## Testing Framework

### Simulation
- Generates structured log data
- Automated adventure progression
- Real-time WebSocket testing
- State serialization to JSON

### Test State Generation
- Realistic states via simulation
- Mock state fallback
- Story category and lesson topic customization

### Test Suite
- `test_summary_button_flow.py`: Tests summary button
- `test_state_storage_reconstruction.py`: Tests state reconstruction
- `test_summary_chapter.py`: Tests summary functionality
- `test_chapter_sequence_validation.py`: Verifies chapter sequences
- `test_chapter_type_assignment.py`: Tests type assignment
