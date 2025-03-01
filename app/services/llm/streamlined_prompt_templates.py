"""
Streamlined templates for prompt engineering.

This module contains streamlined text templates used in generating prompts for the
Learning Odyssey storytelling system. These templates reduce redundancy and improve
clarity by consolidating critical rules and agency instructions.
"""

import re
import random
from typing import Dict

# Streamlined System Prompt Template
# ---------------------------------

STREAMLINED_SYSTEM_PROMPT = """# Storyteller Role
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

# Storytelling Approach & Agency Integration
1. Maintain narrative consistency with meaningful consequences for decisions
2. Seamlessly integrate educational content while developing theme/moral teaching organically
3. Structure content with multiple paragraphs and blank lines for readability
4. Incorporate sensory details naturally to enhance immersion
5. The character's pivotal first-chapter choice (item, companion, role, or ability):
   - Represents a core aspect of their identity
   - Must be referenced consistently throughout ALL chapters
   - Should evolve as the character learns and grows
   - Will play a crucial role in the story's climax
   - Should feel like a natural part of the narrative

# CRITICAL RULES
1. **Narrative Structure**: Begin directly (never with "Chapter X"), end at natural decision points, maintain consistent elements
2. **Content Development**: Incorporate sensory details naturally, develop theme organically, balance entertainment with learning
3. **Educational Integration**: Ensure lessons feel organic to the story, never forced or artificial
4. **Agency Integration**: Weave the character's pivotal choice naturally throughout, showing its evolution and impact
5. **Format Requirements**: Follow exact choice format instructions, never list choices within narrative text"""

# Streamlined User Prompt Template for First Chapter
# ------------------------------------------------

STREAMLINED_FIRST_CHAPTER_PROMPT = """# Current Context
- Chapter: {chapter_number} of {story_length}
- Type: {chapter_type}
- Phase: {story_phase}
- Progress: {correct_lessons}/{total_lessons} lessons correct

# Story History
{story_history}

{phase_guidance}

# Story Chapter Instructions
1. Establish the character's ordinary world through vivid sensory details
2. Introduce the main character and initial situation
3. Build towards a natural story decision point
4. End the scene at a moment of decision

# Agency Choice & Critical Requirements
The character must make a pivotal choice that will influence their entire journey:

## {agency_category_name}
{agency_options}

## Implementation Requirements
- Present distinct options that reflect different approaches or values
- Describe how these choices might influence the character's journey
- Make the options fit naturally within the story world
- End the chapter at this decision point

## Format Requirements
Use this EXACT format for the choices, with NO indentation and NO line breaks within choices:

<CHOICES>
Choice A: [First choice description]
Choice B: [Second choice description]
Choice C: [Third choice description]
</CHOICES>

## CRITICAL RULES
1. Format: Start and end with <CHOICES> tags on their own lines
2. Each choice: Begin with "Choice [A/B/C]: " and contain the complete description on a single line
3. Content: Make each choice meaningful, distinct, and advance the plot in interesting ways
4. Character Establishment: Choices should reveal character traits and establish initial direction"""

# Agency category extraction function
# ---------------------------------


def get_streamlined_agency_category() -> tuple[str, str]:
    """Randomly select one agency category and return its name and formatted options."""
    # Categories with their options
    categories = {
        "Magical Items to Craft": [
            "A Luminous Lantern that reveals hidden truths and illuminates dark places",
            "A Sturdy Rope that helps overcome physical obstacles and bridges gaps",
            "A Mystical Amulet that enhances intuition and provides subtle guidance",
            "A Weathered Map that reveals new paths and hidden locations",
            "A Pocket Watch that helps with timing and occasionally glimpses the future",
            "A Healing Potion that restores strength and provides clarity of mind",
        ],
        "Companions to Choose": [
            "A Wise Owl that offers knowledge and explanations",
            "A Brave Fox that excels in courage and action-oriented tasks",
            "A Clever Squirrel that's skilled in problem-solving and improvisation",
            "A Gentle Deer that provides emotional support and finds peaceful solutions",
            "A Playful Otter that brings joy and finds unexpected approaches",
            "A Steadfast Turtle that offers patience and protection in difficult times",
        ],
        "Roles or Professions": [
            "A Healer who can mend wounds and restore balance",
            "A Scholar who values knowledge and understanding",
            "A Guardian who protects others and stands against threats",
            "A Pathfinder who discovers new routes and possibilities",
            "A Diplomat who resolves conflicts through communication",
            "A Craftsperson who builds and creates solutions",
        ],
        "Special Abilities": [
            "Animal Whisperer who can communicate with creatures",
            "Puzzle Master who excels at solving riddles and mysteries",
            "Storyteller who charms others with words and narratives",
            "Element Bender who has a special connection to natural forces",
            "Dream Walker who can glimpse insights through dreams",
            "Pattern Seer who notices connections others miss",
        ],
    }

    # Select a random category
    category_name = random.choice(list(categories.keys()))

    # Get and shuffle the options for this category
    options = categories[category_name]
    random.shuffle(options)

    # Format the options
    formatted_options = "\n".join([f"- {option}" for option in options])

    return category_name, formatted_options
