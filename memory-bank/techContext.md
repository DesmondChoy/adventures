# Technical Context

## Technology Stack

### Backend
- **Framework**: FastAPI
  - Async WebSocket support
  - Type safety with Pydantic
  - Real-time state synchronization
  - Automated testing integration

- **State Management**: AdventureState
  - Centralized in `models/story.py`
  - Complete state tracking
  - Question data persistence
  - WebSocket synchronization
  - ChapterType enum support
  - Response handling
  - Error recovery
  - Metadata tracking for element consistency
  - Plot twist phase guidance
  - Fixed story length (10 chapters)

- **Language**: Python 3.x
  - Type hints throughout
  - Async/await for WebSocket
  - Provider-agnostic design
  - Automated testing support

### Dependencies
```
fastapi==0.104.1
uvicorn==0.24.0
websockets==12.0
pydantic==2.5.2
sqlalchemy==2.0.23
pyyaml==6.0.1
python-dotenv==1.0.0
pytest==7.4.3
pytest-asyncio==0.21.1
```

## Development Setup

### Environment Requirements
1. Python 3.x installation
2. Virtual environment
3. Dependencies installed via pip
4. LLM provider credentials configured
5. Test environment setup

### Local Development
1. Start server:
   ```bash
   uvicorn app.main:app --reload
   ```
2. Access endpoints:
   - Web: http://localhost:8000
   - WebSocket: ws://localhost:8000/ws
3. Run tests:
   ```bash
   python -m pytest tests/
   ```

### Testing Environment (`tests/simulations/`)
- Story simulation framework (`story_simulation.py`):
  * Primary purpose: Generate test data and logs
  * Random adventure progression
  * Comprehensive DEBUG level logging
  * WebSocket communication validation
  * Error handling and retry logic
  * Test data generation for validation
- State transition validation:
  * AdventureState consistency
  * WebSocket synchronization
  * Recovery mechanism testing
  * Error boundary validation
  * Comprehensive log generation
  * Element consistency validation
  * Plot twist progression testing
- LLM provider compatibility:
  * OpenAI/Gemini cross-testing
  * Response format validation
  * Error handling verification
  * Rate limiting compliance
- WebSocket connection testing:
  * Connection stability
  * State synchronization
  * Error recovery
  * Performance metrics

## Technical Considerations

### State Management System
- **Client-Side State (`app/templates/index.html`)**
  * Centralized manageState function:
    - initialize: Sets up new story state
    - update: Modifies existing state
    - reset: Clears all state
  * Session storage persistence
  * Fixed story length (10 chapters)
  * Screen state management
  * Carousel selection tracking
  * Progress monitoring
  * WebSocket synchronization

- **Server-Side State (`app/models/story.py`)**
  * Real-time WebSocket synchronization
  * Complete state serialization
  * Fixed story length (10 chapters)
  * Error recovery system
  * Critical state preservation:
    - Narrative elements
    - Sensory details
    - Theme and moral teaching
    - Plot twist and phase guidance
    - Metadata for consistency
  * URL parameters handling:
    - Story category and lesson topic via URL
    - Not included in validated_state
    - Used for initial state setup only

### LLM Integration (`app/services/llm/`)
* Provider abstraction layer
* Response standardization
* Rate limiting implementation
* Error handling system
* State handling requirements:
  - Must pass complete AdventureState
  - Direct attribute access for prompts
  - Story config used only for setup
* Enhanced features:
  - Phase-specific plot twist guidance
  - Element consistency validation
  - Narrative continuity enforcement

### Story Elements (`app/services/chapter_manager.py`)
* Comprehensive element selection
* Metadata tracking for consistency
* Phase-specific plot twist guidance
* Enhanced error handling with recovery

## UI Components

### Carousel Component
- **Location**: `app/static/css/carousel.css`
- **Description**: A reusable 3D carousel component with smooth transitions, animations, and card flipping functionality
- **Features**:
  - 3D perspective rotation
  - Active card expansion (340px width vs 300px base)
  - Infinite glowing animation on active cards
  - Card flip animation on selection
  - Portrait orientation (3:4 aspect ratio)
  - Responsive navigation controls
  - Smooth transitions using cubic-bezier timing
- **States**:
  - Default: 300x400px, 0.3 opacity
  - Active: 340x453px, glowing animation, full opacity
  - Selected: Triggers card flip animation
  - Front face: Full-width image display
  - Back face: Title and description content
- **Customization**:
  - Uses theme colors (indigo-600)
  - Configurable card dimensions
  - Modular structure for reuse
  - Image handling with object-fit
- **Technical Details**:
  - Uses CSS transform-style: preserve-3d
  - Hardware-accelerated animations
  - Will-change optimization for performance
  - Backdrop-filter for glass effect
  - Backface visibility hidden for 3D rendering
  - Two-sided card implementation
- **Image Requirements**:
  - Location: `app/static/images/categories/`
  - Naming: Matches category IDs
  - Aspect ratio: 3:4 (portrait)
  - Min resolution: 680x906px
  - Format: JPG/WebP
  - Content: Theme-appropriate and child-friendly

### Mobile Responsiveness (`app/static/css/carousel.css`)
- Breakpoint: max-width 768px
- Container dimensions:
  * Desktop: 400px × 420px
  * Mobile: 320px × 360px
- Card dimensions:
  * Desktop regular: 300px × 400px
  * Desktop active: 340px × 453px
  * Mobile regular: 200px × 267px
  * Mobile active: 240px × 320px
- Typography scaling:
  * Desktop title: 1.25rem
  * Desktop description: 0.95rem
  * Mobile title: 0.85rem
  * Mobile description: 0.75rem
- Touch interaction:
  * Swipe gesture navigation
  * 50px swipe threshold
  * Event prevention for smooth scrolling
  * Hidden navigation arrows
- Content optimization:
  * Reduced padding (4px)
  * Increased line clamp (10)
  * Tighter line height (1.35)
  * Maintained aspect ratios

## Text Rendering and Streaming

### Typography System (`app/static/css/typography.css`)
- Modular typography system using CSS variables
- Primary font: Andika (optimized for educational content)
- Standardized font sizes and weights:
  * Content text: 1.2rem
  * Small text: 0.875rem
  * Base: 1rem
  * Large: 1.125rem
  * Extra large: 1.25rem
  * 2XL: 1.5rem
  * 4XL: 2.25rem
- Consistent typography across:
  * Streaming content
  * Choice buttons
  * Form elements
  * Headers
  * Stats display
- Educational considerations:
  * Enhanced readability with 1.7 line height
  * Medium font weight (500) for clarity
  * Subtle letter spacing (0.01em)
  * Optimized contrast with carefully selected colors

### Markdown Support
- Implementation using marked.js library
- Real-time markdown parsing during streaming
- Support for:
  * Emphasis (*italic*)
  * Strong emphasis (**bold**)
  * Code blocks (inline and multi-line)
  * Line breaks and paragraphs
- Fallback to plain text if parsing fails
- Preserves streaming functionality while rendering markdown

### Streaming Architecture
- Word-by-word streaming for natural reading flow
- WebSocket-based real-time delivery
- Optimized timing:
  * 0.02s delay between words
  * 0.1s delay between paragraphs
- Buffer management for markdown rendering
- Smooth scrolling as content streams
- Maintains proper whitespace and formatting

### UX Considerations
- Natural reading pace through controlled delays
- Immediate visual feedback for markdown elements
- Preserved line breaks and paragraph structure
- Consistent formatting throughout streaming
- Graceful fallback for parsing errors
- Clean state management between chapters
