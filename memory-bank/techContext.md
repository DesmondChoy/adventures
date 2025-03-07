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
    
    # Tracking
    metadata: Dict[str, Any]  # Stores agency, challenge history, etc.
    chapters: List[ChapterData]
```

### ChapterType Enum (`app/models/story.py`)
```python
class ChapterType(str, Enum):
    STORY = "STORY"
    LESSON = "LESSON"
    REFLECT = "REFLECT"
    CONCLUSION = "CONCLUSION"
```

## Key Services

### Chapter Manager (`app/services/chapter_manager.py`)
- Determines chapter sequence based on adventure length
- Enforces chapter type rules (no consecutive LESSON chapters, etc.)
- Samples questions from `lessons.csv` for LESSON chapters
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

### Simulation (`tests/simulations/story_simulation.py`)
- Generates structured log data with standardized prefixes
- Automated adventure progression with random choices
- Real-time WebSocket communication testing

### Test Files
- `test_simulation_functionality.py`: Verifies chapter sequences, ratios
- `test_simulation_errors.py`: Tests error handling and recovery
- `run_simulation_tests.py`: Orchestrates server, simulation, and tests
