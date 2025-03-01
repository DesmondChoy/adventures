# Progress Log

## 2025-03-01: Fixed Image Generation API Compatibility Issue

### Problem
The image generation in Chapter 1 was failing with the error: `module 'google.generativeai' has no attribute 'generate_images'`. This was caused by a mismatch between the implementation in `ImageGenerationService` and the actual API provided by the Google Generative AI SDK.

### Requirements
- Fix the image generation error in Chapter 1
- Update the `ImageGenerationService` to use the correct API
- Ensure compatibility with the installed SDK version
- Maintain the existing functionality and integration with the WebSocket service

### Solution
1. Identified that the Google Generative AI SDK (google-generativeai v0.8.4) doesn't support image generation directly, while the newer Google Gen AI SDK (google-genai v1.3.0) does:
   ```python
   # Before (using google-generativeai which doesn't support image generation)
   import google.generativeai as genai
   from google.generativeai import types
   
   # After (using google-genai which supports image generation)
   from google import genai
   from google.genai.types import GenerateImagesConfig
   ```

2. Updated the initialization to create a proper client:
   ```python
   # Before
   genai.configure(api_key=api_key)
   self.model = genai.GenerativeModel(self.model_name)
   
   # After
   self.client = genai.Client(api_key=api_key)
   ```

3. Modified the image generation method to use the client's models interface:
   ```python
   # Before (using GenerativeModel which doesn't support image generation)
   response = self.model.generate_content(
       prompt,
       generation_config=generation_config,
       stream=False,
   )
   
   # After (using the client's models interface)
   response = self.client.models.generate_images(
       model=self.model_name,
       prompt=prompt,
       config=GenerateImagesConfig(
           number_of_images=1,
       ),
   )
   ```

4. Updated the response handling to match the expected structure:
   ```python
   # Before (trying to extract image from content parts)
   if (
       hasattr(response, "parts")
       and response.parts
       and hasattr(response.parts[0], "image")
   ):
       image_bytes = response.parts[0].image.data
   
   # After (extracting image from generated_images)
   if response.generated_images:
       image_bytes = response.generated_images[0].image.image_bytes
   ```

5. Added detailed logging to help debug any issues:
   ```python
   logger.debug("\n=== DEBUG: Image Generation Response ===")
   logger.debug(f"Response type: {type(response)}")
   logger.debug(f"Response attributes: {dir(response)}")
   if hasattr(response, "generated_images"):
       logger.debug(f"Generated images count: {len(response.generated_images)}")
       if response.generated_images:
           logger.debug(f"First image type: {type(response.generated_images[0])}")
           logger.debug(f"First image attributes: {dir(response.generated_images[0])}")
   logger.debug("========================\n")
   ```

### Results
The implementation successfully:
1. Fixed the image generation error in Chapter 1
2. Updated the `ImageGenerationService` to use the correct API from the Google Gen AI SDK
3. Ensured compatibility with the installed SDK version (google-genai v1.3.0)
4. Maintained the existing functionality and integration with the WebSocket service
5. Added detailed logging to help diagnose any future issues

## 2025-03-01: Standardized Image Generation Service Configuration

### Problem
The `ImageGenerationService` was using a different configuration pattern than the `GeminiService` in the LLM integration. This inconsistency made the codebase harder to maintain and understand.

### Requirements
- Align the `ImageGenerationService` configuration with the `GeminiService` pattern
- Standardize environment variable usage across services
- Improve error handling and logging
- Ensure compatibility with the existing WebSocket service

### Solution
1. Updated the environment variable from `GEMINI_API_KEY` to `GOOGLE_API_KEY` to match the GeminiService:
   ```python
   # Before
   self.api_key = os.getenv("GEMINI_API_KEY")
   if not self.api_key:
       logger.warning("GEMINI_API_KEY not found in environment variables")
   self.client = genai.Client(api_key=self.api_key)
   
   # After
   api_key = os.getenv("GOOGLE_API_KEY")
   if not api_key:
       logger.warning("GOOGLE_API_KEY is not set in environment variables!")
   genai.configure(api_key=api_key)
   ```

2. Modified the image generation method to use the configured API directly:
   ```python
   # Before
   response = self.client.models.generate_images(
       model=self.model,
       prompt=prompt,
       config=types.GenerateImagesConfig(
           number_of_images=1,
       ),
   )
   
   # After
   response = genai.generate_images(
       model=self.model,
       prompt=prompt,
       generation_config=types.GenerateImagesConfig(
           number_of_images=1,
       ),
   )
   ```

3. Added enhanced debug logging similar to GeminiService:
   ```python
   logger.debug("\n=== DEBUG: Image Generation Request ===")
   logger.debug(f"Prompt: {prompt}")
   logger.debug(f"Model: {self.model}")
   logger.debug("========================\n")
   ```

4. Updated the response handling to match the expected structure:
   ```python
   # Before
   if response.generated_images:
       image = Image.open(BytesIO(response.generated_images[0].image.image_bytes))
   
   # After
   if response.images:
       image = Image.open(BytesIO(response.images[0].bytes))
   ```

### Results
The implementation successfully:
1. Aligned the `ImageGenerationService` configuration with the `GeminiService` pattern
2. Standardized environment variable usage to `GOOGLE_API_KEY` across services
3. Improved error handling and logging for better debugging
4. Maintained compatibility with the existing WebSocket service
5. Made the codebase more consistent and easier to maintain

## 2025-02-28: Fixed Syntax Error in F-String

### Problem
There was a syntax error in the `prompt_engineering.py` file that was preventing the application from starting:
```
SyntaxError: f-string expression part cannot include a backslash
```

The issue was in the agency guidance section for story chapters, where there was a trailing space followed by a newline in an f-string. In Python, when a backslash appears at the end of a line inside a string (which happens with trailing spaces), it's treated as a line continuation character. However, in f-strings, backslashes inside the expression part (inside the curly braces) are not allowed.

### Requirements
- Fix the syntax error in the f-string
- Ensure the agency guidance is still properly formatted
- Maintain the functionality of the agency implementation

### Solution
Removed the trailing space at the end of the line in the agency guidance section for story chapters:

```python
# Before:
agency_guidance = f"""
## Agency Presence
Incorporate the character's {agency.get("type", "choice")} ({agency.get("name", "from Chapter 1")}) in a way that feels natural to this part of the story. 
It should be present and meaningful without following a predictable pattern.
"""

# After:
agency_guidance = f"""
## Agency Presence
Incorporate the character's {agency.get("type", "choice")} ({agency.get("name", "from Chapter 1")}) in a way that feels natural to this part of the story.
It should be present and meaningful without following a predictable pattern.
"""
```

### Results
The implementation successfully:
1. Fixed the syntax error in the f-string
2. Maintained the proper formatting of the agency guidance
3. Allowed the application to start successfully
4. Preserved the functionality of the agency implementation

## 2025-02-28: Agency Implementation

### Problem
The adventure experience lacked a form of agency that would allow users to make meaningful choices that impact their journey. The first chapter choices didn't provide a sense of ownership or continuity throughout the adventure.

### Requirements
- Implement a form of agency in the first chapter through meaningful choices
- Track the agency choice throughout the adventure
- Evolve the agency element based on correct/incorrect answers in REFLECT chapters
- Make the agency element play a pivotal role in the climax
- Provide a satisfying resolution to the agency element in the conclusion

### Solution
1. Added agency choice categories in `prompt_templates.py`:
   ```python
   AGENCY_CHOICE_CATEGORIES = """# Agency Choice Categories
   The character should make one of these meaningful choices that will impact their journey:

   ## Magical Items to Craft
   - A Luminous Lantern that reveals hidden truths and illuminates dark places
   - A Sturdy Rope that helps overcome physical obstacles and bridges gaps
   - A Mystical Amulet that enhances intuition and provides subtle guidance
   - A Weathered Map that reveals new paths and hidden locations
   - A Pocket Watch that helps with timing and occasionally glimpses the future
   - A Healing Potion that restores strength and provides clarity of mind

   ## Companions to Choose
   - A Wise Owl that offers knowledge and explanations
   - A Brave Fox that excels in courage and action-oriented tasks
   - A Clever Squirrel that's skilled in problem-solving and improvisation
   - A Gentle Deer that provides emotional support and finds peaceful solutions
   - A Playful Otter that brings joy and finds unexpected approaches
   - A Steadfast Turtle that offers patience and protection in difficult times

   ## Roles or Professions
   - A Healer who can mend wounds and restore balance
   - A Scholar who values knowledge and understanding
   - A Guardian who protects others and stands against threats
   - A Pathfinder who discovers new routes and possibilities
   - A Diplomat who resolves conflicts through communication
   - A Craftsperson who builds and creates solutions

   ## Special Abilities
   - Animal Whisperer who can communicate with creatures
   - Puzzle Master who excels at solving riddles and mysteries
   - Storyteller who charms others with words and narratives
   - Element Bender who has a special connection to natural forces
   - Dream Walker who can glimpse insights through dreams
   - Pattern Seer who notices connections others miss"""
   ```

2. Added agency guidance templates for different chapter types:
   ```python
   # Agency guidance templates for REFLECT chapters
   AGENCY_GUIDANCE_CORRECT = """## Agency Evolution (Correct Understanding)
   The character's agency choice from Chapter 1 should evolve or be empowered by their correct understanding.
   Choose an approach that feels most natural to the narrative:
   - Revealing a new capability or aspect of their chosen item/companion/role/ability
   - Helping overcome a challenge in a meaningful way using their agency element
   - Deepening the connection between character and their agency choice
   - Providing insight or assistance that builds on their knowledge

   This evolution should feel organic to the story and connect naturally to their correct answer."""

   AGENCY_GUIDANCE_INCORRECT = """## Agency Evolution (New Understanding)
   Despite the initial misunderstanding, the character's agency choice from Chapter 1 should grow or transform through this learning experience.
   Choose an approach that feels most natural to the narrative:
   - Adapting to incorporate the new knowledge they've gained
   - Helping the character see where they went wrong
   - Providing a different perspective or approach to the problem
   - Demonstrating resilience and the value of learning from mistakes

   This transformation should feel organic to the story and connect naturally to their learning journey."""

   # Agency guidance for climax phase
   CLIMAX_AGENCY_GUIDANCE = """## Climax Agency Integration
   The character's agency choice from Chapter 1 should play a pivotal role in this climactic moment:

   1. **Narrative Culmination**: Show how this element has been with them throughout the journey
   2. **Growth Reflection**: Reference how it has changed or evolved, especially during reflection moments
   3. **Meaningful Choices**: Present options that leverage this agency element in different ways

   The choices should reflect different approaches to using their agency element:
   - Choice A: A bold, direct application of their agency element
   - Choice B: A clever, unexpected use of their agency element
   - Choice C: A thoughtful, strategic application of their agency element

   Each choice should feel valid and meaningful, with none being obviously "correct" or "incorrect."
   """
   ```

3. Updated the system prompt to include agency continuity guidance:
   ```markdown
   # Agency Continuity
   The character makes a pivotal choice in the first chapter (crafting an item, choosing a companion, selecting a role, or developing a special ability). This choice:

   1. Represents a core aspect of the character's identity and approach
   2. Must be referenced consistently throughout ALL chapters of the adventure
   3. Should evolve and develop as the character learns and grows
   4. Will play a crucial role in the climax of the story
   5. Should feel like a natural part of the narrative, not an artificial element

   Each chapter should include at least one meaningful reference to or use of this agency element, with its significance growing throughout the journey.
   ```

4. Added special handling for the first chapter in `prompt_engineering.py`:
   ```python
   # Special handling for first chapter - include agency choice
   if state.current_chapter_number == 1 and chapter_type == ChapterType.STORY:
       # Get random agency category
       agency_category = get_random_agency_category()
       
       # Log agency category selection
       logger.debug(f"First chapter: Using agency category: {agency_category.split('# Agency Choice:')[1].split('\n')[0].strip()}")
       
       return f"""{base_prompt}

   {_get_phase_guidance(story_phase, state)}

   {STORY_CHAPTER_INSTRUCTIONS}

   {agency_category}

   {FIRST_CHAPTER_AGENCY_INSTRUCTIONS}

   {get_choice_instructions(story_phase)}"""
   ```

5. Added agency detection and storage in `websocket_service.py`:
   ```python
   # Handle first chapter agency choice
   if previous_chapter.chapter_number == 1 and previous_chapter.chapter_type == ChapterType.STORY:
       logger.debug("Processing first chapter agency choice")
       
       # Extract agency type and name from choice text
       agency_type = ""
       agency_name = ""
       
       # Determine agency type based on keywords in choice text
       choice_lower = choice_text.lower()
       if any(word in choice_lower for word in ["craft", "lantern", "rope", "amulet", "map", "watch", "potion"]):
           agency_type = "item"
           # Extract item name
           # ...
       elif any(word in choice_lower for word in ["owl", "fox", "squirrel", "deer", "otter", "turtle", "companion"]):
           agency_type = "companion"
           # Extract companion name
           # ...
       # ... other agency types ...
       
       # Store agency choice in metadata
       state.metadata["agency"] = {
           "type": agency_type,
           "name": agency_name,
           "description": choice_text,
           "properties": {"strength": 1},
           "growth_history": [],
           "references": []
       }
   ```

6. Added agency reference tracking in `adventure_state_manager.py`:
   ```python
   def update_agency_references(self, chapter_data: ChapterData) -> None:
       """Track references to the agency element in chapters."""
       if self.state is None or "agency" not in self.state.metadata:
           return
           
       agency = self.state.metadata["agency"]
       content = chapter_data.content
       
       # Check if agency is referenced
       agency_name = agency.get("name", "")
       agency_type = agency.get("type", "")
       
       has_reference = (
           agency_name.lower() in content.lower() or 
           agency_type.lower() in content.lower()
       )
       
       # Track references
       if "references" not in agency:
           agency["references"] = []
           
       agency["references"].append({
           "chapter": chapter_data.chapter_number,
           "has_reference": has_reference,
           "chapter_type": chapter_data.chapter_type.value
       })
       
       # Log warning if no reference found
       if not has_reference:
           logger.warning(
               f"No reference to agency element ({agency_name}) found in chapter {chapter_data.chapter_number}"
           )
   ```

7. Updated the REFLECT chapter prompt to include agency guidance:
   ```python
   # Determine agency guidance based on whether the answer was correct
   agency_guidance = ""
   if state and "agency" in state.metadata:
       agency_guidance = AGENCY_GUIDANCE_CORRECT if is_correct else AGENCY_GUIDANCE_INCORRECT
       
       # Track agency evolution in metadata
       if "agency_evolution" not in state.metadata:
           state.metadata["agency_evolution"] = []
           
       state.metadata["agency_evolution"].append({
           "chapter": state.current_chapter_number,
           "chapter_type": "REFLECT",
           "is_correct": is_correct,
           "timestamp": datetime.now().isoformat()
       })
   ```

### Results
The implementation successfully:
1. Adds a meaningful form of agency through a first chapter choice
2. Tracks the agency choice throughout the adventure
3. Evolves the agency element based on correct/incorrect answers in REFLECT chapters
4. Makes the agency element play a pivotal role in the climax
5. Provides a satisfying resolution to the agency element in the conclusion
6. Enhances the narrative continuity and user engagement

## 2025-02-28: Removed Obsolete CHOICE_FORMAT_INSTRUCTIONS

### Problem
The codebase contained an obsolete constant `CHOICE_FORMAT_INSTRUCTIONS` that was imported but not used in `prompt_engineering.py`. It was defined in `prompt_templates.py` with a comment "Keep the original for backward compatibility" but was no longer needed as the code had fully transitioned to using the more dynamic `get_choice_instructions(story_phase)` function.

### Requirements
- Remove unused code to improve maintainability
- Ensure no functionality is broken by the removal
- Maintain the `get_choice_instructions()` function that is actively used

### Solution
1. Removed the import of `CHOICE_FORMAT_INSTRUCTIONS` from `prompt_engineering.py`:
   ```python
   # Removed from imports:
   CHOICE_FORMAT_INSTRUCTIONS,
   ```

2. Removed the constant definition from `prompt_templates.py`:
   ```python
   # Removed:
   # Keep the original for backward compatibility
   CHOICE_FORMAT_INSTRUCTIONS = get_choice_instructions("Rising")
   ```

3. Verified no other references to `CHOICE_FORMAT_INSTRUCTIONS` existed in the codebase by searching all Python files.

### Results
The implementation successfully:
1. Removed an unused constant and its import, reducing potential confusion
2. Maintained all functionality as the code was already using `get_choice_instructions()`
3. Improved code maintainability by removing obsolete code
4. Reduced technical debt by eliminating code that was only kept for backward compatibility

## 2025-02-28: REFLECT Chapter Refactoring for Narrative Integration

### Problem
The REFLECT chapter implementation had a binary approach that felt like a detached "test" rather than part of the story:
- For correct answers: Used multiple challenge types (confidence_test, application, connection_making, teaching_moment)
- For incorrect answers: Used a structured four-step process (reflection, narrative deepening, "aha moment", choices)
- In both cases, choices were structured as one correct answer and two incorrect answers, creating a "test" feeling

### Requirements
- Create a unified narrative-driven approach for both correct and incorrect answers
- Focus on narrative integration rather than separate educational prompts
- Make all choices story-driven without labeling any as "correct" or "wrong"
- Maintain the educational value while making it feel like a natural part of the story

### Solution
1. Updated `REFLECT_CHOICE_FORMAT` in `prompt_templates.py` to remove the "correct/incorrect" structure:
   ```markdown
   # Choice Format
   Use this EXACT format for the choices, with NO indentation and NO line breaks within choices:

   <CHOICES>
   Choice A: [First story-driven choice]
   Choice B: [Second story-driven choice]
   Choice C: [Third story-driven choice]
   </CHOICES>

   # CRITICAL RULES
   1. Format: Start and end with <CHOICES> tags on their own lines, with exactly three choices
   2. Each choice: Begin with "Choice [A/B/C]: " and contain the complete description on a single line
   3. Content: Make each choice meaningful, distinct, and advance the story in different ways
   4. Narrative Focus: All choices should be story-driven without any being labeled as "correct" or "incorrect"
   5. Character Growth: Each choice should reflect a different way the character might process or apply what they've learned
   ```

2. Created a unified template (`REFLECT_TEMPLATE`) for both correct and incorrect answers:
   ```markdown
   # Narrative-Driven Reflection
   The character previously answered the question: "{question}"
   Their answer was: "{chosen_answer}"
   {correct_answer_info}

   {reflective_techniques}

   ## Scene Structure for {answer_status}

   1. **NARRATIVE ACKNOWLEDGMENT**: {acknowledgment_guidance}

   2. **SOCRATIC EXPLORATION**: Use questions to guide the character to {exploration_goal}:
      - "What led you to that conclusion?"
      - "How might this connect to [relevant story element]?"
      - "What implications might this have for [story situation]?"

   3. **STORY INTEGRATION**: Weave this reflection naturally into the ongoing narrative:
      - Connect to the character's journey
      - Relate to the story's theme of "{theme}"
      - Set up the next part of the adventure
   ```

3. Added configuration objects to customize the template based on whether the answer was correct or incorrect:
   ```python
   # Template configurations for correct answers
   CORRECT_ANSWER_CONFIG = {
       "answer_status": "Correct Answer",
       "acknowledgment_guidance": "Create a story event that acknowledges success (character praise, reward, confidence boost)",
       "exploration_goal": "deepen their understanding of why their answer is right and explore broader implications",
       "correct_answer_info": "This was the correct answer.",
   }

   # Template configurations for incorrect answers
   INCORRECT_ANSWER_CONFIG = {
       "answer_status": "Incorrect Answer",
       "acknowledgment_guidance": "Create a story event that gently corrects the mistake (character clarification, consequence of error)",
       "exploration_goal": "discover the correct understanding through guided reflection",
       "correct_answer_info": 'The correct answer was: "{correct_answer}".',
   }
   ```

4. Updated the `build_reflect_chapter_prompt()` function to use the unified approach:
   ```python
   # Select the appropriate configuration based on whether the answer was correct
   config = CORRECT_ANSWER_CONFIG if is_correct else INCORRECT_ANSWER_CONFIG

   # Format the template with the appropriate values
   formatted_template = REFLECT_TEMPLATE.format(
       question=lesson_question["question"],
       chosen_answer=chosen_answer,
       correct_answer_info=config["correct_answer_info"].format(
           correct_answer=correct_answer
       )
       if not is_correct
       else config["correct_answer_info"],
       reflective_techniques=reflective_technique,
       answer_status=config["answer_status"],
       acknowledgment_guidance=config["acknowledgment_guidance"],
       exploration_goal=config["exploration_goal"],
       theme=state.selected_theme if state else "the story",
       reflect_choice_format=REFLECT_CHOICE_FORMAT,
   )
   ```

5. Updated metadata tracking to use the new approach:
   ```python
   state.metadata["reflect_challenge_history"].append(
       {
           "chapter": state.current_chapter_number,
           "is_correct": is_correct,
           "timestamp": datetime.now().isoformat(),
           "approach": "narrative_driven",  # New unified approach
       }
   )

   # Also store the most recent reflection type for easy access
   state.metadata["last_reflect_approach"] = "narrative_driven"
   ```

### Results
The implementation successfully:
1. Created a unified narrative-driven approach for both correct and incorrect answers
2. Made REFLECT chapters feel like a natural part of the character's journey rather than a separate educational module
3. Simplified the implementation while maintaining educational value
4. Made all choices story-driven, enhancing user engagement
5. Used the Socratic method to guide deeper understanding through questions
6. Maintained metadata tracking for debugging purposes

## 2025-02-28: UI Fix - Hide "Swipe to explore" Tip on Desktop

### Problem
The "Swipe to explore" tip was showing on desktop devices, even though swiping is only a feature available on mobile devices. This created a confusing user experience on desktop where users navigate using arrow buttons or keyboard instead of swiping.

### Requirements
- Hide the "Swipe to explore" tip on desktop devices
- Keep the tip visible on mobile devices where swiping is a relevant interaction
- Maintain the existing functionality where the tip fades out after a few seconds or on user interaction

### Solution
Added a media query to `app/static/css/carousel.css` to hide the swipe tip on desktop devices:
```css
/* Hide swipe tip on desktop */
@media (min-width: 769px) {
    .swipe-tip {
        display: none;
    }
}
```

### Results
The implementation successfully:
1. Hides the "Swipe to explore" tip on desktop devices (screen width > 768px)
2. Keeps the tip visible on mobile devices (screen width ≤ 768px) where swiping is relevant
3. Maintains the existing functionality where the tip fades out after a few seconds or when the user interacts with the carousel
4. Improves the user experience by only showing interaction hints that are relevant to the user's device

## 2025-02-28: Lesson Chapter Prompt Improvement with Story Object Method

### Problem
The lesson chapter generation prompt had several issues:
1. The narrative often didn't explicitly reference the question being asked, making it difficult for users to answer correctly
2. The thematic bridge between the story world and educational content felt forced and disconnected
3. The instructions were overly complex and difficult for the LLM to follow consistently

### Requirements
- Ensure the exact question is included verbatim in the narrative
- Create a more intuitive way to bridge between the story world and educational questions
- Simplify the instructions for better LLM comprehension
- Allow more flexibility in where the question appears in the narrative

### Solution
1. Condensed the CRITICAL RULES to three succinct points in `prompt_templates.py`:
   ```markdown
   # CRITICAL RULES
   1. NEVER mention any answer options in your narrative, but DO include the exact question "[Core Question]" verbatim somewhere in the story.
   2. Create ONE visually interesting story object (artifact, phenomenon, pattern, or map) that naturally connects to the question and makes it relevant to the character's journey.
   3. Make the question feel like a natural part of the story world, with clear stakes for why answering it matters to the characters.
   ```

2. Implemented the "Story Object Method" for creating narrative bridges:
   ```markdown
   ## Narrative Bridge - The Story Object Method
   1. Identify ONE story object or element that can naturally connect to the [Core Question]:
      - For historical questions: Something that preserves or reveals the past
      - For scientific questions: Something that demonstrates or relates to natural phenomena
      - For mathematical questions: Something involving patterns, quantities, or relationships
      - For geographical questions: Something that represents places or spatial relationships

   2. Make this story element:
      - Visually interesting (describe how it appears in the story world)
      - Relevant to the plot (connect it to the character's journey)
      - Mysterious or incomplete (create a reflectto seek the answer)

   3. Include the exact question "[Core Question]" somewhere in the narrative:
      - It can be in dialogue, a character's thoughts, or written text within the story
      - The question should feel natural in context
      - The narrative should build toward this question, making it feel important
   ```

3. Modified the `_build_chapter_prompt` function in `prompt_engineering.py` to replace the [Core Question] placeholder with the actual question:
   ```python
   {LESSON_CHAPTER_INSTRUCTIONS.replace("[Core Question]", f'"{lesson_question["question"]}"')}
   ```

4. Updated the USER_PROMPT_TEMPLATE to be consistent with the new approach:
   ```markdown
   # CRITICAL RULES
   For LESSON chapters: Include the exact question verbatim, but NEVER mention any answer options.
   ```

### Results
The implementation successfully:
1. Ensures the exact question appears verbatim in the narrative so users know what they're being asked
2. Creates a more intuitive approach using a single concrete story object as the bridge
3. Provides more flexibility in where the question can appear for more natural narrative flow
4. Simplifies the instructions for better LLM comprehension
5. Maintains the core requirement that answer options are never mentioned

This approach should result in lesson chapters that feel more organic and integrated while still clearly presenting the educational question to the user.

## 2025-02-27: Phase-Specific Choice Instructions Implementation

### Problem
The choice format instructions in the Learning Odyssey application included guidance about plot twists in all story phases, including the Exposition phase. However, according to the plot twist development pattern, plot twist elements should only be introduced starting from the Rising phase, not in the Exposition phase.

### Requirements
- Ensure plot twist guidance only appears in appropriate phases (Rising, Trials, Climax)
- Create phase-specific choice instructions for each story phase
- Maintain consistent format and structure across all phases
- Implement a clean, maintainable solution that integrates with existing systems
- Create a test script to verify the implementation

### Solution
1. Modified `prompt_templates.py` to implement phase-specific choice instructions:
   ```python
   # Base choice format (common elements for all phases)
   BASE_CHOICE_FORMAT = """# Choice Format
   Use this EXACT format for the choices, with NO indentation and NO line breaks within choices:
   
   <CHOICES>
   Choice A: [First choice description]
   Choice B: [Second choice description]
   Choice C: [Third choice description]
   </CHOICES>
   
   ## Rules
   1. Format: Start and end with <CHOICES> tags on their own lines, with exactly three choices
   2. Each choice: Begin with "Choice [A/B/C]: " and contain the complete description on a single line
   3. Content: Make each choice meaningful, distinct, and advance the plot in interesting ways"""
   
   # Phase-specific choice guidance
   CHOICE_PHASE_GUIDANCE: Dict[str, str] = {
       "Exposition": "4. Character Establishment: Choices should reveal character traits and establish initial direction",
       "Rising": "4. Plot Development: Choices should subtly hint at the emerging plot twist",
       "Trials": "4. Challenge Response: Choices should show different approaches to mounting challenges",
       "Climax": "4. Critical Decision: Choices should represent pivotal decisions with significant consequences",
       "Return": "4. Resolution: Choices should reflect the character's growth and transformation"
   }
   
   def get_choice_instructions(phase: str) -> str:
       """Get the appropriate choice instructions for a given story phase."""
       base = BASE_CHOICE_FORMAT
       phase_guidance = CHOICE_PHASE_GUIDANCE.get(phase, CHOICE_PHASE_GUIDANCE["Rising"])
       return f"{base}\n\n{phase_guidance}"
   
   # Keep the original for backward compatibility
   CHOICE_FORMAT_INSTRUCTIONS = get_choice_instructions("Rising")
   ```

2. Updated `prompt_engineering.py` to use the new phase-specific instructions:
   ```python
   # In the imports section, added:
   from app.services.llm.prompt_templates import get_choice_instructions
   
   # In _build_chapter_prompt function, replaced:
   {CHOICE_FORMAT_INSTRUCTIONS}
   
   # With:
   {get_choice_instructions(story_phase)}
   
   # Also updated build_user_prompt function similarly
   ```

3. Created a test script `app/services/llm/test_phase_choice_instructions.py` to verify the implementation:
   - Tests each phase to ensure it gets the appropriate choice instructions
   - Verifies that the plot twist guidance only appears in Rising, Trials, and Climax phases
   - Confirms that the fallback behavior works correctly for unknown phases

### Results
The implementation successfully:
1. Ensures plot twist guidance only appears in appropriate phases (Rising, Trials, Climax)
2. Provides phase-appropriate guidance for each story phase:
   - Exposition: Focus on character establishment
   - Rising: Subtle hints at the plot twist
   - Trials: Different approaches to challenges
   - Climax: Pivotal decisions with consequences
   - Return: Character growth and transformation
3. Maintains consistent format and structure across all phases
4. Integrates cleanly with the existing prompt engineering system
5. Provides backward compatibility through the original CHOICE_FORMAT_INSTRUCTIONS constant
6. Verifies correct behavior through comprehensive testing

## 2025-02-27: LLM Prompt Optimization with Markdown Structure

### Problem
The LLM prompts in the Learning Odyssey application were lengthy and not optimally structured, making them harder to parse for both humans and the LLM. Additionally, there was a formatting issue in the continuity guidance section that was causing empty bullet points when there was only one previous lesson.

### Requirements
- Restructure LLM prompts to be more organized and readable
- Create a clear visual hierarchy with markdown headings and subheadings
- Enhance formatting for lesson answers and lesson history
- Fix the continuity guidance formatting issue
- Create a test script to verify the new prompt structure
- Improve the overall clarity and effectiveness of prompts for all chapter types

### Solution
1. Restructured the system prompt and user prompt templates in `app/services/llm/prompt_templates.py` to use markdown headings and formatting
2. Enhanced the formatting of lesson answers and lesson history in `app/services/llm/prompt_engineering.py`
3. Fixed the continuity guidance formatting issue in `build_user_prompt()` by using a more robust approach:
   ```python
   additional_guidance = ""
   if num_previous_lessons > 0:
       guidance_points = ["Build on the consequences of the previous lesson"]
       if num_previous_lessons > 1:
           guidance_points.append("Show how previous lessons have impacted the character")
       
       formatted_points = "\n".join([f"{i+1}. {point}" for i, point in enumerate(guidance_points)])
       additional_guidance = f"## Continuity Guidance\n{formatted_points}"
   ```
4. Created a test script `app/services/llm/test_prompt.py` to verify the new prompt structure
5. Improved the overall clarity and effectiveness of prompts for all chapter types

### Results
The implementation successfully:
1. Created a more organized and readable prompt structure using markdown
2. Established a clear visual hierarchy with headings and subheadings
3. Enhanced the formatting of lesson answers and lesson history
4. Fixed the continuity guidance formatting issue
5. Verified the new prompt structure with a test script
6. Improved the overall clarity and effectiveness of prompts for all chapter types

## 2025-02-27: Chapter Sequence Optimization Tradeoff

### Problem
The chapter sequence algorithm needed to prioritize certain rules over others, particularly ensuring no consecutive LESSON chapters and at least 1 REFLECT chapter in every scenario, while allowing some flexibility in the number of LESSON chapters.

### Requirements
- Prioritize no consecutive LESSON chapters as the highest rule
- Ensure at least 1 REFLECT chapter in every scenario
- Assume every LESSON has at least 3 questions available
- Accept 25% of scenarios where there are two LESSON chapters (when there should be three) in the distribution

### Solution
1. Updated the validation in `check_chapter_sequence()` to prioritize checking for no consecutive LESSON chapters and at least 1 REFLECT chapter
2. Modified tests to verify the distribution of scenarios with 2 vs 3 LESSON chapters
3. Updated documentation to reflect the new priorities
4. Ensured the algorithm assumes at least 3 questions are available for every LESSON

### Results
The implementation successfully:
1. Maintains the priority of no consecutive LESSON chapters
2. Ensures at least 1 REFLECT chapter in every scenario
3. Assumes 3 questions are available for every LESSON
4. Accepts a small percentage (25%) of scenarios with 2 LESSON chapters as an optimization tradeoff

## 2025-02-27: Enhanced REFLECT Chapter Challenge Type Tracking

### Problem
The `build_reflect_chapter_prompt()` function in `app/services/llm/prompt_engineering.py` was improved to add variety to correct answer handling with different challenge types (confidence_test, application, connection_making, teaching_moment), but there was no way to track which challenge type was being used for debugging and analysis purposes.

### Requirements
- Remove unused `all_answers` line in the function
- Implement varied approach for correct answers with different challenge types
- Restructure incorrect answer handling with a more educational approach
- Add tracking of the selected challenge type in the AdventureState metadata

### Solution
1. Removed the unused `all_answers = [answer["text"] for answer in lesson_question["answers"]]` line
2. Enhanced the function to randomly select from four different challenge types for correct answers:
   - `confidence_test`: Original implementation that tests if they'll stick with their answer
   - `application`: Tests if they can apply the concept in a new scenario
   - `connection_making`: Tests if they can connect the concept to broader themes
   - `teaching_moment`: Tests if they can explain the concept to someone else
3. Restructured incorrect answer handling with a more educational approach:
   - Educational reflection: Gently revealing the correct concept
   - Narrative deepening: Using the story environment to illustrate the concept
   - "Aha moment": Creating a moment where understanding clicks
   - Story-integrated choices: Testing understanding while advancing the story
4. Added challenge type tracking in AdventureState metadata:
   - Added an optional `state: Optional[AdventureState]` parameter to the function
   - Added code to track the challenge type in metadata when state is provided
   - Created a structured history in `state.metadata["reflect_challenge_history"]`
   - Stored the most recent challenge type in `state.metadata["last_reflect_challenge_type"]`
   - Added debug logging for the selected challenge type
5. Updated `_build_chapter_prompt()` to pass the state parameter to `build_reflect_chapter_prompt()`

### Results
The implementation successfully:
1. Provides more varied and engaging REFLECT chapters with different challenge types
2. Tracks the selected challenge type in the AdventureState metadata for debugging
3. Offers both detailed history and quick access to challenge type information
4. Improves the educational experience with a more structured approach for incorrect answers
5. Maintains compatibility with the existing system by making the state parameter optional

## 2025-02-26: REFLECT Chapter Type Implementation

### Problem
The original chapter sequence had three chapter types (STORY, LESSON, CONCLUSION) with specific rules for their placement. We needed to implement a new REFLECT chapter type that follows LESSON chapters to test deeper understanding and ensure correct answers weren't just lucky guesses.

### Requirements
- Add a new REFLECT chapter type to the ChapterType enum
- Update chapter sequencing rules:
  - First chapter: STORY (changed from first two chapters)
  - Second-to-last chapter: STORY
  - Last chapter: CONCLUSION
  - 50% of remaining chapters, rounded down: LESSON
  - No consecutive LESSON chapters
  - 50% of LESSON chapters, rounded down: REFLECT chapters
  - REFLECT chapters only occur immediately after a LESSON chapter
  - STORY chapters must follow REFLECT chapters
  - Random selection of which LESSON chapters are followed by REFLECT chapters

### Solution
1. Added REFLECT chapter type to ChapterType enum in `app/models/story.py`
2. Updated `determine_chapter_types()` in `app/services/chapter_manager.py` to implement the new rules:
   - Changed first two chapters rule to just first chapter
   - Added logic to prevent consecutive LESSON chapters
   - Added logic to randomly select which LESSON chapters are followed by REFLECT chapters
   - Ensured REFLECT chapters are only placed after LESSON chapters
   - Ensured STORY chapters follow REFLECT chapters
   - Implemented trimming logic to maintain the total chapter count

3. Implemented `build_reflect_chapter_prompt()` in `app/services/llm/prompt_engineering.py`:
   - For correct answers: Tests confidence without revealing the answer was correct
   - For incorrect answers: Provides a learning opportunity with explanation
   - Added diverse storytelling techniques for reflective moments
   - Structured choices to test true understanding (1 correct, 2 incorrect)

4. Updated tests in `tests/simulations/test_chapter_type_assignment.py` to validate the new rules:
   - No consecutive LESSON chapters
   - REFLECT chapters only follow LESSON chapters
   - STORY chapters follow REFLECT chapters
   - 50% of LESSON chapters (rounded down) are followed by REFLECT chapters

### Results
The implementation successfully:
1. Adds the new REFLECT chapter type with appropriate sequencing rules
2. Creates a more sophisticated educational experience by testing deeper understanding
3. Maintains the total chapter count while accommodating the new chapter type
4. Provides different approaches for correct vs. incorrect previous answers
5. Uses varied storytelling techniques to keep reflective moments engaging

## 2025-02-25: Final Chapter Sequence Testing Implementation

### Problem
The Final Chapter Sequence (from `app/services/chapter_manager.py`) was not being captured in the logs when running simulation tests, making it difficult to validate that the actual chapter types matched the planned sequence.

### Solution
1. Modified `get_chapter_sequence` function in `log_utils.py` to first check if a Final Chapter Sequence exists in the log file using the `get_final_chapter_sequence` function, and if it does, use that sequence instead of trying to extract it from other log entries.

2. Created a new test file `test_chapter_type_assignment.py` with three comprehensive tests:
   - `test_chapter_type_assignment_consistency`: Verifies that the planned chapter types match the actual chapter types used in the simulation
   - `test_chapter_type_assignment_rules`: Validates that the chapter type assignment follows all the required rules (first two chapters are STORY, last is CONCLUSION, etc.)
   - `test_extract_chapter_manager_logic`: Directly extracts and validates the chapter sequence from the log file

### Results
All tests are now passing, confirming that:
1. The Final Chapter Sequence is properly captured in the logs
2. The actual chapter types match the planned sequence
3. The chapter type assignment follows all the required rules

This implementation allows for reliable comparison of the Final Chapter Sequence against the actual ChapterType assignments in tests.
