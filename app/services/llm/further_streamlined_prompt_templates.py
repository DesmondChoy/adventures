"""
Further streamlined templates for prompt engineering.

This module contains even more streamlined text templates for the Learning Odyssey
storytelling system, with additional optimizations to reduce redundancy and improve
clarity beyond the initial streamlining.
"""

import re
import random
from typing import Dict

# Further Streamlined System Prompt Template
# -----------------------------------------

FURTHER_STREAMLINED_SYSTEM_PROMPT = """# Storyteller Role
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
5. **Choice Format**: Use <CHOICES> tags, format as "Choice [A/B/C]: [description]" on single lines, make choices meaningful and distinct"""

# Further Streamlined User Prompt Template for First Chapter
# ---------------------------------------------------------

FURTHER_STREAMLINED_FIRST_CHAPTER_PROMPT = """# Current Context
- Chapter: {chapter_number} of {story_length}
- Type: {chapter_type}
- Phase: {story_phase}
- Progress: {correct_lessons}/{total_lessons} lessons correct

# Story History
{story_history}

# Chapter Development Guidelines
1. **Exposition Focus**: {exposition_focus}
2. **Character Introduction**: Establish the protagonist through vivid sensory details
3. **World Building**: Create an immersive setting using the sensory elements
4. **Decision Point**: Build naturally to a pivotal choice that will shape the character's journey

# Agency Options: {agency_category_name}
{agency_options}

# Choice Format Specification
<CHOICES>
Choice A: [Option that reveals character traits and establishes initial direction]
Choice B: [Option that offers a different approach or value system]
Choice C: [Option that presents an alternative path with unique consequences]
</CHOICES>"""

# Agency category extraction function with more concise formatting
# ---------------------------------------------------------------


def get_further_streamlined_agency_category() -> tuple[str, str]:
    """Randomly select one agency category and return its name and formatted options."""
    # Categories with their options (more concise descriptions)
    categories = {
        "Magical Items to Craft": [
            "Luminous Lantern - reveals hidden truths and illuminates dark places",
            "Sturdy Rope - overcomes physical obstacles and bridges gaps",
            "Mystical Amulet - enhances intuition and provides subtle guidance",
            "Weathered Map - reveals new paths and hidden locations",
            "Pocket Watch - helps with timing and glimpses possible futures",
            "Healing Potion - restores strength and provides clarity of mind",
        ],
        "Companions to Choose": [
            "Wise Owl - offers knowledge and explanations",
            "Brave Fox - excels in courage and action-oriented tasks",
            "Clever Squirrel - skilled in problem-solving and improvisation",
            "Gentle Deer - provides emotional support and peaceful solutions",
            "Playful Otter - brings joy and finds unexpected approaches",
            "Steadfast Turtle - offers patience and protection in difficult times",
        ],
        "Roles or Professions": [
            "Healer - mends wounds and restores balance",
            "Scholar - values knowledge and understanding",
            "Guardian - protects others and stands against threats",
            "Pathfinder - discovers new routes and possibilities",
            "Diplomat - resolves conflicts through communication",
            "Craftsperson - builds and creates solutions",
        ],
        "Special Abilities": [
            "Animal Whisperer - communicates with creatures",
            "Puzzle Master - excels at solving riddles and mysteries",
            "Storyteller - charms others with words and narratives",
            "Element Bender - connects with natural forces",
            "Dream Walker - glimpses insights through dreams",
            "Pattern Seer - notices connections others miss",
        ],
    }

    # Select a random category
    category_name = random.choice(list(categories.keys()))

    # Get and shuffle the options for this category
    options = categories[category_name]
    random.shuffle(options)

    # Format the options more concisely
    formatted_options = "\n".join([f"- {option}" for option in options])

    return category_name, formatted_options


# Phase-specific exposition focus
# ------------------------------

EXPOSITION_FOCUS = {
    "Exposition": "Introduce the ordinary world and establish normalcy that will soon be disrupted",
    "Rising": "Show the character's first steps into a changing world with new challenges",
    "Trials": "Present mounting challenges that test the character's resolve",
    "Climax": "Build tension toward a critical moment of truth and transformation",
    "Return": "Reflect on growth and transformation as the journey nears completion",
}


def get_exposition_focus(phase: str) -> str:
    """Get the appropriate exposition focus for the given story phase."""
    return EXPOSITION_FOCUS.get(phase, EXPOSITION_FOCUS["Exposition"])
