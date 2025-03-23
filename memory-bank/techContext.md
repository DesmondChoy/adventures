# Technical Context

## Technology Stack

### Backend
- **FastAPI Framework**
  * Real-time WebSocket communication
  * Structured logging system
  * Middleware stack for request tracking
  * State management and synchronization

### AI Integration
- **Provider-Agnostic Implementation**
  * `app/services/llm/providers.py`: Supports GPT-4o/Gemini
  * `app/services/image_generation_service.py`: Gemini Imagen API
  * Standardized Google API configuration across services
  * Environment variables:
    ```
    GOOGLE_API_KEY=your_google_key  # Used for both LLM and image generation
    OPENAI_API_KEY=your_openai_key  # Optional alternative for LLM only
    ```

### Frontend
- **State Management**
  ```javascript
  // app/templates/index.html
  class AdventureStateManager {
      STORAGE_KEY = 'adventure_state';
      // Uses localStorage for persistence
      // Maintains complete chapter history
  }
  ```

- **Connection Management**
  ```javascript
  // app/templates/index.html
  class WebSocketManager {
      reconnectAttempts = 0;
      maxReconnectAttempts = 5;
      
      calculateBackoff() {
          // Exponential: 1s to 30s
      }
  }
  ```

- **UI Components**
  * Modular CSS organization (`app/static/css/`)
    - `layout.css`: Structural elements, containers, and screen transitions
    - `components.css`: Reusable UI components (toast notifications, buttons, loaders, etc.)
    - `carousel-component.css`: 3D carousel with animations and touch support
    - `theme.css`: Color schemes, theme variables, and modern visual enhancements
    - `typography.css`: Text styling and CSS variables
  * Modern UI enhancements (consolidated in `theme.css`):
    - Subtle background patterns using SVG data URIs
    - Layered shadows and refined borders for depth
    - Micro-interactions and hover effects
    - Gradient overlays and shine effects
    - Backdrop filters for frosted glass effects
  * Typography system with educational focus
  * Word-by-word content streaming with Markdown support
  * Progressive enhancement for images

## Core Data Structures

### StateStorageService (`app/services/state_storage_service.py`)
```python
class StateStorageService:
    # Singleton pattern implementation
    _instance = None
    _memory_cache = {}  # Shared memory cache across all instances
    _initialized = False
    
    # Methods
    async def store_state(self, state_data: Dict[str, Any]) -> str:
        # Stores state with UUID and returns the ID
        
    async def get_state(self, state_id: str) -> Optional[Dict[str, Any]]:
        # Retrieves state by ID
        
    async def cleanup_expired(self) -> int:
        # Removes expired states
```

### AdventureState (`app/models/story.py`)
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
    
    # Summary chapter data
    chapter_summaries: List[str]  # Summaries of each chapter for the SUMMARY chapter
    summary_chapter_titles: List[str]  # Titles of each chapter for the SUMMARY chapter
    lesson_questions: List[Dict[str, Any]]  # Educational questions for the SUMMARY chapter
    
    # Tracking
    metadata: Dict[str, Any]  # Stores agency, challenge history, etc.
    chapters: List[ChapterData]
```

### ChapterType Enum (`app/models/story.py`)
```python
class ChapterType(str, Enum):
    LESSON = "lesson"
    STORY = "story"
    CONCLUSION = "conclusion"
    REFLECT = "reflect"
    SUMMARY = "summary"
```

**Note:** The enum values are lowercase, but stored states may contain uppercase values (like "STORY", "LESSON"). The `reconstruct_state_from_storage` method in `AdventureStateManager` handles this case sensitivity issue by converting all chapter types to lowercase during state reconstruction.

## Key Services

### Chapter Manager (`app/services/chapter_manager.py`)
- Determines chapter sequence based on adventure length
- Enforces chapter type rules (no consecutive LESSON chapters, etc.)
- Samples questions from `app/data/lessons/*.csv` files for LESSON chapters
- Validates question availability

### WebSocket Service (`app/services/websocket_service.py`)
- Processes user choices and generates responses
- Manages chapter content generation
- Handles streaming of content to client
- Coordinates with ImageGenerationService for agency choice images

### LLM Integration (`app/services/llm/`)
- `providers.py`: Provider abstraction layer
- `prompt_engineering.py`: Builds prompts for all chapter types
- `prompt_templates.py`: Defines templates for different chapter types
- `base.py`: Abstract base classes for LLM providers

### Image Generation (`app/services/image_generation_service.py`)
- Asynchronous processing with `generate_image_async()`
- 5 retries with exponential backoff
- Robust null checking and error handling
- Base64 encoding for WebSocket transmission

### Summary Router (`app/routers/summary_router.py`)
- Serves the React-based Summary Chapter
- Provides API endpoints for adventure summary data
- Extracts chapter summaries, educational questions, and statistics
- Handles state reconstruction with case sensitivity handling
- Implements robust fallback mechanisms for missing data
- Processes the "Take a Trip Down Memory Lane" button functionality

## Agency Implementation

### First Chapter Choice
- Four categories in `prompt_templates.py`:
  * Magical Items to Craft
  * Companions to Choose
  * Roles or Professions
  * Special Abilities

### Agency Tracking
```python
# app/services/adventure_state_manager.py
def update_agency_references(self, chapter_data: ChapterData) -> None:
    # Tracks references to agency element in chapters
    # Warns if no reference found
```

### Agency Evolution
- REFLECT chapters: Agency evolves based on correct/incorrect answers
- CLIMAX phase: Agency plays pivotal role in choices
- CONCLUSION: Agency has meaningful resolution

## Testing Framework

### Simulation (`tests/simulations/generate_all_chapters.py`)
- Generates structured log data with standardized prefixes
- Automated adventure progression with random choices
- Real-time WebSocket communication testing
- Saves complete simulation state to JSON file

### Test State Generation (`tests/utils/generate_test_state.py`)
- Generates realistic test states using `generate_all_chapters.py`
- Provides fallback to mock state when simulation fails
- Adds metadata to track state source for debugging
- Supports customization of story category and lesson topic

### Test Files
- `test_summary_button_flow.py`: Tests "Take a Trip Down Memory Lane" button functionality
- `test_state_storage_reconstruction.py`: Tests case sensitivity handling in state reconstruction
- `test_summary_chapter.py`: Tests summary chapter functionality
- `test_chapter_sequence_validation.py`: Verifies chapter sequences and ratios
- `test_chapter_type_assignment.py`: Tests chapter type assignment logic
