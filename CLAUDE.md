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

### Deployment: Cache Busting
When deploying code changes (especially JS/CSS), update version strings to force cache invalidation:

**Files with version strings:**
- `app/templates/base.html` - CSS files and `font-size-manager.js`
- `app/templates/components/scripts.html` - ES6 module (`main.js`)

**Version format:** `?v=YYYYMMDDC` (date + letter increment)
- Example: `?v=20260101a` → `?v=20260101b` → `?v=20260102a`

**Update all version strings when:**
- Modifying any JavaScript file
- Modifying any CSS file
- Fixing bugs that users might have cached

### Deployment Security Model (Railway)
- Production deploy path is **GitHub -> Railway auto-deploy only**.
- Local `.env` is developer-only and is **not** part of production deploy artifacts unless deployment source changes.
- `.env` must remain gitignored and excluded from Docker context via `.dockerignore`.
- Before rating a secret finding as high/critical, verify:
  - whether secrets are in git history,
  - whether deploy source included local filesystem context,
  - whether secrets are present in shared logs/artifacts.

For policy details and severity criteria, use: `docs/security/deployment-model.md`.

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
Configurable chapter length (currently 10) with rules:
- First chapter through second-to-last chapter: eligible for STORY, LESSON, or REFLECT
- Last chapter: always CONCLUSION
- First chapter is always STORY (with agency choice)
- One LESSON-REFLECT-STORY sequence placed randomly in the middle chapters
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

### 2. Validated Streaming Pattern
Use `stream_chapter_with_live_generation()` to generate, validate, then stream:
```python
# CORRECT - Collect and validate first, then stream approved content
chapter_content = await generate_chapter_content_with_retries(...)
await stream_text_content(chapter_content.content, websocket)
await websocket.send_json({"type": "choices", "choices": ...})
```
This intentionally prioritizes correctness:
- Story chapters must have exactly 3 validated choices before content is shown
- Unvalidated live token streaming should be avoided for chapter output

### 3. Background Task Pattern
Non-critical tasks (summaries, visual extraction) run in background after streaming:
```python
# Defer task factories until after streaming completes
state.deferred_task_factories.append(create_visual_extraction_task)
# Execute after streaming
await execute_deferred_task_factories(state)
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

Use the `/playwright-test` skill for end-to-end testing with Playwright MCP.

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
- Craft a Magical Artifact
- Choose a Companion
- Take on a Profession
- Gain a Special Ability

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


<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:6cd5cc61 -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

**Architecture in one line:** issues live in a local Dolt DB; sync uses `refs/dolt/data` on your git remote; `.beads/issues.jsonl` is a passive export. See https://github.com/gastownhall/beads/blob/main/docs/SYNC_CONCEPTS.md for details and anti-patterns.

## Agent Context Profiles

The managed Beads block is task-tracking guidance, not permission to override repository, user, or orchestrator instructions.

- **Conservative (default)**: Use `bd` for task tracking. Do not run git commits, git pushes, or Dolt remote sync unless explicitly asked. At handoff, report changed files, validation, and suggested next commands.
- **Minimal**: Keep tool instruction files as pointers to `bd prime`; use the same conservative git policy unless active instructions say otherwise.
- **Team-maintainer**: Only when the repository explicitly opts in, agents may close beads, run quality gates, commit, and push as part of session close. A current "do not commit" or "do not push" instruction still wins.

## Session Completion

This protocol applies when ending a Beads implementation workflow. It is subordinate to explicit user, repository, and orchestrator instructions.

1. **File issues for remaining work** - Create beads for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **Handle git/sync by active profile**:
   ```bash
   # Conservative/minimal/default: report status and proposed commands; wait for approval.
   git status

   # Team-maintainer opt-in only, unless current instructions forbid it:
   git pull --rebase
   git push
   git status
   ```
5. **Hand off** - Summarize changes, validation, issue status, and any blocked sync/commit/push step

**Critical rules:**
- Explicit user or orchestrator instructions override this Beads block.
- Do not commit or push without clear authority from the active profile or the current user request.
- If a required sync or push is blocked, stop and report the exact command and error.
<!-- END BEADS INTEGRATION -->
