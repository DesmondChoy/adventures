# LLM Best Practices

## LLM Service Provider Differences

### 1. Streaming Response Handling
- OpenAI and Gemini APIs handle streaming responses differently
- For OpenAI: Async streaming works reliably with `async for chunk in response`
- For Gemini: Direct API calls are more reliable than streaming for short responses
- When implementing features that use LLM responses:
  * Check which service is being used: `isinstance(llm, LLMService) or "Gemini" in llm.__class__.__name__`
  * Implement service-specific handling for critical features
  * For short, single-response use cases (like summaries), prefer direct API calls with Gemini
  * For long, streaming responses, implement robust chunk collection

### 2. Error Handling Differences
- OpenAI errors typically include detailed error messages and status codes
- Gemini errors may be less specific and require additional logging
- Always implement robust fallback mechanisms for LLM-dependent features
- Use try/except blocks with specific error types when possible
- Log both the error type and message for debugging

### 3. Response Format Differences
- OpenAI responses typically follow requested formats more consistently
- Gemini may require more explicit formatting instructions
- When parsing responses, implement flexible parsing that can handle variations
- Add validation to ensure critical information is extracted correctly
- Consider using regex patterns that can handle different response structures
- For critical format requirements, use the Format Example Pattern:
  * Provide both incorrect and correct examples in prompts
  * Show the incorrect example first to highlight what to avoid
  * Follow with the correct example to demonstrate desired format
  * Use clear section headers like "INCORRECT FORMAT (DO NOT USE)" and "CORRECT FORMAT (USE THIS)"
  * Explicitly instruct the LLM to use exact section headers

## LLM Prompting Best Practices

### 1. Context Isolation
* Each prompt MUST be self-contained with all necessary context
* Never reference previous/future prompts (e.g., "for consistency with other chapters")
* GOOD: "Describe appearance to help readers visualize the character"
* BAD: "Describe appearance for visual consistency across chapters"

### 2. Immediate Purpose Framing
* Frame instructions with self-contained purposes
* GOOD: "Include visual details to create vivid mental images"
* BAD: "Include visual details for future image generation"

### 3. Avoid System References
* Never mention system components, pipelines, or other prompts
* Don't reference technical implementation details

### 4. Character Description Requirements (CRITICAL - NOT DUPLICATION)
* **System-wide character descriptions are essential** for visual consistency in image generation
* Character description rules in `SYSTEM_PROMPT_TEMPLATE` apply to ALL chapters, not just first chapter
* **Why this appears like duplication but isn't:**
  - `SYSTEM_PROMPT_TEMPLATE`: Ensures extractable character descriptions in every chapter
  - `FIRST_CHAPTER_PROMPT`: Establishes initial protagonist foundation
  - Each serves different purposes in the visual consistency pipeline
* **Technical dependency:** 
  - `CHARACTER_VISUAL_UPDATE_PROMPT` scans all chapter content for character descriptions
  - Extracted descriptions stored in `state.character_visuals` for image generation
  - Two-step image synthesis requires consistent character data across entire adventure
* **Never remove character description rules from system prompt** - this would break visual continuity
* GOOD: "Describe supporting characters when they first appear"
* BAD: "Help CHARACTER_VISUAL_UPDATE_PROMPT track characters"

### 4. Concrete Over Abstract
* Provide specific examples rather than abstract descriptions
* GOOD: "Describe clothing, physical features, and distinctive characteristics"
* BAD: "Provide a comprehensive visual description"

### 5. Educational Integration
* Frame educational content as narrative opportunities
* GOOD: "Create a situation where the character naturally encounters [concept]"
* BAD: "Insert the educational content about [concept]"

### 6. Character Handling
* Focus on immediate role and appearance for characters
* GOOD: "When introducing the forest guardian, describe their appearance in this scene"
* BAD: "Introduce the forest guardian consistent with their established character"

### 7. Implementation Example
```
INEFFECTIVE: "Include visual descriptions for consistency with future chapters and to help CHARACTER_VISUAL_UPDATE_PROMPT track them."

EFFECTIVE: "Whenever introducing a supporting character, include at least one sentence describing their visual appearance (clothing, physical features, distinctive characteristics) to help readers visualize them clearly."
```

## Character Description Guidelines

### 1. Visual Consistency & Extraction
* **Initial Description:** Always describe character appearances when they first appear in the narrative. Include clothing, physical features, and distinctive characteristics.
* **Storage:** These descriptions are tracked and evolved in the `state.character_visuals` dictionary. The protagonist's base look is also stored in `state.protagonist_description`.
* **Extraction/Update Mechanism:**
    * After each chapter, the `CHARACTER_VISUAL_UPDATE_PROMPT` is used with an LLM to parse the chapter content.
    * This prompt identifies new characters and visual changes to existing ones.
    * The results are intelligently merged into `state.character_visuals` by `AdventureStateManager.update_character_visuals`.
* **Evolution:** Character visual changes should reflect story events. The system aims to maintain core elements while allowing gradual, narrative-driven evolution.
* **Prompting for Extraction:** Use specific, concrete details rather than abstract descriptions when prompting the LLM for visual extraction.

### 2. Tracking Evolution (Logging Example)
* Log the before/after state when `state.character_visuals` is updated.
* Track which characters are NEW, UPDATED, or UNCHANGED.
* Provide a summary count of changes (e.g., "3 new, 1 updated, 2 unchanged").
* Include chapter number for context.

### 3. Logging Implementation Example
```
[CHAPTER 3] AdventureState.character_visuals BEFORE update:
[CHAPTER 3] - Protagonist: "Wearing a blue tunic with a small pouch"
[CHAPTER 3] - Wise Owl: "A grand owl with snowy feathers and golden spectacles"

[CHAPTER 3] LLM response (character_visuals):
[CHAPTER 3] - Protagonist: "Wearing a blue tunic with a small pouch, now with a scratch on his arm"
[CHAPTER 3] - Wise Owl: "A grand owl with snowy feathers and golden spectacles"
[CHAPTER 3] - Forest Guardian: "A tall figure with bark-like skin and leafy hair, eyes glowing green"

[CHAPTER 3] AdventureState.character_visuals AFTER update:
[CHAPTER 3] NEW: "Forest Guardian" - "A tall figure with bark-like skin and leafy hair, eyes glowing green"
[CHAPTER 3] UPDATED: "Protagonist"
[CHAPTER 3]   BEFORE: "Wearing a blue tunic with a small pouch"
[CHAPTER 3]   AFTER:  "Wearing a blue tunic with a small pouch, now with a scratch on his arm"
[CHAPTER 3] UNCHANGED: "Wise Owl" - "A grand owl with snowy feathers and golden spectacles"
[CHAPTER 3] Summary: 1 new, 1 updated, 1 unchanged
```

## Image Prompt Construction (Two-Step Synthesis Pattern)

The system now uses a two-step process involving LLMs to construct the final image prompt, ensuring better integration of various visual elements.

### Step 1: Gather Core Visual Inputs
The following pieces of information are gathered as inputs for the synthesis process:

1.  **Concise Scene Description:**
    *   Generated by an LLM using `IMAGE_SCENE_PROMPT` and the current chapter's content.
    *   Focuses on the single most visually striking moment of the chapter (approx. 50 words).
    *   Describes specific actions, character poses, expressions, and environmental details.
2.  **Protagonist Base Look:**
    *   The consistent base visual description of the protagonist (e.g., "A curious young boy with short brown hair...").
    *   Sourced from `state.protagonist_description`.
3.  **Agency Details:**
    *   The protagonist's chosen agency (item, companion, ability, profession).
    *   Includes its name, category (e.g., "Choose a Companion"), and specific visual description (e.g., "a palm-sized dragon with shimmering scales...").
    *   Sourced from `state.metadata.agency`, with visual details extracted during the initial agency choice.
4.  **Story Visual Sensory Detail:**
    *   An overall visual mood or style element for the story's world (e.g., "everything has a soft, dreamlike glow").
    *   Sourced from `state.selected_sensory_details['visuals']`.
5.  **Evolved Character Visuals:**
    *   The latest, up-to-date visual descriptions for all relevant characters (protagonist if evolved, and NPCs) present in the current scene.
    *   Sourced from `state.character_visuals`.

### Step 2: LLM-Powered Prompt Synthesis
*   **Synthesizer LLM:** An LLM (specifically Gemini Flash) is invoked using the `IMAGE_SYNTHESIS_PROMPT`.
*   **Task:** This meta-prompt instructs the LLM to act as an "Expert Prompt Engineer." Its task is to logically combine all the inputs from Step 1 into a single, coherent, and vivid visual scene description (target 30-50 words) suitable for the image generation model (Imagen).
*   **Key Instructions for Synthesizer:**
    *   Prioritize the "Concise Scene Description" as the primary focus of the image.
    *   Integrate the "Protagonist Base Look" and "Agency Details" naturally into the scene.
    *   If characters from "Evolved Character Visuals" are part of the scene, their descriptions should be used, potentially overriding the protagonist's base look if the protagonist has visually evolved.
    *   Apply the "Story Visual Sensory Detail" only if it logically fits the scene.
    *   The desired output style is a "Colorful storybook illustration."

### Benefits
*   **Improved Consistency:** By having an LLM intelligently merge visual elements, especially the protagonist's appearance with agency and evolved NPC details, visual consistency across chapters is enhanced.
*   **Contextual Relevance:** The final prompt is more contextually relevant to the specific chapter's key moment while respecting established visual characteristics.
*   **Richer Prompts:** The synthesis process can create more nuanced and detailed prompts than simple template concatenation.
