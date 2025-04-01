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

### 1. Visual Consistency
* Always describe character appearances when they first appear
* Include clothing, physical features, and distinctive characteristics
* Use specific, concrete details rather than abstract descriptions
* Maintain consistent core elements across chapters
* Evolve character appearances gradually based on narrative events

### 2. Tracking Evolution
* Character visual changes should reflect story events
* Log the before/after state when character visuals are updated
* Track which characters are NEW, UPDATED, or UNCHANGED
* Provide a summary count of changes (e.g., "3 new, 1 updated, 2 unchanged")
* Include chapter number for context

### 3. Implementation Example
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

## Image Prompt Construction

### 1. Agency Visual Details
* Extract and store agency category and visual details in `state.metadata["agency"]`
* Include `visual_details` field extracted from square brackets in `prompt_templates.py`
* Include `category` field to identify the type of agency (companion, ability, artifact, profession)

### 2. Image Prompt Structure
```
Colorful storybook illustration of this scene: [Chapter Summary]. [Agency Prefix] [Agency Name] ([Visual Details]).
```

### 3. Category-Specific Prefixes
* For companions: "He/she is accompanied by"
* For professions: "He/she is a"
* For abilities: "He/she has the power of"
* For artifacts: "He/she is wielding"

### 4. Chapter Image Focus
* Focus on the most visually striking moment
* Highlight specific dramatic action or emotional peak
* Include clear visual elements (character poses, expressions, environment)
* Target the moment with the most visual energy or emotional impact

### 5. Prompt Optimization
* Replace "Fantasy illustration of" with "Colorful storybook illustration of this scene:"
* Use period before agency descriptions instead of comma for better readability
* Remove base style ("vibrant colors, detailed, whimsical, digital art") for cleaner results
* Include visual details in parentheses after agency name