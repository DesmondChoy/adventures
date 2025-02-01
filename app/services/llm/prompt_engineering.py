from typing import Any, Dict, Optional, List
from app.models.story import StoryState


def build_system_prompt(story_config: Dict[str, Any]) -> str:
    """Create a system prompt that establishes the storytelling framework."""
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
4. End each segment with clear choice points that advance the story
5. Use multiple paragraphs separated by blank lines to ensure readability
6. Keep the story to 3 paragraphs max
7. For story choices, ALWAYS use this exact format at the end:

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


def build_user_prompt(
    story_config: Dict[str, Any],
    state: StoryState,
    question: Optional[Dict[str, Any]] = None,
    previous_questions: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Create a user prompt that includes story state and current requirements."""
    # Format previous choices with display text
    previous_choices = "Story beginning"
    if state.history:
        previous_choices = ", ".join(
            f"{choice.display_text}" for choice in state.history
        )

    base_prompt = f"""Current story state:
- Depth: {state.depth} of 3
- Previous choices: {previous_choices}"""

    if state.previous_content:
        base_prompt += f"\n\nPrevious story segment:\n{state.previous_content}"

    if previous_questions:
        last_qa = previous_questions[-1]
        consequences_guidance = process_consequences(
            state, last_qa["was_correct"], last_qa["question"], last_qa["chosen_answer"]
        )

        if question:
            return f"""{base_prompt}

Continue the story, acknowledging the previous answer{" and earlier responses" if len(previous_questions) > 1 else ""} while leading to a new question.

{consequences_guidance}

Previous Question History:
{format_question_history(previous_questions)}

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
        else:
            return f"""{base_prompt}

Continue the story based on the character's previous answer{" and earlier responses" if len(previous_questions) > 1 else ""}.

{consequences_guidance}

Previous Question History:
{format_question_history(previous_questions)}

IMPORTANT:
1. The story should clearly but naturally acknowledge the impact of their previous answer
2. Build towards a natural story decision point
3. The story choices will be provided separately - do not list them in the narrative
4. End the scene at a moment of decision - explicitly list the choices"""

    if state.depth == 1 and not state.history:
        if question:
            return f"""{base_prompt}

Generate the opening scene of the story, introducing the setting and main character. 
The scene should establish the world and protagonist while naturally leading to this educational question:
{question["question"]}

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
        else:
            return f"""{base_prompt}

Generate the opening scene of the story, introducing the setting and main character. 
The scene should establish the world and protagonist while building towards a natural educational moment.

IMPORTANT: Do not include any story choices or decision points in this scene."""

    if question:
        return f"""{base_prompt}

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

    return f"""{base_prompt}

Continue the story based on the previous choices, creating meaningful 
consequences for the character's decisions. Focus on character development and 
plot progression.

IMPORTANT:
1. DO NOT include any educational questions or historical facts
2. Build towards a natural story decision point
3. The story choices will be provided separately - do not list them in the narrative
4. End the scene at a moment of decision - explicitly list the choices"""


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
