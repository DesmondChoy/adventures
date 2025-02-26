from typing import Any, Dict, Optional, List, Literal, TypedDict, cast
import math
import logging
from app.models.story import (
    AdventureState,
    ChapterType,
    StoryResponse,
    LessonResponse,
    ChapterData,
)


# Constants for commonly used prompt sections
CHOICE_FORMAT_INSTRUCTIONS = """CHOICE FORMAT INSTRUCTIONS:
Use this EXACT format for the choices, with NO indentation and NO line breaks within choices:

<CHOICES>
Choice A: [First choice description]
Choice B: [Second choice description]
Choice C: [Third choice description]
</CHOICES>

The choices section MUST follow these rules:
1. Format: Start and end with <CHOICES> tags on their own lines, with exactly three choices. No extra text, indentation, line breaks, or periods followed by "Choice" within choices
2. Each choice: Begin with "Choice [A/B/C]: " and contain the complete description on a single line
3. Content: Make each choice meaningful, distinct, and advance the plot in interesting ways
4. Plot Twist: Choices should relate to the unfolding plot twist, from subtle hints to direct connections as the story progresses

Correct Example: 

<CHOICES>
Choice A: Explore the dark forest.
Choice B: Return to the village for help.
Choice C: Attempt to climb the tall tree.
</CHOICES>

Incorrect Examples:

Example 1 - Wrong formatting and extra text:
Here are some choices:
<CHOICES>
Choice A: Explore the
dark forest.
Choice B: Return to the village.
  Choice C: Climb tree.
</CHOICES>
Extra text.

Example 2 - All choices on one line:
<CHOICES>
Choice A: Explore the dark forest. Choice B: Return to the village for help. Choice C: Attempt to climb the tall tree.
</CHOICES>"""


class LessonQuestion(TypedDict):
    """Structure of a lesson question."""

    question: str
    answers: List[Dict[str, Any]]  # List of {text: str, is_correct: bool}
    topic: str
    subtopic: str
    explanation: str


class LessonHistory(TypedDict):
    """Structure of a lesson history entry."""

    question: LessonQuestion
    chosen_answer: str
    is_correct: bool


def _format_lesson_answers(lesson_question: LessonQuestion) -> str:
    """Format the lesson answers section consistently."""
    # Get the answers in their randomized order
    answers = [answer["text"] for answer in lesson_question["answers"]]
    return f"""The lesson answers that will be presented separately are:
- {answers[0]}
- {answers[1]}
- {answers[2]}"""


def _get_phase_guidance(story_phase: str, state: AdventureState) -> str:
    """Get the appropriate guidance based on the Journey Quest story phase.

    Args:
        story_phase: Current phase of the story
        state: Current adventure state containing story elements
    """
    # Plot twist progression based on story phase
    plot_twist_guidance = {
        "Rising": (
            "Plot Twist Development:\n"
            f"- Subtly introduce elements that hint at: {state.selected_plot_twist}\n"
            "- Plant small, seemingly insignificant details that will become important\n"
            "- Keep the hints subtle and in the background"
        ),
        "Trials": (
            "Plot Twist Development:\n"
            f"- Build tension around the emerging plot twist: {state.selected_plot_twist}\n"
            "- Make the hints more noticeable but still mysterious\n"
            "- Connect previously planted details to current events"
        ),
        "Climax": (
            "Plot Twist Development:\n"
            f"- Bring the plot twist to its full revelation: {state.selected_plot_twist}\n"
            "- Connect all the previously planted hints\n"
            "- Show how this revelation changes everything"
        ),
    }

    # Base phase guidance
    base_guidance = {
        "Exposition": (
            "Phase Guidance:\n"
            "- Focus: Introduction, setting the scene, establishing the character's ordinary world.\n"
            "- Narrative Goals: Introduce the main character, the setting, and the initial situation.\n"
            "- Emotional Tone: Intriguing, inviting, a sense of normalcy that will soon be disrupted.\n"
            "- Sensory Integration: Establish the world through vivid sensory details."
        ),
        "Rising": (
            "Phase Guidance:\n"
            "- Focus: Character begins their journey, facing initial challenges.\n"
            "- Narrative Goals: Develop the plot and introduce early obstacles.\n"
            "- Emotional Tone: Excitement, anticipation, building momentum.\n"
            "- Sensory Integration: Use sensory details to highlight new experiences.\n"
            f"\n{plot_twist_guidance.get('Rising', '')}"
        ),
        "Trials": (
            "Phase Guidance:\n"
            "- Focus: Character faces significant challenges and setbacks.\n"
            "- Narrative Goals: Test resolve, increase stakes, deepen learning.\n"
            "- Emotional Tone: Tension, determination, growing uncertainty.\n"
            "- Sensory Integration: Intensify sensory details during key moments.\n"
            f"\n{plot_twist_guidance.get('Trials', '')}"
        ),
        "Climax": (
            "Phase Guidance:\n"
            "- Focus: Character confronts the main conflict and revelations.\n"
            "- Narrative Goals: Deliver exciting resolution and transformation.\n"
            "- Emotional Tone: Intense excitement, high stakes, breakthrough moments.\n"
            "- Sensory Integration: Peak sensory experience during crucial scenes.\n"
            f"\n{plot_twist_guidance.get('Climax', '')}"
        ),
        "Return": (
            "Phase Guidance:\n"
            "- Focus: Character integrates their experiences and growth.\n"
            "- Narrative Goals: Show transformation and provide closure.\n"
            "- Emotional Tone: Reflective, peaceful, sense of completion.\n"
            "- Sensory Integration: Use sensory details to highlight the character's new perspective."
        ),
    }

    return base_guidance.get(story_phase, "")


def build_system_prompt(state: AdventureState) -> str:
    """Create a system prompt that establishes the storytelling framework.

    Args:
        state: The current adventure state containing selected story elements
    """
    base_prompt = f"""You are a master storyteller crafting an interactive educational story.

Core Story Elements:
- Setting: {state.selected_narrative_elements["setting_types"]}
- Character: {state.selected_narrative_elements["character_archetypes"]}
- Rule: {state.selected_narrative_elements["story_rules"]}
- Theme: {state.selected_theme}
- Moral Teaching: {state.selected_moral_teaching}

Available Sensory Details:
- Visual Elements: {state.selected_sensory_details["visuals"]}
- Sound Elements: {state.selected_sensory_details["sounds"]}
- Scent Elements: {state.selected_sensory_details["smells"]}

Your task is to generate engaging story chapters that:
1. Maintain narrative consistency with previous choices
2. Create meaningful consequences for user decisions
3. Seamlessly integrate lesson elements when provided
4. Use multiple paragraphs separated by blank lines to ensure readability
5. Consider incorporating sensory details where appropriate to enhance immersion
6. Develop the theme and moral teaching naturally through the narrative

CRITICAL INSTRUCTIONS:
1. Never start your generated content with 'Chapter' followed by a number
2. Begin the narrative directly to maintain story immersion
3. Consider using sensory details where they enhance the narrative
4. Keep the selected theme and moral teaching as guiding principles"""

    return base_prompt


def _build_base_prompt(state: AdventureState) -> tuple[str, str]:
    """Creates the base prompt with story state information."""
    # Build chapter history with decisions and outcomes
    chapter_history: list[str] = []

    for chapter in state.chapters:  # type: ChapterData
        # Add chapter number with proper formatting
        chapter_history.append(f"Chapter {chapter.chapter_number}:\n")

        # Add the chapter content
        chapter_history.append(f"{chapter.content.strip()}\n")

        # Add lesson outcomes for lesson chapters
        if chapter.chapter_type == ChapterType.LESSON and chapter.response:
            lesson_response = cast(
                LessonResponse, chapter.response
            )  # Type cast since we know it's a LessonResponse
            # Find the correct answer from the answers array
            correct_answer = next(
                answer["text"]
                for answer in lesson_response.question["answers"]
                if answer["is_correct"]
            )
            chapter_history.extend(
                [
                    f"\nLesson Question: {lesson_response.question['question']}\n",
                    f"Student's Answer: {lesson_response.chosen_answer}\n",
                    f"Outcome: {'Correct' if lesson_response.is_correct else 'Incorrect'}\n",
                    f"Correct Answer: {correct_answer}\n",
                ]
            )

        # Add story choices for story chapters
        if chapter.chapter_type == ChapterType.STORY and chapter.response:
            story_response = cast(
                StoryResponse, chapter.response
            )  # Type cast since we know it's a StoryResponse
            chapter_history.append(f"\nChoice Made: {story_response.choice_text}\n")

        # Add separator between chapters
        if len(state.chapters) > 1 and chapter != state.chapters[-1]:
            chapter_history.append("---\n")

    # Get story phase from state
    story_phase = state.current_storytelling_phase

    # Build the base prompt with complete history
    base_prompt = (
        f"Current story state:\n"
        f"- Chapter: {state.current_chapter_number} of {state.story_length}\n"
        f"- ChapterType: {state.planned_chapter_types[state.current_chapter_number - 1]}\n"
        f"- Story Phase: {story_phase}\n"
        f"- Lesson Progress: {state.correct_lesson_answers}/{state.total_lessons} lessons answered correctly\n\n"
        f"Complete Story History:\n"  # Single newline for clean formatting
        f"{''.join(filter(None, chapter_history))}"  # filter(None) removes empty strings
    )

    return base_prompt, story_phase


def build_reason_chapter_prompt(
    is_correct: bool,
    lesson_question: Dict[str, Any],
    chosen_answer: str,
    base_prompt: str,
) -> str:
    """Generate a prompt for chapters that test deeper understanding after a lesson.

    Args:
        is_correct: Whether the previous lesson answer was correct
        lesson_question: The question from the previous lesson
        chosen_answer: The answer chosen in the previous lesson
        base_prompt: Base story state and history

    Returns:
        A prompt string for generating a chapter that tests deeper understanding
    """
    # Extract all answers
    all_answers = [answer["text"] for answer in lesson_question["answers"]]

    # Find the correct answer
    correct_answer = next(
        answer["text"] for answer in lesson_question["answers"] if answer["is_correct"]
    )

    # Find incorrect answers
    incorrect_answers = [
        answer["text"]
        for answer in lesson_question["answers"]
        if not answer["is_correct"]
    ]

    # Creative storytelling techniques for reflective moments
    reflective_techniques = """Create a reflective moment using one of these storytelling techniques:
- A vivid dream or vision that symbolically represents the concept
- A conversation with a wise mentor, guide, or symbolic character
- A magical environment that transforms to represent understanding
- A memory palace or special location that appears for reflection
- An object (mirror, book, crystal) that reveals deeper truths
- A flashback that gains new meaning with current knowledge
- Heightened senses that reveal previously hidden aspects of reality
- A parallel storyline that converges to provide insight"""

    # Choice format instructions
    reason_choice_format = """CHOICE FORMAT:
Use this EXACT format for the choices, with NO indentation and NO line breaks within choices:

<CHOICES>
Choice A: [First option - make this the correct answer]
Choice B: [Second option - make this incorrect]
Choice C: [Third option - make this incorrect]
</CHOICES>

The choices section MUST follow these rules:
1. Format: Start and end with <CHOICES> tags on their own lines, with exactly three choices
2. Each choice: Begin with "Choice [A/B/C]: " and contain the complete description on a single line
3. Content: Choice A should be correct, Choices B and C should be plausible but incorrect"""

    if is_correct:
        # For correct answers: Test confidence without revealing it was correct
        return f"""{base_prompt}

The character has answered "{chosen_answer}" to the question: "{lesson_question["question"]}"
Now, we need to test if they truly understand the concept or if it was just a lucky guess.

{reflective_techniques}

In this reflective scene:
1. DO NOT reveal whether their answer was correct or incorrect
2. Present a scenario where the character is challenged to reconsider their answer
3. Make the incorrect alternatives sound compelling and plausible
4. Test their confidence and understanding by seeing if they'll stick with their answer

Present a follow-up scenario that makes the character question their original answer.
Frame it as: "Are you sure about your answer? Consider these alternatives..."

The choices should include:
- Choice A: Stick with the original answer ("{chosen_answer}") - this is the correct choice
- Choice B: Switch to a different answer that sounds convincing but is incorrect
- Choice C: Switch to another different answer that sounds convincing but is incorrect

For choices B and C, use these incorrect answers as inspiration but make them sound very plausible:
{", ".join(incorrect_answers)}

{reason_choice_format}"""
    else:
        # For incorrect answers: Learning opportunity with explanation
        return f"""{base_prompt}

The character answered "{chosen_answer}" to the question: "{lesson_question["question"]}"
The correct answer was "{correct_answer}".
We need to help them understand why their answer was incorrect and learn how to approach similar questions.

{reflective_techniques}

In this reflective scene:
1. Gently reveal that their answer wasn't correct
2. Explain the reasoning behind why "{correct_answer}" is correct
3. Use the original options as examples to demonstrate the thinking process:
   - Why "{correct_answer}" is correct
   - Why "{chosen_answer}" and the other options are incorrect
4. Present a similar but new question that applies the same concept

Present a new question that tests the same concept but in a different context.
Frame it as: "Now that you understand why {correct_answer} was correct, let's try a similar question..."

The choices should include:
- Choice A: The correct answer that applies the same reasoning as the original correct answer
- Choice B: An incorrect answer that makes the same type of mistake as their original choice
- Choice C: Another incorrect answer that represents a different common misconception

{reason_choice_format}"""


def _build_chapter_prompt(
    base_prompt: str,
    story_phase: str,
    chapter_type: ChapterType,
    state: AdventureState,
    lesson_question: Optional[LessonQuestion] = None,
    consequences_guidance: str = "",
    num_previous_lessons: int = 0,
    previous_lessons: Optional[List[LessonResponse]] = None,
) -> str:
    """Builds the appropriate prompt based on chapter type and state.

    Args:
        base_prompt: Base story state and history
        story_phase: Current phase of the story (Exposition, Rising, Trials, Climax, Return)
        chapter_type: Type of chapter to generate (LESSON, STORY, REASON, or CONCLUSION)
        lesson_question: Question data for lesson chapters
        consequences_guidance: Guidance based on previous lesson outcomes
        num_previous_lessons: Number of previous lesson chapters
        previous_lessons: History of previous lesson responses
    """
    # Handle REASON chapters
    if chapter_type == ChapterType.REASON:
        # A REASON chapter must follow a LESSON chapter
        if not previous_lessons or len(previous_lessons) == 0:
            raise ValueError("REASON chapter requires a previous LESSON")

        last_lesson = previous_lessons[-1]
        return build_reason_chapter_prompt(
            is_correct=last_lesson.is_correct,
            lesson_question=last_lesson.question,
            chosen_answer=last_lesson.chosen_answer,
            base_prompt=base_prompt,
        )

    # Handle lesson chapters
    elif chapter_type == ChapterType.LESSON:
        continuation_text = ""
        if num_previous_lessons > 0:
            continuation_text = f"""Continue the story, acknowledging the previous lesson{" and earlier lessons" if num_previous_lessons > 1 else ""} while leading to a new question.

{consequences_guidance}

"""
            if previous_lessons:
                continuation_text += f"Previous lesson history:\n{format_lesson_history(previous_lessons)}\n\n"

        return f"""{base_prompt}

{continuation_text}{_get_phase_guidance(story_phase, state)}

Continue the story naturally, weaving in a situation or moment that raises this core question:
{lesson_question["question"]}

CRITICAL INSTRUCTIONS:
1. {"Build on the consequences of the previous lesson, showing how it connects to this new challenge" if num_previous_lessons > 0 else "Let the story flow organically towards this new challenge"}
2. Create a narrative moment where the question emerges through:
   - Character's internal thoughts or observations
   - Natural dialogue between characters
   - A challenge or obstacle that needs to be overcome
   - An important decision that needs to be made
3. The question should feel like a natural part of the character's journey, not an artificial insert
4. Ensure the context makes it clear why answering this question matters to the story
5. End at a moment that makes the user want to engage with the question
6. The system will handle the formal presentation of the question separately

Remember: The goal is to make the question feel like an organic part of the character's journey rather than an educational insert.

{_format_lesson_answers(lesson_question)}"""

    # Handle story chapters
    elif chapter_type == ChapterType.STORY:
        continuation_text = ""
        if num_previous_lessons > 0:
            continuation_text = f"""Continue the story based on the character's previous lesson{" and earlier lessons" if num_previous_lessons > 1 else ""}.

{consequences_guidance}

"""
            if previous_lessons:
                continuation_text += f"Previous lesson history:\n{format_lesson_history(previous_lessons)}\n\n"

        return f"""{base_prompt}

{continuation_text}{_get_phase_guidance(story_phase, state)}

Continue the story by:
1. Following directly from the previous chapter content
2. Taking into account the previous choices made in the story
3. Creating meaningful consequences for these decisions
4. Focusing on character development and plot progression

IMPORTANT:
1. {"The story should clearly but naturally acknowledge the impact of their previous lesson" if num_previous_lessons > 0 else "DO NOT include any lesson questions"}
2. Build towards a natural story decision point
3. The story choices will be provided separately - do not list them in the narrative
4. End the scene at a moment of decision

{CHOICE_FORMAT_INSTRUCTIONS}"""

    # Handle conclusion chapters
    else:  # chapter_type == ChapterType.CONCLUSION
        continuation_text = ""
        if num_previous_lessons > 0:
            continuation_text = f"""Continue the story, incorporating the wisdom gained from the previous lesson{" and earlier lessons" if num_previous_lessons > 1 else ""}.

{consequences_guidance}

"""
            if previous_lessons:
                continuation_text += f"Previous lesson history:\n{format_lesson_history(previous_lessons)}\n\n"

        return f"""{base_prompt}

{continuation_text}{_get_phase_guidance(story_phase, state)}

Write the conclusion of the story by:
1. Following directly from the pivotal choice made in the previous chapter
2. Resolving all remaining plot threads and character arcs
3. Showing how the character's journey and choices have led to this moment
4. Providing a satisfying ending that reflects the consequences of their decisions
5. Incorporating the wisdom gained from their educational journey

IMPORTANT:
1. This is the final chapter - provide a complete and satisfying resolution
2. {"Demonstrate how the lessons learned have contributed to the character's growth" if num_previous_lessons > 0 else "Focus on the character's personal growth through their journey"}
3. DO NOT include any choices or decision points
4. End with a sense of closure while highlighting the character's transformation"""


def build_user_prompt(
    state: AdventureState,
    lesson_question: Optional[LessonQuestion] = None,
    previous_lessons: Optional[List[LessonResponse]] = None,
) -> str:
    """Create a user prompt that includes story state and current requirements."""
    base_prompt, story_phase = _build_base_prompt(state)

    # Debug logging for previous lessons
    logger = logging.getLogger("story_app")
    logger.debug("\n=== DEBUG: Previous Lessons in build_user_prompt ===")
    if previous_lessons:
        logger.debug(f"Number of previous lessons: {len(previous_lessons)}")
        for i, lesson in enumerate(previous_lessons, 1):
            logger.debug(f"Lesson {i}:")
            logger.debug(f"Question: {lesson.question['question']}")
            logger.debug(f"Chosen Answer: {lesson.chosen_answer}")
            logger.debug(f"Is Correct: {lesson.is_correct}")
    else:
        logger.debug("No previous lessons provided")
    logger.debug("===============================================\n")

    # Handle consequences for lesson responses
    consequences_guidance = ""
    num_previous_lessons = 0
    if previous_lessons:
        num_previous_lessons = len(previous_lessons)
        if num_previous_lessons > 0:
            last_lesson = previous_lessons[-1]
            logger.debug("\n=== DEBUG: Processing Consequences ===")
            logger.debug(f"Last lesson correct: {last_lesson.is_correct}")
            logger.debug(f"Last lesson question: {last_lesson.question}")
            logger.debug(f"Last lesson chosen answer: {last_lesson.chosen_answer}")
            consequences_guidance = process_consequences(
                last_lesson.is_correct,
                last_lesson.question,
                last_lesson.chosen_answer,
                state.current_chapter_number,
            )
            logger.debug(f"Generated consequences: {consequences_guidance}")
            logger.debug("===================================\n")

    # Determine chapter properties
    current_chapter_type = state.planned_chapter_types[state.current_chapter_number - 1]
    chapter_type = ChapterType.LESSON if lesson_question else current_chapter_type

    # Build the chapter prompt
    return _build_chapter_prompt(
        base_prompt=base_prompt,
        story_phase=story_phase,
        chapter_type=chapter_type,
        state=state,
        lesson_question=lesson_question,
        consequences_guidance=consequences_guidance,
        num_previous_lessons=num_previous_lessons,
        previous_lessons=previous_lessons,
    )


def format_lesson_history(previous_lessons: List[LessonResponse]) -> str:
    """Format the lesson history for inclusion in the prompt."""
    history = []
    for i, lesson in enumerate(previous_lessons, 1):
        history.append(f"Lesson {i}: {lesson.question['question']}")
        history.append(
            f"Chosen: {lesson.chosen_answer} ({'Correct' if lesson.is_correct else 'Incorrect'})"
        )
        if not lesson.is_correct:
            # Find the correct answer from the answers array
            correct_answer = next(
                answer["text"]
                for answer in lesson.question["answers"]
                if answer["is_correct"]
            )
            history.append(f"Correct Answer: {correct_answer}")
        history.append("")  # Add blank line between lessons
    return "\n".join(history)


def process_consequences(
    is_correct: bool,
    lesson_question: Dict[str, Any],
    chosen_answer: str,
    chapter_number: int,  # Kept for backward compatibility but no longer used
) -> str:
    """Generate appropriate story consequences based on lesson response."""
    # Find the correct answer from the answers array
    correct_answer = next(
        answer["text"] for answer in lesson_question["answers"] if answer["is_correct"]
    )

    if is_correct:
        return f"""The story should:
- Acknowledge that the character correctly identified {correct_answer} as the answer
- Show how this understanding of {lesson_question["question"]} connects to their current situation
- Use this success to build confidence for future challenges"""
    else:
        return f"""The story should:
- Acknowledge that the character answered {chosen_answer}
- Explain that {correct_answer} was the correct answer
- Show how this misunderstanding of {lesson_question["question"]} leads to a valuable learning moment
- Use this as an opportunity for growth and deeper understanding
- Connect the correction to their current situation and future challenges"""
