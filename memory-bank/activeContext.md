# Active Context

## Current Focus: Logging Improvements & Bug Fixes (2025-04-05)

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

### Next Steps

Continue working on the remaining tasks for the `protagonist_inconsistencies` branch.

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
