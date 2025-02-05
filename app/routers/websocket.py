from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.models.story import (
    StoryState,
    StoryNode,
    QuestionHistory,
    StoryChoice,
    ChoiceHistory,
    StoryChoices,
)
from app.services.llm import LLMService
import yaml
import pandas as pd
import asyncio
import re
from functools import lru_cache

router = APIRouter()
llm_service = LLMService()


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

    # Determine if we need an educational question (odd depths) or story choices (even depths)
    is_question_depth = state.depth % 2 == 1  # True for depths 1, 3, etc.

    # Load question for odd depths (including depth 1)
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
        print("\nDEBUG: Previous questions history:")
        for i, pq in enumerate(previous_questions, 1):
            print(f"Q{i}: {pq['question']['question']}")
            print(f"Chosen: {pq['chosen_answer']} (Correct: {pq['was_correct']})")

    # Load new question if at question depth
    if is_question_depth:
        lesson_data = load_lesson_data()
        print(f"\nDEBUG: Loading question at depth {state.depth}")
        print(
            f"DEBUG: Looking for topic '{lesson_topic}' in available topics: {lesson_data['topic'].unique()}"
        )

        relevant_lessons = lesson_data[lesson_data["topic"] == lesson_topic]
        print(f"DEBUG: Found {len(relevant_lessons)} lessons for topic {lesson_topic}")

        if not relevant_lessons.empty:
            question = relevant_lessons.iloc[
                state.total_questions % len(relevant_lessons)
            ].to_dict()
            print(f"DEBUG: Selected question: {question['question']}")
            print(
                f"DEBUG: Choices: {question['correct_answer']}, {question['wrong_answer1']}, {question['wrong_answer2']}"
            )

    # Generate story content using LLM
    story_content = ""
    try:
        async for chunk in llm_service.generate_story_stream(
            story_config,
            state,
            question,  # Pass question for odd depths
            previous_questions,  # Pass all previous Q&A history
        ):
            story_content += chunk
    except Exception as e:
        print(f"\n=== ERROR: LLM Request Failed ===")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        print("===============================\n")
        raise  # Re-raise the exception after logging

    # Extract choices based on depth
    if is_question_depth and question:
        story_choices = [
            StoryChoice(text=question["correct_answer"], next_node="correct"),
            StoryChoice(text=question["wrong_answer1"], next_node="wrong1"),
            StoryChoice(text=question["wrong_answer2"], next_node="wrong2"),
        ]
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
            choice_pattern = r"Choice ([AB]): (.+)$"
            choices = []

            for line in choices_text.split("\n"):
                match = re.search(choice_pattern, line.strip())
                if match:
                    choices.append(match.group(2).strip())

            # Validate choices using Pydantic
            story_choices_model = StoryChoices(choices=choices)

            # Create StoryChoice objects
            story_choices = [
                StoryChoice(text=choice_text, next_node=f"node_{state.depth}_{i}")
                for i, choice_text in enumerate(story_choices_model.choices)
            ]

        except Exception as e:
            print(f"Error parsing choices: {e}")
            # Fallback to generic choices if parsing fails
            story_choices = [
                StoryChoice(
                    text=f"Continue with option {i + 1}",
                    next_node=f"node_{state.depth}_{i}",
                )
                for i in range(2)
            ]

    # Debug output for choices
    print("\n=== DEBUG: Story Choices ===")
    for i, choice in enumerate(story_choices, 1):
        print(f"Choice {i}: {choice.text} (next_node: {choice.next_node})")
    print("========================\n")

    # Store the current content for the next segment
    state.previous_content = story_content

    return StoryNode(content=story_content, choices=story_choices)


@router.websocket("/ws/story/{story_category}/{lesson_topic}")
async def story_websocket(websocket: WebSocket, story_category: str, lesson_topic: str):
    """Handle WebSocket connection for story streaming."""
    await websocket.accept()

    # Pre-load data at connection time
    story_data = load_story_data()
    lesson_data = load_lesson_data()

    # Initialize state as None - will be set after receiving initial state message
    state = None

    try:
        while True:
            data = await websocket.receive_json()
            print(f"\nDEBUG: Received WebSocket data: {data}")

            # If we receive a state update, use it to initialize our state
            if "state" in data:
                client_state = data["state"]
                print(
                    f"\nDEBUG: Received client state with story_length: {client_state.get('story_length', 3)}"
                )

                # Ensure all required fields are present with appropriate defaults
                validated_state = {
                    "current_node": client_state.get("current_node", "start"),
                    "depth": max(
                        1, client_state.get("depth", 1)
                    ),  # Ensure minimum depth of 1
                    "correct_answers": max(
                        0, client_state.get("correct_answers", 0)
                    ),  # Ensure non-negative
                    "total_questions": max(
                        0, client_state.get("total_questions", 0)
                    ),  # Ensure non-negative
                    "story_length": max(
                        3, min(7, client_state.get("story_length", 3))
                    ),  # Ensure between 3 and 7
                    "previous_content": client_state.get("previous_content", None),
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
                    depth=validated_state["depth"],
                    history=history,
                    correct_answers=validated_state["correct_answers"],
                    total_questions=validated_state["total_questions"],
                    previous_content=validated_state["previous_content"],
                    question_history=validated_state["question_history"],
                    story_length=validated_state["story_length"],
                )
                print(f"\nDEBUG: Initialized state with validated values: {state}")
                continue

            # Ensure state is initialized before processing any choices
            if state is None:
                print(
                    "\nDEBUG: Error - State not initialized. Waiting for initial state message."
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

            # Only append choice and increment depth for non-start messages
            if node_id != "start":
                # Handle educational answers (odd depths) vs narrative choices (even depths)
                if state.depth % 2 == 1:  # Educational answer
                    # Process educational answer but don't update history
                    # After answering a question at odd depths
                    relevant_lessons = lesson_data[lesson_data["topic"] == lesson_topic]
                    if not relevant_lessons.empty:
                        answered_question = relevant_lessons.iloc[
                            state.total_questions % len(relevant_lessons)
                        ].to_dict()

                        # Record this Q&A in history
                        was_correct = node_id == "correct"
                        state.question_history.append(
                            QuestionHistory(
                                question=answered_question,
                                chosen_answer=display_text,
                                was_correct=was_correct,
                            )
                        )

                        if was_correct:
                            state.correct_answers += 1
                        state.total_questions += 1
                else:  # Narrative choice (even depths)
                    # Keep track of narrative choices while maintaining order
                    # Filter out any educational answers that might have slipped in
                    narrative_choices = [
                        ch
                        for ch in state.history
                        if not ch.node_id in ["correct", "wrong1", "wrong2"]
                    ]
                    narrative_choices.append(
                        ChoiceHistory(node_id=node_id, display_text=display_text)
                    )
                    # Keep only the most recent MAX_NARRATIVE_CHOICES choices to prevent unbounded growth
                    MAX_NARRATIVE_CHOICES = 3  # Adjust based on story needs
                    state.history = narrative_choices[-MAX_NARRATIVE_CHOICES:]

                state.depth += 1
                print(
                    f"\nDEBUG: Updated state after choice: depth={state.depth}, history={state.history}"
                )

                # Check if we've reached the story length limit
                if state.depth > state.story_length:
                    # Send a final message indicating story completion
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
                # Generate the complete story node
                story_node = await generate_story_node(
                    story_category, lesson_topic, state
                )

                # Split into paragraphs and stream each word while maintaining paragraph structure
                paragraphs = [
                    p.strip() for p in story_node.content.split("\n\n") if p.strip()
                ]

                # Process paragraphs with optimized streaming
                for i, paragraph in enumerate(paragraphs):
                    if i > 0:  # Add paragraph break for all except first
                        await websocket.send_text("\n\n")
                        await asyncio.sleep(PARAGRAPH_DELAY)

                    # Stream words in batches
                    words = paragraph.split()
                    for i in range(0, len(words), WORD_BATCH_SIZE):
                        batch = words[i : i + WORD_BATCH_SIZE]
                        await websocket.send_text(" ".join(batch) + " ")
                        await asyncio.sleep(WORD_DELAY)

                # Send choices immediately after content
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
                print(f"Client disconnected during story generation")
                break
            except Exception as e:
                print(f"Error during story generation: {e}")
                await websocket.send_text(
                    "An error occurred while generating the story."
                )
                break

    except WebSocketDisconnect:
        print(f"Client disconnected")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        # Ensure we handle any cleanup needed
        print(f"WebSocket connection closed")
