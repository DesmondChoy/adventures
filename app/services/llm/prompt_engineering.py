from typing import Any, Dict, Optional, List, Literal
from app.models.story import StoryState


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


def _format_educational_answers(question: Dict[str, Any]) -> str:
    """Format the educational answers section consistently."""
    return f"""The educational answers that will be presented separately are:
- {question["correct_answer"]}
- {question["wrong_answer1"]}
- {question["wrong_answer2"]}"""


def _get_phase_guidance(story_phase: str) -> str:
    """Get the appropriate guidance based on story phase."""
    return {
        "EARLY": (
            "Story Focus:\n"
            "- Introduce educational elements that help establish the world\n"
            "- Connect learning moments to character discovery\n"
            "- Set up future educational themes"
        ),
        "MIDDLE": (
            "Story Focus:\n"
            "- Deepen the educational significance to the plot\n"
            "- Connect learning to rising stakes\n"
            "- Use knowledge as a tool for overcoming challenges"
        ),
        "FINAL": (
            "Story Focus:\n"
            "- Bring educational themes full circle\n"
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
3. Seamlessly integrate educational elements when provided
4. Use multiple paragraphs separated by blank lines to ensure readability"""


def _build_base_prompt(state: StoryState) -> str:
    """Creates the base prompt with story state information."""
    # Build chapter history with decisions and outcomes
    chapter_history = []

    # Track question/answer history alongside story progression
    qa_index = 0

    for chapter_num in range(1, state.chapter + 1):
        if chapter_num > 1:  # Add separator between chapters
            chapter_history.append("\n---\n")

        # Add chapter number
        chapter_history.append(f"Chapter {chapter_num}:")

        # Add the chapter content if available
        if chapter_num < state.chapter:  # Previous chapters
            content_index = chapter_num - 1  # Convert to 0-based index
            if content_index < len(state.all_previous_content):
                chapter_history.append(state.all_previous_content[content_index])
            elif chapter_num == state.chapter - 1 and state.previous_content:
                # Use previous_content only for the most recently completed chapter
                chapter_history.append(state.previous_content)

        # Add educational outcomes for odd-numbered chapters (question chapters)
        if chapter_num % 2 == 1 and qa_index < len(state.question_history):
            qa = state.question_history[qa_index]
            chapter_history.extend(
                [
                    f"\nQuestion: {qa.question['question']}",
                    f"\nStudent's Answer: {qa.chosen_answer}",
                    f"\nOutcome: {'Correct' if qa.was_correct else 'Incorrect'}",
                    f"\nCorrect Answer: {qa.question['correct_answer']}",
                ]
            )
            qa_index += 1

        # Add story choices for even-numbered chapters
        if chapter_num % 2 == 0 and chapter_num < state.chapter:
            # Only include choices for completed even-numbered chapters
            narrative_choices = [
                ch
                for ch in state.history
                if not ch.node_id in ["correct", "wrong1", "wrong2"]
            ]
            choice_index = (chapter_num - 2) // 2  # Adjust index for even chapters
            if choice_index < len(narrative_choices):
                chapter_history.append(
                    f"\nChoice Made: {narrative_choices[choice_index].display_text}"
                )

    # Calculate story phase
    remaining_chapters = state.story_length - state.chapter
    story_phase = (
        "EARLY"
        if state.chapter == 1
        else "FINAL"
        if remaining_chapters <= 1
        else "LATE"
        if remaining_chapters <= state.story_length // 2
        else "MIDDLE"
    )

    # Build the base prompt with complete history
    base_prompt = (
        f"Current story state:\n"
        f"- Chapter: {state.chapter} of {state.story_length}\n"
        f"- Story Phase: {story_phase}\n"
        f"- Educational Progress: {state.correct_answers}/{state.total_questions} questions answered correctly\n\n"
        f"Complete Story History:\n"
        f"{''.join(filter(None, chapter_history))}"  # filter(None) removes empty strings
    )

    return base_prompt, story_phase


def _build_chapter_prompt(
    base_prompt: str,
    story_phase: str,
    chapter_type: Literal[
        "opening", "question", "story", "question_continuation", "answer_continuation"
    ],
    question: Optional[Dict[str, Any]] = None,
    consequences_guidance: str = "",
    num_previous_questions: int = 0,
    previous_questions: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Builds the appropriate prompt based on chapter type and state."""

    phase_guidance = _get_phase_guidance(story_phase)

    # Build prompt based on chapter type
    if chapter_type == "opening":
        chapter_count = base_prompt.split("of ")[1].split("\n")[0]
        if question:
            return f"""{base_prompt}

Generate the opening scene of the story, introducing the setting and main character. 
The scene should establish the world and protagonist while naturally leading to this educational question:
{question["question"]}

Remember this is the beginning of a {chapter_count}-chapter journey.

CRITICAL INSTRUCTIONS:
1. Create an immersive fantasy world that will subtly connect to {question["question"].split()[0]}'s history
2. The question should emerge naturally from the story events or character interactions
3. DO NOT include any story-based choices or decisions
4. DO NOT use bullet points, numbered lists, or dashes
5. DO NOT end with "What should X do?" or similar prompts
6. The question should feel like a natural part of the character's discovery

{_format_educational_answers(question)}"""
        else:
            return f"""{base_prompt}

Generate the opening scene of the story, introducing the setting and main character. 
The scene should establish the world and protagonist while building towards a natural educational moment.
Remember this is the beginning of a {chapter_count}-chapter journey.

IMPORTANT: Do not include any story choices or decision points in this scene."""

    elif chapter_type == "question":
        return f"""{base_prompt}

{phase_guidance}

Continue the story, leading to a situation where the following educational question naturally arises: 
{question["question"]}

CRITICAL INSTRUCTIONS:
1. The story should flow naturally towards the educational question
2. The question should be asked by a character or emerge from the situation
3. DO NOT include any story-based choices or decisions
4. DO NOT use bullet points, numbered lists, or dashes
5. DO NOT end with "What should X do?" or similar prompts
6. Focus ONLY on building up to the educational question

{_format_educational_answers(question)}"""

    elif chapter_type == "story":
        return f"""{base_prompt}

{phase_guidance}

Continue the story by:
1. Following directly from the previous chapter content (if provided above)
2. Taking into account the previous choices made in the story
3. Creating meaningful consequences for these decisions
4. Focusing on character development and plot progression

IMPORTANT:
1. DO NOT include any educational questions or historical facts
2. Build towards a natural story decision point
3. The story choices will be provided separately - do not list them in the narrative
4. End the scene at a moment of decision - explicitly list the choices

{CHOICE_FORMAT_INSTRUCTIONS}"""

    elif chapter_type == "question_continuation":
        prompt = f"""{base_prompt}

Continue the story, acknowledging the previous answer{" and earlier responses" if num_previous_questions > 1 else ""} while leading to a new question.

{consequences_guidance}"""

        if previous_questions and len(previous_questions) > 1:
            prompt += f"\n\nPrevious question history:\n{format_question_history(previous_questions[:-1])}"

        prompt += f"""

The story should naturally build towards this question:
{question["question"]}

CRITICAL INSTRUCTIONS:
1. First address the consequences of the previous answer
2. Then naturally transition to a situation where the new question arises
3. The question should emerge from the story events or character interactions
4. DO NOT include any story-based choices or decisions
5. The question should feel like a natural part of the character's journey

{_format_educational_answers(question)}"""

        return prompt

    else:  # answer_continuation
        prompt = f"""{base_prompt}

Continue the story based on the character's previous answer{" and earlier responses" if num_previous_questions > 1 else ""}.

{consequences_guidance}"""

        if previous_questions and len(previous_questions) > 1:
            prompt += f"\n\nPrevious question history:\n{format_question_history(previous_questions[:-1])}"

        prompt += f"""

IMPORTANT:
1. The story should clearly but naturally acknowledge the impact of their previous answer
2. Build towards a natural story decision point
3. The story choices will be provided separately - do not list them in the narrative
4. End the scene at a moment of decision - explicitly list the choices

{CHOICE_FORMAT_INSTRUCTIONS}"""

        return prompt


def build_user_prompt(
    state: StoryState,
    question: Optional[Dict[str, Any]] = None,
    previous_questions: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Create a user prompt that includes story state and current requirements."""
    base_prompt, story_phase = _build_base_prompt(state)

    # Handle consequences for educational questions
    consequences_guidance = ""
    if previous_questions and (state.chapter % 2 == 0):
        last_qa = previous_questions[-1]
        consequences_guidance = process_consequences(
            last_qa["was_correct"], last_qa["question"], last_qa["chosen_answer"]
        )

    # Handle opening scene
    if state.chapter == 1 and not state.history:
        return _build_chapter_prompt(base_prompt, story_phase, "opening", question)
    # Alternate between educational questions (odd chapters) and story choices (even chapters)
    elif state.chapter % 2 == 1:
        # Odd chapters are for educational questions
        if question:
            # For chapter > 1, we need to continue the story from previous choice
            if state.chapter > 1:
                num_previous_questions = (
                    len(previous_questions) if previous_questions else 0
                )
                return _build_chapter_prompt(
                    base_prompt,
                    story_phase,
                    "question_continuation",
                    question,
                    consequences_guidance,
                    num_previous_questions,
                    previous_questions,
                )
            else:
                return _build_chapter_prompt(
                    base_prompt, story_phase, "question", question
                )
    else:
        # Even chapters are for story choices
        if previous_questions:
            return _build_chapter_prompt(
                base_prompt,
                story_phase,
                "answer_continuation",
                consequences_guidance=consequences_guidance,
                num_previous_questions=len(previous_questions),
                previous_questions=previous_questions,
            )
        else:
            return _build_chapter_prompt(base_prompt, story_phase, "story")


def format_question_history(previous_questions: List[Dict[str, Any]]) -> str:
    """Format the question history for inclusion in the prompt."""
    history = []
    for i, qa in enumerate(previous_questions, 1):
        history.append(f"Q{i}: {qa['question']['question']}")
        history.append(
            f"Chosen: {qa['chosen_answer']} ({'Correct' if qa['was_correct'] else 'Incorrect'})"
        )
        if not qa["was_correct"]:
            history.append(f"Correct Answer: {qa['question']['correct_answer']}")
        history.append("")  # Add blank line between QAs
    return "\n".join(history)


def process_consequences(
    was_correct: Optional[bool] = None,
    previous_question: Optional[Dict[str, Any]] = None,
    chosen_answer: Optional[str] = None,
) -> str:
    """Generate appropriate story consequences based on question response."""
    if was_correct is None or previous_question is None:
        return ""

    if was_correct:
        return f"""The story should:
- Acknowledge that the character correctly identified {previous_question["correct_answer"]} as the answer
- Show how this understanding of {previous_question["question"]} connects to their current situation
- Use this success to build confidence for future challenges"""

    return f"""The story should:
- Acknowledge that the character answered {chosen_answer}
- Explain that {previous_question["correct_answer"]} was the correct answer
- Show how this misunderstanding of {previous_question["question"]} leads to a valuable learning moment
- Use this as an opportunity for growth and deeper understanding
- Connect the correction to their current situation and future challenges"""
