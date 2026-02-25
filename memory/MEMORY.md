# Learning Odyssey Analysis Memory

## AI/LLM Pipeline - Comprehensive Analysis

### LLM Factory & Model Architecture
- **Dual-model routing system**: Flash (complex tasks) vs Flash Lite (simple processing)
- **Complex reasoning (Flash)**: `story_generation`, `image_scene_generation` (~29% of ops)
- **Simple processing (Flash Lite)**: `summary_generation`, `paragraph_formatting`, `character_visual_processing`, `image_prompt_synthesis` (~71% of ops)
- **Models**: Gemini 2.5 Flash & Flash Lite (cost optimization ~50% reduction)

### Prompt Templates & Engineering
**Sophistication Level: ADVANCED - Multi-stage with Context Awareness**

1. **System Prompt** (`SYSTEM_PROMPT_TEMPLATE`):
   - Establishes storyteller role with natural flow from previous chapters
   - Defines story elements (settings, theme, moral teaching)
   - Agency integration: references protagonist's choice consistently through journey
   - Character description requirements: 2-3 detailed visual sentences for EVERY character
   - Critical emphasis on visual consistency via story history references

2. **First Chapter Prompt** (`FIRST_CHAPTER_PROMPT`):
   - Protagonist visual baseline establishment
   - Agency decision mechanics: 3 distinct sensory-enhanced options
   - Includes visual/sound/smell sensory details
   - Choice format: strict `<CHOICES>` tags with peek into unlocked actions

3. **Story Chapter Prompt** (`STORY_CHAPTER_PROMPT`):
   - Previous impact guidance (consequences from last lesson)
   - Phase-specific narrative guidance (Exposition → Rising → Trials → Climax → Return)
   - Plot twist development: subtle hints → building tension → full revelation
   - Agency presence weaving without predictable patterns

4. **Lesson Chapter Prompt** (`LESSON_CHAPTER_PROMPT`):
   - Topic introduction through character observation/dialogue/events
   - Narrative device options: eavesdropping, character poses question, monologue, story object
   - Agency connection: how does chosen power help understand this topic?
   - CRITICAL: Uses exact question verbatim, no rephrasing

5. **Reflect Chapter Prompt** (`REFLECT_CHAPTER_PROMPT`):
   - 8 reflective techniques: dreams/visions, mentor conversations, magical environments, memory palaces, objects (mirrors/books/crystals), flashbacks, heightened senses, parallel storylines
   - Socratic exploration: guides character to understanding through thoughtful questions
   - Narrative acknowledgment: gentle correction for incorrect answers
   - Story-driven choices: process learning in 3 different ways (no "correct/incorrect" labels)

6. **Conclusion Chapter Prompt** (`CONCLUSION_CHAPTER_PROMPT`):
   - Resolution of all plot threads
   - Character growth showcase
   - Agency resolution: shows evolution from Chapter 1 through journey
   - Satisfying closure while highlighting transformation

7. **Summary Chapter Prompt** (`SUMMARY_CHAPTER_PROMPT`):
   - 5-10 word chapter title capture
   - 70-100 word summary from "we" narrator perspective (reader + narrator)
   - Integrates exact educational questions into narrative recap
   - Child-friendly (ages 6-12) engaging tone

### Image Generation Pipeline (Two-Step Synthesis)
1. **Scene Selection** (`IMAGE_SCENE_PROMPT`):
   - LLM identifies single most visually striking moment (~100 words)
   - Focus: dramatic action, emotional peaks, visual energy
   - Character visual references provided for consistency
   - Output: vivid scene description with protagonist identification

2. **Prompt Synthesis** (`IMAGE_SYNTHESIS_PROMPT`):
   - Combines scene description + protagonist visuals + agency visuals + story sensory detail
   - Agency integration logic:
     - Profession: protagonist looks like profession after adopting role
     - Companion: protagonist accompanied by agency creature/being
     - Artifact: protagonist holding/using magical item
     - Ability: protagonist displays visual manifestation of ability
   - Character consistency: merges new descriptions with existing character_visuals
   - Fallback: omits sensory detail if contradicts scene (inside cave vs dawn sparkles)
   - Output: 30-50 word synthesized prompt ready for Imagen

### Character Visual Tracking
- **Update Mechanism** (`CHARACTER_VISUAL_UPDATE_PROMPT`):
  - Scans entire chapter for ANY character descriptions (primary, secondary, minimal)
  - Extracts: appearance, clothing, accessories, distinctive features
  - Visual descriptions: 25-40 words, self-contained
  - Maintains consistency: core appearance with evolved descriptions
  - Returns JSON with all characters updated from chapter

### Content Generation Validation
- **Story chapter validation**: Exactly 3 choices required
- **Retry logic**: Up to 3 attempts if validation fails
- **Choice extraction**: Regex parsing for `<CHOICES>` tags with single-line format
- **Lesson choices**: Derived from question answers (auto-generated)
- **Reflection choices**: 3 story-driven alternatives for processing learning

### Summary Generation Strategy
- **On-demand generation**: Missing summaries generated when summary screen requested
- **Two-part output**: Title (5-10 words) + Summary (70-100 words)
- **Stored summaries**: Cached in `state.chapter_summaries` and `state.summary_chapter_titles`
- **Learning report**: Questions, chosen answers, correctness, explanations compiled

### Story Content Data Architecture
**Example: "Dream Library of Lost Stories"**
- **Narrative elements**: 5 detailed settings, 5 themes, 5 moral teachings, 5 plot twists (each 2-4 sentences of richness)
- **Sensory details**: 5 visuals, 5 sounds, 5 smells (highly atmospheric and evocative)
- **Themes**: Complex concepts (power of stories, preserving knowledge, empathy, imagination as magic, legacy)
- **Moral teachings**: Nuanced dilemmas (using stories wisely, sharing knowledge, rewriting responsibly, truth vs fiction, respecting authorship)
- **Plot twists**: Sophisticated narrative reversals (escaped protagonist, living library consciousness, lost chapter, reader becomes story, rival librarian)

### Lesson Question Quality
**Example: "Astronomy" CSV** (50+ questions per difficulty level)
- **Difficulty tiers**: "Reasonably Challenging" & "Very Challenging"
- **Question sophistication**: Scientific concepts with child-appropriate explanations
- **Answer structure**: 1 correct + 2 wrong answers, each plausible
- **Explanations**: 1-2 sentences bridging everyday examples to complex science
- **Coverage**: Solar System, Stars, Moon, Space Exploration, Galaxies, Universe
- **Example Q**: "How do scientists determine what stars are made of?" → Spectroscopy with barcode analogy

### Prompt Engineering Sophistication Metrics
1. **Contextual Awareness**: Phase guidance, previous lesson impact, character evolution, agency evolution
2. **Narrative Cohesion**: Story history reconstruction, lesson history formatting, consequence weaving
3. **Educational Integration**: Organic lesson placement, Socratic reflection, multi-perspective processing
4. **Sensory Integration**: Visual/audio/olfactory details driving narrative atmosphere
5. **Validation & Retry**: Automatic re-generation on validation failure, up to 3 attempts
6. **Agency Weaving**: Consistent integration of protagonist's chosen power through ALL chapters
7. **Phase Transitions**: Explicit guidance for each story phase with tone expectations
8. **Visual Consistency**: Character tracking across chapters, protagonist evolution, new NPC integration

### LLM Service Implementations
- **GeminiService**: Uses google-genai client, supports streaming & non-streaming
- **OpenAIService**: Uses AsyncOpenAI client, streaming with buffer-based paragraph detection
- **Paragraph Formatting**: Auto-detects if content needs reformatting, regenerates with proper structure
- **Thinking Budget**: 512 tokens for complex reasoning tasks (story/image generation)
- **Logging**: Comprehensive prompt/response logging with session context
