# NPC Visual Consistency Implementation

**Status:** Not Started

## 1. Problem Statement

The current image generation process, which involves summarizing the *current* chapter and then using that summary to synthesize an image prompt, often lacks visual context for Non-Player Characters (NPCs) introduced in *previous* chapters. This leads to inconsistent visual depictions of recurring NPCs in generated images (e.g., a character described as a dragon in Chapter 1 might be depicted as a dog in Chapter 3 if the Chapter 3 summary only mentions their name without repeating the description). This breaks narrative immersion and visual continuity.

## 2. Root Cause Analysis

The root cause is the lack of persistent memory for NPC visual descriptions across chapters within the image generation pipeline. The image prompt synthesizer primarily relies on the immediate context of the current chapter's summary. If this summary doesn't reiterate an NPC's visual details established earlier, the synthesizer or the downstream image model may hallucinate or generate a default appearance, leading to inconsistencies.

## 3. Proposed Solution

Implement a system to track and update visual descriptions for NPCs encountered during the adventure. This involves:

1.  Storing NPC visual metadata within the `AdventureState`.
2.  Using a **separate, asynchronous LLM call** after each chapter completion to extract or update visual details for NPCs mentioned in that chapter's content.
3.  Injecting this stored NPC visual metadata into the image prompt *synthesizer* step to provide context for consistent image generation.

This approach separates the concern of narrative summarization (for the final recap) from the concern of visual metadata extraction (for image generation), aiming for cleaner prompts and potentially more reliable extraction, while managing the added processing asynchronously.

## 4. Implementation Steps

### 4.1. Update Data Model (`AdventureState`)

*   [ ] **Add `npc_visuals` Field:** Modify `app/models/story.py`. Add a new field `npc_visuals: Dict[str, str]` to the `AdventureState` model.
    ```python
    # Inside AdventureState class definition
    npc_visuals: Dict[str, str] = Field(
        default_factory=dict,
        description="Stores visual descriptions for NPCs encountered, key is NPC name, value is description."
    )
    ```
*   [ ] **Ensure Serialization:** Verify that the new `npc_visuals` field is correctly included when `AdventureState` is serialized (e.g., saved to storage using `state.dict()`) and deserialized (e.g., reconstructed via `AdventureState.parse_obj()` or `reconstruct_state_from_storage`). Pydantic should handle this, but confirmation is needed.

### 4.2. Create NPC Visual Extraction Prompt

*   [ ] **Define Prompt Template:** Create a new, focused prompt template (e.g., in `app/services/llm/prompt_templates.py`) specifically for NPC visual extraction.
    *   **Input:** Full text content of the *last completed* chapter.
    *   **Instruction:** Instruct the LLM to identify all NPCs mentioned (excluding the protagonist) and provide a concise visual description *based only on the provided text*.
    *   **Output Format:** Specify a clear, structured output format, preferably JSON (e.g., `{"Pip": "small green dragon", "Grizelda": "old gnome woman with spectacles"}`). Explicitly state to return an empty dictionary `{}` if no NPCs with descriptions are found.
    *   **Example:**
        ```python
        NPC_VISUAL_EXTRACTION_PROMPT = """
        Analyze the following chapter text. Identify all Non-Player Characters (NPCs) mentioned. For each NPC found, provide a concise visual description based *only* on the details present in this text. Do not include the main protagonist.

        Output the results as a JSON dictionary where keys are NPC names and values are their visual descriptions. If an NPC is mentioned without visual details in this text, do not include them. If no NPCs with descriptions are found, return an empty JSON dictionary `{}`.

        CHAPTER TEXT:
        {chapter_content}

        JSON OUTPUT:
        """
        ```

### 4.3. Implement Asynchronous Extraction Task

*   [ ] **Create Extraction Function:** Create a new asynchronous function (e.g., `async def extract_and_update_npc_visuals(state: AdventureState, chapter_content: str)` maybe within a new `npc_service.py` or `adventure_state_manager.py`).
    *   This function will take the current `AdventureState` and the *completed* chapter's content as input.
    *   It will format the `NPC_VISUAL_EXTRACTION_PROMPT` with the chapter content.
    *   It will call the LLM service (`llm_service.generate_with_prompt` or a direct non-streaming call if preferred for Gemini for this specific task) using the extraction prompt.
    *   It needs robust error handling (log errors, but don't crash the main application).
*   [ ] **Parse LLM Output:** Inside the extraction function, parse the LLM's response. Expect JSON format. Handle potential parsing errors gracefully (e.g., log warning, return empty dict).
*   [ ] **Update State Logic:** Call a method (e.g., `state_manager.update_npc_visuals(state, extracted_visuals)`) to update the `npc_visuals` dictionary in the provided `AdventureState` object.

### 4.4. Trigger Asynchronous Task

*   [ ] **Identify Trigger Point:** Determine the best place to trigger the `extract_and_update_npc_visuals` task. A good candidate is within `app/services/websocket/choice_processor.py`, likely inside `process_non_start_choice` *after* the previous chapter's response has been processed and *before* or *concurrently with* generating the next chapter's content. It should also be triggered after the *first* chapter is generated (maybe in `process_start_choice` after generation).
*   [ ] **Launch Task:** Use `asyncio.create_task()` to launch the `extract_and_update_npc_visuals` function without awaiting its completion, allowing the main flow (sending the next chapter to the user) to proceed immediately.
    ```python
    # Example within process_non_start_choice or similar context
    # ... after processing previous_chapter response ...

    # Get the content of the chapter just completed
    completed_chapter_content = previous_chapter.content

    # Trigger async NPC visual update (don't await)
    asyncio.create_task(
        extract_and_update_npc_visuals(state, completed_chapter_content)
    )
    logger.info(f"Launched async task to update NPC visuals for chapter {previous_chapter.chapter_number}")

    # ... continue generating the *next* chapter ...
    ```

### 4.5. Implement Metadata Update Strategy

*   [ ] **Create Update Method:** Add a method like `update_npc_visuals(self, state: AdventureState, new_visuals: Dict[str, str])` to `AdventureStateManager`.
*   [ ] **Define Update Logic:**
    *   Iterate through the `new_visuals` dictionary received from the LLM extraction.
    *   For each `npc_name`, `description`:
        *   Check if `npc_name` already exists in `state.npc_visuals`.
        *   **Initial Strategy:** If it exists, *overwrite* the existing description with the new one (simplest). If it doesn't exist, add it.
        *   Log the update (e.g., "Updated visuals for NPC 'Pip'" or "Added new NPC visuals for 'Grizelda'").
    *   Ensure thread-safety if necessary, although `AdventureState` modifications within a single WebSocket connection context might be safe enough initially.

### 4.6. Modify Image Prompt Synthesizer

*   [ ] **Access `npc_visuals`:** Modify `ImageGenerationService.synthesize_image_prompt` to accept the full `AdventureState` object or at least the `npc_visuals` dictionary.
*   [ ] **Identify Relevant NPCs:** Analyze the `image_scene_description` (the concise summary generated by the first step of image gen) to identify NPC names mentioned in the scene.
*   [ ] **Retrieve Stored Visuals:** For each identified NPC name, look up their description in `state.npc_visuals`.
*   [ ] **Update Synthesizer Prompt Template:** Modify `IMAGE_SYNTHESIS_PROMPT` in `prompt_templates.py`.
    *   Add a new section/placeholder, e.g., `{npc_visual_context}`.
    *   Add instructions for the LLM on how to *use* this context when describing characters in the final image prompt. Example Instruction: "Use the details provided in the 'NPC VISUAL CONTEXT' section below to accurately depict any NPCs mentioned in the main scene description. Prioritize these provided details over hallucinating an appearance."
*   [ ] **Inject Data:** In `synthesize_image_prompt`, format the retrieved NPC visuals (e.g., as a list like "Pip: small green dragon") and inject it into the `{npc_visual_context}` placeholder of the meta-prompt being sent to the synthesizer LLM.
    ```python
    # Example Injection Logic in synthesize_image_prompt
    npc_context_str = ""
    mentioned_npcs = find_npcs_in_scene(image_scene_description) # Needs implementation
    relevant_visuals = {
        name: desc for name, desc in state.npc_visuals.items() if name in mentioned_npcs
    }
    if relevant_visuals:
        npc_context_str = "NPC VISUAL CONTEXT:\n" + "\n".join(
            f"- {name}: {desc}" for name, desc in relevant_visuals.items()
        )

    # Format the main meta-prompt including npc_context_str
    meta_prompt = IMAGE_SYNTHESIS_PROMPT.format(
        # ... other fields ...
        npc_visual_context=npc_context_str
    )
    ```

### 4.7. Handle Potential Staleness

*   [ ] **Initial Approach:** Acknowledge that the async nature means the `npc_visuals` might be slightly behind. For the initial implementation, the image synthesizer will simply use the *latest available* data in the state when it runs. This is often acceptable.
*   [ ] **Logging:** Add logging within `synthesize_image_prompt` to indicate which NPC visuals (if any) were retrieved from the state and injected into the prompt. This helps diagnose staleness issues later.

## 5. Known Issues & Considerations

*   **LLM Costs:** This adds one LLM call per chapter transition specifically for NPC visual extraction.
*   **Data Staleness:** The asynchronous nature means the `npc_visuals` state used for image generation might lag slightly behind the very latest chapter content. This is usually minor but could be noticeable if users progress extremely rapidly.
*   **Extraction Accuracy:** The reliability depends on the LLM's ability to correctly identify NPCs and extract relevant visual details from the chapter text. Complex narratives or subtle descriptions might pose challenges.
*   **Description Evolution:** The current plan uses an "overwrite" strategy for simplicity. A more advanced implementation might try to merge or refine descriptions over time, but this adds significant complexity.