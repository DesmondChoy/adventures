from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.models.story import (
    StoryState,
    StoryNode,
    QuestionHistory,
    StoryChoice,
    ChoiceHistory,
)
from app.services.llm import LLMService
from app.init_data import sample_question
import yaml
import pandas as pd
import asyncio
import re
import logging
from functools import lru_cache

router = APIRouter()
llm_service = LLMService()
logger = logging.getLogger("story_app")


# Cache for story and lesson data
@lru_cache(maxsize=1)
def load_story_data():
    with open("app/data/stories.yaml", "r") as f:
        return yaml.safe_load(f)


@lru_cache(maxsize=1)
def load_lesson_data():
    return pd.read_csv("app/data/lessons.csv")


# Constants for streaming optimization
WORD_BATCH_SIZE = 5  # Number of words to send at once
WORD_DELAY = 0.02  # Reduced delay between word batches
PARAGRAPH_DELAY = 0.1  # Reduced delay between paragraphs


async def generate_story_node(
    story_category: str, lesson_topic: str, state: StoryState
) -> StoryNode:
    """Generate a complete story node with content and choices.

    This function orchestrates the story generation process by:
    1. Loading the appropriate story configuration and lesson data
    2. Using the LLM service to generate the story content as a stream
    3. Processing the streamed content into a complete story node
    4. Adding appropriate choices based on the story state

    This is different from the LLM service's generate_story_stream which only
    handles the raw story content generation. This function provides the complete
    story node that includes both content and available choices.

    Args:
        story_category: The category of story being generated
        lesson_topic: The educational topic being covered
        state: The current state of the story session

    Returns:
        StoryNode: A complete story node with content and choices
    """
    # Load story configuration
    story_data = load_story_data()
    story_config = story_data["story_categories"][story_category]

    # Determine if we need an educational question
    is_question_chapter = state.chapter % 2 == 1

    # Load question for odd chapters (including chapter 1)
    question = None
    previous_questions = []

    # Get previous questions if we have history
    if state.question_history:
        previous_questions = [
            {
                "question": qh.question,
                "chosen_answer": qh.chosen_answer,
                "was_correct": qh.was_correct,
            }
            for qh in state.question_history
        ]
        logger.debug("\nDEBUG: Previous questions history:")
        for i, pq in enumerate(previous_questions, 1):
            logger.debug(f"Q{i}: {pq['question']['question']}")
            logger.debug(
                f"Chosen: {pq['chosen_answer']} (Correct: {pq['was_correct']})"
            )

    # Load new question if at question chapter
    if is_question_chapter:
        try:
            # Get list of previously asked questions
            used_questions = [qh.question["question"] for qh in state.question_history]
            # Sample a new question
            question = sample_question(lesson_topic, exclude_questions=used_questions)
            logger.debug(f"DEBUG: Selected question: {question['question']}")
            logger.debug(f"DEBUG: Answers: {question['answers']}")
        except ValueError as e:
            logger.error(f"Error sampling question: {e}")
            raise

    # Generate story content using LLM
    story_content = ""
    try:
        async for chunk in llm_service.generate_story_stream(
            story_config,
            state,
            question,
            previous_questions,
        ):
            story_content += chunk
    except Exception as e:
        logger.error("\n=== ERROR: LLM Request Failed ===")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error("===============================\n")
        raise

    # Extract choices based on chapter
    if is_question_chapter and question:
        # Create choices from randomized answers
        story_choices = []
        for answer in question["answers"]:
            story_choices.append(
                StoryChoice(
                    text=answer["text"],
                    next_node="correct"
                    if answer["is_correct"]
                    else f"wrong{len(story_choices) + 1}",
                )
            )
    else:
        # Extract structured choices from the story content
        try:
            # Find the choices section
            choices_start = story_content.find("<CHOICES>")
            choices_end = story_content.find("</CHOICES>")

            if choices_start == -1 or choices_end == -1:
                raise ValueError("Could not find choice markers in story content")

            # Extract and clean up the choices section
            choices_text = story_content[choices_start:choices_end].strip()
            # Remove the choices section from the main content
            story_content = story_content[:choices_start].strip()

            # Parse choices using regex
            choice_pattern = r"Choice ([ABC]): (.+)$"
            choices = []

            for line in choices_text.split("\n"):
                match = re.search(choice_pattern, line.strip())
                if match:
                    choices.append(match.group(2).strip())

            if len(choices) != 3:
                raise ValueError("Must have exactly 3 story choices")

            # Create StoryChoice objects
            story_choices = [
                StoryChoice(text=choice_text, next_node=f"node_{state.chapter}_{i}")
                for i, choice_text in enumerate(choices)
            ]
        except Exception as e:
            logger.error(f"Error parsing choices: {e}")
            # Fallback to generic choices if parsing fails
            story_choices = [
                StoryChoice(
                    text=f"Continue with option {i + 1}",
                    next_node=f"node_{state.chapter}_{i}",
                )
                for i in range(3)
            ]

    # Debug output for choices
    logger.debug("\n=== DEBUG: Story Choices ===")
    for i, choice in enumerate(story_choices, 1):
        logger.debug(f"Choice {i}: {choice.text} (next_node: {choice.next_node})")
    logger.debug("========================\n")

    # Store the current content in the state's history
    if state.previous_content:
        state.all_previous_content.append(state.previous_content)
    state.previous_content = story_content

    return StoryNode(content=story_content, choices=story_choices)


@router.websocket("/ws/story/{story_category}/{lesson_topic}")
async def story_websocket(websocket: WebSocket, story_category: str, lesson_topic: str):
    """Handle WebSocket connection for story streaming."""
    await websocket.accept()

    # Pre-load data at connection time
    story_config = load_story_data()
    lesson_data = load_lesson_data()

    # Initialize state as None - will be set after receiving initial state message
    state = None

    try:
        while True:
            data = await websocket.receive_json()
            logger.debug(f"Received WebSocket data: {data}")

            # If we receive a state update, use it to initialize our state
            if "state" in data:
                client_state = data["state"]
                logger.debug(
                    f"Received client state with story_length: {client_state.get('story_length', 3)}"
                )

                # Ensure all required fields are present with appropriate defaults
                validated_state = {
                    "current_node": client_state.get("current_node", "start"),
                    "chapter": max(1, client_state.get("chapter", 1)),
                    "correct_answers": max(0, client_state.get("correct_answers", 0)),
                    "total_questions": max(0, client_state.get("total_questions", 0)),
                    "story_length": max(3, min(7, client_state.get("story_length", 3))),
                    "previous_content": client_state.get("previous_content", None),
                    "all_previous_content": client_state.get(
                        "all_previous_content", []
                    ),
                    "question_history": client_state.get("question_history", []),
                }

                # Convert history from client format to ChoiceHistory objects
                history = []
                client_history = client_state.get("history", [])
                if isinstance(client_history, list):
                    for choice in client_history:
                        if isinstance(choice, dict):
                            history.append(
                                ChoiceHistory(
                                    node_id=choice.get("node_id", ""),
                                    display_text=choice.get("display_text", ""),
                                )
                            )
                        elif isinstance(choice, str):
                            # Handle legacy format where only node_id was stored
                            history.append(
                                ChoiceHistory(
                                    node_id=choice, display_text="Unknown choice"
                                )
                            )

                # Initialize or update state with validated values
                state = StoryState(
                    current_node=validated_state["current_node"],
                    chapter=validated_state["chapter"],
                    history=history,
                    correct_answers=validated_state["correct_answers"],
                    total_questions=validated_state["total_questions"],
                    previous_content=validated_state["previous_content"],
                    all_previous_content=validated_state["all_previous_content"],
                    question_history=validated_state["question_history"],
                    story_length=validated_state["story_length"],
                )
                logger.debug(f"Initialized state with validated values: {state}")
                continue

            # Ensure state is initialized before processing any choices
            if state is None:
                logger.error(
                    "State not initialized. Waiting for initial state message."
                )
                continue

            choice_data = data.get("choice")
            if choice_data is None:
                continue

            # Extract both node_id and display_text from choice
            if isinstance(choice_data, dict):
                node_id = choice_data.get("node_id", "")
                display_text = choice_data.get("display_text", "")
            else:
                # Handle legacy format where only node_id was sent
                node_id = choice_data
                display_text = "Unknown choice"

            # Only append choice and increment chapter for non-start messages
            if node_id != "start":
                if state.chapter % 2 == 1:  # Educational answer
                    # Get list of previously asked questions
                    used_questions = [
                        qh.question["question"] for qh in state.question_history
                    ]

                    try:
                        # Sample the current question again to get its data
                        current_question = sample_question(
                            lesson_topic,
                            exclude_questions=used_questions[:-1]
                            if used_questions
                            else None,
                        )

                        # Record this Q&A in history
                        was_correct = node_id == "correct"
                        state.question_history.append(
                            QuestionHistory(
                                question=current_question,
                                chosen_answer=display_text,
                                was_correct=was_correct,
                            )
                        )

                        if was_correct:
                            state.correct_answers += 1
                        state.total_questions += 1
                    except ValueError as e:
                        logger.error(f"Error processing answer: {e}")
                        raise
                else:  # Narrative choice (even chapters)
                    narrative_choices = [
                        ch
                        for ch in state.history
                        if not ch.node_id in ["correct", "wrong1", "wrong2"]
                    ]
                    narrative_choices.append(
                        ChoiceHistory(node_id=node_id, display_text=display_text)
                    )
                    MAX_NARRATIVE_CHOICES = state.story_length
                    state.history = narrative_choices[-MAX_NARRATIVE_CHOICES:]

                state.chapter += 1
                logger.debug(
                    f"Updated state after choice: chapter={state.chapter}, history={state.history}"
                )

                # Check if we've reached the story length limit
                if state.chapter > state.story_length:
                    await websocket.send_text(
                        "\n\nCongratulations! You've completed your journey."
                    )
                    await websocket.send_json(
                        {
                            "type": "story_complete",
                            "stats": {
                                "total_questions": state.total_questions,
                                "correct_answers": state.correct_answers,
                                "completion_percentage": round(
                                    (
                                        state.correct_answers
                                        / state.total_questions
                                        * 100
                                    )
                                    if state.total_questions > 0
                                    else 0,
                                    1,
                                ),
                            },
                        }
                    )
                    break

            try:
                story_node = await generate_story_node(
                    story_category, lesson_topic, state
                )
                paragraphs = [
                    p.strip() for p in story_node.content.split("\n\n") if p.strip()
                ]

                for i, paragraph in enumerate(paragraphs):
                    if i > 0:
                        await websocket.send_text("\n\n")
                        await asyncio.sleep(PARAGRAPH_DELAY)

                    words = paragraph.split()
                    for i in range(0, len(words), WORD_BATCH_SIZE):
                        batch = words[i : i + WORD_BATCH_SIZE]
                        await websocket.send_text(" ".join(batch) + " ")
                        await asyncio.sleep(WORD_DELAY)

                await websocket.send_json(
                    {
                        "type": "choices",
                        "choices": [
                            {
                                "text": choice.text,
                                "id": choice.next_node,
                                "node_id": choice.next_node,
                                "display_text": choice.text,
                            }
                            for choice in story_node.choices
                        ],
                    }
                )
            except WebSocketDisconnect:
                logger.info("Client disconnected during story generation")
                break
            except Exception as e:
                logger.error(f"Error during story generation: {e}")
                await websocket.send_text(
                    "An error occurred while generating the story."
                )
                break

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        logger.info("WebSocket connection closed")
