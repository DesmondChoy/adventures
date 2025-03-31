# Character Visual Consistency & Evolution Implementation

**Status:** Not Started

**Related Document:** `protagonist_inconsistencies.md` (Established initial protagonist/agency visual consistency via prompt synthesis). This plan extends that work to include NPCs and track visual *evolution* for all characters.

## 1. Problem Statement

While protagonist visual consistency was addressed by incorporating base descriptions and agency details into the image prompt synthesis step (see `protagonist_inconsistencies.md`), recurring Non-Player Characters (NPCs) introduced in earlier chapters still lack visual persistence. The current two-step image generation process (summarize chapter -> synthesize prompt -> generate image) doesn't carry forward NPC visual descriptions, leading to inconsistent depictions.

## 2. Root Cause Analysis

The image generation pipeline lacks a mechanism to track and *update* visual descriptions for *all* characters (protagonist + NPCs) based on narrative developments across chapters. The prompt synthesizer relies on immediate context, which doesn't reflect character evolution.

## 3. Proposed Solution

Implement a multi-step, asynchronous post-chapter processing flow to maintain visual consistency:

1.  **Post-Chapter Processing (Triggered after Chapter N narrative generation & user choice processing):**
    *   **Step 1a (Summary for Recap):** Use the existing `SUMMARY_CHAPTER_PROMPT` LLM call to generate the narrative chapter summary (title + text) needed *only* for the final adventure recap page. Store this in `state.chapter_summaries`.
    *   **Step 1b (Visual Update - Async):** Trigger a *separate, asynchronous* LLM call using `CHARACTER_VISUAL_UPDATE_PROMPT`. Input is Chapter N's content and current `state.character_visuals`. Output is an *updated* JSON dictionary of character visuals. This task updates `state.character_visuals` in the background.
    *   **Step 1c (Image Scene Description):** Trigger a *separate* LLM call using `IMAGE_SCENE_PROMPT`. Input is Chapter N's content. Output is a concise (~50 words) description focusing *only* on the most visually striking moment/action/emotion of Chapter N. This description serves as the core input for the next step.
2.  **Step 2 (Synthesize Image Prompt - Async):** Triggered after Step 1c completes.
    *   **Input:** `Image Scene Description` (from 1c), `state.protagonist_description`, `state.metadata['agency']['visual_details']`, `state.selected_sensory_details['visuals']`, and the *latest available* `state.character_visuals` (updated by 1b).
    *   **Prompt:** Use the existing `IMAGE_SYNTHESIS_PROMPT` (modified to accept unified character context).
    *   **Output:** A detailed `Synthesized Image Prompt`.
3.  **Step 3 (Generate Image - Async):** Triggered after Step 2 completes.
    *   **Input:** `Synthesized Image Prompt`.
    *   **Output:** Image data.
    *   **Action:** Send image to frontend.

This maintains separation of concerns, allows character visual evolution, reuses infrastructure, and uses focused prompts for each step.

## 4. Implementation Steps

### 4.1. Update Data Model (`AdventureState`)

*   [ ] **Modify `AdventureState`:** In `app/models/story.py`:
    *   Rename `npc_visuals` to `character_visuals`.
    *   Update its description: "Stores current visual descriptions for characters (protagonist if changed, and NPCs). Key: character name, Value: description."
    ```python
    # Inside AdventureState class definition
    character_visuals: Dict[str, str] = Field(
        default_factory=dict,
        description="Stores current visual descriptions for characters (protagonist if changed, and NPCs). Key: character name, Value: description."
    )
    ```
*   [ ] **Update References:** Refactor codebase from `npc_visuals` to `character_visuals`.
*   [ ] **Ensure Serialization/Deserialization:** Verify `character_visuals` handling.

### 4.2. Create/Modify Prompts

*   [ ] **Define `CHARACTER_VISUAL_UPDATE_PROMPT`:** Add new template in `app/services/llm/prompt_templates.py` (as defined in previous response - takes `chapter_content`, `existing_visuals`; outputs updated JSON).
*   [ ] **Modify `IMAGE_SCENE_PROMPT`:** In `app/services/llm/prompt_templates.py`:
    *   Update the description length guidance: "Describe ONLY this scene in **~50 words** using vivid, specific language..."
    ```python
    IMAGE_SCENE_PROMPT = """Identify the single most visually striking moment from this chapter that would make a compelling illustration.

    Focus on:
    1. A specific dramatic action or emotional peak
    2. Clear visual elements (character poses, expressions, environmental details)
    3. The moment with the most visual energy or emotional impact
    4. Elements that best represent the chapter's theme or turning point

    Describe ONLY this scene in **approximately 50 words** using vivid, specific language. Focus purely on the visual elements and action, not narrative explanation. Do not include character names or story title unless essential for the scene.

    CHAPTER CONTENT:
    {chapter_content}

    SCENE DESCRIPTION:
    """
    ```
*   [ ] **Modify `IMAGE_SYNTHESIS_PROMPT`:** In `app/services/llm/prompt_templates.py`:
    *   Add placeholder: `CHARACTER_VISUAL_CONTEXT:\n{character_visual_context}`.
    *   Update **TASK** instructions to prioritize `CHARACTER_VISUAL_CONTEXT` for *all* character descriptions (including protagonist overrides) while still using `Protagonist Base Look` as a fallback/starting point. Ensure Agency details are still incorporated.

### 4.3. Implement Post-Chapter Processing Steps

*   [ ] **Step 1a (Summary):** Ensure the existing `generate_chapter_summary` call (using `SUMMARY_CHAPTER_PROMPT`) correctly stores its output (title+summary) in `state.chapter_summaries` and `state.summary_chapter_titles`. This likely runs within the choice processing logic already.
*   [ ] **Step 1b (Visual Update):**
    *   Create `_update_character_visuals(state: AdventureState, chapter_content: str)` async function (e.g., in `choice_processor.py`).
    *   Implement logic using `CHARACTER_VISUAL_UPDATE_PROMPT` and `LLMService` (non-streaming preferred).
    *   Implement JSON parsing and error handling.
    *   Call `state_manager.update_character_visuals(state, updated_visuals_dict)` on success.
*   [ ] **Step 1c (Image Scene):**
    *   Ensure the existing `chapter_manager.generate_image_scene` function (or wherever `IMAGE_SCENE_PROMPT` is used) correctly generates the ~50-word visual description based on the *completed* chapter content. This likely runs as part of the image generation trigger logic.

### 4.4. Trigger Asynchronous Tasks

*   [ ] **Modify Trigger Logic:** In `app/services/websocket/choice_processor.py` (or related helpers like `process_non_start_choice`):
    *   After processing the user's choice for Chapter N and finalizing the content for Chapter N (`completed_chapter_content = previous_chapter.content`):
        *   Trigger the existing `generate_chapter_summary` task (Step 1a - if not already happening correctly).
        *   Trigger the *new* visual update task: `asyncio.create_task(_update_character_visuals(state, completed_chapter_content))` (Step 1b).
    *   The logic that triggers image generation (likely in `image_generator.py` or `stream_handler.py`) should *first* execute Step 1c (`generate_image_scene`) and *then* proceed to Step 2 (synthesize prompt) and Step 3 (generate image), using the output from 1c.

### 4.5. Implement State Update Method (Reuse `AdventureStateManager`)

*   [ ] **Create `update_character_visuals` Method:** Add `update_character_visuals(self, state: AdventureState, updated_visuals: Dict[str, str])` to `app/services/adventure_state_manager.py`.
*   [ ] **Implement Update Logic:** Replace `state.character_visuals` with `updated_visuals` dictionary from the LLM. Add validation and logging.

### 4.6. Modify Image Prompt Synthesizer (Reuse & Refine Existing)

*   [ ] **Modify `synthesize_image_prompt` Signature:** Ensure `app/services/image_generation_service.py` -> `synthesize_image_prompt` receives `character_visuals: Dict[str, str]`. Update callers in `image_generator.py`.
*   [ ] **Identify Characters & Retrieve Visuals:** Inside `synthesize_image_prompt`, identify characters in the `image_scene_description` and retrieve their latest descriptions from the passed `character_visuals`.
*   [ ] **Inject Data:** Format retrieved character visuals and inject into the `{character_visual_context}` placeholder of the modified `IMAGE_SYNTHESIS_PROMPT`.

### 4.7. Handle Potential Staleness

*   [ ] **Accept Initial Staleness:** The synthesizer uses the latest `character_visuals` available when it runs.
*   [ ] **Add Logging:** Log timestamps and which character details were used during synthesis.

## 5. Code Reuse Summary

*   **Reused/Modified:** `AdventureState`, `AdventureStateManager`, `LLMService`, `SUMMARY_CHAPTER_PROMPT`, `IMAGE_SCENE_PROMPT` (length change), `IMAGE_SYNTHESIS_PROMPT` (context addition), `synthesize_image_prompt` function, async task triggering logic, `image_generator.py`, `choice_processor.py`.
*   **Newly Created:** `character_visuals` field (replaces `npc_visuals`), `CHARACTER_VISUAL_UPDATE_PROMPT` template, `_update_character_visuals` async function, `update_character_visuals` method.

## 6. Known Issues & Considerations

*   (Same as previous: LLM Costs, Data Staleness, Extraction Accuracy, Description Evolution/Merging).
*   Increased number of LLM calls per chapter (1 for narrative, 1 for summary, 1 for visual update, 1 for image scene, 1 for synthesis = potentially 5 calls, although some are async).
*   Potential bottleneck if the async visual update (1b) consistently takes longer than the steps leading up to image synthesis (1c + 2).