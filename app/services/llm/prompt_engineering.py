from typing import Any, Dict, Optional, List, Literal, TypedDict, cast
import math
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

The choices section MUST:
1. Start with <CHOICES> on its own line with NO indentation
2. Have exactly three choices, each on its own line with NO indentation
3. Each choice MUST start with "Choice [A/B/C]: " followed by the choice text
4. Each choice MUST be on a single line:
   - NO line breaks (pressing Enter/Return) within a choice
   - NO word wrapping or splitting choices across lines
   - NO periods followed by "Choice" within a choice
5. End with </CHOICES> on its own line with NO indentation
6. Each choice should be meaningful and distinct
7. All choices must advance the plot in interesting ways
8. There must be NO text before or after the <CHOICES> and </CHOICES> tags

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
    # Add choice formatting rules to the system prompt
    choice_rules = """
IMPORTANT: When writing choices, ensure each choice is COMPLETELY contained on a single line.
DO NOT use any line breaks or word wrapping within choices.
"""

    base_prompt = f"""You are a master storyteller crafting an interactive educational story.

Core Story Elements:
- Setting: {state.selected_narrative_elements["setting_types"]}
- Character: {state.selected_narrative_elements["character_archetypes"]}
- Rule: {state.selected_narrative_elements["story_rules"]}
- Theme: {state.selected_theme}
- Moral Lesson: {state.selected_moral_lesson}

Sensory Details to Incorporate:
- Visual Elements: {state.selected_sensory_details["visuals"]}
- Sound Elements: {state.selected_sensory_details["sounds"]}
- Scent Elements: {state.selected_sensory_details["smells"]}

Your task is to generate engaging story chapters that:
1. Maintain narrative consistency with previous choices
2. Create meaningful consequences for user decisions
3. Seamlessly integrate lesson elements when provided
4. Use multiple paragraphs separated by blank lines to ensure readability
5. Incorporate sensory details to enhance immersion
6. Develop the theme and moral lesson naturally through the narrative

CRITICAL INSTRUCTIONS:
1. Never start your generated content with 'Chapter' followed by a number
2. Begin the narrative directly to maintain story immersion
3. Weave sensory details naturally into the narrative
4. Keep the selected theme and moral lesson as guiding principles"""

    return base_prompt + choice_rules


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


def _build_chapter_prompt(
    base_prompt: str,
    story_phase: str,
    chapter_type: ChapterType,
    lesson_question: Optional[LessonQuestion] = None,
    consequences_guidance: str = "",
    num_previous_lessons: int = 0,
    previous_lessons: Optional[List[LessonResponse]] = None,
) -> str:
    """Builds the appropriate prompt based on chapter type and state.

    Args:
        base_prompt: Base story state and history
        story_phase: Current phase of the story (Exposition, Rising, Trials, Climax, Return)
        chapter_type: Type of chapter to generate (LESSON or STORY)
        lesson_question: Question data for lesson chapters
        consequences_guidance: Guidance based on previous lesson outcomes
        num_previous_lessons: Number of previous lesson chapters
        previous_lessons: History of previous lesson responses
    """
    # Handle lesson chapters
    if chapter_type == ChapterType.LESSON:
        continuation_text = ""
        if num_previous_lessons > 0:
            continuation_text = f"""Continue the story, acknowledging the previous lesson{" and earlier lessons" if num_previous_lessons > 1 else ""} while leading to a new question.

{consequences_guidance}

"""
            if previous_lessons:
                continuation_text += f"Previous lesson history:\n{format_lesson_history(previous_lessons)}\n\n"

        return f"""{base_prompt}

{continuation_text}{_get_phase_guidance(story_phase)}

Continue the story, leading to a situation where the following lesson question naturally arises: 
{lesson_question["question"]}

CRITICAL INSTRUCTIONS:
1. {"First address the consequences of the previous lesson" if num_previous_lessons > 0 else "The story should flow naturally towards the lesson topic"}
2. Have the topic emerge naturally through dialogue, thoughts, or observations
3. End the narrative at the moment when the topic is introduced
4. DO NOT include "Lesson Question:" or repeat the question after the narrative
5. The system will handle the question presentation separately

Example of correct formats:

[Question format]
"Which makes me wonder," Alex pondered, "if they wanted to maximize the breakdown of the pumpkin, wouldn't they want to mimic the longest part of the digestive system?"

[Statement format]
Maya studied the diagram intently. The small intestine seemed too short for such a complex process - there had to be a longer section of the digestive system where most of the breakdown occurred.

Example of incorrect format:
[Narrative introduces topic]
[Additional unnecessary content]
Lesson Question: [Repeating the question]

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

{continuation_text}{_get_phase_guidance(story_phase)}

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

{continuation_text}{_get_phase_guidance(story_phase)}

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

    # Handle consequences for lesson responses
    consequences_guidance = ""
    num_previous_lessons = 0
    if previous_lessons:
        num_previous_lessons = len(previous_lessons)
        if num_previous_lessons > 0:
            last_lesson = previous_lessons[-1]
            consequences_guidance = process_consequences(
                last_lesson.is_correct,
                last_lesson.question,
                last_lesson.chosen_answer,
                state.current_chapter_number,
            )

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
