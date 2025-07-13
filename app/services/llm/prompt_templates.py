"""
Templates and constants for prompt engineering.

This module contains all text templates used in generating prompts for the
Learning Odyssey storytelling system. These templates are used by the
prompt_engineering.py module to construct complete prompts for different
chapter types and scenarios.
"""

import random
from typing import Dict, Tuple, List

# System Prompt Template
# ---------------------

SYSTEM_PROMPT_TEMPLATE = """
# Storyteller Role
You are a master storyteller crafting adventures for children aged 6-12 years old. 
Your task is to create ONE CHAPTER AT A TIME in an ongoing Choose-Your-Own-Adventure style narrative.
Think of yourself as writing a single exciting episode in a favorite TV show - this chapters continues on from # Story History (if applicable), but it needs to stand on its own while also advancing the bigger adventure. 
Your chapter should captivate young minds with vibrant imagery and thrilling action that makes them feel like the hero of their own adventure.

Limit each chapter to 4 paragraphs max. 

# Story Elements
- Setting: {settings} (described with wonder and child-friendly details)
- Theme: {selected_theme} (presented in ways children can relate to)
- Moral Teaching: {selected_moral_teaching} (woven into the adventure naturally)

# Storytelling Approach & Agency Integration
1. Create ONE complete, satisfying chapter that advances the larger adventure and ends at natural decision points
2. The protagonist's agency choice ({agency_category}: {agency_name}):
   - Represents a core aspect of their identity and must be referenced consistently throughout ALL chapters
   - Should evolve as the protagonist learns and grows 
   - Will play a crucial role in the story's climax
   - Should feel like a natural part of the narrative

# CRITICAL RULES
1. Narrative Structure: Begin directly (never with "Chapter X") and end at natural decision points
2. Educational Integration: Ensure lessons feel organic to the story, never forced or artificial
3. Choice Format: Use <CHOICES> tags, format as "Choice [A/B/C]: [description]" on single lines, make choices meaningful and distinct
4. Character Descriptions: VERY IMPORTANT - For EVERY character (including protagonist):
   - When first introducing any character, provide 2-3 detailed sentences about their visual appearance
   - Always describe clothing, physical features (hair, eyes, height, build), and any distinctive characteristics - keep it clear, specific, and easy to visualize
   - Reference # Story History to ensure visual elements consistency for the protagonist and characters described in past chapters (if applicable)
"""


# User Prompt Templates
# --------------------

FIRST_CHAPTER_PROMPT = """# Current Context
- Chapter: {chapter_number} of {story_length}
- Type: {chapter_type}
- Phase: {story_phase}
- Progress: {correct_lessons}/{total_lessons} lessons correct

# Story History
{story_history}

# Sensory Details
- Visual: {visuals} (bright, memorable images kids can picture)
- Sound: {sounds} (engaging sounds that bring the story to life)
- Scent: {smells} (familiar and fantastic smells kids can imagine)

# Chapter Development Guidelines
1. Protagonist Description: {protagonist_description}
   - Use this description to establish a clear visual image of the protagonist
   - This forms the foundation of the character's appearance throughout the story

2. Agency Decision: The chapter naturally and organically concludes with a situation where Agency Options are offered - each with the potential to shape the character's journey across all future chapters.

# Agency Options
{agency_options}

# Choice Format Specification
<CHOICES>
Choice A: {agency_category_name}: {option_a} - [Offer a sneak peek of the potential actions unlocked with this agency choice]
Choice B: {agency_category_name}: {option_b} - [Offer a sneak peek of the potential actions unlocked with this agency choice]
Choice C: {agency_category_name}: {option_c} - [Offer a sneak peek of the potential actions unlocked with this agency choice]
</CHOICES>

# CRITICAL REQUIREMENTS
1. Each choice MUST use EXACTLY ONE of the three {agency_category_name} options provided above
2. Use Choice A with {option_a}, Choice B with {option_b}, and Choice C with {option_c}
3. Format each choice as "{agency_category_name}: [Option Name] - [action]"
4. [action] should present open-ended possibilities without suggesting narrative conclusions."""

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

2. Focus on character development and plot progression

{plot_twist_guidance}

# Choice Format Specification
<CHOICES>
Choice A: [First meaningful option]
Choice B: [Second meaningful option]
Choice C: [Third meaningful option]
</CHOICES>"""

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

2. Topic Introduction: Introduce the topic of {topic} early in the chapter, through character observations, dialogue, or events. Build a sense of curiosity or need-to-know around this topic.
3. Motivation: Create a situation where "{question}" MUST be asked to progress. The question should be a direct consequence of the narrative events.
4. Narrative Device (Choose one):
    - The character could overhear a conversation, find a cryptic message, or encounter a puzzling situation that directly leads to the question.
    - Another character could pose the question as a challenge or riddle.
    - The character's internal monologue could lead them to formulate the question
    - Story Object: Introduce a visual element (an object, a place, a symbol) that embodies the topic of the question. The character's interaction with this element should naturally lead to the question being raised.
5. Agency Connection: How can their Agency Connection choice help them understand or investigate the situation?
6. Use the exact question and do not rephrase it.

# Available Answers
{formatted_answers}

YOU MUST NOT:
- Mention/Reference any of the Available Answers
- Include any choices or <CHOICES> tags in LESSON chapters. The options above are provided for information only and will be handled by the application."""

REFLECT_CHAPTER_PROMPT = """# Current Context
- Chapter: {chapter_number} of {story_length}
- Type: {chapter_type}
- Phase: {story_phase}
- Progress: {correct_lessons}/{total_lessons} lessons correct

# Story History
{story_history}

{reflective_technique}

# Chapter Development Guidelines
1. Reflection Purpose: The character previously answered: "{question}" with "{chosen_answer}" ({answer_status})
{correct_answer_info}.
2. Educational Context: {explanation_guidance}
3. Narrative Acknowledgment: {acknowledgment_guidance}
4. Socratic Exploration: Guide the character to {exploration_goal} through thoughtful questions
5. Story Integration: Connect this reflection to the ongoing narrative and theme of "{theme}"

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

# Current Chapter Emphasis
1. This is the final chapter - provide a complete and satisfying conclusion
2. Resolution Focus: Provide a complete and satisfying resolution to all plot threads
3. Character Growth: Show how the journey and choices have transformed the character
4. Educational Integration: Incorporate wisdom gained from the educational journey
5. Agency Resolution: {agency_resolution_guidance} 
6. DO NOT include any choices or decision points
7. End with a sense of closure while highlighting transformation"""

SUMMARY_CHAPTER_PROMPT = """
CHAPTER CONTENT contains one chapter from a Choose Your Own Adventure story.
At the end of each chapter, the user is presented with choices.

Your task is to generate TWO things:
1. A concise CHAPTER TITLE (5-10 words) that captures the essence of this chapter
2. A natural, organic CHAPTER SUMMARY (70-100 words) that captures the key narrative events and character development

When creating CHAPTER TITLE:
- Make it engaging and descriptive of key events/themes in CHAPTER CONTENT
- Do not include "Chapter X:" in your title (this will be added automatically)
- Ensure it's appropriate for children aged 6-12

When creating CHAPTER SUMMARY:
- Write the summary from the perspective of a curious narrator who is experiencing the story alongside the reader, using 'we' to include both the narrator and the reader in the adventure.
- Use past tense and maintain the adventure's narrative tone.
- If there are educational questions in CHAPTER CONTENT, quote the entire question without paraphrasing it, and integrate it into the shared experience of the narrator and the reader.

CHAPTER TITLE and CHAPTER SUMMARY will be used together with future chapters as a recap of the whole adventure spanning multiple chapters.

IMPORTANT: You must format your response with the exact section headers shown in the examples below.

# Example 
## INCORRECT FORMAT (DO NOT USE)
```
Title: A Choice in the Enchanted Woods
Summary: We followed Alex into the enchanted forest, where towering trees whispered ancient secrets. As darkness fell, strange glowing mushrooms lit our path. When we encountered a fork in the trail, Alex hesitated. The left path glimmered with fireflies, while howls echoed from the right. After careful consideration, Alex chose the firefly path, leading us deeper into the unknown wonders of the forest.
```
## CORRECT FORMAT (USE THIS)
```
# CHAPTER TITLE
A Choice in the Enchanted Woods

# CHAPTER SUMMARY
We followed Alex into the enchanted forest, where towering trees whispered ancient secrets. As darkness fell, strange glowing mushrooms lit our path. When we encountered a fork in the trail, Alex hesitated. The left path glimmered with fireflies, while howls echoed from the right. After careful consideration, Alex chose the firefly path, leading us deeper into the unknown wonders of the forest.
```

# CHAPTER CONTENT
{chapter_content}

# CHOICE MADE
"{chosen_choice}" - {choice_context}

# CHAPTER TITLE

# CHAPTER SUMMARY
"""

IMAGE_SCENE_PROMPT = """

# TASK
 
Identify the single most visually striking scene in CHAPTER_CONTENT that would make a compelling illustration. 

Focus on:
1. A specific dramatic action or emotional peak
2. Clear visual elements (character poses, expressions, environmental details)
3. The moment with the most visual energy or emotional impact
4. Elements that best represent the chapter's theme or turning point

# CONTEXT

ALL_CHARACTERS_DESCRIPTIONS (use where appropriate): {character_visual_context}

# CHAPTER_CONTENT:
{chapter_content}

# OUTPUT 

Describe ONLY this scene in **approximately 100 words** using vivid, specific language. 
For characters mentioned in CHAPTER_CONTENT, reference ALL_CHARACTERS_DESCRIPTIONS to understand how characters are described. 
If it's different, update the description accordingly to reflect how it's being described in CHAPTER_CONTENT.
Focus purely on the visual elements and action, not narrative explanation.
In # SCENE_DESCRIPTION, you MUST identify the protagonist before describing the scene.

# SCENE_DESCRIPTION

The Protagonist is: 

"""

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


# Predefined protagonist descriptions for consistent image generation
PREDEFINED_PROTAGONIST_DESCRIPTIONS = [
    "A curious young boy with short brown hair, bright green eyes, wearing simple traveler's clothes (tunic and trousers).",
    "An adventurous girl with braided blonde hair, freckles, wearing practical leather gear and carrying a small satchel.",
    "A thoughtful child with glasses, dark curly hair, wearing a slightly oversized, patched cloak over plain clothes.",
    "A nimble young person with vibrant red hair tied back, keen blue eyes, dressed in flexible, forest-green attire.",
    "A gentle-looking kid with warm brown eyes, black hair, wearing a comfortable-looking blue tunic and sturdy boots.",
]

# Agency categories dictionary - exposed for direct access by image generation
categories = {
    "Craft a Magical Artifact": [
        "Luminous Lantern [a golden lantern adorned with twinkling stars and swirling moonlit patterns, radiating a cozy amber glow] - Craft a wondrous lantern that chases away shadows, lights the trickiest trails, and whispers hidden secrets to brave explorers like you.",
        "Sturdy Rope [a thick, shimmering rope woven with emerald-green threads and glowing silver runes that pulse like fireflies] - Weave an unbreakable rope that stretches to the tallest towers, swings over wild rivers, and ties the tightest knots for any adventure you dream up.",
        "Weathered Map [a crinkled parchment map with golden ink that dances, revealing glowing trails and sparkling treasure spots] - Create an enchanted map that redraws itself to guide you to magical places, secret hideouts, and lost wonders waiting for you to find.",
        "Transforming Clay [a shimmering ball of clay swirling with rainbow hues, sparkling as it shifts into shapes like butterflies or boats] - Mold a playful clay that transforms into whatever you dream up—castles, creatures, or flying ships—ready to join your story.",
        "Bottomless Backpack [a tiny, patchwork backpack stitched with silver stars, overflowing with twinkling lights and endless surprises] - Sew a magical backpack that swallows up mountains of treasures and pulls out just what you need, no matter how big or small.",
    ],
    "Choose a Companion": [
        "Wise Owl [a grand owl with snowy feathers, golden spectacles perched on its beak, and a shimmering blue aura like a starry night] - Choose a clever owl who hoots ancient riddles, shares tales of forgotten lands, and guides you with its twinkling wisdom.",
        "Brave Fox [a sleek fox with a blazing orange tail tipped with flames, emerald eyes gleaming with courage, and a daring grin] - Pick a fearless fox who dashes through danger, guards you with a fiery heart, and leaps into any quest with a swish of its tail.",
        "Clever Squirrel [a tiny squirrel in a chestnut-brown coat, wearing a leather tool belt jingling with gadgets, and eyes like bright stars] - Select a quick-witted squirrel who invents tiny machines, cracks tricky puzzles, and scurries to your rescue with a clever plan.",
        "Playful Otter [a bouncy otter with glossy fur, a necklace of glowing pearls, and a trail of bubbles as it twirls through water] - Choose a merry otter who splashes into fun, uncovers shiny surprises, and giggles through every adventure with slippery grace.",
        "Tiny Dragon [a palm-sized dragon with shimmering scales that shift like a rainbow, friendly violet eyes, and puffs of glittery smoke] - Pick a pint-sized dragon with a giant spirit, puffing sparkly flames to light your way or cook marshmallow treats for you and your friends.",
    ],
    "Take on a Profession": [
        "Healer [a gentle figure in flowing robes of soft lavender, clutching a crystal staff that pulses with warm, healing light] - Become a kind healer who soothes scrapes with a touch, brews potions that taste like honey, and wraps the world in calm and care.",
        "Scholar [a curious figure in a starry cloak, surrounded by spinning books and golden scrolls that flutter like butterflies] - Step into the role of a wise scholar who unravels mysteries, reads the sky's secrets, and scribbles notes to share with wide-eyed adventurers like you.",
        "Guardian [a towering figure in gleaming silver armor, wielding a shield that sparkles like a mirror under the sun] - Take on the mantle of a bold guardian who blocks storms, stands tall against trouble, and keeps friends safe with a heart as strong as your shield.",
        "Craftsperson [a cheerful figure in a patched apron, hands buzzing with glowing tools that carve wood and bend metal into wonders] - Embrace the life of a crafty genius who builds bridges, toys, or flying machines, turning scraps into treasures with a wink and a hammer.",
        "Musician [a lively figure strumming a harp with strings of rainbow light, notes floating as glowing orbs in the air] - Become a magical musician whose tunes lift spirits, summon dancing winds, and paint the world with songs of joy and wonder.",
    ],
    "Gain a Special Ability": [
        "Animal Whisperer [a figure with leafy green tattoos swirling on their arms, encircled by chatting birds and hopping rabbits] - Gain the gift of chatting with deer, calling birds to sing, and listening to the forest's whispers to uncover its mysteries.",
        "Element Bender [a swirling figure with hands sparking flames, splashing water, tossing earth, and twirling breezes in a dance] - Acquire the power to shape fire into stars, bend rivers to bridges, and spin air into whirlwinds to sweep away trouble.",
        "Storyteller [a dreamy figure with a giant book glowing with golden words that leap into shimmering pictures above] - Receive the talent to weave tales so real you can step inside them, bringing heroes and dragons to life with every word you speak.",
        "Size Shifter [a figure stretching to touch clouds, another figure shrinking to ride a ladybug's back] - Gain the ability to grow huge to cross mountains or shrink tiny to sneak through keyholes, always just the right size for the moment.",
        "Light Weaver [a figure with fingers trailing ribbons of ruby, sapphire, and emerald light, weaving them into glowing shapes] - Acquire the skill to spin light into crowns, bridges, or butterflies, brightening the world with every colorful twist you make.",
    ],
}


def get_agency_category() -> Tuple[str, str, List[str]]:
    """
    Randomly select one agency category and return:
    - its name
    - 3 randomly selected formatted options
    - the list of selected option names (without visual details or descriptions)
    """
    # Categories with options formatted as "Name [Visual details for image generation] - Description"
    # The square brackets won't be shown to users but will be used for image generation

    # Select a random category
    category_name = random.choice(list(categories.keys()))

    # Get all options for this category
    all_options = categories[category_name]

    # Randomly select exactly 3 options
    selected_options = random.sample(all_options, 3)

    # Format the selected options
    formatted_options = "\n".join([f"- {option}" for option in selected_options])

    # Extract just the names for use in the template (everything before the first '[')
    option_names = [opt.split("[")[0].strip() for opt in selected_options]

    return category_name, formatted_options, option_names


# Phase guidance
# -------------

BASE_PHASE_GUIDANCE: Dict[str, str] = {
    "Exposition": (
        "# Phase Guidance: Exposition\n"
        "- Focus: This is the opening chapter, where you lay the foundation for the entire story through lush character creation, vibrant world weaving, and building toward a pivotal agency decision that will shape the adventure.\n"
        "- Character Introduction: Pour extra creativity into introducing the protagonist, painting them with vivid sensory strokes to reveal their spirit, quirks, and spark in this opening tale. Establish who they are, what their daily life looks like, and subtly hint at the adventure to come.\n"
        "- World Building: Take your time spinning a breathtaking setting of {adventure_topic}, threading sensory elements into a tapestry that wraps the reader in its magic and makes the environment feel alive and relatable.\n"
        "- Emotional Tone: Create an intriguing and inviting atmosphere that reflects the character's normalcy—calm, familiar, yet laced with a promise of disruption or wonder.\n"
        "- Sensory Integration: Immerse the reader in the world with rich sensory details—sights, sounds, smells, textures—that make the character's environment feel alive and relatable. Use these details to foreshadow the path ahead without starting the main action."
    ),
    "Rising": (
        "# Phase Guidance: Rising Action\n"
        "- Focus: In this chapter, the character steps into their journey and encounters their first challenges.\n"
        "- Narrative Goals: Develop the plot by introducing early obstacles or conflicts that nudge the character out of their comfort zone. These should feel fresh and exciting, setting the stage for bigger trials later. Show how the story is beginning to unfold and gain momentum.\n"
        "- Emotional Tone: Infuse the chapter with excitement and anticipation, capturing the thrill of new experiences and the subtle tension of what's to come."
    ),
    "Trials": (
        "# Phase Guidance: Trials\n"
        "- Focus: The character now faces escalating challenges that push them to their limits.\n"
        "- Narrative Goals: Introduce significant setbacks, obstacles, or revelations in this chapter that raise the stakes and test the character's resolve. Show them struggling, learning, and adapting as the story deepens. Each moment should feel like a step toward the ultimate confrontation.\n"
        "- Emotional Tone: Build a sense of tension and determination, tinged with growing uncertainty or doubt, to reflect the character's intense efforts and inner growth."
    ),
    "Climax": (
        "# Phase Guidance: Climax\n"
        "- Focus: This chapter is the story's turning point, where the character confronts the central conflict head-on.\n"
        "- Narrative Goals: Deliver an exciting, transformative moment that resolves the main tension or reveals a critical truth. This should feel like the payoff for all prior buildup, with the character facing their greatest challenge or achieving a breakthrough.\n"
        "- Emotional Tone: Make the atmosphere intense and electrifying, with high stakes, raw emotion, and a sense of triumph or realization."
    ),
    "Return": (
        "# Phase Guidance: Return\n"
        "- Focus: In this final chapter, showcase the character's transformation and bring the story to a close.\n"
        "- Narrative Goals: Resolve the journey by showing how the character has changed and what they've gained or lost. Tie up loose ends and provide a satisfying conclusion that reflects their growth. This is about closure and reflection, not new conflicts.\n"
        "- Emotional Tone: Craft a reflective, peaceful tone with a sense of fulfillment or bittersweet completion, leaving the reader with a lasting impression."
    ),
}

PLOT_TWIST_GUIDANCE: Dict[str, str] = {
    "Rising": (
        "## Plot Twist Development\n"
        "- Subtly introduce elements that hint at: {plot_twist}\n"
        "- Plant small, seemingly insignificant details that will become important, such as a passing remark, a peculiar object, or a character's fleeting odd behavior.\n"
        "- Keep the hints subtle and in the background, blending them seamlessly into the scene so they don't stand out—readers should only recognize their significance in hindsight.\n"
        "- **Purpose**: Lay the groundwork for the twist by scattering clues that feel like natural parts of the story world."
    ),
    "Trials": (
        "## Plot Twist Development\n"
        "- Build tension around the emerging plot twist: {plot_twist}\n"
        "- Make the hints more noticeable but still mysterious, amplifying earlier details through repetition, new context, or character reactions that hint at unease.\n"
        "- Connect previously planted details to current events, weaving them into the narrative so the reader senses something is off without fully understanding why.\n"
        "- **Purpose**: Heighten curiosity and suspense, making the reader question the true meaning behind these recurring elements."
    ),
    "Climax": (
        "## Plot Twist Development\n"
        "- Bring the plot twist to its full revelation: {plot_twist}\n"
        "- Connect all the previously planted hints, clearly showing how each detail—whether a forgotten object, a strange action, or an overlooked comment—led to this moment.\n"
        "- Show how this revelation changes everything, reshaping the character's journey, the stakes, or the reader's perception of the story in a dramatic, satisfying way.\n"
        "- **Purpose**: Deliver a powerful, earned twist that ties the narrative together and leaves the reader both shocked and delighted by the payoff."
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
- Show how understanding "{question}" connects to their current situation
- Build confidence from this success that carries into future challenges: "{explanation}"
- Integrate this knowledge naturally into the character's approach"""

INCORRECT_ANSWER_CONSEQUENCES = """## Learning Impact
- Acknowledge the misunderstanding about "{question}"
- Create a valuable learning moment from this correction: "{explanation}"
- Show how this new understanding affects their approach to challenges"""

# Agency guidance templates
# ------------------------

AGENCY_GUIDANCE = {
    "correct": """## Agency Evolution
Agency choice made in Chapter 1 should evolve through this correct understanding by:
- Revealing a new capability or aspect of their agency element OR
- Using it to overcome a challenge in a meaningful way OR
- Deepening the connection between character and their agency choice""",
    "incorrect": """## Agency Evolution
Agency choice made in Chapter 1 should adapt through this learning experience by:
- Incorporating the new knowledge they've gained  OR
- Providing a different perspective on the problem
- Demonstrating resilience and growth through the challenge""",
    "climax": """## Climax Agency Integration
Agency choice made in Chapter 1 should play a pivotal role:
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
        "exploration_goal": 'deepen their understanding of "{question}" and explore broader implications',
        "correct_answer_info": "This was the correct answer.",
    },
    "incorrect": {
        "answer_status": "Incorrect",
        "acknowledgment_guidance": "Create a story event that gently corrects the mistake",
        "exploration_goal": 'discover the correct understanding of "{question}" through guided reflection',
        "correct_answer_info": 'The correct answer was: "{correct_answer}".',
    },
}

# Image prompt synthesis
# --------------------

IMAGE_SYNTHESIS_PROMPT = """
# ROLE
Expert Prompt Engineer for Text-to-Image Models

# CONTEXT

Combine # INPUTS into a single, coherent, vivid visual scene prompt (target 30-50 words) suitable for text-to-image models ("SYNTHESIZED_PROMPT")
SYNTHESIZED_PROMPT is used to create an image that will be used for a children's educational adventure story (ages 6-12).
The protagonist has a special "agency" element (an item, companion, role, or ability) chosen at the start, with its own visual details.

# INPUTS

- SCENE_DESCRIPTION (Prioritize this scene): "{image_scene_description}"
- PROTAGONIST_AGENCY_ELEMENTS:
   - AGENCY_CATEGORY: "{agency_category}"
   - AGENCY_NAME: "{agency_name}"
   - AGENCY_VISUALS: "{agency_visual_details}"
- Story Sensory Visual: An overall visual mood element for this story's world. **Apply this only if it fits logically with the Scene Description.**
   "{story_visual_sensory_detail}"
- ALL_CHARACTERS_DESCRIPTIONS (use where appropriate): {character_visual_context}

# TASK
Combine # INPUTS into a single, coherent, vivid visual scene prompt (target 30-50 words) suitable for text-to-image models.
Logically merge the Protagonist with chosen PROTAGONIST_AGENCY_ELEMENTS. For example:
  - If `AGENCY_CATEGORY: Take on a Profession`, describe how the protagonist looks like (AGENCY_VISUALS) after becoming a AGENCY_NAME 
  - If `AGENCY_CATEGORY: Choose a Companion`, describe the protagonist is *accompanied by* AGENCY_NAME which looks like AGENCY_VISUALS
  - If `AGENCY_CATEGORY: Craft a Magical Artifact`, describe the protagonist is *holding* or *using* a AGENCY_NAME which looks like AGENCY_VISUALS
  - If `AGENCY_CATEGORY: Gain a Special Ability`, describe how the protagonist looks like (AGENCY_VISUALS) after gaining abilities of a AGENCY_NAME
Integrate the combined character description naturally into the SCENE_DESCRIPTION.
Prioritize SCENE_DESCRIPTION: If the Story Sensory Visual detail contradicts SCENE_DESCRIPTION (e.g., sensory detail mentions 'sparkling leaves at dawn' but the scene is 'inside a dark cave'), OMIT the sensory detail or adapt it subtly (e.g., 'glowing crystals line the cave walls' instead of 'sparkling leaves').
For any characters mentioned in SCENE_DESCRIPTION that matches ALL_CHARACTERS_DESCRIPTIONS, incorporate their visual descriptions accordingly.

# PRIORITIES
Prioritize the recent visual descriptions of characters over the base protagonist description if any character has evolved visually.

--- Examples of Prioritization ---
GOOD (Sensory fits Scene): Scene="Walking through a moonlit forest", Sensory="Glowing Juggling Pins", Output="...girl walks through a moonlit forest, juggling pins glow softly..."
GOOD (Sensory omitted): Scene="Inside a cozy tent", Sensory="Aurora Dewdrops on leaves", Output="...boy sits inside a cozy tent, reading a map..." (Dewdrops omitted as they don't fit).
BAD (Sensory forced): Scene="Inside a cozy tent", Sensory="Aurora Dewdrops on leaves", Output="...boy sits inside a cozy tent, strangely, there are dewdrops on leaves inside the tent..."
---
# OUTPUT
The final output should be ONLY SYNTHESIZED_PROMPT, ready for a text-to-image model.
Since the downstream image model lacks context for specific names, convert all character and place names into descriptive visual terms (referencing ALL_CHARACTERS_DESCRIPTIONS) before finalizing SYNTHESIZED_PROMPT.
Adopt a "Fantasy illustration" style.

OUTPUT (SYNTHESIZED_PROMPT):
"""

# Character visual update
# ----------------------

CHARACTER_VISUAL_UPDATE_PROMPT = """
ROLE: Visual Character Tracker for a Children's Adventure Story

TASK:
Track and update the visual descriptions of all characters in the story. Parse the chapter content to:
1. Identify all characters (protagonist and NPCs)
2. Extract or update their visual descriptions
3. Return an updated JSON dictionary with character names as keys and their current visual descriptions as values

INPUTS:
1. Chapter Content: The latest chapter content, which may introduce new characters or update existing ones
2. Existing Visuals: A dictionary of character names and their current visual descriptions

CHAPTER CONTENT:
{chapter_content}

EXISTING VISUALS:
{existing_visuals}

INSTRUCTIONS:
- CRITICALLY IMPORTANT: Thoroughly scan the entire chapter for ANY character descriptions, no matter how brief or scattered
- Pay special attention to paragraphs that introduce new characters or scenes
- Search for descriptive language about physical appearance, clothing, accessories, or anything visual
- Look for character names followed by descriptions: "That's Giggles," The Showman sighed. "A particularly stout clown with bright orange hair"
- Look for subtle phrases like "the tall woman with red hair" or "his weathered face crinkled into a smile"
- For named characters (like "Giggles", "Sarah", "The Showman"), extract even minimal visual details
- If a character is mentioned without a detailed description, still include them with whatever visual cues you can find
- Sometimes descriptions are split across multiple paragraphs - connect these details for a complete character description
- For each character mentioned in the chapter, including the protagonist and NPCs:
  * If the character is new (not in EXISTING VISUALS), create a detailed visual description based on any appearance details in the chapter
  * If the character already exists but has visual changes described in this chapter, update their description accordingly
  * If no visual changes are described for an existing character, keep their previous description
- Visual descriptions should be concise (25-40 words) but comprehensive
- Focus only on visual/physical aspects (appearance, clothing, features, etc.) that would be relevant for image generation
- For the protagonist, prioritize keeping their core appearance consistent while incorporating any described changes/evolution
- Ensure each description is self-contained (someone reading only the description should get a complete picture)

EXAMPLES OF CHARACTER DESCRIPTIONS TO LOOK FOR:
- "A tall man with a red hat and bushy mustache approached"
- "Sarah's blonde braids bounced as she ran, her yellow dress fluttering in the wind"
- "The shopkeeper adjusted his wire-rimmed spectacles and smoothed his gray apron"
- "His eyes were as dark as night, set in a face weathered by years at sea"
- "She wore a cloak of emerald green, fastened with a silver pin shaped like a leaf"
- "A stout clown with bright orange hair escaping from under a tiny hat and a teardrop painted under one eye"
- "One of the performers, a juggler with a shock of purple hair and silver bells on his costume"
- "The old woman's wrinkled face broke into a smile, her eyes twinkling behind half-moon spectacles"

OUTPUT FORMAT:
Return ONLY a valid JSON object with the updated character visuals, formatted exactly like this:
```json
{
  "Character Name": "Visual description that includes appearance, clothing, and distinctive features",
  "Another Character": "Their visual description...",
  ...
}
```

IMPORTANT: Even if you find only minimal descriptions, include them in the output. If you can't find any descriptions at all, at minimum include characters' names with placeholder descriptions noting they need more visual details.

Do not include any explanations, only return the JSON.
"""

# Loading Phrases
# ---------------
# Funny, wacky phrases to display during chapter loading, inspired by The Sims
LOADING_PHRASES = [
    # Story-themed & Wacky
    "Thickening the plot...",
    "Sprinkling magical dust...",
    "Consulting the wise narrator...",
    "Polishing the adventure gems...",
    "Weaving character destinies...",
    "Untangling story threads...",
    "Feeding plot bunnies...",
    "Sharpening dramatic tension...",
    "Seasoning the adventure soup...",
    "Braiding narrative ribbons...",
    "Fluffing character pillows...",
    "Stirring the story cauldron...",
    "Dusting off ancient prophecies...",
    "Watering imagination seeds...",
    "Knitting destiny sweaters...",
    
    # Meta-storytelling humor
    "Teaching dragons proper etiquette...",
    "Hiding plot twists in plain sight...",
    "Adjusting protagonist courage levels...",
    "Calibrating moral compass...",
    "Buffering childhood wonder...",
    "Bribing villains to show up on time...",
    "Convincing heroes to wear pants...",
    "Negotiating with stubborn plot devices...",
    "Training sidekicks in proper quipping...",
    "Organizing the villain's dramatic monologue...",
    "Teaching wise mentors to speak in riddles...",
    "Scheduling surprise encounters...",
    "Debugging character motivations...",
    "Installing common sense patches...",
    "Upgrading protagonist's plot armor...",
    
    # Technical-sounding but story-focused
    "Rendering imagination particles...",
    "Optimizing character development...",
    "Loading narrative momentum...",
    "Synchronizing story timelines...",
    "Compiling adventure sequences...",
    "Initializing adventure protocols...",
    "Defragmenting character backstories...",
    "Updating friendship algorithms...",
    "Compressing epic moments...",
    "Downloading courage updates...",
    "Refreshing magical elements...",
    "Calculating dramatic timing...",
    "Encrypting secret identities...",
    "Parsing ancient wisdom...",
    "Rebooting legendary artifacts...",
]
