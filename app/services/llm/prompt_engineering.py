from typing import Any, Dict, Optional, List
from app.models.story import StoryState


def build_system_prompt(
    story_config: Dict[str, Any], is_question_chapter: bool = False
) -> str:
    """Create a system prompt that establishes the storytelling framework.

    Args:
        story_config: Configuration for the story
        is_question_chapter: Whether this is a chapter that should include an educational question
    """
    return f"""You are a master storyteller crafting an interactive educational story.

Writing Style:
- Maintain a {story_config["tone"]} tone throughout the narrative
- Use vocabulary appropriate for {story_config["vocabulary_level"]}
- Follow these story rules: {", ".join(story_config["story_rules"])}

Story Elements to Include:
- Setting types: {", ".join(story_config["narrative_elements"]["setting_types"])}
- Character archetypes: {", ".join(story_config["narrative_elements"]["character_archetypes"])}

Your task is to generate engaging story segments that:
1. Maintain narrative consistency with previous choices
2. Create meaningful consequences for user decisions
3. Seamlessly integrate educational elements when provided
4. Use multiple paragraphs separated by blank lines to ensure readability"""


def _build_base_prompt(state: StoryState) -> str:
    """Creates the base prompt with story state information."""
    previous_choices = "Story beginning"
    if state.history:
        previous_choices = ", ".join(
            f"{choice.display_text}" for choice in state.history
        )

    # Calculate remaining chapters and story phase
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

    base_prompt = (
        f"Current story state:\n"
        f"- Chapter: {state.chapter} of {state.story_length}\n"
        f"- Story Phase: {story_phase}\n"
        f"- Previous choices: {previous_choices}"
    )

    if state.previous_content:
        base_prompt += f"\n\nPrevious story segment:\n{state.previous_content}"

    return base_prompt


def _build_opening_scene_prompt(
    base_prompt: str, question: Optional[Dict[str, Any]]
) -> str:
    """Builds prompt for the opening scene."""
    if question:
        chapter_count = base_prompt.split("of ")[1].split("\n")[0]
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

The educational answers that will be presented separately are:
- {question["correct_answer"]}
- {question["wrong_answer1"]}
- {question["wrong_answer2"]}"""

    chapter_count = base_prompt.split("of ")[1].split("\n")[0]
    return f"""{base_prompt}

Generate the opening scene of the story, introducing the setting and main character. 
The scene should establish the world and protagonist while building towards a natural educational moment.
Remember this is the beginning of a {chapter_count}-chapter journey.

IMPORTANT: Do not include any story choices or decision points in this scene."""


def _build_educational_question_prompt(
    base_prompt: str, question: Dict[str, Any]
) -> str:
    """Builds prompt for educational questions."""
    # Extract story phase from base prompt
    story_phase = [line for line in base_prompt.split("\n") if "Story Phase:" in line][
        0
    ].split(": ")[1]

    phase_guidance = {
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
        ),
    }.get(story_phase, "")

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

The educational answers that will be presented separately are:
- {question["correct_answer"]}
- {question["wrong_answer1"]}
- {question["wrong_answer2"]}"""


def _build_story_continuation_prompt(base_prompt: str) -> str:
    """Builds prompt for regular story continuation."""
    # Extract story phase from base prompt
    story_phase = [line for line in base_prompt.split("\n") if "Story Phase:" in line][
        0
    ].split(": ")[1]

    phase_guidance = {
        "EARLY": (
            "Focus on:\n"
            "1. Expanding the world and introducing key elements\n"
            "2. Setting up potential future challenges\n"
            "3. Developing character motivations"
        ),
        "MIDDLE": (
            "Focus on:\n"
            "1. Deepening the plot complications\n"
            "2. Raising the stakes of decisions\n"
            "3. Building towards the story's climax"
        ),
        "FINAL": (
            "Focus on:\n"
            "1. Beginning to resolve major plot threads\n"
            "2. Making choices particularly impactful\n"
            "3. Preparing for a satisfying conclusion\n"
            "4. Ensuring educational elements are reinforced"
            "5. The story must come to an end."
        ),
    }.get(story_phase, "")

    return f"""{base_prompt}

{phase_guidance}

Continue the story by:
1. Following directly from the previous story segment (if provided above)
2. Taking into account the previous choices made in the story
3. Creating meaningful consequences for these decisions
4. Focusing on character development and plot progression

IMPORTANT:
1. DO NOT include any educational questions or historical facts
2. Build towards a natural story decision point
3. The story choices will be provided separately - do not list them in the narrative
4. End the scene at a moment of decision - explicitly list the choices

CHOICE FORMAT INSTRUCTIONS:
Use this exact format for the choices at the end:

<CHOICES>
- Choice A: [First choice description]
- Choice B: [Second choice description]
</CHOICES>

The choices section must:
- Start with <CHOICES> on its own line
- List exactly two choices prefixed with "Choice A:" and "Choice B:"
- End with </CHOICES> on its own line
- Be placed after the main narrative
- Contain meaningful, contextual choices that advance the story"""


def _build_question_continuation_prompt(
    base_prompt: str,
    consequences_guidance: str,
    question: Dict[str, Any],
    num_previous_questions: int,
    previous_questions: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Builds prompt for continuing with a new question."""
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

The educational answers that will be presented separately are:
- {question["correct_answer"]}
- {question["wrong_answer1"]}
- {question["wrong_answer2"]}"""

    return prompt


def _build_answer_continuation_prompt(
    base_prompt: str,
    consequences_guidance: str,
    num_previous_questions: int,
    previous_questions: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Builds prompt for continuing after an answer."""
    prompt = f"""{base_prompt}

Continue the story based on the character's previous answer{" and earlier responses" if num_previous_questions > 1 else ""}.

{consequences_guidance}"""

    if previous_questions and len(previous_questions) > 1:
        prompt += f"\n\nPrevious question history:\n{format_question_history(previous_questions[:-1])}"

    prompt += """

IMPORTANT:
1. The story should clearly but naturally acknowledge the impact of their previous answer
2. Build towards a natural story decision point
3. The story choices will be provided separately - do not list them in the narrative
4. End the scene at a moment of decision - explicitly list the choices

CHOICE FORMAT INSTRUCTIONS:
Use this exact format for the choices at the end:

<CHOICES>
- Choice A: [First choice description]
- Choice B: [Second choice description]
</CHOICES>

The choices section must:
- Start with <CHOICES> on its own line
- List exactly two choices prefixed with "Choice A:" and "Choice B:"
- End with </CHOICES> on its own line
- Be placed after the main narrative
- Contain meaningful, contextual choices that advance the story"""

    return prompt


def build_user_prompt(
    story_config: Dict[str, Any],
    state: StoryState,
    question: Optional[Dict[str, Any]] = None,
    previous_questions: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Create a user prompt that includes story state and current requirements."""
    # Determine if this is a question chapter (odd chapters are for questions)
    is_question_chapter = state.chapter % 2 == 1

    # Get system prompt with appropriate choice instructions
    system_prompt = build_system_prompt(story_config, is_question_chapter)

    base_prompt = _build_base_prompt(state)

    # Handle consequences for educational questions
    consequences_guidance = ""
    if previous_questions and (state.chapter % 2 == 0):
        last_qa = previous_questions[-1]
        consequences_guidance = process_consequences(
            state, last_qa["was_correct"], last_qa["question"], last_qa["chosen_answer"]
        )

    # Handle opening scene
    if state.chapter == 1 and not state.history:
        user_prompt = _build_opening_scene_prompt(base_prompt, question)
    # Alternate between educational questions (odd chapters) and story choices (even chapters)
    elif state.chapter % 2 == 1:
        # Odd chapters are for educational questions
        if question:
            # For chapter > 1, we need to continue the story from previous choice
            if state.chapter > 1:
                num_previous_questions = (
                    len(previous_questions) if previous_questions else 0
                )
                user_prompt = _build_question_continuation_prompt(
                    base_prompt,
                    consequences_guidance,
                    question,
                    num_previous_questions,
                    previous_questions,
                )
            else:
                user_prompt = _build_educational_question_prompt(base_prompt, question)
    else:
        # Even chapters are for story choices
        if previous_questions:
            user_prompt = _build_answer_continuation_prompt(
                base_prompt,
                consequences_guidance,
                len(previous_questions),
                previous_questions,
            )
        else:
            user_prompt = _build_story_continuation_prompt(base_prompt)

    # Return the combined prompt with system prompt and user content
    return f"{system_prompt}\n\n---\n\n{user_prompt}"


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
    state: StoryState,
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
