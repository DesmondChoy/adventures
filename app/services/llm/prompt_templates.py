"""
Templates and constants for prompt engineering.

This module contains all text templates used in generating prompts for the
Learning Odyssey storytelling system. These templates are used by the
prompt_engineering.py module to construct complete prompts for different
chapter types and scenarios.
"""

import re
import random
from typing import Dict

# Choice format instructions
# --------------------------

# Base choice format (common elements for all phases)
BASE_CHOICE_FORMAT = """# Choice Format
Use this EXACT format for the choices, with NO indentation and NO line breaks within choices:

<CHOICES>
Choice A: [First choice description]
Choice B: [Second choice description]
Choice C: [Third choice description]
</CHOICES>

# CRITICAL RULES
1. Format: Start and end with <CHOICES> tags on their own lines, with exactly three choices
2. Each choice: Begin with "Choice [A/B/C]: " and contain the complete description on a single line
3. Content: Make each choice meaningful, distinct, and advance the plot in interesting ways"""

# Phase-specific choice guidance that aligns with existing phase guidance
CHOICE_PHASE_GUIDANCE: Dict[str, str] = {
    "Exposition": "4. Character Establishment: Choices should reveal character traits and establish initial direction",
    "Rising": "4. Plot Development: Choices should subtly hint at the emerging plot twist",
    "Trials": "4. Challenge Response: Choices should show different approaches to mounting challenges",
    "Climax": "4. Critical Decision: Choices should represent pivotal decisions with significant consequences",
    "Return": "4. Resolution: Choices should reflect the character's growth and transformation",
}


def get_choice_instructions(phase: str) -> str:
    """Get the appropriate choice instructions for a given story phase."""
    base = BASE_CHOICE_FORMAT
    phase_guidance = CHOICE_PHASE_GUIDANCE.get(phase, CHOICE_PHASE_GUIDANCE["Rising"])
    return f"{base}\n\n{phase_guidance}"


REFLECT_CHOICE_FORMAT = """# Choice Format
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
5. Character Growth: Each choice should reflect a different way the character might process or apply what they've learned"""

# Agency choice categories
# -----------------------

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


def get_random_agency_category() -> str:
    """Randomly select one agency category from the available options."""
    # Extract individual categories from the AGENCY_CHOICE_CATEGORIES string
    categories_text = AGENCY_CHOICE_CATEGORIES.split("# Agency Choice Categories")[1]

    # Split by section headers and clean up
    sections = re.findall(r"## ([^\n]+)\n((?:- [^\n]+\n)+)", categories_text)

    # Select one random category
    category_name, category_items = random.choice(sections)

    # Format the selected category
    items_list = re.findall(r"- ([^\n]+)", category_items)
    formatted_items = "\n".join([f"- {item}" for item in items_list])

    return f"""# Agency Choice: {category_name}
Choose one of these options to offer the character:
{formatted_items}

Make this choice feel meaningful and consequential. The character's selection will influence their journey throughout the adventure."""


# First chapter agency instructions
# -------------------------------

FIRST_CHAPTER_AGENCY_INSTRUCTIONS = """# First Chapter Agency
Include a meaningful choice that provides agency through one of the options above.

## Requirements
- Present three distinct options that reflect different approaches or values
- Describe how this choice might influence their journey
- Make the options fit naturally within the story world
- End the chapter at this decision point

This choice is pivotal and will impact the character throughout their journey."""


# Storytelling techniques
# ----------------------

REFLECTIVE_TECHNIQUES = """# Reflective Techniques
Create a reflective moment using one of these storytelling techniques:
- A vivid dream or vision that symbolically represents the concept
- A conversation with a wise mentor, guide, or symbolic character
- A magical environment that transforms to represent understanding
- A memory palace or special location that appears for reflection
- An object (mirror, book, crystal) that reveals deeper truths
- A flashback that gains new meaning with current knowledge
- Heightened senses that reveal previously hidden aspects of reality
- A parallel storyline that converges to provide insight"""

# Phase guidance
# -------------

BASE_PHASE_GUIDANCE: Dict[str, str] = {
    "Exposition": (
        "# Phase Guidance: Exposition\n"
        "- **Focus**: Introduction, setting the scene, establishing the character's ordinary world\n"
        "- **Narrative Goals**: Introduce the main character, the setting, and the initial situation\n"
        "- **Emotional Tone**: Intriguing, inviting, a sense of normalcy that will soon be disrupted\n"
        "- **Sensory Integration**: Establish the world through vivid sensory details"
    ),
    "Rising": (
        "# Phase Guidance: Rising Action\n"
        "- **Focus**: Character begins their journey, facing initial challenges\n"
        "- **Narrative Goals**: Develop the plot and introduce early obstacles\n"
        "- **Emotional Tone**: Excitement, anticipation, building momentum\n"
        "- **Sensory Integration**: Use sensory details to highlight new experiences"
    ),
    "Trials": (
        "# Phase Guidance: Trials\n"
        "- **Focus**: Character faces significant challenges and setbacks\n"
        "- **Narrative Goals**: Test resolve, increase stakes, deepen learning\n"
        "- **Emotional Tone**: Tension, determination, growing uncertainty\n"
        "- **Sensory Integration**: Intensify sensory details during key moments"
    ),
    "Climax": (
        "# Phase Guidance: Climax\n"
        "- **Focus**: Character confronts the main conflict and revelations\n"
        "- **Narrative Goals**: Deliver exciting resolution and transformation\n"
        "- **Emotional Tone**: Intense excitement, high stakes, breakthrough moments\n"
        "- **Sensory Integration**: Peak sensory experience during crucial scenes"
    ),
    "Return": (
        "# Phase Guidance: Return\n"
        "- **Focus**: Character integrates their experiences and growth\n"
        "- **Narrative Goals**: Show transformation and provide closure\n"
        "- **Emotional Tone**: Reflective, peaceful, sense of completion\n"
        "- **Sensory Integration**: Use sensory details to highlight the character's new perspective"
    ),
}

PLOT_TWIST_GUIDANCE: Dict[str, str] = {
    "Rising": (
        "## Plot Twist Development\n"
        "- Subtly introduce elements that hint at: {plot_twist}\n"
        "- Plant small, seemingly insignificant details that will become important\n"
        "- Keep the hints subtle and in the background"
    ),
    "Trials": (
        "## Plot Twist Development\n"
        "- Build tension around the emerging plot twist: {plot_twist}\n"
        "- Make the hints more noticeable but still mysterious\n"
        "- Connect previously planted details to current events"
    ),
    "Climax": (
        "## Plot Twist Development\n"
        "- Bring the plot twist to its full revelation: {plot_twist}\n"
        "- Connect all the previously planted hints\n"
        "- Show how this revelation changes everything"
    ),
}

# Chapter-specific instructions
# ----------------------------

LESSON_CHAPTER_INSTRUCTIONS = """# Lesson Chapter Instructions
Create a narrative moment where the question emerges through:
- Character's internal thoughts or observations
- Natural dialogue between characters
- A challenge or obstacle that needs to be overcome
- An important decision that needs to be made

# CRITICAL RULES
1. NEVER mention any answer options in your narrative, but DO include the exact question "[Core Question]" verbatim somewhere in the story.
2. Create ONE visually interesting story object (artifact, phenomenon, pattern, or map) that naturally connects to the question and makes it relevant to the character's journey.
3. Make the question feel like a natural part of the story world, with clear stakes for why answering it matters to the characters.

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

## Key Requirements
1. The question should feel like a natural part of the character's journey, not an artificial insert
2. Ensure the context makes it clear why answering this question matters to the story
3. End at a moment that makes the user want to engage with the question
4. The system will handle the formal presentation of the question separately

**Remember**: Make the question feel like an organic part of the character's journey rather than an educational insert."""

STORY_CHAPTER_INSTRUCTIONS = """# Story Chapter Instructions
Continue the story by:
1. Following directly from the previous chapter content
2. Taking into account the previous choices made in the story
3. Creating meaningful consequences for these decisions
4. Focusing on character development and plot progression

# CRITICAL RULES
1. Build towards a natural story decision point
2. The story choices will be provided separately - do not list them in the narrative
3. End the scene at a moment of decision"""

CONCLUSION_CHAPTER_INSTRUCTIONS = """# Conclusion Chapter Instructions
Write the conclusion of the story by:
1. Following directly from the pivotal choice made in the previous chapter
2. Resolving all remaining plot threads and character arcs
3. Showing how the character's journey and choices have led to this moment
4. Providing a satisfying ending that reflects the consequences of their decisions
5. Incorporating the wisdom gained from their educational journey

# CRITICAL RULES
1. This is the final chapter - provide a complete and satisfying resolution
2. DO NOT include any choices or decision points
3. End with a sense of closure while highlighting the character's transformation"""

# Consequences guidance templates
# ------------------------------

CORRECT_ANSWER_CONSEQUENCES = """## Correct Answer Consequences
The story should:
- Acknowledge that the character correctly identified {correct_answer} as the answer
- Show how this understanding of {question} connects to their current situation
- Use this success to build confidence for future challenges"""

INCORRECT_ANSWER_CONSEQUENCES = """## Incorrect Answer Consequences
The story should:
- Acknowledge that the character answered {chosen_answer}
- Explain that {correct_answer} was the correct answer
- Show how this misunderstanding of {question} leads to a valuable learning moment
- Use this as an opportunity for growth and deeper understanding
- Connect the correction to their current situation and future challenges"""

# REFLECT templates
# ----------------

# Unified template for both correct and incorrect answers
REFLECT_TEMPLATE = """# Narrative-Driven Reflection
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

{agency_guidance}

## Choice Structure
Create three story-driven choices that:
- Feel like natural next steps in the narrative
- Reflect different ways to process what was learned
- Lead to different but equally valid story paths
- Advance the plot in meaningful ways

Each choice should set up clear narrative consequences for the next chapter without any being labeled as "correct" or "incorrect".

{reflect_choice_format}"""

# Agency guidance templates for REFLECT chapters
# ---------------------------------------------

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
# ------------------------------

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

# Prompt templates
# ---------------

USER_PROMPT_TEMPLATE = """# Current Context
- Chapter: {chapter_number} of {story_length}
- Type: {chapter_type}
- Phase: {story_phase}
- Progress: {correct_lessons}/{total_lessons} lessons correct

# CRITICAL RULES
For LESSON chapters: Include the exact question verbatim, but NEVER mention any answer options.

# Story History
{story_history}

{phase_guidance}

{chapter_instructions}

{additional_guidance}
"""

# System prompt template
# ---------------------

SYSTEM_PROMPT_TEMPLATE = """# Storyteller Role
You are a master storyteller crafting an interactive educational story that seamlessly blends narrative and learning.

# Story Elements
- **Setting**: {setting_types}
- **Character**: {character_archetypes}
- **Rule**: {story_rules}
- **Theme**: {selected_theme}
- **Moral Teaching**: {selected_moral_teaching}
- **Sensory Details**:
  - Visual: {visuals}
  - Sound: {sounds}
  - Scent: {smells}

# Storytelling Approach
1. Maintain narrative consistency and create meaningful consequences for user decisions
2. Seamlessly integrate lesson elements and develop theme/moral teaching organically
3. Structure content with multiple paragraphs and blank lines for readability
4. Incorporate sensory details naturally to enhance immersion
5. Apply markdown formatting judiciously: use **bold** for critical revelations or important realizations, and *italics* for character thoughts or emotional emphasis

# Agency Continuity
The character makes a pivotal choice in the first chapter (crafting an item, choosing a companion, selecting a role, or developing a special ability). This choice:

1. Represents a core aspect of the character's identity and approach
2. Must be referenced consistently throughout ALL chapters of the adventure
3. Should evolve and develop as the character learns and grows
4. Will play a crucial role in the climax of the story
5. Should feel like a natural part of the narrative, not an artificial element

Each chapter should include at least one meaningful reference to or use of this agency element, with its significance growing throughout the journey.

# CRITICAL RULES
1. Structure and flow: begin narrative directly (never with "Chapter X"), end at natural decision points, maintain consistent narrative elements
2. Content development: incorporate sensory details naturally, develop theme and moral teaching organically
3. Educational integration: balance entertainment with learning, ensure lessons feel organic to the story
4. Agency integration: weave the character's agency choice naturally throughout the story, showing its evolution and impact"""
