# Implementation Plan: Two-Step Image Prompt Generation with Refinements

## Implementation Status

**Status: IN PROGRESS ⏳**

**Completed Steps:**
- ✅ Step 1: Define Predefined Protagonist Descriptions (2025-03-30)
- ✅ Step 2: Add Protagonist Field and Implement Selection in Initialization (2025-03-30)
- ✅ Step 3: Create Prompt Synthesis Function (2025-03-30)
- ✅ Step 4: Modify Image Generation Trigger Logic (2025-03-30)
- ✅ Step 5: Update `generate_agency_images` for Agency-Only Focus (2025-03-30)
- ✅ Step 6: Remove/Refactor Redundant Code (2025-03-30)
- ✅ Step 7: Configuration & Model Verification (2025-03-30)
- ✅ Step 8: Logging and Monitoring (2025-03-30)

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

*   [x] **Step 1: Define Predefined Protagonist Descriptions:**
    *   **File:** `app/services/llm/prompt_templates.py` (Place it near the `categories` dictionary).
    *   **Action:** Define the `PREDEFINED_PROTAGONIST_DESCRIPTIONS` list.
    *   **Implementation Details:**
        * Added a list of 5 diverse protagonist descriptions to serve as the foundation for consistent image generation
        * Placed the list near the `categories` dictionary as specified
        * Implemented on 2025-03-30
    *   **Code:**
        ```python
        # Added to app/services/llm/prompt_templates.py
        PREDEFINED_PROTAGONIST_DESCRIPTIONS = [
            "A curious young boy with short brown hair, bright green eyes, wearing simple traveler's clothes (tunic and trousers).",
            "An adventurous girl with braided blonde hair, freckles, wearing practical leather gear and carrying a small satchel.",
            "A thoughtful child with glasses, dark curly hair, wearing a slightly oversized, patched cloak over plain clothes.",
            "A nimble young person with vibrant red hair tied back, keen blue eyes, dressed in flexible, forest-green attire.",
            "A gentle-looking kid with warm brown eyes, black hair, wearing a comfortable-looking blue tunic and sturdy boots.",
        ]
        ```

*   [x] **Step 2: Add Protagonist Field and Implement Selection in Initialization:**
    *   **File:** `app/models/story.py`
    *   **Action:** Add a new field `protagonist_description` to the `AdventureState` model.
    *   **Implementation Details:**
        * Added a new field to the `AdventureState` class with appropriate default and description
        * Modified `initialize_adventure_state` function to randomly select a protagonist description
        * Added logging to track which protagonist description was selected
        * Passed the selected description to the `AdventureState` constructor
        * Implemented on 2025-03-30
    *   **Code (in `AdventureState`):**
        ```python
        protagonist_description: str = Field(default="", description="Base visual description of the protagonist")
        ```
    *   **Code (in `initialize_adventure_state`):**
        ```python
        # Randomly select a protagonist description
        selected_protagonist_desc = random.choice(PREDEFINED_PROTAGONIST_DESCRIPTIONS)
        
        logger.info(
            "Selected protagonist description",
            extra={"protagonist_description": selected_protagonist_desc},
        )
        
        # Create adventure state with validated elements
        state = AdventureState(
            # ... other fields ...
            protagonist_description=selected_protagonist_desc,
        )
        ```

**Core Implementation Steps:**

*   [x] **Step 3: Create Prompt Synthesis Function:**
    *   **File:** `app/services/image_generation_service.py`
    *   **Function:** Define `async def synthesize_image_prompt(image_scene_description: str, protagonist_description: str, agency_details: dict, story_visual_sensory_detail: str) -> str:`
    *   **Implementation Details:**
        * Created a new function in the `ImageGenerationService` class that uses Gemini Flash to intelligently combine inputs
        * Implemented a detailed meta-prompt that instructs the LLM how to merge the protagonist description with agency details
        * Added prioritization rules to ensure scene description takes precedence
        * Implemented both direct Gemini API call and fallback to streaming approach
        * Added comprehensive error handling with fallback prompt generation
        * Added detailed logging of inputs, outputs, and any errors
        * Implemented on 2025-03-30
    *   **Meta-Prompt Design:** Crafted a detailed prompt for the LLM-Synthesizer with clear instructions:
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
        # Logically merge the Protagonist Base Look with the Agency Element Visuals...
        ```
    *   **Error Handling:** Implemented comprehensive try/except blocks with fallback prompt generation:
        ```python
        try:
            # LLM call implementation
        except Exception as e:
            logger.error(f"Error synthesizing image prompt: {str(e)}")
            # Return a fallback prompt
            fallback_prompt = f"Colorful storybook illustration of this scene: {image_scene_description}. Protagonist: {protagonist_description}. Agency: {agency_details.get('visual_details', '')}. Atmosphere: {story_visual_sensory_detail}."
            logger.info(f"Using fallback prompt due to error: {fallback_prompt}")
            return fallback_prompt
        ```

*   [x] **Step 4: Modify Image Generation Trigger Logic:**
    *   **File:** `app/services/websocket/image_generator.py`
    *   **Function:** Update `generate_chapter_image`.
    *   **Implementation Details:**
        * Updated the function to use the new two-step prompt generation process
        * Added code to retrieve protagonist description from the state
        * Added code to retrieve agency details from state metadata
        * Added code to retrieve story visual sensory detail from state
        * Replaced the call to `enhance_prompt` with a call to `synthesize_image_prompt`
        * Added special handling for the first chapter (Chapter 1)
        * Added fallback handling for error cases
        * Added detailed logging throughout the function
        * Implemented on 2025-03-30
    *   **Code:**
        ```python
        # Get protagonist description
        protagonist_description = getattr(state, "protagonist_description", "A young adventurer")
        
        # Get agency details
        agency_details = state.metadata.get("agency", {})
        
        # Get story visual sensory detail
        story_visual_sensory_detail = state.selected_sensory_details.get("visuals", "")
        
        # Synthesize the prompt using the LLM
        prompt = await image_service.synthesize_image_prompt(
            image_scene,
            protagonist_description,
            agency_details,
            story_visual_sensory_detail
        )
        ```

*   [x] **Step 5: Update `generate_agency_images` (Chapter 1 - Direct Prompt for Agency Only):**
    *   **File:** `app/services/websocket/image_generator.py`
    *   **Function:** `generate_agency_images`.
    *   **Action:** Modify the prompt generation to focus *only* on the agency item/companion/ability/profession itself, using its visual description, plus the atmospheric sensory detail.
    *   **Implementation Details:**
        * Updated the function docstring to clarify the new focus on agency elements only
        * Added code to retrieve the story visual sensory detail from state
        * Modified the prompt generation to focus only on the agency element
        * Extracted visual details from within brackets using regex
        * Extracted the agency name (text before bracket)
        * Constructed a focused prompt that emphasizes only the agency element
        * Added better error handling and fallback for cases where no visual details are found
        * Enhanced logging to track prompt generation
        * Implemented on 2025-03-30
    *   **Code:**
        ```python
        # Retrieve the story visual sensory detail
        story_visual_sensory_detail = state.selected_sensory_details.get("visuals", "")
        
        # Extract visual details from the original option (text in square brackets)
        visual_match = re.search(r"\[(.*?)\]", original_option)
        visual_details = ""
        if visual_match:
            visual_details = visual_match.group(1)
            
        # Extract the agency name (text before bracket)
        agency_name = original_option.split("[")[0].strip()
        
        # Construct the focused prompt
        prompt = f"Colorful storybook illustration focusing ONLY on: {agency_name} [{visual_details}]. Subtle atmosphere hints from: {story_visual_sensory_detail}."
        ```

*   [x] **Step 6: Remove/Refactor Redundant Code:**
    *   **File:** `app/services/image_generation_service.py`
    *   **Function:** `enhance_prompt`.
    *   **Action:** Remove this function.
    *   **Implementation Details:**
        * Removed the redundant `enhance_prompt` function from `app/services/image_generation_service.py`
        * This function is no longer needed since it has been replaced by the more sophisticated `synthesize_image_prompt` function
        * The new function provides better integration of protagonist description with agency details
        * All code that previously used `enhance_prompt` has been updated to use `synthesize_image_prompt` instead
        * Implemented on 2025-03-30

*   [x] **Step 7: Configuration & Model Verification:**
    *   **File:** `app/services/image_generation_service.py`
    *   **Action:** Verify the LLM call within `synthesize_image_prompt` specifically uses the `"gemini-2.0-flash"` model. Check that the `LLMService` instance used is the intended `GeminiService`.
    *   **Implementation Details:**
        * Verified that `LLMService` is set to `GeminiService` by default in `app/services/llm/__init__.py`
        * Confirmed that `GeminiService` initializes with `model: str = "gemini-2.0-flash"` by default in `app/services/llm/providers.py`
        * Added explicit model name verification in the `synthesize_image_prompt` function
        * Added enhanced logging to confirm the model being used
        * Added verification for the fallback mechanism to ensure it also uses the correct model
        * Added warning logs when a different model is detected
        * Implemented on 2025-03-30
    *   **Code:**
        ```python
        # Explicitly verify we're using the correct model
        model_name = "gemini-2.0-flash"
        logger.info(f"Using model {model_name} for image prompt synthesis")
        
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction="You are a helpful assistant that follows instructions precisely.",
        )
        
        # In fallback code:
        # Verify the LLMService is using the correct model
        if hasattr(llm, "model"):
            logger.info(f"LLMService is using model: {llm.model}")
            if llm.model != "gemini-2.0-flash":
                logger.warning(f"LLMService is using {llm.model} instead of gemini-2.0-flash")
        ```

*   [x] **Step 8: Logging and Monitoring:**
    *   **Files:** `app/services/image_generation_service.py` and `app/services/websocket/image_generator.py`
    *   **Action:** Add detailed logs to show the entire prompt being sent to the image model.
    *   **Implementation Details:**
        * Enhanced logging in `_generate_image()` method to show the complete prompt at INFO level
        * Added prominent, formatted logging with clear separators to make prompts stand out in the terminal
        * Enhanced logging in `synthesize_image_prompt()` to show the final synthesized prompt
        * Updated logging in `generate_agency_images()` and `generate_chapter_image()` to show prompts at INFO level
        * Removed duplicate logging to keep logs clean and focused
        * Used consistent formatting with separators to make prompts easily identifiable
        * Implemented on 2025-03-30
    *   **Code (in `_generate_image()`):**
        ```python
        logger.info("\n" + "=" * 50)
        logger.info("COMPLETE IMAGE PROMPT SENT TO MODEL:")
        logger.info(f"{prompt}")
        logger.info(f"Model: {self.model_name} | Attempt: {attempt + 1}/{retries + 1}")
        logger.info("=" * 50 + "\n")
        ```
    *   **Code (in `synthesize_image_prompt()`):**
        ```python
        logger.info("\n" + "=" * 50)
        logger.info("SYNTHESIZED IMAGE PROMPT (BEFORE SENDING TO IMAGE MODEL):")
        logger.info(f"{synthesized_prompt}")
        logger.info("=" * 50 + "\n")
        ```
    *   **Code (in `generate_chapter_image()`):**
        ```python
        logger.info("\n" + "=" * 50)
        logger.info("CHAPTER IMAGE PROMPT (BEFORE SENDING TO IMAGE SERVICE):")
        logger.info(f"{prompt}")
        logger.info("=" * 50 + "\n")
        ```

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

## 6. Additional Implementations Made

*   [x] **Move Image Synthesis Prompt to prompt_templates.py (2025-03-30):**
    *   **File:** `app/services/llm/prompt_templates.py`
    *   **Action:** Extract the meta-prompt from `synthesize_image_prompt` function and move it to prompt_templates.py as a constant.
    *   **Implementation Details:**
        * Created a new constant named `IMAGE_SYNTHESIS_PROMPT` in prompt_templates.py
        * Used consistent formatting with other prompts in the file
        * Added it under a new section "# Image prompt synthesis"
        * Updated the `synthesize_image_prompt()` function to import and use this template
        * Modified the function to format the template with the proper parameter names
        * Kept all existing functionality intact
        * Implemented on 2025-03-30
    *   **Code (in `prompt_templates.py`):**
        ```python
        # Image prompt synthesis
        # --------------------

        IMAGE_SYNTHESIS_PROMPT = """
        ROLE: Expert Prompt Engineer for Text-to-Image Models

        CONTEXT:
        You are creating an image prompt for one chapter of an ongoing children's educational adventure story (ages 6-12).
        The image should be a snapshot of a key moment from this specific chapter.
        The story features a main protagonist whose base look is described below.
        The protagonist also has a special "agency" element (an item, companion, role, or ability) chosen at the start, with its own visual details.

        INPUTS:
        1. Scene Description: A concise summary of the key visual moment in *this specific chapter*. **This scene takes priority.**
           "{image_scene_description}"
        2. Protagonist Base Look: The core appearance of the main character throughout the adventure.
           "{protagonist_description}"
        3. Protagonist Agency Element: The special element associated with the protagonist.
           - Category: "{agency_category}"
           - Name: "{agency_name}"
           - Visuals: "{agency_visual_details}"
        4. Story Sensory Visual: An overall visual mood element for this story's world. **Apply this only if it fits logically with the Scene Description.**
           "{story_visual_sensory_detail}"

        TASK:
        Combine these inputs into a single, coherent, vivid visual scene description (target 30-50 words) suitable for Imagen.
        ...
        """
        ```
    *   **Code (in `image_generation_service.py`):**
        ```python
        # Import the template from prompt_templates
        from app.services.llm.prompt_templates import IMAGE_SYNTHESIS_PROMPT

        # Format the template with the provided inputs
        meta_prompt = IMAGE_SYNTHESIS_PROMPT.format(
            image_scene_description=image_scene_description,
            protagonist_description=protagonist_description,
            agency_category=agency_details.get("category", "N/A"),
            agency_name=agency_details.get("name", "N/A"),
            agency_visual_details=agency_details.get("visual_details", "N/A"),
            story_visual_sensory_detail=story_visual_sensory_detail,
        )
        ```
