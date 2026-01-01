# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Learning Odyssey is an AI-powered interactive educational storytelling platform. Children select a story world and educational topic, then progress through personalized adventures where choices shape the narrative. The application uses LLM-generated content with structured chapter types (STORY, LESSON, REFLECT, CONCLUSION, SUMMARY).

## Development Commands

### Running the Application
```bash
# Activate virtual environment (required for all Python commands)
source .venv/bin/activate

# Run development server
uvicorn app.main:app --reload
```

### Dependencies
```bash
pip install -r requirements.txt
```

## Architecture Overview

### Core Flow
1. **WebSocket Router** (`app/routers/websocket_router.py`) - Entry point for adventure sessions, handles JWT auth
2. **AdventureStateManager** (`app/services/adventure_state_manager.py`) - Central state management
3. **ChapterManager** (`app/services/chapter_manager.py`) - Chapter type sequencing and story element selection
4. **LLMServiceFactory** (`app/services/llm/factory.py`) - Dual-model architecture for cost optimization

### Dual-Model LLM Architecture
The factory pattern routes tasks to appropriate models (~50% cost reduction):
- **Gemini Flash** (29% of ops): Complex reasoning - `story_generation`, `image_scene_generation`
- **Gemini Flash Lite** (71% of ops): Simple processing - `summary_generation`, `paragraph_formatting`, `character_visual_processing`, `image_prompt_synthesis`

```python
from app.services.llm.factory import LLMServiceFactory
llm = LLMServiceFactory.create_for_use_case("story_generation")  # Returns Flash
llm = LLMServiceFactory.create_for_use_case("summary_generation")  # Returns Flash Lite
```

### State Model
`AdventureState` (in `app/models/story.py`) is the central data structure:
- `planned_chapter_types`: Pre-determined sequence of ChapterType enums
- `chapters`: List of completed ChapterData objects
- `selected_narrative_elements`, `selected_sensory_details`: Story elements chosen at initialization
- `chapter_summaries`, `lesson_questions`: Accumulated data for final summary
- `character_visuals`: Dict tracking visual descriptions for all characters (for image consistency)
- `protagonist_description`: Base visual description of protagonist
- `metadata`: Agency details, challenge history, timing data

### Chapter Type Sequencing
Fixed 10-chapter structure with rules:
- Chapter 1 and 9: STORY
- Chapter 10: CONCLUSION
- One LESSON-REFLECT-STORY sequence placed randomly between chapters 2-7
- Two additional non-consecutive LESSON chapters
- Remaining positions: STORY

### WebSocket Services (app/services/websocket/)
- `core.py`: Connection management and coordination
- `choice_processor.py`: User choice handling, triggers character visual updates
- `content_generator.py`: Chapter content generation
- `stream_handler.py`: Live streaming responses (chunk-by-chunk for performance)
- `image_generator.py`: AI image generation with two-step prompt synthesis
- `summary_generator.py`: Final adventure summary

### Data Sources
- `app/data/lessons/*.csv`: Educational questions by topic
- `app/data/stories/*.yaml`: Story categories with narrative elements, sensory details, themes

### Persistence
- **Supabase**: User auth (Google OAuth + Guest), adventure state, telemetry
- `StateStorageService`: State persistence with RLS policies
- `TelemetryService`: Analytics logging with duration tracking

## Critical Development Patterns

### 1. Dynamic Narrative Handling (CRITICAL)
Narrative content is generated dynamically by LLMs and is inherently variable. **Never hardcode narrative text in application logic or tests.**
- Rely on structure (AdventureState fields, ChapterType) not specific content
- Use metadata for reliable decision-making
- Tests should verify state transitions and structure, not narrative sentences

### 2. Live Streaming Performance
Use `stream_chapter_with_live_generation()` for 50-70% faster chapter generation:
```python
# CORRECT - Stream directly from LLM
async for chunk in get_llm_service().generate_chapter_stream():
    await websocket.send_text(chunk)

# AVOID - Collecting then streaming (causes 2-5s delays)
content = await llm.generate_content()  # Blocks
await stream_word_by_word(content)
```

### 3. Background Task Pattern
Non-critical tasks (summaries, visual extraction) run in background after streaming:
```python
# Defer tasks until after streaming completes
state.deferred_summary_tasks.append(create_visual_extraction_task)
# Execute after streaming
await execute_deferred_summary_tasks(state)
```

### 4. Two-Step Image Prompt Synthesis
Images use a sophisticated synthesis process for visual consistency:
1. Generate scene description from chapter content (`IMAGE_SCENE_PROMPT`)
2. LLM combines scene + protagonist look + agency + character_visuals into final prompt
3. Send synthesized prompt to Imagen

### 5. Character Visual Evolution
- `state.character_visuals` tracks all character appearances
- `CHARACTER_VISUAL_UPDATE_PROMPT` extracts descriptions from each chapter
- `update_character_visuals()` merges new descriptions intelligently
- **System-wide character description rules in `SYSTEM_PROMPT_TEMPLATE` are NOT duplication** - they ensure extractable descriptions in every chapter

### 6. Security: User Isolation
- WebSocket: Authenticated users access adventures via `user_id` only (no `client_uuid` fallback)
- REST APIs: `validate_user_adventure_access()` checks ownership before data access
- Guest adventures (`user_id IS NULL`) remain accessible to anyone

### 7. On-Demand Summary Generation
Missing summaries are generated lazily when the summary screen is requested (not during chapter flow):
```python
# In summary_generator.py
await ensure_all_summaries_exist(state)  # Generates only missing summaries
```
This avoids complex async task coordination and handles any scenario where summaries might be missing.

### 8. Story Chapter Validation with Retries
Story chapters MUST have exactly 3 choices. The system uses `generate_chapter_content_with_retries()` which:
- Validates LLM output has 3 choices
- Retries up to 3 times if validation fails
- Only streams content that passes validation

### 9. Chapter Update Timing
**Critical**: Send `chapter_update` message BEFORE streaming content, not after. This ensures the UI shows the correct chapter number immediately when content starts streaming.

## Testing Guidelines

### Manual Testing with Playwright MCP

Use the Playwright MCP server for end-to-end testing. Launch the dev server first, then navigate through a complete adventure.

```bash
# Terminal 1: Start the dev server
source .venv/bin/activate
uvicorn app.main:app --reload

# Terminal 2: Use Playwright MCP via Claude Code to test
```

#### Test Flow
1. Navigate to `http://localhost:8000/select`
2. Select a story category and lesson topic
3. Progress through all 10 chapters by clicking choices
4. Click "Memory Lane" to view the summary
5. Verify summary shows actual adventure data

#### Critical Checkpoints

**Image Behavior (Check at EVERY chapter transition)**
- Wait for content to fully stream before checking for image
- Image should appear AFTER text content completes (allow 5-10 seconds after content)
- Verify image alt text matches current chapter: `"Illustration for Chapter X"`
- Previous chapter's image must NOT be visible when new chapter starts
- If image doesn't appear, check console for errors

**Chapter Transitions**
- Chapter counter should update immediately when new chapter starts (e.g., "Chapter 3 of 10")
- Old content should be cleared before new content streams
- All 3 choice buttons should be visible and clickable after content streams
- No JavaScript errors in console during transitions

**Content Streaming**
- Allow 30 seconds for chapter content to fully stream
- Text should appear progressively (word-by-word or chunk-by-chunk)
- Loader should appear during generation and hide when content starts streaming

**Summary Screen Validation**
- Verify "Chapters Completed" shows total number of chapters
- Verify "Questions Answered" shows `3`
- All 10 chapter summaries should have meaningful titles (not "Chapter 1: The Beginning" placeholder)
- All 3 lesson questions should show actual questions from the adventure
- Each question should show user's answer and explanation
- If placeholder data appears (rare), refresh the page - this indicates a race condition in `react-app-patch.js`

**WebSocket Stability**
- Watch for timeout errors in console (especially after idle periods)
- If connection drops, the app should attempt reconnection
- After reconnection, state should be preserved

#### Common Issues and Debugging

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Previous chapter's image showing | `chapter_update` not hiding image container | Check `uiManager.js` hides image on `chapter_update` |
| Summary shows placeholder data | Race condition - fetch not patched in time | Refresh page; verify `patchReactFetch()` is called immediately on script load |
| Buttons unresponsive after idle | WebSocket disconnected silently | Check reconnection logic in `webSocketManager.js` |
| Image never appears | Image generation failed or timed out | Check backend logs for Imagen API errors |
| Content doesn't stream | LLM generation failed | Check backend logs for API errors |

#### Wait Times Reference
- Chapter content streaming: 10-20 seconds
- Image generation: 5-10 seconds after content
- Summary page load: 3-5 seconds
- Summary generation (first time): up to 30 seconds

### Unit Testing

#### What to Test
- State transitions and `AdventureState` updates
- Structural correctness (does chapter have content? does summary have title?)
- Correct function calls and service interactions
- Chapter type validation and sequence rules

#### What NOT to Test
- Specific LLM-generated narrative text (will break tests)
- Exact sentences or character names from generated content

#### Mocking
Use mocking to provide structurally correct but non-specific narrative content when testing components that consume it.

## Key Validation Rules

### ChapterType Enum
```python
class ChapterType(str, Enum):
    LESSON = "lesson"
    STORY = "story"
    CONCLUSION = "conclusion"
    REFLECT = "reflect"
    SUMMARY = "summary"
```

### Chapter Validation
- Story chapters: exactly 3 choices
- CONCLUSION/SUMMARY chapters: exactly 0 choices
- No consecutive LESSON chapters
- REFLECT must follow LESSON and precede STORY

## Agency Implementation

Four categories defined in `prompt_templates.py`:
- Magical Items to Craft
- Companions to Choose
- Roles or Professions
- Special Abilities

Agency is tracked in `state.metadata["agency"]` with visual details extracted from choice text.

## Frontend Architecture

### ES6 Modules (app/static/js/)
- `authManager.js`: Supabase auth, session management
- `adventureStateManager.js`: localStorage operations
- `webSocketManager.js`: Connection lifecycle, reconnection with exponential backoff
- `stateManager.js`: State transitions
- `uiManager.js`: DOM manipulation, story rendering
- `main.js`: Entry point, module coordination

### Configuration Bridge
`app/templates/components/scripts.html` sets up `window.appConfig` with server-side data for client modules.

## Environment Variables
Required in `.env`:
- `GOOGLE_API_KEY`: For LLM and image generation
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`, `SUPABASE_JWT_SECRET`: Database/auth
- `APP_ENVIRONMENT`: development/production

## Database Migrations
Supabase migrations are in `supabase/migrations/`. Apply with:
```bash
npx supabase db push
```

## Additional Documentation
- `memory-bank/` - Architectural decisions, implementation plans, progress logs, LLM best practices
- `wip/implemented/` - Detailed implementation history for major features (streaming optimization, Supabase integration, visual consistency, etc.)
