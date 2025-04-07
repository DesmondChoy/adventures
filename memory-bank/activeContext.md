# Active Context

## Current Focus: Logging Configuration Fix (2025-04-07)

We fixed a logging configuration issue in `app/utils/logging_config.py` that caused both a `TypeError` on startup and potential `UnicodeEncodeError` during runtime on Windows.

### Problem Addressed

1.  **`TypeError` on Startup:** The `logging.StreamHandler` was incorrectly initialized with an `encoding="utf-8"` argument, which it does not accept.
2.  **`UnicodeEncodeError` during Runtime:** The default Windows console encoding (`cp1252`) could not handle certain Unicode characters, causing errors when logging messages containing them.

### Implemented Solution

1.  **Removed Invalid Argument:** Removed the `encoding="utf-8"` argument from the `logging.StreamHandler` initialization.
2.  **Wrapped `sys.stdout`:** Wrapped the standard output stream (`sys.stdout.buffer`) using `io.TextIOWrapper` configured with `encoding='utf-8'` and `errors='replace'`. This ensures the stream passed to `StreamHandler` correctly handles UTF-8 and replaces problematic characters instead of crashing.
3.  **Added Basic Console Formatter:** Added a simple `logging.Formatter('%(message)s')` to the console handler to prevent the `StructuredLogger` from causing duplicate message prints (once via `print`, once via the handler).
4.  **Ensured File Handler Encoding:** Explicitly set `encoding='utf-8'` for the `logging.FileHandler` as well for consistency.
5.  **Added JSON File Formatter:** Added a basic JSON formatter to the file handler to maintain structured logging in the file output.

### Result

The application now starts without the `TypeError`, and console logging correctly handles Unicode characters without causing `UnicodeEncodeError`, ensuring robust logging on different platforms.

### Affected Files

1.  `app/utils/logging_config.py`: Updated `setup_logging` function.

## Previous Focus: Image Scene Prompt Enhancement (2025-04-06)

We updated the `IMAGE_SCENE_PROMPT` to include character visual context, improving image generation consistency.

### Problem Addressed

The `IMAGE_SCENE_PROMPT` used for generating a visual scene description for image generation did not include the context of existing character visual descriptions (`state.character_visuals`). This meant the LLM generating the scene description might not be aware of established character appearances, potentially leading to inconsistencies in the final generated image.

### Implemented Solution

1.  **Prompt Template Update:**
    *   Modified `IMAGE_SCENE_PROMPT` in `app/services/llm/prompt_templates.py` to include a new placeholder: `{character_visual_context}`.
    *   Added instructions for the LLM to use this context when describing characters in the scene.

2.  **Function Signature Update:**
    *   Modified the `generate_image_scene` static method in `app/services/chapter_manager.py` to accept an additional argument: `character_visuals: Dict[str, str]`.

3.  **Prompt Formatting Update:**
    *   Updated the `generate_image_scene` method to format the `IMAGE_SCENE_PROMPT` by passing the `character_visuals` dictionary (serialized as JSON) into the new `{character_visual_context}` placeholder.

4.  **Calling Code Update:**
    *   Modified the call to `chapter_manager.generate_image_scene` within `app/services/websocket/image_generator.py` to pass the `state.character_visuals` dictionary.

### Result

The LLM responsible for generating the image scene description now receives the current visual descriptions of all known characters. This allows it to generate scene descriptions that are more consistent with the established character appearances throughout the adventure, leading to more coherent image generation via the `IMAGE_SYNTHESIS_PROMPT` which already used this context.

### Affected Files

1.  `app/services/llm/prompt_templates.py`: Updated `IMAGE_SCENE_PROMPT`.
2.  `app/services/chapter_manager.py`: Updated `generate_image_scene` method signature and prompt formatting.
3.  `app/services/websocket/image_generator.py`: Updated the call to `generate_image_scene`.

## Previous Focus: Agency Choice Visual Details Enhancement (2025-04-06)

We implemented an enhancement to include visual details of agency choices in the story history for Chapter 2 onwards. This ensures the LLM has access to the complete visual description of the agency choice when generating subsequent chapters.

### Problem Addressed

When a user selects an agency choice in Chapter 1 (e.g., "Tiny Dragon"), the visual details in square brackets (e.g., "[a palm-sized dragon with shimmering scales that shift like a rainbow, friendly violet eyes, and puffs of glittery smoke]") were not being included in the story history section of the prompt for Chapter 2 onwards. This resulted in the LLM not having access to the complete visual description of the agency choice when generating subsequent chapters.

### Implemented Solution

1. **Enhanced Agency Choice Processing:**
   * Modified `process_story_response()` in `choice_processor.py` to extract the full option text with visual details
   * Created an enhanced choice text that includes the visual details in square brackets
   * Used this enhanced choice text when creating the `StoryResponse` object

2. **Story History Enhancement:**
   * When the story history is built for subsequent chapters in `_build_base_prompt()` (in `prompt_engineering.py`), it now automatically includes the visual details because they're already part of the `choice_text` field in the `StoryResponse` object

3. **Result:**
   * Now, when the LLM generates Chapter 2 and beyond, the prompt includes the complete agency choice with visual details in the story history section:
   ```
   # Story History
   ## Chapter 1
   <Content...>
   **Choice Made**: Choose a Companion: Tiny Dragon [a palm-sized dragon with shimmering scales that shift like a rainbow, friendly violet eyes, and puffs of glittery smoke] - Befriend a creature that can light the darkest paths, provide warmth in the coldest climates, and cook a mean marshmallow over its tiny flames.
   ```

## Previous Focus: Character Visual Extraction Timing Fix (2025-04-06)

We implemented a fix for the character visual extraction timing issue that was causing character visuals to not be properly extracted from LLM responses.

### Problem Addressed

The system was attempting to extract character visuals from streamed LLM responses before the complete response was received, resulting in empty or incomplete character visual dictionaries. This was particularly evident in the logs:

```
=== CHARACTER_VISUAL_UPDATE_PROMPT RESPONSE [CHAPTER 1] ===
Response:

=== END RESPONSE ===

JSON parsing error: Expecting value: line 1 column 1 (char 0)
```

### Implemented Solution

1. **LLM Service API Enhancement:**
   * Added a new non-streaming `generate_character_visuals_json()` method to the `BaseLLMService` abstract class
   * Implemented this method in both OpenAI and Gemini service providers
   * This ensures we get complete, synchronous responses for character visual extraction

2. **Character Visual Extraction Improvement:**
   * Modified `_update_character_visuals()` to use the new non-streaming API
   * Enhanced JSON extraction to better handle different response formats
   * Added proper validation for extracted character visuals
   * Improved error handling and fallbacks

3. **State Management Robustness:**
   * Ensured proper state initialization for character visuals
   * Improved error handling in the state update process
   * Added better logging of character visual extraction results

The key insight was that character visual extraction should not use streaming responses, as the complete JSON object is critical for proper extraction. By using a dedicated non-streaming API method, we've eliminated the race conditions that were causing empty responses.

### Affected Files

1. `app/services/llm/base.py`: Added new abstract method for character visual extraction
2. `app/services/llm/providers.py`: Implemented non-streaming methods for both LLM providers
3. `app/services/websocket/choice_processor.py`: Updated character visual extraction process
4. `app/services/adventure_state_manager.py`: Enhanced state handling for character visuals

## Previous Focus: Logging Improvements & Bug Fixes (2025-04-05)

We addressed several logging issues and a prompt formatting bug to improve debugging visibility and stability.

### Implemented Changes

1.  **Protagonist Description Logging:**
    *   Modified `app/services/chapter_manager.py` to log the selected protagonist description directly in the INFO message (`logger.info(f"Selected protagonist description: {selected_protagonist_desc}")`) instead of using the `extra` dictionary. This makes the description visible in standard console output.

2.  **Prompt Formatting Fix:**
    *   Fixed a `KeyError` in `app/services/websocket/choice_processor.py` that occurred when formatting the `CHARACTER_VISUAL_UPDATE_PROMPT`.
    *   Changed the formatting method from `.format()` to `.replace()` to safely substitute the `chapter_content` and `existing_visuals` JSON string without misinterpreting curly braces within the JSON.

3.  **Narrative Prompt Logging Level:**
    *   Updated the Gemini implementation in `app/services/llm/providers.py` to log the narrative generation prompts (system and user) at the INFO level instead of DEBUG.
    *   This ensures these prompts are visible in the console, which is configured to show INFO level logs and above (`app/utils/logging_config.py`).

## Previous Focus: Protagonist Inconsistencies Fix (2025-04-01)

We were working on the `protagonist_inconsistencies` branch to address issues with protagonist visual consistency across chapters. The implementation has been partially completed with the two-step image prompt generation system, but there are remaining tasks to fully integrate protagonist descriptions throughout the application.

### Problem Analysis

The protagonist's visual appearance has shown inconsistencies across chapters:

1. **Inconsistent Protagonist Descriptions:**
   * Different chapters may describe the protagonist with varying visual details
   * The image generation prompts don't consistently maintain the protagonist's base appearance
   * Agency elements (companion, ability, etc.) sometimes replace rather than augment the protagonist's description

2. **Gender Inconsistency:**
   * The protagonist's gender sometimes changes between chapters
   * No mechanism exists to maintain gender consistency in LLM-generated content
   * Pronouns may switch unexpectedly (he/she/they) across the adventure

3. **Missing Visual Extraction:**
   * Character visuals are not consistently updated between chapters
   * There's no formal validation for character visual extraction
   * The protagonist's appearance evolution isn't properly tracked

### Partial Implementation

We've already implemented a two-step prompt generation process for images:

1. **Predefined Protagonist Descriptions:**
   * Added `PREDEFINED_PROTAGONIST_DESCRIPTIONS` to `prompt_templates.py`
   * Added `protagonist_description` field to `AdventureState`
   * Randomly selects a description during state initialization

2. **Prompt Synthesis:**
   * Created `synthesize_image_prompt` in `image_generation_service.py`
   * Uses Gemini Flash to intelligently combine protagonist description, agency details, and scene
   * Improved image consistency by prioritizing scene content while maintaining protagonist appearance

3. **Agency-Focused Imagery:**
   * Updated `generate_agency_images` to focus solely on agency elements
   * Enhanced visual representation of agency choices
   * Added better error handling and fallbacks

### Remaining Tasks

1. **Chapter 1 Prompt Enhancement:**
   * Update `FIRST_CHAPTER_PROMPT` to incorporate protagonist description
   * Modify `build_first_chapter_prompt` to pass protagonist description
   * Ensure the LLM respects the chosen protagonist gender and appearance

2. **Character Visual Management:**
   * Enhance `update_character_visuals` in `adventure_state_manager.py`
   * Add protagonist consistency checks
   * Ensure protagonist description is included in all character visuals updates

3. **Gender Consistency:**
   * Extract protagonist gender from predefined description
   * Store gender in `state.metadata["protagonist"]["gender"]`
   * Add instructions in prompts to maintain gender consistency
   * Add validation to ensure pronouns remain consistent

4. **Visual Evolution Tracking:**
   * Enhance logging to show protagonist visual evolution
   * Ensure changes are intentional and story-driven
   * Maintain a history of visual changes in the state

### Implementation Files

The key files requiring modification are:

1. `app/services/llm/prompt_templates.py`:
   * Update `FIRST_CHAPTER_PROMPT` to include protagonist description
   * Add placeholder for protagonist gender consistency

2. `app/services/llm/prompt_engineering.py`:
   * Modify `build_first_chapter_prompt` to pass protagonist description
   * Add gender consistency instructions

3. `app/services/adventure_state_manager.py`:
   * Enhance `update_character_visuals` with protagonist consistency
   * Add gender extraction and validation
   * Implement visual evolution tracking

4. `app/services/websocket/choice_processor.py`:
   * Update `_update_character_visuals` to respect protagonist description
   * Add validation for extracted character visuals
   * Enhance logging for protagonist visual changes

## Previous Focus: Character Visual Consistency & Evolution Debugging (2025-04-01)

We implemented detailed logging for character visuals state management to help debug visual inconsistencies in character evolution. This implementation builds on the recently completed "Character Visual Consistency & Evolution Implementation" (see `wip/characters_evolution_visual_inconsistencies.md`).

### Problem Analysis

The character visual consistency and evolution system was recently implemented, but there was a need for better visibility into how the state is being tracked, updated, and used throughout the application:

1. **Limited Visibility:**
   * It was difficult to see what character visuals were being tracked in the `AdventureState.character_visuals` dictionary
   * There was no clear way to see when and how character visuals were being updated
   * It was unclear which character visuals were being used for image generation

2. **Debugging Challenges:**
   * Without detailed logging, it was hard to identify if character visuals were being properly extracted from chapter content
   * It was difficult to verify if character visuals were being correctly updated in the state
   * There was no way to confirm if character visuals were being properly included in image prompts

3. **Tracking Evolution:**
   * Character evolution across chapters was hard to track without seeing the before/after state
   * It was difficult to verify if the LLM was correctly identifying visual changes in the narrative
   * There was no visibility into which characters were being added, updated, or remaining unchanged

### Implemented Solution

We added comprehensive logging throughout the character visuals pipeline to provide complete visibility into the state management:

1. **Character Visual Extraction** (`choice_processor.py`):
   * Added logging to show the existing character visuals before update
   * Added logging to display the base protagonist description
   * Added logging to show the raw LLM response with extracted character visuals
   * Added logging when the update is successful

2. **State Updates** (`adventure_state_manager.py`):
   * Added logging to show which characters are NEW, UPDATED, or UNCHANGED
   * Added logging to show BEFORE/AFTER comparison for updated characters
   * Added logging to provide a summary count of changes (e.g., "3 new, 1 updated, 2 unchanged")

3. **Image Generation** (`image_generator.py`):
   * Added logging to show all character visuals being used for image generation
   * Added logging to display the base protagonist description
   * Added logging to show agency details being used
   * Added logging for the final image prompt

4. **Image Prompt Synthesis** (`image_generation_service.py`):
   * Added logging to show character visuals being included in the image prompt
   * Added logging when no character visuals are available
