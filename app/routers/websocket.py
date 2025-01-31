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

router = APIRouter()
llm_service = LLMService()


# Load story and lesson data
def load_story_data():
    with open("app/data/stories.yaml", "r") as f:
        return yaml.safe_load(f)


def load_lesson_data():
    return pd.read_csv("app/data/lessons.csv")


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

    # Initialize with default state
    state = StoryState(
        current_node="start",
        depth=1,
        history=[],
        correct_answers=0,
        total_questions=0,
        previous_content=None,
        question_history=[],
    )

    try:
        while True:
            data = await websocket.receive_json()
            print(f"\nDEBUG: Received WebSocket data: {data}")

            # If we receive a state update, use it to initialize our state
            if "state" in data:
                # Convert history from client format to ChoiceHistory objects
                history = []
                client_history = data["state"].get("history", [])
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

                state = StoryState(
                    current_node=data["state"].get("current_node", "start"),
                    depth=data["state"].get("depth", 1),
                    history=history,
                    correct_answers=data["state"].get("correct_answers", 0),
                    total_questions=data["state"].get("total_questions", 0),
                    previous_content=data["state"].get("previous_content", None),
                    question_history=data["state"].get("question_history", []),
                )
                print(f"\nDEBUG: Updated state from client: {state}")
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
                    lesson_data = load_lesson_data()
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
                                chosen_answer=node_id,
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

            try:
                # Generate the complete story node
                story_node = await generate_story_node(
                    story_category, lesson_topic, state
                )

                # Split into paragraphs and stream each word while maintaining paragraph structure
                paragraphs = [
                    p.strip() for p in story_node.content.split("\n\n") if p.strip()
                ]

                # Process first paragraph
                if paragraphs:
                    words = paragraphs[0].split()
                    for word in words:
                        await websocket.send_text(word + " ")
                        await asyncio.sleep(0.05)  # Small delay between words

                # Process remaining paragraphs
                for paragraph in paragraphs[1:]:
                    # Send paragraph break
                    await websocket.send_text("\n\n")
                    await asyncio.sleep(0.2)  # Slightly longer pause between paragraphs

                    # Stream words in the paragraph
                    words = paragraph.split()
                    for word in words:
                        await websocket.send_text(word + " ")
                        await asyncio.sleep(0.05)  # Small delay between words

                # Send choices as a separate message
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
