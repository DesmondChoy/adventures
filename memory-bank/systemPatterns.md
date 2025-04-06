# System Patterns

## Key Design Patterns

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
  ```python
  # Convert chapter_type to lowercase
  if isinstance(chapter["chapter_type"], str):
      chapter["chapter_type"] = chapter["chapter_type"].lower()
      logger.debug(f"Converted chapter_type to lowercase: {chapter['chapter_type']}")
  ```

### 3. Modular Summary Service Pattern
- **Package Structure** (`app/services/summary/`)
  * Organized by responsibility with clear component separation
  * Proper package exports through `__init__.py`
  * Comprehensive unit tests
  * Dependency injection for improved testability

- **Dependency Injection Pattern**
  * Components receive dependencies through constructor parameters
  * Facilitates unit testing with mock objects
  * Reduces coupling between components
  * Example in `summary_router.py`:
  ```python
  def get_summary_service():
      """Dependency injection for SummaryService."""
      state_storage_service = StateStorageService()
      return SummaryService(state_storage_service)
      
  @router.get("/api/adventure-summary")
  async def get_adventure_summary(
      state_id: Optional[str] = None,
      summary_service: SummaryService = Depends(get_summary_service)
  ):
      # Use injected summary_service
  ```

### 4. Format Example Pattern for LLM Prompts
- **Structure and Examples**
  * Providing both incorrect and correct examples in prompts
  * Showing the incorrect example first to highlight what to avoid
  * Following with the correct example to demonstrate desired format
  * Using clear section headers like "INCORRECT FORMAT (DO NOT USE)" and "CORRECT FORMAT (USE THIS)"
  * Explicitly instructing the LLM to use exact section headers
  * Example implementation in `SUMMARY_CHAPTER_PROMPT` for title and summary extraction

### 5. Mobile-Optimized Scrolling Pattern
- **Fixed Height with Dynamic Content**
  * Using fixed container heights with scrollable content areas
  * Explicit height containers with proper overflow handling
  * Conditional rendering based on device type using the `useIsMobile` hook
  * Different scroll behavior for mobile vs. desktop

- **Touch-Optimized Scroll Areas**
  * Enhanced ScrollArea component with mobile-specific properties
  * Custom CSS classes for touch device optimization
  * Properties like `touch-auto`, `overflow-auto`, and `overscroll-contain`
  * Wider scrollbars for better touch interaction
  * Visual indicators (fade effects) to show scrollable content

### 6. Backend-Frontend Naming Convention Pattern
- **Centralized Case Conversion** (`app/utils/case_conversion.py`)
  * Utility functions for converting between snake_case and camelCase
  * Recursive handling of nested dictionaries and lists
  * Applied at the API boundary to maintain language-specific conventions
  * Backend uses snake_case (Python convention), frontend receives camelCase (JavaScript convention)
  ```python
  # Convert snake_case to camelCase
  def to_camel_case(snake_str):
      components = snake_str.split("_")
      return components[0] + "".join(x.title() for x in components[1:])
      
  # Recursively convert dictionary keys
  def snake_to_camel_dict(d):
      if not isinstance(d, dict):
          return d
      
      result = {}
      for key, value in d.items():
          if isinstance(key, str) and not key.startswith("_"):
              camel_key = to_camel_case(key)
              
              if isinstance(value, dict):
                  result[camel_key] = snake_to_camel_dict(value)
              elif isinstance(value, list):
                  result[camel_key] = [
                      snake_to_camel_dict(item) if isinstance(item, dict) else item
                      for item in value
                  ]
              else:
                  result[camel_key] = value
          else:
              result[key] = value
      
      return result
  ```

### 7. Modular Template Structure Pattern
- **Template Hierarchy** (`app/templates/`)
  * `layouts/main_layout.html`: Base layout template that extends `base.html`
  * `pages/index.html`: Page-specific template that extends the layout
  * `components/`: Reusable UI components
  * `macros/`: Reusable template functions

- **Benefits**
  * Improved maintainability through separation of concerns
  * Enhanced reusability of UI components
  * Clearer code organization with focused template files
  * Easier navigation and understanding of the template structure
  * Simplified testing and debugging of individual components
  * Reduced duplication through component reuse

### 8. Paragraph Formatting Pattern
- **Regeneration-First Approach**
  * Detects text that needs paragraph formatting based on length and structure
  * Makes up to 3 new requests with the original prompt to get properly formatted text
  * Only falls back to specialized reformatting if regeneration attempts fail
  * Maintains full story context in regeneration attempts

- **Buffer-Based Streaming**
  * Collects initial text buffer (1000 characters) before checking formatting
  * Only starts special handling if text lacks proper paragraph breaks
  * Streams text normally if properly formatted
  * Optimizes for different LLM providers

### 9. Story Simulation Pattern
- **Standardized Logging**
  * Consistent event prefixes (e.g., `EVENT:CHAPTER_SUMMARY`)
  * Source tracking for debugging
  * Structured data in log entries
  * Multiple verification points to ensure complete data capture

- **Error Handling and Recovery**
  * Specific error types for different failure scenarios
  * Exponential backoff for retries with configurable parameters
  * Graceful degradation when services are unavailable
  * Comprehensive logging of error states and recovery attempts

### 10. Dual-Purpose Content Generation
- **Chapter Summaries** (`generate_chapter_summary()`)
  * Focus on narrative events and character development
  * 70-100 words covering key events and educational content
  * Used for SUMMARY chapter and adventure recap
  * Written in third person, past tense narrative style

- **Image Scenes** (`generate_image_scene()`)
  * Focus on the most visually striking moment from a chapter
  * 20-30 words of pure visual description
  * Used exclusively for image generation
  * Describes specific dramatic action or emotional peak

### 11. Dynamic Narrative Handling Pattern (CRITICAL)
- **Principle:** Narrative content (story text, character names, specific events) is generated dynamically by LLMs and is inherently variable. It MUST NOT be hardcoded into application logic or tests.
- **Strategies:**
  * **Rely on Structure:** Base logic and validation on the defined structure of the `AdventureState`, `ChapterData`, and expected `ChapterType`. Check for the presence and type of data, not its specific content.
  * **Use Metadata:** Leverage structured data stored in `state.metadata` (e.g., agency details, extracted character identifiers) for reliable decision-making.
  * **Abstract Testing:** Focus tests on verifying state transitions, structural correctness of data, service interactions, and adherence to chapter flow rules. Avoid asserting against specific narrative sentences. (See `testingGuidelines.md`).
  * **LLM-Based Extraction:** If specific details *must* be extracted from narrative text (e.g., character visuals), use robust LLM-based extraction prompts designed for this purpose. Store the extracted information in structured fields within the state, rather than re-parsing the text later. Avoid brittle regex for narrative content.
- **Goal:** Ensure the application is robust and functions correctly regardless of the specific text generated by the LLM in any given playthrough.
