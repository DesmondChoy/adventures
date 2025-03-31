# Character Visual Consistency & Evolution Implementation

**Status:** Completed

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

*   [x] **Modify `AdventureState`:** In `app/models/story.py`:
    *   Added `character_visuals` field (note: there wasn't a pre-existing `npc_visuals` field to rename)
    *   Set description: "Stores current visual descriptions for characters (protagonist if changed, and NPCs). Key: character name, Value: description."
    ```python
    # Inside AdventureState class definition
    character_visuals: Dict[str, str] = Field(
        default_factory=dict,
        description="Stores current visual descriptions for characters (protagonist if changed, and NPCs). Key: character name, Value: description."
    )
    ```
*   [x] **Update References:** Added new field, no references needed to update.
*   [x] **Ensure Serialization/Deserialization:** Field is properly serializable via built-in dictionary serialization.

### 4.2. Create/Modify Prompts

*   [x] **Define `CHARACTER_VISUAL_UPDATE_PROMPT`:** Added new template in `app/services/llm/prompt_templates.py`:
    ```python
    CHARACTER_VISUAL_UPDATE_PROMPT = """
    ROLE: Visual Character Tracker for a Children's Adventure Story

    TASK:
    Track and update the visual descriptions of all characters in the story. Parse the chapter content to:
    1. Identify all characters (protagonist and NPCs)
    2. Extract or update their visual descriptions
    3. Return an updated JSON dictionary with character names as keys and their current visual descriptions as values

    INPUTS:
    1. Chapter Content: The latest chapter content, which may introduce new characters or update existing ones
    2. Existing Visuals: A dictionary of character names and their current visual descriptions

    CHAPTER CONTENT:
    {chapter_content}

    EXISTING VISUALS:
    {existing_visuals}

    INSTRUCTIONS:
    - For each character mentioned in the chapter, including the protagonist and NPCs:
      * If the character is new (not in EXISTING VISUALS), create a detailed visual description based on any appearance details in the chapter
      * If the character already exists but has visual changes described in this chapter, update their description accordingly
      * If no visual changes are described for an existing character, keep their previous description
    - Visual descriptions should be concise (25-40 words) but comprehensive
    - Focus only on visual/physical aspects (appearance, clothing, features, etc.) that would be relevant for image generation
    - For the protagonist, prioritize keeping their core appearance consistent while incorporating any described changes/evolution
    - Ensure each description is self-contained (someone reading only the description should get a complete picture)

    OUTPUT FORMAT:
    Return ONLY a valid JSON object with the updated character visuals, formatted exactly like this:
    ```json
    {
      "Character Name": "Visual description that includes appearance, clothing, and distinctive features",
      "Another Character": "Their visual description...",
      ...
    }
    ```

    Do not include any explanations, only return the JSON.
    """
    ```
*   [x] **Modify `IMAGE_SCENE_PROMPT`:** Updated in `app/services/llm/prompt_templates.py`:
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
*   [x] **Modify `IMAGE_SYNTHESIS_PROMPT`:** Updated in `app/services/llm/prompt_templates.py`:
    *   Added placeholder: `CHARACTER_VISUAL_CONTEXT:\n{character_visual_context}`.
    *   Updated **TASK** instructions to include: "For other characters mentioned in CHARACTER_VISUAL_CONTEXT, incorporate their visual descriptions if they appear in the scene description. Prioritize the recent visual descriptions of characters over the base protagonist description if any character has evolved visually."

### 4.3. Implement Post-Chapter Processing Steps

*   [x] **Step 1a (Summary):** Verified the existing `generate_chapter_summary` call (using `SUMMARY_CHAPTER_PROMPT`) correctly stores its output in `state.chapter_summaries` and `state.summary_chapter_titles`. This already runs within the choice processing logic.
*   [x] **Step 1b (Visual Update):**
    *   Created `_update_character_visuals(state: AdventureState, chapter_content: str, state_manager: AdventureStateManager)` async function in `choice_processor.py`.
    *   Implemented logic using `CHARACTER_VISUAL_UPDATE_PROMPT` and `LLMService` with streaming.
    *   Added JSON extraction with regex to handle both formatted (```json) and unformatted JSON responses.
    *   Implemented error handling for JSON parsing, LLM errors, and general exceptions.
    *   Added call to `state_manager.update_character_visuals(state, updated_visuals_dict)` on success.
*   [x] **Step 1c (Image Scene):**
    *   Updated the existing `IMAGE_SCENE_PROMPT` to specify ~50-word description.
    *   Verified that `chapter_manager.generate_image_scene` function correctly uses this template.
    *   Confirmed it's called appropriately within the image generation pipeline.

### 4.4. Trigger Asynchronous Tasks

*   [x] **Modify Trigger Logic:** Updated `app/services/websocket/choice_processor.py` in the `process_non_start_choice` function:
    *   After processing the user's choice and generating the chapter summary:
        *   Added: `asyncio.create_task(_update_character_visuals(state, previous_chapter.content, state_manager))` to launch the asynchronous character visual update.
    *   Ensured this runs after the summaries are generated but before the next chapter is created.
    *   Verified the existing image generation pipeline already follows the correct sequence:
        *   First generates the image scene description with `chapter_manager.generate_image_scene`
        *   Then passes this to `synthesize_image_prompt` to create the final prompt
        *   Finally generates the image using this synthesized prompt

### 4.5. Implement State Update Method (Reuse `AdventureStateManager`)

*   [x] **Create `update_character_visuals` Method:** Added `update_character_visuals(self, state: AdventureState, updated_visuals: Dict[str, str])` to `app/services/adventure_state_manager.py`.
*   [x] **Implement Update Logic:**
    *   Added validation for empty or missing visuals dictionary.
    *   Added attribute existence check for backward compatibility.
    *   Implemented intelligent merging that only updates changed or new character descriptions.
    *   Added detailed logging for updates and validation.

### 4.6. Modify Image Prompt Synthesizer (Reuse & Refine Existing)

*   [x] **Modify `synthesize_image_prompt` Signature:** Updated `app/services/image_generation_service.py` -> `synthesize_image_prompt` to accept `character_visuals: Dict[str, str] = None` parameter.
*   [x] **Identify Characters & Retrieve Visuals:** Added logic to format character visuals into a readable context list:
    ```python
    # Format character visuals context
    character_visual_context = ""
    if character_visuals and len(character_visuals) > 0:
        # Format as a list for easier reading
        character_visual_context = "Character Visual Descriptions:\n"
        for name, description in character_visuals.items():
            character_visual_context += f"- {name}: {description}\n"
        logger.info(f"Including {len(character_visuals)} character visual descriptions in the prompt")
    else:
        character_visual_context = "No additional character visuals available"
        logger.debug("No character visuals to include in the prompt")
    ```
*   [x] **Inject Data:** Added the formatted character context to the template when formatting:
    ```python
    meta_prompt = IMAGE_SYNTHESIS_PROMPT.format(
        image_scene_description=image_scene_description,
        protagonist_description=protagonist_description,
        agency_category=agency_details.get("category", "N/A"),
        agency_name=agency_details.get("name", "N/A"),
        agency_visual_details=agency_details.get("visual_details", "N/A"),
        story_visual_sensory_detail=story_visual_sensory_detail,
        character_visual_context=character_visual_context,
    )
    ```

### 4.7. Handle Potential Staleness

*   [x] **Accept Initial Staleness:** Implemented the system to use the latest available `character_visuals` when synthesizing the image prompt. Since the visual update runs asynchronously, there may be cases where an image is generated before the latest character visuals are available, but this is an acceptable tradeoff for performance.
*   [x] **Add Logging:** Added detailed logging throughout the process:
    * In `synthesize_image_prompt`: `logger.info(f"Including {len(character_visuals)} character visual descriptions in the prompt")`
    * In `update_character_visuals`: `logger.info(f"Updated {updates_count} character visual descriptions")`
    * In `_update_character_visuals`: `logger.info(f"Successfully updated character visuals with {len(updated_visuals)} entries")`
    * Also log any errors or empty visuals for debugging

## 5. Code Reuse Summary

*   **Successfully Reused/Modified:** 
    * `AdventureState`: Extended with `character_visuals`
    * `AdventureStateManager`: Added `update_character_visuals` method
    * `LLMService`: Used for character visual extraction
    * `IMAGE_SCENE_PROMPT`: Updated for ~50 word descriptions
    * `IMAGE_SYNTHESIS_PROMPT`: Enhanced with character context
    * `synthesize_image_prompt` function: Modified to accept and use character visuals
    * Async task triggering logic: Enhanced to run character visual updates
    * `image_generator.py`: Updated to pass character visuals to prompt synthesis
    * `choice_processor.py`: Extended with character visual update functionality
    
*   **Successfully Created:** 
    * `character_visuals` field in AdventureState model
    * `CHARACTER_VISUAL_UPDATE_PROMPT` template for LLM extraction
    * `_update_character_visuals` async function for background processing
    * `update_character_visuals` method for state management

## 6. Known Issues & Considerations

All implemented features account for these potential issues:

*   **LLM Costs**: The implementation uses an additional LLM call per chapter for character visual extraction, but this is a necessary tradeoff for visual consistency.
*   **Data Staleness**: Since character visual updates run asynchronously, there may be occasional 1-chapter lag in visual updates, but this is an acceptable tradeoff for performance.
*   **Extraction Accuracy**: The CHARACTER_VISUAL_UPDATE_PROMPT is designed to extract visual details as accurately as possible, but LLM limitations may still cause occasional inconsistencies.
*   **Description Evolution/Merging**: The system intelligently merges character descriptions, only updating when there are actual changes rather than replacing everything.
*   **Increased LLM Calls**: The implementation adds one additional LLM call per chapter (for character visual extraction), but this runs asynchronously to minimize impact on user experience.
*   **Potential Bottlenecks**: During testing, the asynchronous approach showed no significant bottlenecks, as the visual update process runs in parallel with other operations.

## 7. Implementation Complete

The character visual consistency and evolution system has been fully implemented according to the proposed solution. All components work together to ensure that characters maintain visual consistency throughout the adventure while still allowing for natural evolution based on the narrative.

The implementation was completed on March 31, 2025 and committed to the `protagonist_inconsistencies` branch (commit efa8319).