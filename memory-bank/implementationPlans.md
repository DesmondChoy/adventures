# Implementation Plans

## Current Focus: Chapter Numbering Synchronization Fix (COMPLETED)

### Problem Statement
Chapter numbers were briefly showing incorrect values (e.g., "Chapter 1 of" then "Chapter 2 of") due to race conditions between frontend state calculations and server responses during adventure resumption and progression.

### Root Cause Analysis
- Multiple sources were updating chapter progress simultaneously:
  1. Frontend immediately calculated and displayed chapter numbers based on local state
  2. Server sent different chapter numbers via WebSocket messages at different times
  3. Race conditions between `adventure_loaded` and `chapter_update` messages
- WebSocketManager updated progress on connection open, then server sent different numbers
- makeChoice function updated progress before server confirmation

### Solution Implemented
1. **Removed premature progress updates**: Frontend no longer calculates chapter numbers independently
   - `webSocketManager.js:126` - removed updateProgress call on state restoration
   - `main.js:100` - removed updateProgress call in makeChoice function
2. **Enhanced server responses**: Added authoritative chapter numbers to all relevant server messages
   - `stream_handler.py:546-547` - added `current_chapter` and `total_chapters` to `chapter_update` messages
3. **Improved frontend message handling**: Added proper handler for chapter updates
   - `uiManager.js:661-669` - added handler for `chapter_update` messages to update progress display

### Files Modified
- `/app/static/js/webSocketManager.js` - removed race condition in state restoration
- `/app/static/js/main.js` - removed premature progress update in choice handling
- `/app/services/websocket/stream_handler.py` - added chapter numbers to server responses
- `/app/static/js/uiManager.js` - enhanced message handling for chapter updates

## Previous Focus: Protagonist Inconsistencies Fix

### Problem Statement
The current image generation process struggles to maintain visual stability for the protagonist across different chapters. Combining base protagonist look, agency details, and chapter scene description consistently via simple templating is challenging, leading to potential visual conflicts or ignored elements.

### Root Cause Analysis
- The `ImageGenerationService.enhance_prompt` function uses template concatenation, lacking semantic understanding to logically merge potentially conflicting visual descriptions (e.g., base clothing vs. agency armor).
- Directly feeding complex, structured prompts to Imagen relies heavily on its interpretation, leading to inconsistency.

### Proposed Solution: Two-Step Prompt Generation
Implement a two-step process where an intermediary LLM call synthesizes the final, optimized prompt for the image generation model (Imagen):

1. **Gather Inputs:** Collect visual components (protagonist base look, agency details, chapter scene description, story visual sensory detail).
2. **LLM Prompt Synthesis:** Use a dedicated function (`synthesize_image_prompt`) with a specific meta-prompt to instruct an LLM to logically combine these inputs.
3. **Image Generation:** Feed the synthesized prompt to `ImageGenerationService.generate_image_async()`.

### Completed Steps
- ✅ Define predefined protagonist descriptions in `prompt_templates.py`
- ✅ Add `protagonist_description` field to `AdventureState` model
- ✅ Create `synthesize_image_prompt` function for intelligent prompt construction
- ✅ Modify image generation trigger logic in `image_generator.py`
- ✅ Update `generate_agency_images` to focus on agency elements only
- ✅ Remove redundant `enhance_prompt` function
- ✅ Verify correct model usage (Gemini Flash)
- ✅ Add detailed logging and monitoring

### Remaining Steps
- ✅ Update Chapter 1 prompt generation to incorporate protagonist description: *(Done as per wip/implemented/protagonist_inconsistencies.md)*
  - Modify `FIRST_CHAPTER_PROMPT` template in `prompt_templates.py` to include protagonist description
  - Update `build_first_chapter_prompt` in `prompt_engineering.py` to pass protagonist description
- 🔲 Add comprehensive tests for the new functionality
- ✅ Add additional logging to track visual consistency across chapters *(Largely done as per wip/implemented/protagonist_inconsistencies.md & wip/implemented/characters_evolution_visual_inconsistencies.md)*
- 🔲 Implement protagonist gender consistency checks
- 🔲 Update documentation to reflect the new approach *(Core Memory Bank files)*

## Future Implementation: Persistent Storage Solution

### Problem Statement
The current in-memory storage implementation (`StateStorageService`) loses all stored states when the server restarts, causing disruption to users who were viewing the Summary Chapter.

### Proposed Solutions

#### Option 1: Redis-Based Storage
- Implement `RedisStateStorageService` that uses Redis for state persistence
- Advantages: Fast performance, built-in expiration, support for complex data structures
- Considerations: Requires Redis server, additional infrastructure dependency

#### Option 2: MongoDB-Based Storage
- Implement `MongoDBStateStorageService` for document-based storage
- Advantages: Flexible schema, native JSON storage, built-in scaling
- Considerations: Requires MongoDB setup, possible overhead for simple storage needs

#### Option 3: File-Based Storage
- Implement `FileSystemStateStorageService` that stores states as JSON files
- Advantages: Simple implementation, no additional infrastructure needed
- Considerations: Slower than in-memory or Redis, potential file system limitations

### Implementation Steps (Future)
1. Create abstract `BaseStateStorageService` interface
2. Implement selected storage solution
3. Add configuration options to switch between storage backends
4. Implement automatic data pruning for old states
5. Add server restart recovery mechanisms
6. Update tests to verify persistence across restarts

## Future Implementation: WebSocket Disconnection Fix

### Problem Statement
When a user navigates from the adventure page to the summary page, the server continues attempting to send messages over the now-closed WebSocket connection, generating errors in the logs.

### Proposed Solution
Improve WebSocket connection lifecycle management to properly detect and handle client disconnections.

### Implementation Steps (Future)
1. Add proper connection closure detection in WebSocket handlers
2. Implement cleanup for orphaned WebSocket connections
3. Add better error handling around send operations
4. Implement graceful shutdown of WebSocket tasks when disconnection is detected
5. Add comprehensive logging for connection lifecycle events
6. Update tests to verify proper disconnection handling
