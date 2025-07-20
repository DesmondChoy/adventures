# System Patterns

## Key Design Patterns

### 1. Async Background Task Pattern (Performance Optimization)
- **Background Task Management with Race Condition Prevention:**
  * **Thread-Safe State Mutation:** Uses `async with state.summary_lock` to prevent race conditions during concurrent background operations
  * **Task Tracking:** `pending_summary_tasks` field tracks all background tasks for proper cleanup and synchronization
  * **Synchronization Points:** Critical operations (like summary screen display) await all pending tasks before proceeding
  * **Error Isolation:** Background task failures don't crash main application flow
- **Implementation Example (`app/services/websocket/choice_processor.py`):**
  ```python
  async def generate_chapter_summary_background(
      previous_chapter: ChapterData, state: AdventureState
  ) -> None:
      """Background task wrapper for chapter summary generation with error handling."""
      try:
          # ... summary generation logic ...
          await _store_summary_safe(previous_chapter, state, title, summary_text)
      except Exception as e:
          logger.error(f"Background chapter summary generation failed: {e}")
          # Ensure fallback summary to prevent summary screen issues
          async with state.summary_lock:
              if len(state.chapter_summaries) < previous_chapter.chapter_number:
                  state.chapter_summaries.append("Chapter summary not available")
  
  # Usage in main flow
  task = asyncio.create_task(generate_chapter_summary_background(previous_chapter, state))
  state.pending_summary_tasks.append(task)
  task.add_done_callback(lambda t: logger.error(f"Summary task crashed: {t.exception()}") if t.exception() else None)
  ```
- **Thread-Safe State Storage:**
  ```python
  async def _store_summary_safe(
      prev_chapter: ChapterData, state: AdventureState, title: str, summary_text: str
  ) -> None:
      """Safely write summary/title to shared state object using lock."""
      async with state.summary_lock:
          chap_idx = prev_chapter.chapter_number - 1
          # Pad lists if needed
          while len(state.chapter_summaries) <= chap_idx:
              state.chapter_summaries.append("Chapter summary not available")
          # Store actual summary
          state.chapter_summaries[chap_idx] = summary_text
  ```
- **Synchronization Before Critical Operations:**
  ```python
  async def handle_reveal_summary(...):
      # Wait for any pending summary tasks to complete
      if state.pending_summary_tasks:
          await asyncio.gather(*state.pending_summary_tasks, return_exceptions=True)
          state.pending_summary_tasks.clear()
      # ... proceed with summary display ...
  ```
- **Benefits:**
  * **Performance:** Eliminates blocking operations (1-3 second improvement)
  * **Data Integrity:** Thread-safe operations prevent race conditions
  * **Resilience:** Background failures don't affect main user experience
  * **Resource Utilization:** Better parallelization of I/O operations

### 2. Supabase Persistence Pattern
- **StateStorageService** (`app/services/state_storage_service.py`)
  * Uses the `supabase-py` client to interact with a Supabase backend.
  * Initializes the client using environment variables (`SUPABASE_URL`, `SUPABASE_SERVICE_KEY`).
  * Provides methods (`store_state`, `get_state`, `get_active_adventure_id`) for CRUD operations on the `adventures` table.
  * Handles JSON serialization/deserialization for the `state_data` column.
  * Implements an upsert mechanism in `store_state` (update if `adventure_id` exists, insert otherwise).
  * Extracts key fields (`story_category`, `lesson_topic`, `is_complete`, `completed_chapter_count`, `environment`) into dedicated columns for querying, while storing the full state in `state_data`.
  * Enables persistent adventure state across sessions and server restarts.
  * Handles `user_id` (from authenticated users) by converting it to a string before database operations to prevent serialization errors.
  * Prioritizes `user_id` over `client_uuid` for retrieving active adventures if `user_id` is available.
  ```python
  # Example Initialization in StateStorageService
  class StateStorageService:
      def __init__(self):
          load_dotenv()
          supabase_url = os.getenv("SUPABASE_URL")
          supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
          # ... error handling ...
          self.supabase: Client = create_client(supabase_url, supabase_key)
          logger.info("Initialized StateStorageService with Supabase client")

      async def store_state(self, state_data: Dict[str, Any], adventure_id: Optional[str] = None, user_id: Optional[UUID] = None, ...) -> str:
          user_id_for_db = str(user_id) if user_id is not None else None
          # ... prepares record including user_id_for_db ...
          if adventure_id:
              # ... update logic using self.supabase.table("adventures").update()...
          else:
              # ... insert logic using self.supabase.table("adventures").insert()...
          # ... returns adventure_id ...

      async def get_state(self, state_id: str) -> Optional[Dict[str, Any]]:
          # ... logic using self.supabase.table("adventures").select("state_data")...
          # ... returns state_data ...

      async def get_active_adventure_id(self, client_uuid: Optional[str] = None, user_id: Optional[UUID] = None) -> Optional[str]:
          # ... logic prioritizes user_id (converted to str for query) then client_uuid ...
          # ... returns adventure_id or None ...
  ```

### 3. Security Validation and User Isolation Pattern (CRITICAL)
- **Defense-in-Depth Security Architecture:**
  * **Application Layer:** User validation in all endpoints (WebSocket + REST)
  * **Database Layer:** RLS policies prevent unauthorized database queries  
  * **Service Layer:** Comprehensive ownership validation despite service key usage
- **WebSocket User Isolation (`app/routers/websocket_router.py`):**
  * Authenticated users ONLY access adventures via their `user_id`
  * Guest users access adventures via `client_uuid` 
  * **Security Fix:** Prevents fallback to `client_uuid` for authenticated users
  ```python
  # SECURITY FIX: Only fall back to client_uuid if user is NOT authenticated
  if (
      not active_adventure_id
      and client_uuid  
      and not connection_data.get("user_id")  # ← KEY: Only for guests
  ):
      # Search by client_uuid for guest users only
  elif (
      not active_adventure_id
      and client_uuid
      and connection_data.get("user_id")  # ← Authenticated user case
  ):
      logger.info("User authenticated - skipping client_uuid fallback for security")
  ```
- **REST API User Ownership Validation (`app/routers/summary_router.py`):**
  * `validate_user_adventure_access()` function validates ownership before data access
  * Checks adventure ownership via `user_id` in metadata or state data
  * Guest adventures (`user_id IS NULL`) remain accessible
  * User adventures require authentication and ownership validation
  ```python
  async def validate_user_adventure_access(
      state_id: str, user_id: Optional[UUID], summary_service: SummaryService
  ) -> dict:
      # Get raw state data to check ownership
      state_data = await summary_service.state_storage_service.get_state(state_id)
      if not state_data:
          raise HTTPException(status_code=404, detail="Adventure not found")
      
      # Check ownership logic...
      if adventure_user_id_str and adventure_user_id_str != str(user_id):
          raise HTTPException(status_code=403, detail="Access denied: not your adventure")
      
      return state_data
  ```
- **Service Key vs RLS Consideration:**
  * `StateStorageService` uses `SUPABASE_SERVICE_KEY` which bypasses RLS policies
  * Application-level validation compensates by checking ownership before data access
  * RLS policies provide additional protection for direct database queries
- **Goal:** Complete user data isolation preventing cross-user adventure access while preserving guest functionality.

### 3. WebSocket JWT Authentication and User Identification Pattern
- **Mechanism:**
  * User authentication (e.g., Google Sign-In) is handled on the frontend, yielding a JWT from Supabase Auth.
  * The JWT is passed as a query parameter (`token`) when establishing the WebSocket connection (`/ws/story/{story_category}/{lesson_topic}?token=...`).
  * **Backend Validation (`app/routers/websocket_router.py`):**
    * The `story_websocket` endpoint receives the `token`.
    * If a token is present, it's decoded and validated using `PyJWT` and the `SUPABASE_JWT_SECRET` environment variable.
    * The `sub` claim from the JWT payload is extracted as the `user_id`.
    * This `user_id` (as a `UUID` object) is stored in a `connection_data` dictionary associated with the WebSocket session.
    * **Telemetry Timing (As of 2025-07-20):** `connection_data` also stores `current_chapter_start_time_ms` for engagement duration tracking, with persistent backup in `AdventureState.metadata` for connection restart resilience.
- **Usage:**
  * The `user_id` from `connection_data` is used by services like `StateStorageService` (for associating adventures with users) and `TelemetryService` (for logging user-specific events).
  * This allows linking game state and telemetry data to authenticated users.
  * **Duration Tracking:** `current_chapter_start_time_ms` measures user engagement time per chapter for analytics (stored as `event_duration_seconds` in Supabase telemetry).
- **Error Handling:** Includes checks for missing tokens, missing JWT secret, expired tokens, and invalid tokens.
  ```python
  # Simplified example from websocket_router.py
  async def story_websocket(websocket: WebSocket, token: Optional[str] = Query(None)):
      connection_data = {"user_id": None}
      if token:
          supabase_jwt_secret = os.getenv("SUPABASE_JWT_SECRET")
          if supabase_jwt_secret:
              try:
                  payload = jwt.decode(token, supabase_jwt_secret, algorithms=["HS256"], audience="authenticated")
                  user_id_from_token_str = payload.get("sub")
                  if user_id_from_token_str:
                      connection_data["user_id"] = UUID(user_id_from_token_str)
              except Exception as e:
                  logger.warning(f"JWT processing error: {e}")
      # ... rest of WebSocket logic using connection_data["user_id"] ...
  ```

### 4. Case Sensitivity Handling Pattern
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

### 5. Modular Summary Service Pattern
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

### 6. Format Example Pattern for LLM Prompts
- **Structure and Examples**
  * Providing both incorrect and correct examples in prompts
  * Showing the incorrect example first to highlight what to avoid
  * Following with the correct example to demonstrate desired format
  * Using clear section headers like "INCORRECT FORMAT (DO NOT USE)" and "CORRECT FORMAT (USE THIS)"
  * Explicitly instructing the LLM to use exact section headers
  * Example implementation in `SUMMARY_CHAPTER_PROMPT` for title and summary extraction

### 7. Mobile-Optimized Scrolling Pattern
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

### 8. Backend-Frontend Naming Convention Pattern
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

### 9. Modular Template Structure Pattern
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

### 10. Modular JavaScript Architecture Pattern
- **ES6 Module Structure** (`app/static/js/`)
  * `authManager.js`: Handles Supabase authentication, session management, and user status UI updates
  * `adventureStateManager.js`: Manages localStorage operations for adventure state persistence and client UUID generation
  * `webSocketManager.js`: Handles WebSocket connections, reconnection logic, URL construction, and message handling setup
  * `stateManager.js`: Manages adventure state operations, state transitions, and state manipulation functions
  * `uiManager.js`: Consolidates all DOM manipulation, UI updates, story content rendering, choice display, and user interface functions (including story streaming with disabled auto-scroll)
  * `main.js`: Serves as the main entry point, coordinates all modules, handles application initialization, and manages global state

- **Configuration Bridge** (`app/templates/components/scripts.html`)
  * Sets up `window.appConfig` with server-side Jinja2 data (totalCategories, totalLessonTopics)
  * Loads the main JavaScript application module using `<script type="module">`
  * Exposes necessary functions globally for template onclick handlers
  * Minimal inline JavaScript focused on module loading and configuration

- **Benefits**
  * Clean dependency management through ES6 import/export
  * Improved testability with isolated, focused modules
  * Enhanced maintainability through separation of concerns
  * Reduced global namespace pollution
  * Clear module boundaries and responsibilities
  * Easier debugging and development with focused files

### 11. Paragraph Formatting Pattern
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

### 12. Story Simulation Pattern
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

### 13. Dual-Purpose Content Generation
- **Chapter Summaries** (`generate_chapter_summary()`)
  * Focus on narrative events and character development
  * 70-100 words covering key events and educational content
  * Used for SUMMARY chapter and adventure recap
  * Written in third person, past tense narrative style

- **Image Scenes** (`generate_image_scene()`)
  * Focus on the most visually striking moment from a chapter.
  * Generates a concise visual description (approx. 50 words) of this moment using `IMAGE_SCENE_PROMPT`.
  * This description serves as a primary input to the two-step image prompt synthesis process.
  * Describes specific dramatic action or emotional peak, focusing purely on visual elements of the immediate scene.

### 14. Dynamic Narrative Handling Pattern (CRITICAL)
- **Principle:** Narrative content (story text, character names, specific events) is generated dynamically by LLMs and is inherently variable. It MUST NOT be hardcoded into application logic or tests.
- **Strategies:**
  * **Rely on Structure:** Base logic and validation on the defined structure of the `AdventureState`, `ChapterData`, and expected `ChapterType`. Check for the presence and type of data, not its specific content.
  * **Use Metadata:** Leverage structured data stored in `state.metadata` (e.g., agency details, extracted character identifiers) for reliable decision-making.
  * **Abstract Testing:** Focus tests on verifying state transitions, structural correctness of data, service interactions, and adherence to chapter flow rules. Avoid asserting against specific narrative sentences. (See `testingGuidelines.md`).
  * **LLM-Based Extraction:** If specific details *must* be extracted from narrative text (e.g., character visuals), use robust LLM-based extraction prompts designed for this purpose. Store the extracted information in structured fields within the state (e.g., `state.character_visuals`), rather than re-parsing the text later. Avoid brittle regex for narrative content.
- **Goal:** Ensure the application is robust and functions correctly regardless of the specific text generated by the LLM in any given playthrough.

### 15. Character Visual Evolution Pattern
- **State Management (`AdventureState.character_visuals`):**
  * A dictionary `state.character_visuals` stores the current visual descriptions for all significant characters (protagonist and NPCs), keyed by character name.
  * Initialized with the protagonist's base description (`state.protagonist_description`).
- **Asynchronous Visual Updates (`choice_processor.py` -> `_update_character_visuals`):**
  * After each chapter's narrative is processed, an asynchronous task is triggered.
  * This task uses the `CHARACTER_VISUAL_UPDATE_PROMPT` with the latest chapter content and the current `state.character_visuals` as input.
  * The LLM identifies new characters or visual changes to existing ones and returns an updated JSON dictionary of visuals.
  * Robust JSON extraction and error handling are employed.
- **Synchronous Extraction Fix:**
  * The call to `_update_character_visuals` is made synchronously (awaited) within `choice_processor.py` after a timing issue was identified with fully asynchronous calls, ensuring visual data is processed reliably before subsequent steps that might depend on it. Non-streaming LLM calls are used for this extraction to get complete JSON objects. (Details in `wip/implemented/character_visual_extraction_timing_fix.md`).
- **Intelligent Merging (`AdventureStateManager.update_character_visuals`):**
  * The `AdventureStateManager` takes the updated visuals dictionary from the LLM.
  * It intelligently merges this with the existing `state.character_visuals`, only updating descriptions for characters that are new or have changed, preserving existing descriptions otherwise.
  * Detailed logging tracks new, updated, and unchanged character visuals.
- **Goal:** Maintain consistent and evolving character appearances throughout the adventure, reflecting narrative developments in their visual descriptions for use in image generation.

### 16. Chapter Number Display Synchronization Pattern
- **Problem:** Chapter numbers displayed incorrect values during streaming due to timing issues between frontend display and backend state mutations
- **Root Causes Identified:**
  * **Timing Dependency**: Using `len(state.chapters)` creates race conditions between state mutations and display updates
  * **Code Path Divergence**: Final chapter follows different execution path (`send_story_complete()`) that bypassed chapter number updates
  * **Calculation After Mutation**: Computing chapter numbers after chapters were already appended to state caused off-by-one errors
- **Solution Architecture:**
  * **Explicit Parameters**: Use explicit `chapter_number` parameter instead of state-derived calculations
  * **Message-First Pattern**: Send `chapter_update` messages BEFORE content streaming, not after
  * **Unified Flow Coverage**: Ensure both normal chapters and final chapter send consistent `chapter_update` messages
- **Implementation Pattern:**
  * **Normal Chapters** (`stream_handler.py`): `send_chapter_data()` → `stream_text_content()` 
  * **Final Chapter** (`core.py`): Add explicit `chapter_update` message in `send_story_complete()`
  * **Chapter Number Source**: Use `state.chapters[-1].chapter_number` (from appended chapter) not `len(state.chapters) + 1`
- **Key Files:**
  * `/app/services/websocket/stream_handler.py` - Chapter timing and calculation logic
  * `/app/services/websocket/core.py` - Final chapter special handling
  * `/app/static/js/uiManager.js` - Frontend message processing
- **Benefits:** Eliminates timing-dependent chapter numbering, ensures consistent display across all chapters, prevents legacy code path issues

### 17. Landing Page Visual Accuracy Pattern
- **Problem:** Landing page images can create false expectations about app functionality
- **Core Principle:** Visual representations must accurately reflect the actual user experience, not idealized or misleading interpretations
- **Implementation Strategy:**
  * **Truthful Metaphors**: Use images that metaphorically represent the core functionality (reading/text → adventure) rather than literal depictions of fantasy worlds
  * **Educational Context**: Include visual elements that clearly indicate learning/educational purpose (books, libraries, academic tools)
  * **Interface Hints**: Suggest text-based interaction through floating words, open books, or portal metaphors
  * **Static Assets**: Store custom images in `app/static/images/` directory following established FastAPI static file serving patterns
- **Example Implementation:**
  * **Before**: Generic Unsplash forest photo suggesting graphical game experience
  * **After**: Custom magical library with floating text swirling toward portal, showing books as gateway to adventure
  * **Technical**: Replace `src="https://external-url"` with `/static/images/custom-image.png`
- **Benefits:**
  * Reduces user confusion and expectation mismatch
  * Increases user retention by setting accurate expectations
  * Maintains fantasy appeal while being truthful about functionality
  * Creates unique brand identity instead of generic stock photos

### 18. Two-Step Image Prompt Synthesis Pattern
- **Overview:** A multi-step process to create rich, context-aware prompts for the image generation model (Imagen), enhancing visual consistency and relevance.
- **Step 1: Gather Core Visual Inputs:**
  * **Image Scene Description:** A concise (~50 words) description of the chapter's most visually striking moment, generated by an LLM call using `IMAGE_SCENE_PROMPT` and the chapter content. This focuses purely on the immediate scene's action and visual elements.
  * **Protagonist Base Look:** The consistent base visual description of the protagonist, stored in `state.protagonist_description`.
  * **Agency Details:** The protagonist's chosen agency (item, companion, etc.), including its name, category, and specific visual description, stored in `state.metadata.agency`. (Enhanced by `wip/implemented/agency_visual_details_enhancement.md`).
  * **Story Visual Sensory Detail:** An overall visual mood/style element for the story, from `state.selected_sensory_details['visuals']`.
  * **Evolved Character Visuals:** The latest available `state.character_visuals` dictionary, containing up-to-date descriptions for the protagonist (if evolved) and NPCs.
- **Step 2: LLM-Powered Prompt Synthesis (`ImageGenerationService.synthesize_image_prompt`):**
  * An LLM (Gemini Flash) is invoked with a specialized meta-prompt (`IMAGE_SYNTHESIS_PROMPT`).
  * This meta-prompt instructs the LLM to logically combine all the above inputs into a single, coherent, and vivid visual scene description (target 30-50 words) suitable for Imagen.
  * The LLM is guided to prioritize the immediate `Image Scene Description` while integrating the protagonist's look, agency, and relevant NPC visuals from `state.character_visuals` if they appear in the scene.
- **Step 3: Image Generation:**
  * The synthesized prompt from Step 2 is then fed to `ImageGenerationService.generate_image_async()` to produce the final image.
- **Benefits:**
  * Improves visual consistency for the protagonist and recurring NPCs.
  * Allows for dynamic integration of agency elements.
  * Produces more contextually relevant and detailed images by leveraging an LLM to intelligently merge various visual cues.
  * (Details in `wip/implemented/protagonist_inconsistencies.md` and `wip/implemented/characters_evolution_visual_inconsistencies.md`).

### 19. Summary Screen Data Integrity Issues (DEBUGGING)
- **Current Problem**: Despite multiple serialization and race condition fixes, summary screen still shows incomplete data
- **Symptoms**: 
  - 9 chapters instead of 10 (missing CONCLUSION)
  - Placeholder questions instead of actual LESSON chapter questions
  - Missing `planned_chapter_types` during state reconstruction
  - All chapters stored as "story" type regardless of actual type during adventure
- **Root Cause Analysis**: Issue appears to be in adventure progression logic, not state persistence
- **Evidence**: Adventures stopping at Chapter 9 with `last chapter type (story): False` instead of proceeding to CONCLUSION
- **Investigation Required**: 
  - Story flow determination logic for CONCLUSION chapter generation
  - LESSON chapter creation and question storage during adventures
  - Chapter type preservation during the adventure progression (not just at summary)

### 20. System-Wide Character Description Pattern (CRITICAL UX)
- **Purpose:** Ensures visual consistency across all chapters for image generation and character continuity
- **Common Misconception:** The character description rules in `SYSTEM_PROMPT_TEMPLATE` (lines 42-45) may appear to duplicate guidance from `FIRST_CHAPTER_PROMPT`, but they serve a fundamentally different purpose
- **Why This Is NOT Duplication:**
  * **SYSTEM_PROMPT_TEMPLATE rules**: Apply to ALL chapter types (STORY, LESSON, REFLECT, CONCLUSION) to ensure every chapter provides extractable character descriptions
  * **FIRST_CHAPTER_PROMPT guidance**: Establishes initial protagonist foundation only
- **Visual Consistency Architecture:**
  * Each chapter content is scanned for character descriptions using `CHARACTER_VISUAL_UPDATE_PROMPT`
  * Descriptions are extracted and stored in `state.character_visuals` dictionary
  * Two-step image synthesis process (`synthesize_image_prompt()`) combines these descriptions for consistent image generation
  * New characters can be introduced in any chapter, requiring consistent visual detail extraction
- **Implementation Details:**
  ```python
  # Character descriptions flow through entire system:
  # 1. SYSTEM_PROMPT_TEMPLATE forces detailed descriptions in ALL chapters
  # 2. CHARACTER_VISUAL_UPDATE_PROMPT extracts these descriptions
  # 3. update_character_visuals() stores them in state.character_visuals
  # 4. Image generation uses these for visual consistency
  ```
- **Critical Rule:** Never remove character description requirements from `SYSTEM_PROMPT_TEMPLATE` as this would break the visual consistency system that is core to the user experience
- **Files Involved:**
  * `app/services/llm/prompt_templates.py` - Character description rules
  * `app/services/image_generation_service.py` - Two-step image synthesis
  * `app/services/adventure_state_manager.py` - Character visual updates
  * `app/services/websocket/choice_processor.py` - Character visual extraction

### 21. LLM Factory Pattern for Cost Optimization
- **Architecture:** Centralized factory pattern for automatic model selection based on task complexity
- **Implementation:** `app/services/llm/factory.py` with `LLMServiceFactory` class
- **Model Assignment Strategy:**
  * **Flash (Complex Reasoning - 29% of operations):**
    - `story_generation`: Creative narrative writing with character development
    - `image_scene_generation`: Visual storytelling requiring rich descriptive language
  * **Flash Lite (Simple Processing - 71% of operations):**
    - `summary_generation`: Template-based content summarization
    - `paragraph_formatting`: Text structure improvement
    - `character_visual_processing`: JSON extraction from narrative text
    - `image_prompt_synthesis`: Structured prompt assembly for image generation
    - `chapter_summaries`: Test utility summarization
    - `fallback_summaries`: Emergency content generation
- **Usage Pattern:**
  ```python
  from app.services.llm.factory import LLMServiceFactory
  
  # Automatic model selection based on complexity
  llm_service = LLMServiceFactory.create_for_use_case("summary_generation")  # Flash Lite
  story_service = LLMServiceFactory.create_for_use_case("story_generation")   # Flash
  
  # Direct model access when needed
  flash_service = LLMServiceFactory.create_flash()
  lite_service = LLMServiceFactory.create_flash_lite()
  ```
- **Implementation Status:** ✅ **COMPLETED** with lazy instantiation pattern to prevent WebSocket timeouts
- **Module-Level Issue Resolved:** Replaced direct factory instantiation with lazy loading pattern:
  ```python
  # Problematic (causing WebSocket timeouts):
  llm_service = LLMServiceFactory.create_for_use_case("character_visual_processing")
  
  # Fixed (lazy instantiation):
  def get_llm_service():
      global _llm_service
      if _llm_service is None:
          _llm_service = LLMServiceFactory.create_for_use_case("character_visual_processing")
      return _llm_service
  ```
- **Benefits:**
  * **Cost Reduction:** ~50% savings through strategic Flash Lite usage
  * **Quality Preservation:** Complex reasoning tasks maintain full Flash capabilities
  * **Centralized Configuration:** Easy to adjust model assignments
  * **WebSocket Stability:** Lazy instantiation prevents module-level initialization delays
  * **Maintainability:** Clear separation between cost optimization and business logic

### 22. Chapter Opening Enhancement System
- **Problem:** Chapters consistently started with "The" making them formulaic and disengaging
- **Oracle Analysis:** Identified that prompts lacked guidance on HOW to begin chapters, causing LLMs to default to safe "The..." patterns
- **Architecture:** Contextual guidance system in `SYSTEM_PROMPT_TEMPLATE` rather than rigid rules
- **Implementation Strategy:**
  * **Replaced TV Episode Metaphor:** Changed from standalone episode approach to book chapter flow
  * **Book Flow Emphasis:** "Think of yourself as writing the next chapter in a captivating book - each chapter should flow seamlessly from where the previous chapter left off"
  * **Prioritized Opening Hook:** Moved opening guidance to first position as primary instruction
  * **Expanded Opening Techniques:** Added environmental storytelling (Roald Dahl-inspired) and emotional hooks (J.K. Rowling-style atmosphere) alongside dialogue, action, sensory details, and character thoughts
  * **Flexible Approach:** Provides multiple techniques rather than rigid rules
- **Technical Details:**
  * **Location:** `SYSTEM_PROMPT_TEMPLATE` in `app/services/llm/prompt_templates.py`
  * **Scope:** Applied to all chapter types (story, lesson, reflect, conclusion) since system prompt is universal
  * **Approach:** Contextual guidance rather than hard-coded restrictions
- **Key Improvements:**
  * **Primary Focus on Opening:** Opening hook guidance moved to first position, emphasizing it as the primary consideration
  * **Flow-Based:** Emphasizes connection to previous chapter rather than standalone episodes
  * **Engagement Focus:** Prioritizes reader engagement over formulaic structure
  * **Expanded Technique Arsenal:** Added environmental storytelling and emotional hooks to existing techniques
  * **Natural Transitions:** Encourages seamless flow from where previous chapter ended
- **User Experience Impact:**
  * **Immediate Hook Priority:** Opening hook is now the first consideration, ensuring every chapter starts with engagement
  * **Diverse Chapter Openings:** Expanded toolkit including environmental storytelling and emotional hooks creates more varied beginnings
  * **Better Flow:** Chapters feel more connected to previous content rather than episodic restarts
  * **Enhanced Literary Quality:** More sophisticated techniques inspired by proven children's authors
  * **Seamless Reading Experience:** Natural transitions that feel like turning pages in a captivating book
- **Implementation Status:** ✅ **COMPLETED** (2025-07-15)
- **Files Modified:** `app/services/llm/prompt_templates.py` (updated SYSTEM_PROMPT_TEMPLATE with new chapter opening guidance)

### 23. Mobile Auto-Scroll Behavior System
- **Problem:** Inconsistent auto-scroll behavior during story streaming on mobile devices - sometimes scrolled, sometimes didn't
- **Root Cause:** Auto-scroll code was applying `storyContent.scrollTop = storyContent.scrollHeight` but `storyContent` wasn't the actual scrollable element
- **Technical Investigation:**
  * **HTML Structure:** `storyContainer` (outer with `overflow: hidden`) contains `storyContent` (inner text div)
  * **Font Size Manager:** Listens to scroll events on `storyContainer`, not `storyContent`
  * **Mobile Behavior:** On mobile, scrollable element is typically window or document body
  * **Inconsistent Results:** `storyContent.scrollTop` doesn't work reliably when `storyContent` itself isn't scrollable
- **Solution Architecture:**
  * **Initial Fix:** Changed to `window.scrollTo(0, document.body.scrollHeight)` to use correct scrollable element
  * **Final Decision:** Disabled auto-scroll entirely to give users full control over reading pace
  * **Implementation:** Commented out auto-scroll code in `appendStoryText` function
- **Technical Details:**
  * **Location:** `app/static/js/uiManager.js` line 566 in `appendStoryText` function
  * **Change:** Replaced auto-scroll code with descriptive comment explaining the decision
  * **Impact:** Eliminated all unexpected scrolling behavior during streaming on any device
- **User Experience Impact:**
  * **Consistent Behavior:** No more unpredictable scrolling during story streaming across all devices
  * **User Control:** Users can manually scroll to read new content at their preferred pace
  * **Mobile Friendly:** Eliminates jarring auto-scroll behavior that was inconsistent on mobile devices
- **Implementation Status:** ✅ **COMPLETED** (2025-07-15)
- **Files Modified:** `app/static/js/uiManager.js` (disabled auto-scroll in appendStoryText function)

### 24. Live Streaming Optimization Pattern
- **Problem:** Content generation blocks streaming by collecting entire LLM response before streaming begins
- **Root Cause Analysis:** Multiple blocking operations created 4-8 second delays before streaming could start
- **Performance Impact:** Users wait 4-8 seconds seeing only loading screens instead of immediate content
- **Bottlenecks Identified:**
  * **Chapter summary generation**: 1-3 seconds blocking (RESOLVED via async background tasks)
  * **Character visual extraction**: 1-3 seconds blocking (RESOLVED via background deferral)
  * **Content generation blocking**: 1-3 seconds collecting LLM response before streaming (RESOLVED via live streaming)
  * **First chapter inconsistency**: Used word-by-word streaming instead of chunk streaming (RESOLVED)
- **Multi-Phase Solution (All COMPLETED):**
  ```python
  # PHASE 1 - Background Summary Tasks (COMPLETED):
  asyncio.create_task(generate_chapter_summary_background(previous_chapter, state))
  
  # PHASE 2 - Deferred Character Visuals (COMPLETED):
  state.deferred_summary_tasks.append(create_visual_extraction_task)
  
  # PHASE 3 - Live Streaming Generation (COMPLETED):
  async for chunk in get_llm_service().generate_chapter_stream():
      await websocket.send_text(chunk)  # Stream immediately
      accumulated_content += chunk
  
  # PHASE 4 - First Chapter Consistency (COMPLETED):
  # process_start_choice() now uses same live streaming as other chapters
  ```
- **Architecture Benefits:**
  * **Immediate Feedback:** Content streams as LLM generates it (50-70% faster)
  * **Background Processing:** Non-critical tasks run after streaming completes
  * **Consistent Performance:** All chapters use same live streaming approach
  * **Quality Preservation:** All content processing maintained through post-streaming cleanup
- **Technical Implementation:**
  * **Files Modified:**
    - `app/services/websocket/stream_handler.py` (live streaming function)
    - `app/services/websocket/choice_processor.py` (background task deferral + first chapter live streaming)
    - `app/services/websocket/core.py` (first chapter WebSocket parameter)
    - `app/static/js/uiManager.js` (choice duplication fix)
  * **Key Features:**
    - Direct LLM streaming without intermediate collection
    - Deferred task execution after streaming completes
    - Graceful fallback to traditional method if live streaming fails
    - Content replacement to clean choice text duplication
- **Implementation Status:** ✅ **FULLY COMPLETED** (2025-07-20)
- **Performance Results:**
  * **50-70% faster chapter transitions** across all chapters
  * **Eliminated 2-5 second streaming delays**
  * **Consistent chunk-by-chunk streaming** from Chapter 1 through completion
  * **Maintained all functionality** while achieving dramatic performance improvement
