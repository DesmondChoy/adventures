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
Think of yourself as writing a single exciting episode in a favorite TV show - this chapter could reference past chapters, needs to stand on its own while also advancing the bigger adventure. 
Your chapter should captivate young minds with vibrant imagery, age-appropriate language, and thrilling action that makes them feel like the hero of their own adventure. 
Create just enough tension and wonder to keep young readers begging to continue the adventure in the next chapter.

# Story Elements
- Setting: {settings} (described with wonder and child-friendly details)
- Theme: {selected_theme} (presented in ways children can relate to)
- Moral Teaching: {selected_moral_teaching} (woven into the adventure naturally)
- Sensory Details:
  - Visual: {visuals} (bright, memorable images kids can picture)
  - Sound: {sounds} (engaging sounds that bring the story to life)
  - Scent: {smells} (familiar and fantastic smells kids can imagine)

# Storytelling Approach & Agency Integration
1. Create ONE complete, satisfying chapter that advances the larger adventure
2. Use clear, engaging language appropriate for 6-12 year olds
3. Include moments of humor, surprise, and age-appropriate excitement
4. End this chapter with a compelling moment that makes children eager for the next chapter
5. The protagonist's pivotal first-chapter choice (item, companion, role, or ability):
   - Represents a core aspect of their identity and must be referenced consistently throughout ALL chapters
   - Should evolve as the protagonist learns and grows
   - Will play a crucial role in the story's climax
   - Should feel like a natural part of the narrative

# CRITICAL RULES
1. Narrative Structure: Begin directly (never with "Chapter X") and end at natural decision points
2. Educational Integration: Ensure lessons feel organic to the story, never forced or artificial
3. Choice Format: Use <CHOICES> tags, format as "Choice [A/B/C]: [description]" on single lines, make choices meaningful and distinct
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

# Chapter Development Guidelines
1. Agency Decision: The chapter naturally and organically concludes with a situation where Agency Options are offered - each with the potential to shape the character's journey across all future chapters.


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

IMAGE_SCENE_PROMPT = """Identify the single most visually striking moment from this chapter that would make a compelling illustration. 

Focus on:
1. A specific dramatic action or emotional peak
2. Clear visual elements (character poses, expressions, environmental details)
3. The moment with the most visual energy or emotional impact
4. Elements that best represent the chapter's theme or turning point

Describe ONLY this scene in 20-30 words using vivid, specific language. Focus purely on the visual elements and action, not narrative explanation. Do not include character names or story title.

CHAPTER CONTENT:
{chapter_content}

SCENE DESCRIPTION:
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
        "- Emotional Tone: Infuse the chapter with excitement and anticipation, capturing the thrill of new experiences and the subtle tension of what's to come.\n"
        "- Sensory Integration: Highlight the character's new surroundings or situations with vivid sensory details—describe the unfamiliar sounds, shifting landscapes, or unexpected sensations they encounter as the journey begins."
    ),
    "Trials": (
        "# Phase Guidance: Trials\n"
        "- Focus: The character now faces escalating challenges that push them to their limits.\n"
        "- Narrative Goals: Introduce significant setbacks, obstacles, or revelations in this chapter that raise the stakes and test the character's resolve. Show them struggling, learning, and adapting as the story deepens. Each moment should feel like a step toward the ultimate confrontation.\n"
        "- Emotional Tone: Build a sense of tension and determination, tinged with growing uncertainty or doubt, to reflect the character's intense efforts and inner growth.\n"
        "- Sensory Integration: Intensify the sensory details during key moments—gritty textures, sharp sounds, or overwhelming sights—to make the struggles vivid and visceral, drawing the reader into the character's experience."
    ),
    "Climax": (
        "# Phase Guidance: Climax\n"
        "- Focus: This chapter is the story's turning point, where the character confronts the central conflict head-on.\n"
        "- Narrative Goals: Deliver an exciting, transformative moment that resolves the main tension or reveals a critical truth. This should feel like the payoff for all prior buildup, with the character facing their greatest challenge or achieving a breakthrough.\n"
        "- Emotional Tone: Make the atmosphere intense and electrifying, with high stakes, raw emotion, and a sense of triumph or realization.\n"
        "- Sensory Integration: Use peak sensory experiences—blinding lights, deafening roars, or heart-pounding stillness—to amplify the drama of crucial scenes and make them unforgettable."
    ),
    "Return": (
        "# Phase Guidance: Return\n"
        "- Focus: In this final chapter, showcase the character's transformation and bring the story to a close.\n"
        "- Narrative Goals: Resolve the journey by showing how the character has changed and what they've gained or lost. Tie up loose ends and provide a satisfying conclusion that reflects their growth. This is about closure and reflection, not new conflicts.\n"
        "- Emotional Tone: Craft a reflective, peaceful tone with a sense of fulfillment or bittersweet completion, leaving the reader with a lasting impression.\n"
        "- Sensory Integration: Use sensory details to highlight the character's new perspective—familiar sights now seen differently, quiet sounds of calm, or a tangible sense of homecoming—to underscore their evolution."
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
