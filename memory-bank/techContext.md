# Technical Context

## Technology Stack

### Backend
[Previous backend section remains unchanged...]

### Frontend
- **State Management**: AdventureStateManager
  - Uses localStorage for persistence
  - Independent of cookies
  - Complete state tracking
  - Automatic recovery
  - CRITICAL: Cannot cache future content (LLM dependent)

- **Connection Management**: WebSocketManager
  - Exponential backoff (1s to 30s)
  - Maximum 5 reconnection attempts
  - Automatic state restoration
  - Silent recovery attempts
  - Connection health monitoring

- **Error Handling**
  - Clear user feedback
  - Graceful degradation
  - Automatic recovery attempts
  - Progress preservation
  - CRITICAL: Must maintain server connection

### Dependencies
[Previous dependencies section remains unchanged...]

## Development Setup
[Previous development setup section remains unchanged...]

## Technical Considerations

### State Management System
- **Client-Side State (`app/templates/index.html`)**
  * AdventureStateManager class:
    ```javascript
    class AdventureStateManager {
        STORAGE_KEY = 'adventure_state';
        // Methods: saveState, loadState, clearState
        // Uses localStorage for persistence
        // Maintains complete chapter history
    }
    ```
  * WebSocketManager class:
    ```javascript
    class WebSocketManager {
        // Properties
        stateManager: AdventureStateManager;
        connection: WebSocket | null;
        reconnectAttempts: number;
        maxReconnectAttempts: number;
        
        // Methods
        handleDisconnect(): Promise<void>;
        calculateBackoff(): number;
        reconnect(): Promise<void>;
        setupConnectionHandlers(): void;
    }
    ```
  * State Structure:
    ```typescript
    interface AdventureState {
        storyCategory: string;
        lessonTopic: string;
        story_length: number;
        current_chapter_id: string;
        chapters: ChapterData[];
        selected_narrative_elements: Record<string, string>;
        selected_sensory_details: Record<string, string>;
        selected_theme: string;
        selected_moral_teaching: string;
        selected_plot_twist: string;
        metadata: Record<string, any>;
        current_storytelling_phase: string;
    }
    ```
  * Storage Considerations:
    - localStorage preferred over sessionStorage
    - Not affected by cookie settings
    - Typically 5-10MB limit
    - Persists across browser sessions
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
  * State Update Handling:
    - Critical response preservation for LESSON chapters
    - Proper chapter type determination from planned_chapter_types
    - Robust handling of existing vs new chapters:
      * Existing chapters: preserve responses, update content only
      * New chapters: set appropriate response based on type
    - State consistency through sorted chapter ordering
    - Enhanced error handling with detailed logging
    - CRITICAL: Cannot recreate responses from client data

  * LESSON Chapter Requirements:
    - Must call process_consequences() after every LESSON chapter
    - Function generates narrative guidance based on:
      * Whether answer was correct (is_correct)
      * The lesson question
      * The chosen answer
      * Current chapter number
    - Critical for story continuity and educational impact
    - Influences subsequent chapter generation
    - CRITICAL: Skipping this step breaks the educational narrative flow
  
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

[Rest of the content remains unchanged...]
