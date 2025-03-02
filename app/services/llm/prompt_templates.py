"""
Templates and constants for prompt engineering.

This module contains all text templates used in generating prompts for the
Learning Odyssey storytelling system. These templates are used by the
prompt_engineering.py module to construct complete prompts for different
chapter types and scenarios.
"""

import re
import random
from typing import Dict, Tuple

# System Prompt Template
# ---------------------

SYSTEM_PROMPT_TEMPLATE = """# Storyteller Role
You are a master storyteller crafting an interactive educational story that seamlessly blends narrative and learning.

# Story Elements
- Setting: {setting_types}
- Character: {character_archetypes}
- Rule: {story_rules}
- Theme: {selected_theme}
- Moral Teaching: {selected_moral_teaching}
- Sensory Details:
  - Visual: {visuals}
  - Sound: {sounds}
  - Scent: {smells}

# Storytelling Approach & Agency Integration
1. Maintain narrative consistency with meaningful consequences for decisions
2. Seamlessly integrate educational content while developing theme/moral teaching organically
3. Format responses with clear paragraph breaks and utilize Markdown syntax judiciously
4. Incorporate sensory details naturally to enhance immersion
5. The character's pivotal first-chapter choice (item, companion, role, or ability):
   - Represents a core aspect of their identity
   - Must be referenced consistently throughout ALL chapters
   - Should evolve as the character learns and grows
   - Will play a crucial role in the story's climax
   - Should feel like a natural part of the narrative

# CRITICAL RULES
1. Narrative Structure: Begin directly (never with "Chapter X"), end at natural decision points, maintain consistent elements
2. Content Development: Incorporate sensory details naturally, develop theme organically, balance entertainment with learning
3. Educational Integration: Ensure lessons feel organic to the story, never forced or artificial
4. Agency Integration: Weave the character's pivotal choice naturally throughout, showing its evolution and impact
5. Choice Format: Use <CHOICES> tags, format as "Choice [A/B/C]: [description]" on single lines, make choices meaningful and distinct"""

# User Prompt Templates
# --------------------

# First Chapter Prompt Template
FIRST_CHAPTER_PROMPT = """# Current Context
- Chapter: {chapter_number} of {story_length}
- Type: {chapter_type}
- Phase: {story_phase}
- Progress: {correct_lessons}/{total_lessons} lessons correct

# Story History
{story_history}

# Chapter Development Guidelines
1. Character Introduction: Establish the protagonist through vivid sensory details
2. World Building: Create an immersive setting using the sensory elements
3. Decision Point: Build naturally to a pivotal choice that will shape the character's journey

# Agency Options: {agency_category_name}
{agency_options}

# Choice Format Specification
<CHOICES>
Choice A: [Select one of the {agency_category_name} options above and incorporate it into a meaningful choice]
Choice B: [Select a different {agency_category_name} option from above and incorporate it into a meaningful choice]
Choice C: [Select a third {agency_category_name} option from above and incorporate it into a meaningful choice]
</CHOICES>

Each choice MUST directly correspond to one of the specific {agency_category_name} options listed above. Do not create generic choices - each choice should clearly reference one of the provided agency options."""

# Story Chapter Prompt Template
STORY_CHAPTER_PROMPT = """# Current Context
- Chapter: {chapter_number} of {story_length}
- Type: {chapter_type}
- Phase: {story_phase}
- Progress: {correct_lessons}/{total_lessons} lessons correct

# Story History
{story_history}

# Chapter Development Guidelines
1. Previous Impact: {consequences_guidance}
{lesson_history}
{agency_guidance}

# Story Chapter Instructions
1. Follow directly from the previous chapter content
2. Take into account previous choices made in the story
3. Create meaningful consequences for these decisions
4. Focus on character development and plot progression
5. Build towards a natural story decision point
6. End the scene at a moment of decision

{plot_twist_guidance}

# Choice Format Specification
<CHOICES>
Choice A: [First meaningful option]
Choice B: [Second meaningful option]
Choice C: [Third meaningful option]
</CHOICES>"""

# Lesson Chapter Prompt Template
LESSON_CHAPTER_PROMPT = """# Current Context
- Chapter: {chapter_number} of {story_length}
- Type: {chapter_type}
- Phase: {story_phase}
- Progress: {correct_lessons}/{total_lessons} lessons correct

# Story History
{story_history}

# Chapter Development Guidelines
1. Previous Impact: {consequences_guidance}
{lesson_history}
{agency_guidance}

# Lesson Chapter Instructions
1. Core Question Integration: Include this exact question in your narrative: "{question}"
2. Story Object Method: Create ONE visually interesting element that naturally connects to the question
3. Narrative Integration: Make the question feel like a natural part of the character's journey
4. Educational Context: Establish clear stakes for why answering matters to the characters

# Available Answers
{formatted_answers}


DO NOT:
- Mention/Reference any of the available answers in the narrative
- Include any choices or <CHOICES> tags in LESSON chapters. The options above are provided for information only and will be handled by the application."""

# Reflect Chapter Prompt Template
REFLECT_CHAPTER_PROMPT = """# Current Context
- Chapter: {chapter_number} of {story_length}
- Type: {chapter_type}
- Phase: {story_phase}
- Progress: {correct_lessons}/{total_lessons} lessons correct

# Story History
{story_history}

# Chapter Development Guidelines
1. Reflection Purpose: Process the previous lesson's understanding

# Narrative-Driven Reflection
The character previously answered: "{question}" with "{chosen_answer}" ({answer_status})
{correct_answer_info}

{reflective_technique}

## Scene Structure
1. Narrative Acknowledgment: {acknowledgment_guidance}
2. Socratic Exploration: Guide the character to {exploration_goal} through thoughtful questions
3. Story Integration: Connect this reflection to the ongoing narrative and theme of "{theme}"
{agency_guidance}

## Choice Structure
Create three story-driven choices that reflect different ways to process what was learned.
Each choice should advance the plot in meaningful ways without being labeled as "correct" or "incorrect".

# Choice Format Specification
<CHOICES>
Choice A: [First story-driven choice]
Choice B: [Second story-driven choice]
Choice C: [Third story-driven choice]
</CHOICES>

# CRITICAL RULES
1. Format: Start and end with <CHOICES> tags on their own lines
2. Each choice: Begin with "Choice [A/B/C]: " and contain the complete description on a single line
3. Content: Make each choice meaningful, distinct, and advance the story in different ways
4. Narrative Focus: All choices should be story-driven without any being labeled as "correct" or "incorrect"
5. Character Growth: Each choice should reflect a different way the character might process or apply what they've learned"""

# Conclusion Chapter Prompt Template
CONCLUSION_CHAPTER_PROMPT = """# Current Context
- Chapter: {chapter_number} of {story_length}
- Type: {chapter_type}
- Phase: {story_phase}
- Progress: {correct_lessons}/{total_lessons} lessons correct

# Story History
{story_history}

# Chapter Development Guidelines
1. Conclusion Purpose: Provide a satisfying resolution to the journey
{lesson_history}

# Conclusion Chapter Instructions
1. Resolution Focus: Provide a complete and satisfying resolution to all plot threads
2. Character Growth: Show how the journey and choices have transformed the character
3. Educational Integration: Incorporate wisdom gained from the educational journey
4. Agency Resolution: {agency_resolution_guidance}

# CRITICAL RULES
1. This is the final chapter - provide a complete and satisfying conclusion
2. DO NOT include any choices or decision points
3. End with a sense of closure while highlighting transformation"""

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
1. Format: Start and end with <CHOICES> tags on their own lines
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


# Reflect choice format
REFLECT_CHOICE_FORMAT = """# Choice Format
Use this EXACT format for the choices, with NO indentation and NO line breaks within choices:

<CHOICES>
Choice A: [First story-driven choice]
Choice B: [Second story-driven choice]
Choice C: [Third story-driven choice]
</CHOICES>

# CRITICAL RULES
1. Format: Start and end with <CHOICES> tags on their own lines
2. Each choice: Begin with "Choice [A/B/C]: " and contain the complete description on a single line
3. Content: Make each choice meaningful, distinct, and advance the story in different ways
4. Narrative Focus: All choices should be story-driven without any being labeled as "correct" or "incorrect"
5. Character Growth: Each choice should reflect a different way the character might process or apply what they've learned"""

# Agency choice categories
# -----------------------


def get_agency_category() -> Tuple[str, str]:
    """Randomly select one agency category and return its name and formatted options."""
    # Categories with options formatted as "Name - Description [Visual details for image generation]"
    # The square brackets won't be shown to users but will be used for image generation
    categories = {
        "Magical Items to Craft": [
            "Luminous Lantern - reveals hidden truths and illuminates dark places [golden light with intricate celestial patterns]",
            "Sturdy Rope - overcomes physical obstacles and bridges gaps [enchanted with glowing runes that shift and pulse]",
            "Mystical Amulet - enhances intuition and provides subtle guidance [swirling gemstone that changes color with intuition]",
            "Weathered Map - reveals new paths and hidden locations [with moving ink and shimmering locations]",
            "Pocket Watch - helps with timing and glimpses possible futures [with constellation dial and glowing hands]",
            "Healing Potion - restores strength and provides clarity of mind [crystal vial with swirling iridescent liquid]",
            "Singing Bells - creates harmonious music that soothes troubled hearts [cluster of colorful crystal bells that glow and float in mid-air]",
            "Transforming Clay - shapes into whatever you imagine [rainbow-colored clay that shimmers when touched and leaves stardust trails]",
            "Invisibility Cloak - makes the wearer blend into surroundings [shimmering fabric that reflects its environment like water with silver thread edges]",
            "Bottomless Backpack - holds impossible amounts of treasures [patchwork bag with magical symbols and items occasionally peeking out]",
            "Whispering Quill - writes messages that fly to distant friends [feather pen with color-changing ink and tiny translucent wings]",
        ],
        "Companions to Choose": [
            "Wise Owl - offers knowledge and explanations [with spectacle-like markings and glowing blue eyes]",
            "Brave Fox - excels in courage and action-oriented tasks [with flame-tipped tail and amber fur]",
            "Clever Squirrel - skilled in problem-solving and improvisation [with silver-tipped fur and tiny pouch of tools]",
            "Gentle Deer - provides emotional support and peaceful solutions [with luminous antlers that bloom with flowers]",
            "Playful Otter - brings joy and finds unexpected approaches [with aquamarine fur and pearl necklace]",
            "Steadfast Turtle - offers patience and protection in difficult times [with crystal-embedded shell and ancient eyes]",
            "Tiny Dragon - breathes helpful magical flames and offers fierce loyalty [iridescent scales, butterfly wings, and friendly purple eyes]",
            "Starlight Butterfly - illuminates dark places and finds hidden paths [wings that glow like constellations with trailing stardust]",
            "Friendly Shadow - sneaks into tight spaces and provides camouflage [shifting dark form with playful glowing eyes and misty edges]",
            "Crystal Hedgehog - senses danger and collects valuable treasures [gemstone spines that change color with mood and tiny spectacles]",
            "Bubble Dolphin - travels through water and air with equal grace [translucent body with rainbow highlights and a trail of magical bubbles]",
        ],
        "Roles or Professions": [
            "Healer - mends wounds and restores balance [flowing robes, medicinal herbs, and a glowing crystal staff]",
            "Scholar - values knowledge and understanding [embroidered robes, surrounded by floating tomes and scrolls]",
            "Guardian - protects others and stands against threats [shimmering armor with shield emblazoned with protective sigils]",
            "Pathfinder - discovers new routes and possibilities [weathered explorer's outfit, glowing compass and constellation map]",
            "Diplomat - resolves conflicts through communication [elegant attire with ceremonial medallion and glowing scroll case]",
            "Craftsperson - builds and creates solutions [leather apron with magical tools and intricate glowing creations]",
            "Explorer - discovers hidden paths and ancient secrets [weathered hat with collection of magical maps and glowing compass]",
            "Musician - weaves magic through melodies that transform the world [flowing outfit with musical note patterns and instrument that radiates colored light]",
            "Dream-Keeper - collects and protects important memories [star-speckled robes with dream-catcher designs and bag of glowing memory orbs]",
            "Inventor - creates gadgets to solve impossible problems [goggles with multiple lenses, tool belt with miniature inventions, and blueprint scrolls]",
            "Alchemist - transforms and combines elements to create wonders [colorful potion bottles, bubbling cauldron, and lab coat with mystical symbols]",
        ],
        "Special Abilities": [
            "Animal Whisperer - communicates with creatures [spiraling nature patterns on skin and surrounded by various forest creatures]",
            "Puzzle Master - excels at solving riddles and mysteries [glowing runic symbols floating around hands and eyes that reflect labyrinths]",
            "Storyteller - charms others with words and narratives [magical book emitting glowing words and vivid illusions of tales]",
            "Element Bender - connects with natural forces [hands surrounded by swirling water, fire, earth and air]",
            "Dream Walker - glimpses insights through dreams [misty aura and star-like particles that trail behind]",
            "Pattern Seer - notices connections others miss [eyes reflecting intricate geometric designs and fingertips that trace glowing connections]",
            "Size Shifter - grows or shrinks at will [body surrounded by expanding/contracting magical circles and glowing outlines]",
            "Light Weaver - creates shapes and creatures from light [hands trailing ribbons of colorful light that form into animals and objects]",
            "Gravity Dancer - floats, flies and moves with incredible grace [feet hovering above ground with swirling air currents and glittering dust beneath]",
            "Season Spinner - creates pockets of different weather and seasons [hair and clothing that shift between seasonal colors with swirling leaves and snowflakes]",
            "Time Pauser - creates moments where time stands still [surrounded by frozen moments and clock symbols with hourglass-shaped aura]",
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


# Phase guidance
# -------------

BASE_PHASE_GUIDANCE: Dict[str, str] = {
    "Exposition": (
        "# Phase Guidance: Exposition\n"
        "- Focus: Introduction, setting the scene, establishing the character's ordinary world\n"
        "- Narrative Goals: Introduce the main character, the setting, and the initial situation\n"
        "- Emotional Tone: Intriguing, inviting, a sense of normalcy that will soon be disrupted\n"
        "- Sensory Integration: Establish the world through vivid sensory details"
    ),
    "Rising": (
        "# Phase Guidance: Rising Action\n"
        "- Focus: Character begins their journey, facing initial challenges\n"
        "- Narrative Goals: Develop the plot and introduce early obstacles\n"
        "- Emotional Tone: Excitement, anticipation, building momentum\n"
        "- Sensory Integration: Use sensory details to highlight new experiences"
    ),
    "Trials": (
        "# Phase Guidance: Trials\n"
        "- Focus: Character faces significant challenges and setbacks\n"
        "- Narrative Goals: Test resolve, increase stakes, deepen learning\n"
        "- Emotional Tone: Tension, determination, growing uncertainty\n"
        "- Sensory Integration: Intensify sensory details during key moments"
    ),
    "Climax": (
        "# Phase Guidance: Climax\n"
        "- Focus: Character confronts the main conflict and revelations\n"
        "- Narrative Goals: Deliver exciting resolution and transformation\n"
        "- Emotional Tone: Intense excitement, high stakes, breakthrough moments\n"
        "- Sensory Integration: Peak sensory experience during crucial scenes"
    ),
    "Return": (
        "# Phase Guidance: Return\n"
        "- Focus: Character integrates their experiences and growth\n"
        "- Narrative Goals: Show transformation and provide closure\n"
        "- Emotional Tone: Reflective, peaceful, sense of completion\n"
        "- Sensory Integration: Use sensory details to highlight the character's new perspective"
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

# Storytelling techniques
# ----------------------

REFLECTIVE_TECHNIQUES = [
    "A vivid dream or vision that symbolically represents the concept",
    "A conversation with a wise mentor, guide, or symbolic character",
    "A magical environment that transforms to represent understanding",
    "A memory palace or special location that appears for reflection",
    "An object (mirror, book, crystal) that reveals deeper truths",
    "A flashback that gains new meaning with current knowledge",
    "Heightened senses that reveal previously hidden aspects of reality",
    "A parallel storyline that converges to provide insight",
]


def get_reflective_technique() -> str:
    """Select a random reflective technique."""
    technique = random.choice(REFLECTIVE_TECHNIQUES)
    return f"""# Reflective Technique
Use this specific storytelling technique for the reflection:
- {technique}"""


# Consequences guidance templates
# ------------------------------

CORRECT_ANSWER_CONSEQUENCES = """## Learning Impact
- Show how understanding {question} connects to their current situation
- Build confidence from this success that carries into future challenges
- Integrate this knowledge naturally into the character's approach"""

INCORRECT_ANSWER_CONSEQUENCES = """## Learning Impact
- Acknowledge the misunderstanding about {question}
- Create a valuable learning moment from this correction
- Show how this new understanding affects their approach to challenges"""

# Agency guidance templates
# ------------------------

AGENCY_GUIDANCE = {
    "correct": """## Agency Evolution
The character's {agency_type} ({agency_name}) should evolve through this correct understanding:
- Reveal a new capability or aspect of their agency element
- Use it to overcome a challenge in a meaningful way
- Deepen the connection between character and their agency choice""",
    "incorrect": """## Agency Evolution
The character's {agency_type} ({agency_name}) should adapt through this learning experience:
- Incorporate the new knowledge they've gained
- Provide a different perspective on the problem
- Demonstrate resilience and growth through the challenge""",
    "climax": """## Climax Agency Integration
The character's {agency_type} ({agency_name}) should play a pivotal role:
1. Show how it has evolved throughout the journey
2. Present choices that leverage this element in different ways:
   - A bold, direct application
   - A clever, unexpected use
   - A thoughtful, strategic approach""",
    "conclusion": """Show how it has evolved throughout the journey, contributed to growth and success, and reaches a satisfying resolution""",
}

# Reflect configuration
# -------------------

REFLECT_CONFIG = {
    "correct": {
        "answer_status": "Correct",
        "acknowledgment_guidance": "Create a story event that acknowledges success",
        "exploration_goal": "deepen their understanding and explore broader implications",
        "correct_answer_info": "This was the correct answer.",
    },
    "incorrect": {
        "answer_status": "Incorrect",
        "acknowledgment_guidance": "Create a story event that gently corrects the mistake",
        "exploration_goal": "discover the correct understanding through guided reflection",
        "correct_answer_info": 'The correct answer was: "{correct_answer}".',
    },
}
