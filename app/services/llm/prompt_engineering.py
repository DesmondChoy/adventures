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
Use this exact format for the choices at the end:

<CHOICES>
Choice A: [First choice description]
Choice B: [Second choice description]
Choice C: [Third choice description]
</CHOICES>

The choices section must:
- Start with <CHOICES> on its own line
- List exactly three choices prefixed with "Choice A:", "Choice B:", and "Choice C:"
- End with </CHOICES> on its own line
- Be placed after the main narrative
- Each choice should be meaningful and distinct
- Choices should represent different approaches or directions for the story
- All choices must advance the plot in interesting ways"""


class LessonQuestion(TypedDict):
    """Structure of a lesson question."""
    question: str
    answers: List[Dict[str, Any]]  # List of {text: str, is_correct: bool}


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
            "Story Focus:\n"
            "- Introduce lesson elements that help establish the world\n"
            "- Connect learning moments to character discovery\n"
            "- Set up future lesson themes"
        ),
        "MIDDLE": (
            "Story Focus:\n"
            "- Deepen the lesson significance to the plot\n"
            "- Connect learning to rising stakes\n"
            "- Use knowledge as a tool for overcoming challenges"
        ),
        "FINAL": (
            "Story Focus:\n"
            "- Bring lesson themes full circle\n"
            "- Show how knowledge has transformed the character\n"
            "- Create satisfying connections to previous learning moments"
            "- Prepare for a satisfying conclusion"
        ),
    }.get(story_phase, "")


def build_system_prompt(story_config: Dict[str, Any]) -> str:
    """Create a system prompt that establishes the storytelling framework.

    Args:
        story_config: Configuration for the story
    """
    return f"""You are a master storyteller crafting an interactive educational story.

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


def _build_base_prompt(state: AdventureState) -> tuple[str, str]:
    """Creates the base prompt with story state information."""
    # Build chapter history with decisions and outcomes
    chapter_history: list[str] = []

    for chapter in state.chapters:  # type: ChapterData
        if len(chapter_history) > 0:  # Add separator between chapters
            chapter_history.append("\n---\n")

        # Add chapter number
        chapter_history.append(f"Chapter {chapter.chapter_number}:")

        # Add the chapter content
        chapter_history.append(chapter.content)

        # Add lesson outcomes for lesson chapters
        if chapter.chapter_type == ChapterType.LESSON and chapter.response:
            lesson_response = cast(LessonResponse, chapter.response)  # Type cast since we know it's a LessonResponse
            # Find the correct answer from the answers array
            correct_answer = next(
                answer["text"]
                for answer in lesson_response.question["answers"]
                if answer["is_correct"]
            )
            chapter_history.extend(
                [
                    f"\nLesson Question: {lesson_response.question['question']}",
                    f"\nStudent's Answer: {lesson_response.chosen_answer}",
                    f"\nOutcome: {'Correct' if lesson_response.is_correct else 'Incorrect'}",
                    f"\nCorrect Answer: {correct_answer}",
                ]
            )

        # Add story choices for story chapters
        if chapter.chapter_type == ChapterType.STORY and chapter.response:
            story_response = cast(StoryResponse, chapter.response)  # Type cast since we know it's a StoryResponse
            chapter_history.append(
                f"\nChoice Made: {story_response.choice_text}"
            )

    # Calculate story phase
    remaining_chapters = state.story_length - state.current_chapter_number
    story_phase = (
        "EARLY"
        if state.current_chapter_number == 1
        else "FINAL"
        if remaining_chapters <= 1
        else "LATE"
        if remaining_chapters <= state.story_length // 2
        else "MIDDLE"
    )

    # Build the base prompt with complete history
    base_prompt = (
        f"Current story state:\n"
        f"- Chapter: {state.current_chapter_number} of {state.story_length}\n"
        f"- Story Phase: {story_phase}\n"
        f"- Lesson Progress: {state.correct_lesson_answers}/{state.total_lessons} lessons answered correctly\n\n"
        f"Complete Story History:\n"
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
1. Create an immersive fantasy world that will subtly connect to {lesson_question["question"].split()[0]}'s history
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
            if previous_lessons and len(previous_lessons) > 1:
                continuation_text += f"Previous lesson history:\n{format_lesson_history(previous_lessons[:-1])}\n\n"

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
    else:
        continuation_text = ""
        if num_previous_lessons > 0:
            continuation_text = f"""Continue the story based on the character's previous lesson{" and earlier lessons" if num_previous_lessons > 1 else ""}.

{consequences_guidance}

"""
            if previous_lessons and len(previous_lessons) > 1:
                continuation_text += f"Previous lesson history:\n{format_lesson_history(previous_lessons[:-1])}\n\n"

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
                last_lesson.chosen_answer
            )

    # Determine chapter properties
    is_opening = state.current_chapter_number == 1
    chapter_type = ChapterType.LESSON if lesson_question else ChapterType.STORY

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
) -> str:
    """Generate appropriate story consequences based on lesson response."""
    # Find the correct answer from the answers array
    correct_answer = next(
        answer["text"]
        for answer in lesson_question["answers"]
        if answer["is_correct"]
    )

    if is_correct:
        return f"""The story should:
- Acknowledge that the character correctly identified {correct_answer} as the answer
- Show how this understanding of {lesson_question["question"]} connects to their current situation
- Use this success to build confidence for future challenges"""

    return f"""The story should:
- Acknowledge that the character answered {chosen_answer}
- Explain that {correct_answer} was the correct answer
- Show how this misunderstanding of {lesson_question["question"]} leads to a valuable learning moment
- Use this as an opportunity for growth and deeper understanding
- Connect the correction to their current situation and future challenges"""
