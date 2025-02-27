"""
Templates and constants for prompt engineering.

This module contains all text templates used in generating prompts for the
Learning Odyssey storytelling system. These templates are used by the
prompt_engineering.py module to construct complete prompts for different
chapter types and scenarios.
"""

from typing import Dict

# Choice format instructions
# --------------------------

CHOICE_FORMAT_INSTRUCTIONS = """# Choice Format
Use this EXACT format for the choices, with NO indentation and NO line breaks within choices:

<CHOICES>
Choice A: [First choice description]
Choice B: [Second choice description]
Choice C: [Third choice description]
</CHOICES>

## Rules
1. Format: Start and end with <CHOICES> tags on their own lines, with exactly three choices
2. Each choice: Begin with "Choice [A/B/C]: " and contain the complete description on a single line
3. Content: Make each choice meaningful, distinct, and advance the plot in interesting ways
4. Plot Twist: Choices should relate to the unfolding plot twist, from subtle hints to direct connections as the story progresses"""

REASON_CHOICE_FORMAT = """# Choice Format
Use this EXACT format for the choices, with NO indentation and NO line breaks within choices:

<CHOICES>
Choice A: [First option - make this the correct answer]
Choice B: [Second option - make this incorrect]
Choice C: [Third option - make this incorrect]
</CHOICES>

## Rules
1. Format: Start and end with <CHOICES> tags on their own lines, with exactly three choices
2. Each choice: Begin with "Choice [A/B/C]: " and contain the complete description on a single line
3. Content: One choice must be correct, the other choices should be plausible but incorrect"""

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

## Important Guidelines
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

## Important Guidelines
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

# Reason challenge templates
# -------------------------

REASON_CHALLENGE_TEMPLATES: Dict[str, str] = {
    "confidence_test": """# Confidence Test Challenge
The character has answered "{chosen_answer}" to the question: "{question}"
Now, we need to test if they truly understand the concept or if it was just a lucky guess.

{reflective_techniques}

## Scene Structure
1. DO NOT reveal whether their answer was correct or incorrect
2. Present a scenario where the character is challenged to reconsider their answer
3. Make the incorrect alternatives sound compelling and plausible
4. Test their confidence and understanding by seeing if they'll stick with their answer

Present a follow-up scenario that makes the character question their original answer.
Frame it as: "Are you sure about your answer? Consider these alternatives..."

## Choice Structure
- Choice A: Stick with the original answer ("{chosen_answer}") - this is the correct choice
- Choice B: Switch to a different answer that sounds convincing but is incorrect
- Choice C: Switch to another different answer that sounds convincing but is incorrect

For choices B and C, use these incorrect answers as inspiration but make them sound very plausible:
{incorrect_answers}

{reason_choice_format}""",
    "application": """# Application Challenge
The character has answered "{chosen_answer}" to the question: "{question}"
Now, we need to see if they can apply this concept in a different context.

{reflective_techniques}

## Scene Structure
1. DO NOT reveal whether their previous answer was correct or incorrect
2. Present a new scenario that tests the same concept but in a different context
3. The correct answer should apply the same reasoning as their original answer
4. Make the incorrect alternatives sound compelling and plausible

Present a new scenario that applies the same concept in a different way.
Frame it as: "Now let's see if you can apply this knowledge to a new situation..."

## Choice Structure
- Choice A: The answer that correctly applies the same concept (correct)
- Choice B: An answer that misapplies the concept in a plausible way (incorrect)
- Choice C: Another answer that misapplies the concept differently (incorrect)

{reason_choice_format}""",
    "connection_making": """# Connection-Making Challenge
The character has answered "{chosen_answer}" to the question: "{question}"
Now, let's explore how this concept connects to broader themes and ideas.

{reflective_techniques}

## Scene Structure
1. DO NOT reveal whether their previous answer was correct or incorrect
2. Present a moment where the character can connect this concept to the story's broader theme
3. Focus on how this knowledge relates to the moral teaching or theme of the adventure
4. Create choices that test their ability to make meaningful connections

Present a reflective moment that invites deeper connections.
Frame it as: "How does this knowledge connect to the bigger picture?"

## Choice Structure
- Choice A: The connection that correctly relates the concept to the broader theme (correct)
- Choice B: A connection that misunderstands either the concept or the theme (incorrect)
- Choice C: A connection that seems logical but misses the deeper significance (incorrect)

{reason_choice_format}""",
    "teaching_moment": """# Teaching Moment Challenge
The character has answered "{chosen_answer}" to the question: "{question}"
Now, let's see if they can explain this concept to someone else.

{reflective_techniques}

## Scene Structure
1. DO NOT reveal whether their previous answer was correct or incorrect
2. Create a situation where another character needs help understanding this concept
3. The main character must choose how to explain it
4. This tests if they truly understand the concept well enough to teach it

Present a teaching moment where another character asks for help.
Frame it as: "How would you explain this to someone who doesn't understand?"

## Choice Structure
- Choice A: An explanation that correctly conveys the concept (correct)
- Choice B: An explanation that contains a subtle but important misconception (incorrect)
- Choice C: An explanation that completely misunderstands the concept (incorrect)

{reason_choice_format}""",
}

INCORRECT_ANSWER_TEMPLATE = """# Incorrect Answer Learning Opportunity
The character answered "{chosen_answer}" to the question: "{question}"
The correct answer was "{correct_answer}".

## Scene Structure
Create a reflective scene with this structure:

1. **EDUCATIONAL REFLECTION**: Gently reveal the correct concept and why their answer wasn't right.

2. **NARRATIVE DEEPENING**: Use the story environment to illustrate the concept through metaphor or direct experience.

3. **"AHA MOMENT"**: Create a moment where understanding clicks for the character, changing their perspective.

4. **STORY-INTEGRATED CHOICES**: Present a situation requiring application of this new knowledge.

{reflective_techniques}

## Choice Structure
The choices must both test understanding AND advance the story:
- Choice A: Apply the newly learned concept correctly (correct)
- Choice B: Show incomplete understanding (incorrect)
- Choice C: Fall back to the original misconception (incorrect)

Each choice should set up clear narrative consequences for the next chapter.

{reason_choice_format}"""

# Prompt templates
# ---------------

USER_PROMPT_TEMPLATE = """# Current Context
- Chapter: {chapter_number} of {story_length}
- Type: {chapter_type}
- Phase: {story_phase}
- Progress: {correct_lessons}/{total_lessons} lessons correct

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
1. Maintain narrative consistency with previous choices
2. Create meaningful consequences for user decisions
3. Seamlessly integrate lesson elements when provided
4. Use multiple paragraphs separated by blank lines for readability
5. Incorporate sensory details naturally to enhance immersion
6. Develop the theme and moral teaching organically through the narrative

# Critical Rules
1. Never start with "Chapter X" - begin narrative directly
2. End at a natural decision point
3. Incorporate sensory details naturally
4. Develop theme and moral teaching organically
5. Maintain consistent narrative elements"""
