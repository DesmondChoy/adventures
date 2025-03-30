# Implementation Plan: Two-Step Image Prompt Generation with Refinements

## Implementation Status

**Status: NOT STARTED ❌**

## 1. Problem Statement

The current image generation process struggles to maintain visual stability for the protagonist across different chapters. Combining base protagonist look, agency details, and chapter scene description consistently via simple templating is challenging, leading to potential visual conflicts or ignored elements.

## 2. Root Cause Analysis

*   The `ImageGenerationService.enhance_prompt` function uses template concatenation, lacking semantic understanding to logically merge potentially conflicting visual descriptions (e.g., base clothing vs. agency armor).
*   Directly feeding complex, structured prompts to Imagen relies heavily on its interpretation, leading to inconsistency.

## 3. Proposed Solution: Two-Step Prompt Generation

Implement a two-step process where an intermediary LLM call synthesizes the final, optimized prompt for the image generation model (Imagen):

1.  **Gather Inputs:** Collect necessary visual components (protagonist base look, agency details, chapter scene description, story visual sensory detail).
2.  **LLM Prompt Synthesis:** Use a dedicated function (`synthesize_image_prompt`) with a specific meta-prompt to instruct an LLM (LLM-Synthesizer, specifically Gemini Flash) to logically combine these inputs into a coherent Imagen prompt.
3.  **Image Generation:** Feed the synthesized prompt to `ImageGenerationService.generate_image_async()`.

## 4. Implementation Plan

**Prerequisites & Setup:**

*   [ ] **Step 1: Define Predefined Protagonist Descriptions:**
    *   **File:** `app/services/llm/prompt_templates.py` (Place it near the `categories` dictionary).
    *   **Action:** Define the `PREDEFINED_PROTAGONIST_DESCRIPTIONS` list.
    *   **Code:**
        ```python
        # Example added to app/services/llm/prompt_templates.py
        PREDEFINED_PROTAGONIST_DESCRIPTIONS = [
            "A curious young boy with short brown hair, bright green eyes, wearing simple traveler's clothes (tunic and trousers).",
            "An adventurous girl with braided blonde hair, freckles, wearing practical leather gear and carrying a small satchel.",
            "A thoughtful child with glasses, dark curly hair, wearing a slightly oversized, patched cloak over plain clothes.",
            "A nimble young person with vibrant red hair tied back, keen blue eyes, dressed in flexible, forest-green attire.",
            "A gentle-looking kid with warm brown eyes, black hair, wearing a comfortable-looking blue tunic and sturdy boots."
        ]
        ```

*   [ ] **Step 2: Add Protagonist Field and Implement Selection in Initialization:**
    *   **File:** `app/models/story.py`
    *   **Action:** Add a new field `protagonist_description` to the `AdventureState` model.
    *   **Code (in `AdventureState`):**
        ```python
        protagonist_description: str = Field(default="", description="Base visual description of the protagonist")
        ```
    *   **File:** `app/services/chapter_manager.py`
    *   **Function:** `initialize_adventure_state`
    *   **Action:**
        *   Import `PREDEFINED_PROTAGONIST_DESCRIPTIONS` from `app.services.llm.prompt_templates`.
        *   Import `random`.
        *   Inside the function, *before* creating the `AdventureState` object:
            *   Randomly select one description: `selected_protagonist_desc = random.choice(PREDEFINED_PROTAGONIST_DESCRIPTIONS)`
        *   When creating the `AdventureState` object, pass the selected description: `protagonist_description=selected_protagonist_desc`.
    *   **Logging:** Add a log entry indicating which protagonist description was selected.

**Core Implementation Steps:**

*   [ ] **Step 3: Create Prompt Synthesis Function:**
    *   **File:** `app/services/image_generation_service.py` (or a new `prompt_synthesis_service.py`).
    *   **Function:** Define `async def synthesize_image_prompt(image_scene_description: str, protagonist_description: str, agency_details: dict, story_visual_sensory_detail: str) -> str:`
    *   **Meta-Prompt Design:** Craft the prompt for the LLM-Synthesizer. Key instructions:
        ```prompt
        # ROLE: Expert Prompt Engineer for Text-to-Image Models

        # CONTEXT:
        # You are creating an image prompt for one chapter of an ongoing children's educational adventure story (ages 6-12).
        # The image should be a snapshot of a key moment from this specific chapter.
        # The story features a main protagonist whose base look is described below.
        # The protagonist also has a special "agency" element (an item, companion, role, or ability) chosen at the start, with its own visual details.

        # INPUTS:
        # 1. Scene Description: A concise summary of the key visual moment in *this specific chapter*. **This scene takes priority.**
        #    "{image_scene_description}"
        # 2. Protagonist Base Look: The core appearance of the main character throughout the adventure.
        #    "{protagonist_description}"
        # 3. Protagonist Agency Element: The special element associated with the protagonist.
        #    - Category: "{agency_details.get('category', 'N/A')}"
        #    - Name: "{agency_details.get('name', 'N/A')}"
        #    - Visuals: "{agency_details.get('visual_details', 'N/A')}"
        # 4. Story Sensory Visual: An overall visual mood element for this story's world. **Apply this only if it fits logically with the Scene Description.**
        #    "{story_visual_sensory_detail}"

        # TASK:
        # Combine these inputs into a single, coherent, vivid visual scene description (target 30-50 words) suitable for Imagen.
        # Logically merge the Protagonist Base Look with the Agency Element Visuals. For example:
        #   - If Agency is "Guardian [gleaming silver armor]", describe the protagonist *wearing* the armor over their base clothes.
        #   - If Agency is "Wise Owl [snowy feathers...]", describe the protagonist *accompanied by* the owl within the scene.
        #   - If Agency is "Luminous Lantern [golden...]", describe the protagonist *holding* or *using* the lantern in the scene.
        #   - If Agency is "Element Bender [sparking flames...]", describe the protagonist *manifesting* these elements as part of the scene's action.
        # Integrate the combined character description naturally into the Scene Description.
        # The prompt MUST focus on what's happening *in the scene* while clearly including the protagonist and their agency element.
        # Prioritize the Scene Description: If the Story Sensory Visual detail contradicts the Scene Description (e.g., sensory detail mentions 'sparkling leaves at dawn' but the scene is 'inside a dark cave'), OMIT the sensory detail or adapt it subtly (e.g., 'glowing crystals line the cave walls' instead of 'sparkling leaves').

        # --- Examples of Prioritization ---
        # GOOD (Sensory fits Scene): Scene="Walking through a moonlit forest", Sensory="Glowing Juggling Pins", Output="...girl walks through a moonlit forest, juggling pins glow softly..."
        # GOOD (Sensory omitted): Scene="Inside a cozy tent", Sensory="Aurora Dewdrops on leaves", Output="...boy sits inside a cozy tent, reading a map..." (Dewdrops omitted as they don't fit).
        # BAD (Sensory forced): Scene="Inside a cozy tent", Sensory="Aurora Dewdrops on leaves", Output="...boy sits inside a cozy tent, strangely, there are dewdrops on leaves inside the tent..."
        # ---

        # The final output should be ONLY the synthesized prompt string itself, ready for an image model like Imagen.
        # Adopt a "colorful storybook illustration" style.

        # OUTPUT (Synthesized Prompt String Only):
        ```
    *   **LLM Call:** Use `LLMService` (which defaults to `GeminiService`). Ensure the call within *this* function specifically uses the `gemini-2.0-flash` model (see Step 7). Use a reliable method (e.g., direct non-streaming call for Gemini).
    *   **Error Handling:** Implement try/except blocks. Log detailed error messages, including LLM provider-specific errors if available, ensuring visibility in logs (and terminal during debugging). If synthesis fails, generate a fallback prompt (e.g., `f"Colorful storybook illustration of this scene: {image_scene_description}. Protagonist: {protagonist_description}. Agency: {agency_details.get('visual_details', '')}. Atmosphere: {story_visual_sensory_detail}."`).
    *   **Logging:** Log all inputs, the final synthesized prompt, and any errors encountered during synthesis.

*   [ ] **Step 4: Modify Image Generation Trigger Logic:**
    *   **File:** `app/services/websocket/image_generator.py`
    *   **Function:** Update `generate_chapter_image`.
    *   **Changes:**
        *   After getting `current_content`, call `image_scene = await chapter_manager.generate_image_scene(current_content)`.
        *   Retrieve `protagonist_description = getattr(state, 'protagonist_description', 'A young adventurer')`.
        *   Retrieve `agency_details = state.metadata.get('agency', {})`.
        *   Retrieve `story_visual_sensory_detail = state.selected_sensory_details.get('visuals', '')`.
        *   Call the new synthesis function: `synthesized_prompt = await synthesize_image_prompt(image_scene, protagonist_description, agency_details, story_visual_sensory_detail)`.
        *   Call the image generation service with the result: `task = asyncio.create_task(image_service.generate_image_async(synthesized_prompt))`.
        *   Update the task list: `image_tasks.append(("chapter", task))`.

*   [ ] **Step 5: Update `generate_agency_images` (Chapter 1 - Direct Prompt for Agency Only):**
    *   **File:** `app/services/websocket/image_generator.py`
    *   **Function:** `generate_agency_images`.
    *   **Action:** Modify the prompt generation to focus *only* on the agency item/companion/ability/profession itself, using its visual description, plus the atmospheric sensory detail.
        *   For each choice `i`:
            *   Find the `original_option` string (e.g., "Wise Owl [a grand owl with snowy feathers...]") using `find_matching_agency_option`.
            *   Extract the visual details from within the brackets: `visual_match = re.search(r"\[(.*?)\]", original_option)` -> `visual_details = visual_match.group(1)` if match, else ""
            *   Extract the agency name (text before bracket): `agency_name = original_option.split("[")[0].strip()`
            *   Retrieve the `story_visual_sensory_detail = state.selected_sensory_details.get('visuals', '')`.
            *   Construct the focused prompt: `prompt = f"Colorful storybook illustration focusing ONLY on: {agency_name} [{visual_details}]. Subtle atmosphere hints from: {story_visual_sensory_detail}."`
            *   Create the task: `task = asyncio.create_task(image_service.generate_image_async(prompt))`
            *   Append: `image_tasks.append((i, task))`

*   [ ] **Step 6: Remove/Refactor Redundant Code:**
    *   **File:** `app/services/image_generation_service.py`
    *   **Function:** `enhance_prompt`.
    *   **Action:** Remove this function.

*   [ ] **Step 7: Configuration & Model Verification:**
    *   **File:** `app/services/image_generation_service.py` (or wherever `synthesize_image_prompt` lives).
    *   **Action:** Verify the LLM call within `synthesize_image_prompt` specifically uses the `"gemini-2.0-flash"` model. Check that the `LLMService` instance used is the intended `GeminiService`.

*   [ ] **Step 8: Logging and Monitoring:**
    *   Add detailed logs within `synthesize_image_prompt` for inputs, outputs, and errors.
    *   Monitor image generation latency after implementation.

*   [ ] **Step 9: Update Chapter 1 Prompt Generation:**
    *   **File:** `app/services/llm/prompt_templates.py`
    *   **Action:** Modify the `FIRST_CHAPTER_PROMPT` template to accept and incorporate the `protagonist_description`. Add a placeholder like `{protagonist_description}` within the "Chapter Development Guidelines" or similar section.
    *   **File:** `app/services/llm/prompt_engineering.py`
    *   **Function:** Modify `build_first_chapter_prompt`.
    *   **Action:** Retrieve `protagonist_description=state.protagonist_description` and pass it as a variable when formatting the `FIRST_CHAPTER_PROMPT` template.

## 5. Potential Challenges & Risks

*   **Latency:** Adding an LLM call increases image generation time. Mitigation: Use Gemini Flash, optimize meta-prompt.
*   **Cost:** Increased LLM calls raise operational costs.
*   **Synthesizer Reliability:** Quality depends on the LLM-Synthesizer interpreting the meta-prompt correctly. Mitigation: Robust error handling and fallback in Step 3.
*   **Meta-Prompt Engineering:** Requires careful design and iteration.