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
    - Cleared on story completion

[Rest of the content remains unchanged...]
