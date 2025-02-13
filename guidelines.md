# Learning Odyssey AI Coding Assistant Rules and Guidelines (Concise)

This guide provides concise rules and guidelines for AI coding assistants working on the Learning Odyssey project, consolidated from `.cursor/rules/`. It emphasizes code quality, maintainability, and proper application behavior.

## Table of Contents

1.  **Code Quality & Architecture**
    *   1.1. LLM Agnostic & Cross-Provider Compatibility
    *   1.2. Centralized State: `AdventureState`
    *   1.3. WebSocket State Synchronization
2.  **Cursor IDE Workflow**
    *   2.1. Rule File Location: `.cursor/rules/`
    *   2.2. Automated Prompt Debugging
3.  **Story Flow & Debugging**
    *   3.1. Story Flow Debugging
    *   3.2. Story Testing & Validation

---

## 1. Code Quality & Architecture

These guidelines are critical for maintaining code integrity and application functionality.

### 1.1. LLM Agnostic & Cross-Provider Compatibility

**Rule:**

*   Implement prompt logic in `prompt_engineering.py` to be LLM-agnostic.
*   Ensure LLM interactions in `providers.py` are compatible with both OpenAI and Gemini.
*   Test all changes with both providers.
*   Abstract provider differences in prompt engineering and service layers.
*   Keep core logic LLM-API independent.

**Rationale:** Enables LLM provider switching and long-term flexibility.

### 1.2. Centralized State: `AdventureState`

**Rule:**

*   Manage all application state exclusively via `AdventureState` in `app/models/story.py`.
*   All story progression, user context, and learning tracking must be attributes of `AdventureState`.
*   No state variables outside `AdventureState`.
*   Synchronize state transitions between client and server via WebSocket in `app/routers/websocket.py`.
*   Update all linked files when modifying `AdventureState`.
*   Use `ChapterType` enum (in `app/models/story.py`) authoritatively for chapter type.
*   Use `state.story_length` for dynamic story length handling, avoid hardcoding chapter counts.

**Rationale:** Simplifies debugging, predictability, and maintainability.

**Key Files:**

*   `app/models/story.py` (State Definition)
*   `app/routers/websocket.py` (WebSocket Logic)

### 1.3. WebSocket State Synchronization

**Rule:**

*   Ensure WebSocket communication in `websocket.py` correctly serializes/deserializes `AdventureState`.
*   Verify server and client state updates are synchronized.
*   Prevent client-server state discrepancies in WebSocket data structures.

**Rationale:** Prevents broken user experience and unpredictable behavior due to state desynchronization.

---

## 2. Cursor IDE Workflow

These rules optimize development workflow within Cursor IDE.

### 2.1. Automated Prompt Debugging

**Rule:**

*   `tests/simulations/story_simulation.py` runs automatically upon saving changes in:
    *   `app/services/llm/*`
    *   `app/routers/websocket.py`
    *   `app/services/chapter_manager.py`
    *   `app/models/story.py`
    *   `app/init_data.py`
    *   `app/data/stories.yaml`
    *   `app/data/lessons.csv`

**Debug Workflow:**

1.  Review terminal output (prompts, responses, logs).
2.  Assess expected behavior and errors.
3.  Iterate code, re-run simulation on save.

**Action:**

*   Executes shell command to run `story_simulation.py`.
*   Displays message with debugging instructions.

---

## 3. Story Flow & Debugging

Guidelines for debugging story generation and ensuring narrative integrity.

### 3.1. Story Flow Debugging

**Critical Checks:**

1.  **Narrative Preservation:** `_build_base_prompt` appends all chapters correctly with separators. Debug: `print(base_prompt)`.
2.  **Lesson Context:**  Previous lesson details in prompt if applicable. Debug: Verify lesson info in prompt.
3.  **Choice Context:** Only chosen story option in prompt if applicable. Debug: Verify choice info in prompt.

**Quick Debug Checklist:**

1.  Narrative Flow: Check `state.chapters[-1].content`, `base_prompt` (full history), chapter separators.
2.  State Consistency: Verify chapter numbers, remaining chapters, response types.
3.  Response Chain: Check `state.chapters[-1].response`, `previous_lessons`, `consequences_guidance`.

**Core Function Debug Points:**

*   **`build_user_prompt`:** Input validation (state, lesson\_question, previous\_lessons), narrative, phase, response type.
*   **`_build_base_prompt`:** Chapter history completion, phase calculation, progress metrics.
*   **`_build_chapter_prompt`:** Narrative flow, format by chapter type, consequence reflection.

**Debugging by Symptom:**

*   **Broken Narrative:** Check `state.chapters`, `_build_base_prompt`, prompt construction.
*   **Incorrect Lessons:** Verify `LessonResponse`, `correct_lesson_answers`, lesson history.
*   **Choice Failures:** Verify `StoryResponse`, `consequences_guidance`, choice history.
*   **State Issues:** Verify chapter progression, phase calculation, response type matching.

**Type Validation:** Check `AdventureState`, `ChapterData`, `LessonResponse`, `StoryResponse` in `models.py`.

### 3.2. Story Testing & Validation

**Testing:**

*   Simulation Tests: `tests/simulations/story_simulation.py`.


**Key Files for Testing:** Test files in `tests/`, data files in `app/data/`, core logic in `app/services/llm/*`, `app/routers/websocket.py`, `app/services/chapter_manager.py`, `app/models/story.py`, `app/init_data.py`.

This concise guide provides essential rules and debugging steps for contributing to Learning Odyssey. Adhering to these guidelines ensures code quality, maintainability, and a consistent user experience.

## 4. Naming Conventions

Consistent naming is crucial for code readability and understanding within the Learning Odyssey project.

### 4.1. Core Concept Naming

*   **Chapter:** Represents a unit of progression in the user's adventure. Chapters are sequentially numbered and can be of type `LESSON` or `STORY`.
*   **Lesson:**  A chapter specifically designed for educational content. Lessons include a question, answers, and an explanation related to the chosen lesson topic. User responses to lessons are tracked for learning progress.
*   **Story:** A chapter focused on narrative progression and user choices. Story chapters present choices that branch the storyline and lead to different outcomes.

These terms (`Chapter`, `Lesson`, `Story`) should be used consistently throughout the codebase and documentation to refer to these core concepts. Avoid using synonyms or alternative terms that could cause confusion.