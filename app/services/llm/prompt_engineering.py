from typing import Any, Dict, Optional, List, Literal, TypedDict, cast
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
4. Each choice MUST be on a single line (NO line breaks within choices)
5. End with </CHOICES> on its own line with NO indentation
6. Each choice should be meaningful and distinct
7. All choices must advance the plot in interesting ways
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


def _get_phase_guidance(story_phase: str) -> str:
    """Get the appropriate guidance based on story phase."""
    return {
        "EARLY": (
            "Phase Guidance:\n"
            "- Introduce lesson elements that help establish the world\n"
            "- Connect learning moments to character discovery\n"
            "- Set up future lesson themes"
        ),
        "MIDDLE": (
            "Phase Guidance:\n"
            "- Deepen the lesson significance to the plot\n"
            "- Connect learning to rising stakes\n"
            "- Use knowledge as a tool for overcoming challenges"
        ),
        "FINAL": (
            "Phase Guidance:\n"
            "- Bring lesson themes full circle\n"
            "- Show how knowledge has transformed the character\n"
            "- Create satisfying connections to previous learning moments\n"
            "- Prepare for a satisfying conclusion"
        ),
    }.get(story_phase, "")


def build_system_prompt(story_config: Dict[str, Any]) -> str:
    """Create a system prompt that establishes the storytelling framework.

    Args:
        story_config: Configuration for the story
    """
    # Add choice formatting rules to the system prompt
    choice_rules = """
IMPORTANT: When writing choices, ensure each choice is COMPLETELY contained on a single line.
DO NOT use any line breaks or word wrapping within choices.
"""

    base_prompt = f"""You are a master storyteller crafting an interactive educational story.

Writing Style:
- Maintain a {story_config["tone"]} tone throughout the narrative
- Use vocabulary appropriate for {story_config["vocabulary_level"]}
- Follow these story rules: {", ".join(story_config["story_rules"])}

Story Elements to Include:
- Setting types: {", ".join(story_config["narrative_elements"]["setting_types"])}
- Character archetypes: {", ".join(story_config["narrative_elements"]["character_archetypes"])}

Your task is to generate engaging story chapters that:
1. Maintain narrative consistency with previous choices
2. Create meaningful consequences for user decisions
3. Seamlessly integrate lesson elements when provided
4. Use multiple paragraphs separated by blank lines to ensure readability"""

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

    # Calculate story phase based on story progression percentage
    total_chapters = state.story_length
    current_chapter = state.current_chapter_number
    progress_percentage = (current_chapter / total_chapters) * 100

    # Educational context: Story phases help maintain narrative pacing
    # EARLY: First chapter (introduction, world-building)
    # MIDDLE: Core chapters (rising action, character development)
    # LATE: Final quarter (building to climax)
    # FINAL: Last chapter (resolution)
    story_phase = (
        "EARLY"
        if current_chapter == 1
        else "FINAL"
        if current_chapter == total_chapters
        else "LATE"
        if progress_percentage >= 75  # Last quarter of the story
        else "MIDDLE"
    )

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
    is_opening: bool = False,
) -> str:
    """Builds the appropriate prompt based on chapter type and state.

    Args:
        base_prompt: Base story state and history
        story_phase: Current phase of the story (EARLY, MIDDLE, FINAL)
        chapter_type: Type of chapter to generate (LESSON or STORY)
        lesson_question: Question data for lesson chapters
        consequences_guidance: Guidance based on previous lesson outcomes
        num_previous_lessons: Number of previous lesson chapters
        previous_lessons: History of previous lesson responses
        is_opening: Whether this is the opening chapter
    """
    # Handle opening chapter special case
    if is_opening:
        chapter_count = base_prompt.split("of ")[1].split("\n")[0]
        if chapter_type == ChapterType.LESSON:
            return f"""{base_prompt}

Generate the opening scene of the story, introducing the setting and main character. 
The scene should establish the world and protagonist while naturally leading to this lesson question:
{lesson_question["question"]}

Remember this is the beginning of a {chapter_count}-chapter journey.

CRITICAL INSTRUCTIONS:
1. Create an immersive fantasy world that subtly connects to {lesson_question["topic"]}, including but not limited to {lesson_question["subtopic"]}
2. The question should emerge naturally from the story events or character interactions
3. DO NOT include any story-based choices or decisions
4. DO NOT use bullet points, numbered lists, or dashes
5. DO NOT end with "What should X do?" or similar prompts
6. The question should feel like a natural part of the character's discovery

{_format_lesson_answers(lesson_question)}"""
        else:
            return f"""{base_prompt}

Generate the opening scene of the story, introducing the setting and main character. 
The scene should establish the world and protagonist while building towards a natural lesson moment.
Remember this is the beginning of a {chapter_count}-chapter journey.

IMPORTANT: Do not include any story choices or decision points in this scene."""

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
1. {"First address the consequences of the previous lesson" if num_previous_lessons > 0 else "The story should flow naturally towards the lesson question"}
2. Then naturally transition to a situation where the new question arises
3. The question should emerge from the story events or character interactions
4. DO NOT include any story-based choices or decisions
5. DO NOT use bullet points, numbered lists, or dashes
6. The question should feel like a natural part of the character's journey

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
                state.current_chapter_number,  # Pass current chapter number
            )

    # Determine chapter properties
    is_opening = state.current_chapter_number == 1
    current_chapter_type = state.planned_chapter_types[state.current_chapter_number - 1]
    chapter_type = ChapterType.LESSON if lesson_question else current_chapter_type

    # Build the chapter prompt
    return _build_chapter_prompt(
        base_prompt=base_prompt,
        story_phase=story_phase,
        chapter_type=chapter_type,
        lesson_question=lesson_question,
        consequences_guidance=consequences_guidance,
        num_previous_lessons=num_previous_lessons,
        previous_lessons=previous_lessons,
        is_opening=is_opening,
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
