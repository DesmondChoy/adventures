from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import os
import logging
import json
import re
from enum import Enum
from app.models.story import ChapterType, AdventureState, ChapterContent, StoryChoice
from app.services.state_storage_service import StateStorageService
from app.services.adventure_state_manager import AdventureStateManager

router = APIRouter()
logger = logging.getLogger("summary_router")

# Initialize the state storage service
state_storage_service = StateStorageService()

# Directory for storing summary data
SUMMARY_DATA_DIR = "app/static"
SUMMARY_JSON_FILE = "adventure_summary_react.json"
SUMMARY_CHAPTER_DIR = "app/static/summary-chapter"


@router.get("/summary")
async def summary_page(request: Request):
    """Serve the adventure summary page."""
    try:
        # Check if the app is available in the new location
        new_index_path = os.path.join(SUMMARY_CHAPTER_DIR, "index.html")
        if os.path.exists(new_index_path):
            logger.info(f"Serving React app from: {new_index_path}")
            return FileResponse(new_index_path)

        # Fall back to test HTML if React app is not built
        test_html_path = os.path.join(SUMMARY_DATA_DIR, "test_summary.html")
        if os.path.exists(test_html_path):
            logger.info(f"Falling back to test HTML file: {test_html_path}")
            return FileResponse(test_html_path)

        # If no options are available, return an error
        logger.warning("Summary page not found")
        return {
            "error": "Summary page not available. Please build the React app first."
        }
    except Exception as e:
        logger.error(f"Error serving summary page: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/test-plain")
async def test_plain():
    """Test route that returns plain text."""
    logger.info("Serving test plain text")
    return "This is a test plain text response from the summary router"


@router.get("/api/adventure-summary")
async def get_adventure_summary(state_id: Optional[str] = None):
    """API endpoint to get the adventure summary data.

    Args:
        state_id: Optional ID of the stored state to use for generating the summary.
                 If not provided, uses the current adventure state.
    """
    # Log the request parameters for debugging
    logger.info(f"get_adventure_summary called with state_id: {state_id}")

    # Check if state_id is provided
    if not state_id:
        logger.warning("No state_id provided to get_adventure_summary")
        # Create minimal mock data for testing if needed
        mock_data = {
            "chapterSummaries": [
                {
                    "number": 1,
                    "title": "Chapter 1: The Beginning",
                    "summary": "This is a sample summary for testing. You can start a real adventure to see actual chapter summaries.",
                    "chapterType": "story",
                },
                {
                    "number": 2,
                    "title": "Chapter 2: The Journey",
                    "summary": "This is another sample summary. Real adventures will have actual content here based on your choices.",
                    "chapterType": "story",
                },
            ],
            "educationalQuestions": [
                {
                    "question": "Would you like to go on an educational adventure?",
                    "userAnswer": "Yes",
                    "isCorrect": True,
                    "explanation": "Great! Click the Start button to begin a new adventure.",
                }
            ],
            "statistics": {
                "chaptersCompleted": 2,
                "questionsAnswered": 1,
                "timeSpent": "5 mins",
                "correctAnswers": 1,
            },
        }
        logger.info("Returning mock data for testing")
        return mock_data

    # If state_id contains multiple values (e.g., from duplicate parameters), use the first one
    if "," in state_id:
        logger.warning(f"Multiple state_id values detected: {state_id}")
        state_id = state_id.split(",")[0].strip()
        logger.info(f"Using first state_id value: {state_id}")

    try:
        # Get adventure state from storage or active state
        logger.info(f"Getting adventure state from ID: {state_id}")
        adventure_state = await get_adventure_state_from_id(state_id)

        # Ensure the last chapter is properly identified as a CONCLUSION chapter
        logger.info("Ensuring CONCLUSION chapter is properly identified")
        adventure_state = ensure_conclusion_chapter(adventure_state)

        # Format the adventure state data for the React summary component
        logger.info("Formatting adventure summary data")
        summary_data = format_adventure_summary_data(adventure_state)

        # Log all the data being returned to check its structure
        logger.info("=== Final Summary Data Structure ===")
        logger.info(
            f"chapter_summaries count: {len(summary_data.get('chapter_summaries', []))}"
        )
        logger.info(
            f"educational_questions count: {len(summary_data.get('educational_questions', []))}"
        )
        logger.info(f"statistics: {summary_data.get('statistics', {})}")

        # Import the case conversion utility
        from app.utils.case_conversion import snake_to_camel_dict

        # Convert all keys from snake_case to camelCase at the API boundary
        camel_case_data = snake_to_camel_dict(summary_data)

        # Make sure we have the right structure expected by the React app
        expected_structure = {
            "chapterSummaries": camel_case_data.get("chapterSummaries", []),
            "educationalQuestions": camel_case_data.get("educationalQuestions", []),
            "statistics": camel_case_data.get("statistics", {}),
        }

        # Log more details about the chapter summaries
        chapter_summaries = expected_structure.get("chapterSummaries", [])
        if chapter_summaries:
            logger.info("\nCHAPTER SUMMARIES BREAKDOWN:")
            for i, summary in enumerate(chapter_summaries):
                logger.info(
                    f'Chapter {summary.get("number")}: Type={summary.get("chapterType")}, Title="{summary.get("title")}"'
                )

            # Check specifically for conclusion chapter
            conclusion_chapters = [
                ch for ch in chapter_summaries if ch.get("chapterType") == "conclusion"
            ]
            if conclusion_chapters:
                logger.info(
                    f"Found {len(conclusion_chapters)} conclusion chapters: {[ch.get('number') for ch in conclusion_chapters]}"
                )
            else:
                logger.warning("No conclusion chapter found in final data")

        # Log details about educational questions
        questions = expected_structure.get("educationalQuestions", [])
        if questions:
            logger.info("\nEDUCATIONAL QUESTIONS BREAKDOWN:")
            for i, q in enumerate(questions):
                logger.info(f'Question {i + 1}: "{q.get("question")[:50]}..."')
                logger.info(
                    f'  Properties: isCorrect={q.get("isCorrect")}, userAnswer="{q.get("userAnswer")[:30]}..."'
                )
                if not q.get("isCorrect") and "correctAnswer" in q:
                    logger.info(f'  Correct answer: "{q.get("correctAnswer")[:30]}..."')
        else:
            logger.warning("No educational questions found in final data")

        # Final verification of the API response
        logger.info("\nAPI RESPONSE VALIDATION:")
        # Check chapter summaries
        if not chapter_summaries:
            logger.warning(
                "No chapter summaries in response - this will cause rendering issues"
            )

        # Check questions
        if not questions:
            logger.warning(
                "No educational questions in response - this section won't render"
            )

        # Log the complete structure for debugging
        logger.info(
            f"Complete API response structure: {json.dumps(expected_structure)[:200]}..."
        )

        logger.info("Returning formatted summary data to React app")
        return expected_structure
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving summary data: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error serving summary data: {str(e)}"
        )


async def get_adventure_state_from_id(state_id: Optional[str] = None) -> AdventureState:
    """Retrieves and reconstructs AdventureState from storage or active state.

    Args:
        state_id: Optional ID of the stored state

    Returns:
        Reconstructed AdventureState object

    Raises:
        HTTPException: If state cannot be found or reconstructed
    """
    # Create the adventure state manager
    state_manager = AdventureStateManager()

    # First try to get state from the state manager (active state)
    state = state_manager.get_current_state()

    # If no active state and state_id is provided, try to get from storage
    if not state and state_id:
        logger.info(f"No active state, trying to get stored state: {state_id}")

        # Log the memory cache contents for debugging
        logger.info(
            f"Memory cache keys before retrieval: {list(state_storage_service._memory_cache.keys())}"
        )

        # Get the stored state from the storage service
        stored_state = await state_storage_service.get_state(state_id)

        if not stored_state:
            logger.warning(f"No stored state found with ID: {state_id}")
            raise HTTPException(
                status_code=404,
                detail="No adventure state found. Please complete an adventure to view the summary.",
            )

        try:
            logger.info(f"Retrieved state with ID: {state_id}")
            logger.debug(f"State content keys: {list(stored_state.keys())}")

            # Use the method to reconstruct state from stored data
            state = await state_manager.reconstruct_state_from_storage(stored_state)

            if not state:
                logger.error("State reconstruction failed")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to reconstruct adventure state",
                )

            logger.info(f"Successfully reconstructed state with ID: {state_id}")
        except Exception as e:
            logger.error(f"Error reconstructing state: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Error reconstructing state: {str(e)}"
            )

    # If we still don't have a state, return 404
    if not state:
        logger.warning("No active adventure state found")
        raise HTTPException(
            status_code=404,
            detail="No adventure state found. Please complete an adventure to view the summary.",
        )

    return state


def ensure_conclusion_chapter(state: AdventureState) -> AdventureState:
    """Ensures the last chapter is properly identified as a CONCLUSION chapter.

    Args:
        state: The adventure state to process

    Returns:
        Updated adventure state with proper CONCLUSION chapter
    """
    # Log all chapters for debugging
    logger.info(f"Total chapters: {len(state.chapters)}")

    # If no chapters, return the state as is
    if not state.chapters:
        logger.warning("No chapters found in state")
        return state

    # Sort chapters by chapter_number to ensure proper ordering
    sorted_chapters = sorted(state.chapters, key=lambda ch: ch.chapter_number)

    # Print information about all chapters for debugging
    for i, ch in enumerate(sorted_chapters):
        logger.info(f"Chapter {ch.chapter_number}: Type={ch.chapter_type}")

    # Track if we've found a CONCLUSION chapter
    has_conclusion = False

    # First check if we have a chapter with type CONCLUSION
    for ch in sorted_chapters:
        if ch.chapter_type == ChapterType.CONCLUSION or (
            isinstance(ch.chapter_type, str) and ch.chapter_type.lower() == "conclusion"
        ):
            has_conclusion = True
            logger.info(f"Found explicit CONCLUSION chapter: {ch.chapter_number}")

            # Ensure chapter type is set to the enum value
            if ch.chapter_type != ChapterType.CONCLUSION:
                logger.info(
                    f"Converting chapter {ch.chapter_number} type from '{ch.chapter_type}' to ChapterType.CONCLUSION"
                )
                ch.chapter_type = ChapterType.CONCLUSION

    # If no conclusion chapter was found, mark the last chapter as CONCLUSION
    if not has_conclusion and sorted_chapters:
        # Get the last chapter by number (not index)
        last_chapter = sorted_chapters[-1]

        logger.info(
            f"No CONCLUSION chapter found. Setting last chapter {last_chapter.chapter_number} as CONCLUSION (was {last_chapter.chapter_type})"
        )
        last_chapter.chapter_type = ChapterType.CONCLUSION
        has_conclusion = True

    # Final verification - Check if we successfully identified a CONCLUSION chapter
    conclusion_chapter = None
    for ch in sorted_chapters:
        if ch.chapter_type == ChapterType.CONCLUSION:
            conclusion_chapter = ch
            break

    if conclusion_chapter:
        logger.info(
            f"Verified CONCLUSION chapter {conclusion_chapter.chapter_number} is properly set"
        )
    else:
        logger.warning("Failed to set CONCLUSION chapter. Using fallback approach.")
        # Ultimate fallback - just set the last chapter to CONCLUSION
        if sorted_chapters:
            sorted_chapters[-1].chapter_type = ChapterType.CONCLUSION
            logger.info(
                f"Set last chapter {sorted_chapters[-1].chapter_number} as CONCLUSION using fallback"
            )

    return state


def extract_chapter_summaries(state: AdventureState):
    """Extract chapter summaries with robust fallbacks.

    Args:
        state: The adventure state to process

    Returns:
        List of chapter summary objects
    """
    logger.info("\n=== Extracting Chapter Summaries ===")
    chapter_summaries = []

    # Check if we have stored chapter summaries
    existing_summaries = getattr(state, "chapter_summaries", [])
    existing_titles = getattr(state, "summary_chapter_titles", [])

    logger.info(
        f"Found {len(existing_summaries)} existing summaries and {len(existing_titles)} existing titles"
    )

    # Ensure the last chapter is marked as CONCLUSION
    try:
        # This ensures the CONCLUSION chapter is properly identified before processing
        state = ensure_conclusion_chapter(state)
        logger.info("Ensured CONCLUSION chapter is properly identified")
    except Exception as e:
        logger.error(f"Error ensuring CONCLUSION chapter: {str(e)}")

    # Process each chapter in chapter number order
    for chapter in sorted(state.chapters, key=lambda x: x.chapter_number):
        chapter_number = chapter.chapter_number
        logger.info(
            f"Processing chapter {chapter_number} of type {chapter.chapter_type}"
        )

        # Get or generate summary
        summary_text = ""
        if chapter_number <= len(existing_summaries):
            summary_text = existing_summaries[chapter_number - 1]
            logger.info(
                f"Using existing summary for chapter {chapter_number}: {summary_text[:50]}..."
            )
        else:
            # Try to use ChapterManager to generate a proper summary if we have access to it
            try:
                # This is a more robust way to get summary - import only when needed
                from app.services.chapter_manager import ChapterManager

                chapter_manager = ChapterManager()

                # Check if we can use the async function
                import asyncio

                if asyncio.get_event_loop().is_running():
                    # We're in an async context, can directly use the async function
                    logger.info(
                        f"Generating proper summary for chapter {chapter_number} using ChapterManager"
                    )
                    summary_result = asyncio.create_task(
                        chapter_manager.generate_chapter_summary(chapter.content)
                    )
                    # Wait for the result (this is safe in an async context)
                    summary_result = asyncio.get_event_loop().run_until_complete(
                        summary_result
                    )
                    if isinstance(summary_result, dict):
                        summary_text = summary_result.get("summary", "")
                        logger.info(
                            f"Generated summary using ChapterManager: {summary_text[:50]}..."
                        )
                else:
                    # We're not in an async context, fall back to content-based summary
                    logger.warning("Not in async context, cannot use ChapterManager")
                    summary_text = (
                        f"{chapter.content[:150]}..."
                        if len(chapter.content) > 150
                        else chapter.content
                    )
            except Exception as e:
                logger.warning(
                    f"Error generating summary with ChapterManager: {str(e)}"
                )
                # Generate simple summary from content
                summary_text = (
                    f"{chapter.content[:150]}..."
                    if len(chapter.content) > 150
                    else chapter.content
                )
                logger.info(
                    f"Generated fallback summary for chapter {chapter_number}: {summary_text[:50]}..."
                )

        # Get or generate title
        title = f"Chapter {chapter_number}"
        if chapter_number <= len(existing_titles):
            title = existing_titles[chapter_number - 1]
            logger.info(f"Using existing title for chapter {chapter_number}: {title}")
        else:
            # Try extracting title from summary (if it has title: content format)
            if ":" in summary_text and len(summary_text.split(":", 1)[0]) < 50:
                title = summary_text.split(":", 1)[0].strip()
                summary_text = summary_text.split(":", 1)[1].strip()
                logger.info(f"Extracted title from summary: {title}")
            else:
                # Generate title based on chapter type
                chapter_type_str = "Story"  # Default

                # Handle all possible chapter type formats
                if hasattr(chapter.chapter_type, "value"):
                    chapter_type_str = chapter.chapter_type.value.capitalize()
                elif isinstance(chapter.chapter_type, str):
                    chapter_type_str = chapter.chapter_type.capitalize()
                elif isinstance(chapter.chapter_type, Enum):
                    chapter_type_str = str(chapter.chapter_type).capitalize()

                title = f"Chapter {chapter_number}: {chapter_type_str}"
                logger.info(f"Generated title based on chapter type: {title}")

        # Get chapter type as string in a consistent format
        chapter_type_str = "story"  # Default

        # Try multiple approaches to get the correct chapter type
        if isinstance(chapter.chapter_type, ChapterType):
            chapter_type_str = chapter.chapter_type.value.lower()
            logger.info(f"Chapter {chapter_number} type from enum: {chapter_type_str}")
        elif isinstance(chapter.chapter_type, str):
            chapter_type_str = chapter.chapter_type.lower()
            logger.info(
                f"Chapter {chapter_number} type from string: {chapter_type_str}"
            )
        elif hasattr(chapter.chapter_type, "value"):
            chapter_type_str = chapter.chapter_type.value.lower()
            logger.info(
                f"Chapter {chapter_number} type from value attribute: {chapter_type_str}"
            )
        elif hasattr(chapter.chapter_type, "name"):
            chapter_type_str = chapter.chapter_type.name.lower()
            logger.info(
                f"Chapter {chapter_number} type from name attribute: {chapter_type_str}"
            )

        # Validate chapter_type_str against known types
        valid_types = ["story", "lesson", "reflect", "conclusion", "summary"]
        if chapter_type_str not in valid_types:
            logger.warning(
                f"Invalid chapter type: {chapter_type_str}, defaulting to 'story'"
            )
            chapter_type_str = "story"

        # Special case handling for the last chapter
        if chapter_number == len(state.chapters):
            logger.info(f"Chapter {chapter_number} is the last chapter")
            # If the last chapter isn't already marked as conclusion, consider marking it
            if (
                chapter_type_str != "conclusion" and chapter_number >= 9
            ):  # Only consider if chapter 9+
                logger.info(f"Setting last chapter {chapter_number} as CONCLUSION type")
                chapter_type_str = "conclusion"

        # Create summary object with snake_case keys (will be converted to camelCase at API boundary)
        summary_obj = {
            "number": chapter_number,
            "title": title,
            "summary": summary_text,
            "chapter_type": chapter_type_str,
        }

        logger.info(
            f"Created summary object for chapter {chapter_number} with type {chapter_type_str}"
        )
        chapter_summaries.append(summary_obj)

    # Log details about the chapter summaries
    if chapter_summaries:
        logger.info("\n=== Chapter Summaries Sample Data ===")

        # Log the first chapter summary's keys and values
        first_summary = chapter_summaries[0]
        logger.info(f"First chapter summary keys: {list(first_summary.keys())}")
        logger.info(
            f'First chapter summary values: number={first_summary["number"]}, title="{first_summary["title"]}", chapter_type={first_summary["chapter_type"]}'
        )
        logger.info(
            f"First chapter summary preview: {first_summary['summary'][:100]}..."
        )

        # Log the last chapter summary to verify CONCLUSION handling
        last_summary = chapter_summaries[-1]
        logger.info(
            f"Last chapter summary: number={last_summary['number']}, chapter_type={last_summary['chapter_type']}"
        )

        # Log the total count and final check
        logger.info(f"Total chapter summaries: {len(chapter_summaries)}")

        # Verify all required fields are present in all summaries
        missing_fields = False
        for i, summary in enumerate(chapter_summaries):
            if not all(
                k in summary for k in ["number", "title", "summary", "chapter_type"]
            ):
                missing_fields = True
                logger.warning(
                    f"Chapter summary at index {i} is missing required fields: {list(summary.keys())}"
                )

        if not missing_fields:
            logger.info("All chapter summaries have the required fields")

        # Log all chapters for debugging
        for i, summary in enumerate(chapter_summaries):
            logger.info(
                f"Summary {i + 1}: Chapter {summary['number']} ({summary['chapter_type']})"
            )

    # Final confirmation
    logger.info(f"Successfully extracted {len(chapter_summaries)} chapter summaries")
    return chapter_summaries


def extract_educational_questions(state: AdventureState):
    """Extract educational questions from LESSON chapters.

    Args:
        state: The adventure state to process

    Returns:
        List of educational question objects with the expected structure for React:
        {
            "question": "Question text?",
            "userAnswer": "The user's selected answer",
            "isCorrect": true/false,
            "explanation": "Explanation text",
            "correctAnswer": "Correct answer" (only included if isCorrect is false)
        }
    """
    questions = []

    logger.info("\n=== Extracting Educational Questions ===")

    # Track all found question data for debugging
    all_found_questions = []

    # First method: Check if lesson_questions exists in the state (preferred source)
    if hasattr(state, "lesson_questions") and state.lesson_questions:
        logger.info(
            f"Found {len(state.lesson_questions)} questions in state.lesson_questions"
        )
        all_found_questions.extend(state.lesson_questions)

        # Process each question from lesson_questions
        for i, question_data in enumerate(state.lesson_questions):
            try:
                logger.info(f"Processing question {i + 1} from lesson_questions")

                # Skip non-dictionary question data
                if not isinstance(question_data, dict):
                    logger.warning(
                        f"Skipping non-dictionary question data: {type(question_data)}"
                    )
                    continue

                # Log full question data for debugging
                logger.info(f"Question data: {json.dumps(question_data)[:200]}...")

                # Extract question text (required field)
                question_text = question_data.get("question", "")
                if not question_text:
                    logger.warning("Question has no text, skipping")
                    continue

                # Extract user's answer
                user_answer = "No answer recorded"
                for key in [
                    "chosen_answer",
                    "userAnswer",
                    "user_answer",
                    "selected_answer",
                ]:
                    if key in question_data and question_data[key]:
                        user_answer = question_data[key]
                        logger.info(
                            f"Found user answer in '{key}': {user_answer[:50]}..."
                        )
                        break

                # Extract correctness information
                is_correct = False
                for key in ["is_correct", "isCorrect"]:
                    if key in question_data:
                        is_correct = bool(question_data[key])
                        logger.info(f"Found correctness in '{key}': {is_correct}")
                        break

                # Extract explanation
                explanation = ""
                if "explanation" in question_data:
                    explanation = question_data["explanation"]
                    logger.info(f"Found explanation: {explanation[:50]}...")

                # Build the standardized question object with snake_case keys
                question_obj = {
                    "question": question_text,
                    "user_answer": user_answer,
                    "is_correct": is_correct,
                    "explanation": explanation,
                }

                # Add correct answer if user's answer was incorrect
                if not is_correct:
                    correct_answer = None

                    # Try various formats for correct answer
                    for key in ["correct_answer", "correctAnswer"]:
                        if key in question_data and question_data[key]:
                            correct_answer = question_data[key]
                            logger.info(
                                f"Found correct answer in '{key}': {correct_answer}"
                            )
                            break

                    # If no direct correct answer, check answers array
                    if not correct_answer and "answers" in question_data:
                        for answer in question_data["answers"]:
                            if isinstance(answer, dict) and answer.get(
                                "is_correct", False
                            ):
                                correct_answer = answer.get("text", "")
                                if correct_answer:
                                    logger.info(
                                        f"Found correct answer in answers array: {correct_answer}"
                                    )
                                    break

                    # Add correct answer to question object if found
                    if correct_answer:
                        question_obj["correctAnswer"] = correct_answer

                # Add the processed question to our list
                questions.append(question_obj)
                logger.info(
                    f"Successfully processed question: '{question_text[:50]}...'"
                )

            except Exception as e:
                logger.error(f"Error processing question {i + 1}: {str(e)}")
                # Continue processing other questions

    # Second method: If no questions from lesson_questions, extract from LESSON chapters
    if not questions:
        logger.info(
            "No questions from lesson_questions, extracting from LESSON chapters"
        )

        # Find all LESSON chapters with questions
        lesson_chapters = []

        for chapter in state.chapters:
            try:
                # Determine if this is a LESSON chapter
                chapter_type = chapter.chapter_type
                is_lesson = False

                if (
                    isinstance(chapter_type, ChapterType)
                    and chapter_type == ChapterType.LESSON
                ):
                    is_lesson = True
                elif isinstance(chapter_type, str) and chapter_type.lower() == "lesson":
                    is_lesson = True
                elif (
                    hasattr(chapter_type, "value")
                    and chapter_type.value.lower() == "lesson"
                ):
                    is_lesson = True

                if is_lesson:
                    logger.info(f"Found LESSON chapter {chapter.chapter_number}")
                    lesson_chapters.append(chapter)

                    # Check for question data in this chapter
                    question_data = None

                    # Try to get question from various sources
                    if hasattr(chapter, "question") and chapter.question:
                        question_data = chapter.question
                        logger.info(
                            f"Found question data in chapter.question: {str(question_data)[:50]}..."
                        )
                        all_found_questions.append(question_data)

                    if not question_data:
                        continue

                    # Get response data for the question if available
                    response_data = None
                    user_answer = "No answer recorded"
                    is_correct = False

                    if hasattr(chapter, "response") and chapter.response:
                        response_data = chapter.response
                        logger.info(
                            f"Found response data: {str(response_data)[:50]}..."
                        )

                        # Extract user answer from response
                        if hasattr(response_data, "chosen_answer"):
                            user_answer = response_data.chosen_answer
                            logger.info(
                                f"Found user answer in response.chosen_answer: {user_answer}"
                            )
                        elif (
                            isinstance(response_data, dict)
                            and "chosen_answer" in response_data
                        ):
                            user_answer = response_data["chosen_answer"]
                            logger.info(
                                f"Found user answer in response dict: {user_answer}"
                            )

                        # Extract correctness from response
                        if hasattr(response_data, "is_correct"):
                            is_correct = bool(response_data.is_correct)
                            logger.info(
                                f"Found is_correct in response.is_correct: {is_correct}"
                            )
                        elif (
                            isinstance(response_data, dict)
                            and "is_correct" in response_data
                        ):
                            is_correct = bool(response_data["is_correct"])
                            logger.info(
                                f"Found is_correct in response dict: {is_correct}"
                            )

                    # Get question text
                    question_text = ""
                    explanation = ""

                    # Handle question_data as both dict and object
                    if isinstance(question_data, dict):
                        question_text = question_data.get("question", "")
                        explanation = question_data.get("explanation", "")
                    else:
                        if hasattr(question_data, "question"):
                            question_text = question_data.question
                        if hasattr(question_data, "explanation"):
                            explanation = question_data.explanation

                    if not question_text:
                        logger.warning(f"No question text found, skipping")
                        continue

                    # Create standardized question object with snake_case keys
                    question_obj = {
                        "question": question_text,
                        "user_answer": user_answer,
                        "is_correct": is_correct,
                        "explanation": explanation,
                    }

                    # Add correct answer if the user was wrong
                    if not is_correct:
                        correct_answer = None

                        # Try to extract correct answer from question data
                        if isinstance(question_data, dict):
                            # Direct correct_answer field
                            if "correct_answer" in question_data:
                                correct_answer = question_data["correct_answer"]

                            # Look in answers array
                            if not correct_answer and "answers" in question_data:
                                for answer in question_data["answers"]:
                                    if isinstance(answer, dict) and answer.get(
                                        "is_correct", False
                                    ):
                                        correct_answer = answer.get("text", "")
                                        break
                        else:
                            # Try attribute access
                            if hasattr(question_data, "correct_answer"):
                                correct_answer = question_data.correct_answer

                            # Try answers attribute
                            if not correct_answer and hasattr(question_data, "answers"):
                                for answer in question_data.answers:
                                    if getattr(answer, "is_correct", False):
                                        correct_answer = getattr(answer, "text", "")
                                        break

                        # Add correct answer to question object if found
                        if correct_answer:
                            question_obj["correctAnswer"] = correct_answer
                            logger.info(f"Added correct answer: {correct_answer}")

                    # Add the processed question to our list
                    questions.append(question_obj)
                    logger.info(
                        f"Successfully extracted question from chapter {chapter.chapter_number}"
                    )

            except Exception as e:
                logger.error(
                    f"Error processing chapter {getattr(chapter, 'chapter_number', 'unknown')}: {str(e)}"
                )
                # Continue processing other chapters

    # Third method: Look for lesson_questions in simulation_metadata if present
    if (
        not questions
        and hasattr(state, "metadata")
        and isinstance(state.metadata, dict)
    ):
        logger.info(
            "No questions found, checking metadata for simulation_metadata.lesson_questions"
        )

        simulation_metadata = state.metadata.get("simulation_metadata", {})
        if (
            isinstance(simulation_metadata, dict)
            and "lesson_questions" in simulation_metadata
        ):
            logger.info("Found lesson_questions in simulation_metadata")

            for i, question_data in enumerate(simulation_metadata["lesson_questions"]):
                try:
                    if not isinstance(question_data, dict):
                        continue

                    # Extract basic question data
                    question_text = question_data.get("question", "")
                    if not question_text:
                        continue

                    is_correct = question_data.get("is_correct", False)
                    user_answer = question_data.get(
                        "chosen_answer", "No answer recorded"
                    )
                    explanation = question_data.get("explanation", "")

                    # Create question object with snake_case keys
                    question_obj = {
                        "question": question_text,
                        "user_answer": user_answer,
                        "is_correct": is_correct,
                        "explanation": explanation,
                    }

                    # Add correct answer if answer was incorrect
                    if not is_correct:
                        correct_answer = question_data.get("correct_answer")
                        if correct_answer:
                            question_obj["correctAnswer"] = correct_answer

                    questions.append(question_obj)
                    logger.info(
                        f"Added question from simulation_metadata: {question_text[:50]}..."
                    )

                except Exception as e:
                    logger.error(f"Error processing metadata question {i}: {str(e)}")

    # Final method: Generate fallback questions if needed
    if not questions:
        logger.warning("No questions found using any method")

        # First check if we have LESSON chapters to determine whether we should have questions
        has_lesson_chapters = False
        for chapter in state.chapters:
            chapter_type = chapter.chapter_type
            is_lesson = False

            if (
                isinstance(chapter_type, ChapterType)
                and chapter_type == ChapterType.LESSON
            ):
                is_lesson = True
            elif isinstance(chapter_type, str) and chapter_type.lower() == "lesson":
                is_lesson = True
            elif (
                hasattr(chapter_type, "value")
                and chapter_type.value.lower() == "lesson"
            ):
                is_lesson = True

            if is_lesson:
                has_lesson_chapters = True
                break

        if has_lesson_chapters or all_found_questions:
            logger.warning(
                "Questions should exist (found LESSON chapters or raw question data), creating fallback question"
            )
            fallback_question = {
                "question": "What did you learn from this adventure?",
                "user_answer": "I learned about important concepts through this interactive story",
                "is_correct": True,
                "explanation": "This adventure was designed to teach important concepts while telling an engaging story.",
            }
            questions.append(fallback_question)
            logger.info(
                f"Added educational fallback question: {fallback_question['question']}"
            )
        else:
            logger.info("No LESSON chapters found, adding standard reflection question")
            standard_question = {
                "question": "Did you enjoy your adventure?",
                "user_answer": "Yes, the adventure was enjoyable and educational",
                "is_correct": True,
                "explanation": "We hope you had a great time on this adventure!",
            }
            questions.append(standard_question)
            logger.info(
                f"Added standard reflection question: {standard_question['question']}"
            )

    # Ensure consistent format for all questions
    normalized_questions = []
    for q in questions:
        # Create a normalized question with required fields
        normalized_question = {
            "question": q.get("question", ""),
            "userAnswer": q.get("userAnswer", ""),
            "isCorrect": bool(q.get("isCorrect", False)),  # Ensure boolean type
            "explanation": q.get("explanation", ""),
        }

        # Only add correctAnswer if the answer was incorrect
        if not q.get("isCorrect", False) and "correctAnswer" in q:
            normalized_question["correctAnswer"] = q["correctAnswer"]

        # Validate and ensure we have necessary fields
        if not normalized_question["question"]:
            logger.warning("Skipping question with empty question text")
            continue

        normalized_questions.append(normalized_question)

    # Final validation and logging
    logger.info(
        f"Successfully extracted {len(normalized_questions)} educational questions"
    )

    # Log each question's structure for verification
    for i, q in enumerate(normalized_questions):
        logger.info(f"Question {i + 1}: '{q['question'][:50]}...'")
        logger.info(
            f"  Properties: userAnswer='{q['userAnswer'][:30]}...', isCorrect={q['isCorrect']}"
        )
        if "correctAnswer" in q:
            logger.info(f"  Correct answer: '{q['correctAnswer'][:30]}...'")

    # Final sanity check - if we have LESSON chapters but no questions, add a fallback
    if not normalized_questions and has_lesson_chapters:
        logger.error(
            "Failed to extract any valid questions despite having LESSON chapters"
        )
        fallback_question = {
            "question": "What was the most important thing you learned from this adventure?",
            "user_answer": "I learned valuable educational concepts presented in an engaging way",
            "is_correct": True,
            "explanation": "Adventures combine education and storytelling to create memorable learning experiences.",
        }
        normalized_questions.append(fallback_question)
        logger.info(
            f"Added emergency fallback question: {fallback_question['question']}"
        )

    return normalized_questions


def calculate_adventure_statistics(state: AdventureState, questions):
    """Calculate adventure statistics with safety checks.

    Args:
        state: The adventure state to process
        questions: List of extracted educational questions

    Returns:
        Dictionary with adventure statistics
    """
    logger.info("\n=== Calculating Adventure Statistics ===")

    # Count chapters by type
    chapter_counts = {}
    for chapter in state.chapters:
        chapter_type = str(chapter.chapter_type).lower()
        if hasattr(chapter.chapter_type, "value"):
            chapter_type = chapter.chapter_type.value.lower()

        chapter_counts[chapter_type] = chapter_counts.get(chapter_type, 0) + 1

    logger.info(f"Chapter type counts: {chapter_counts}")

    # Calculate educational statistics
    total_questions = max(len(questions), 1)  # Avoid division by zero
    correct_answers = sum(1 for q in questions if q.get("isCorrect", False))

    logger.info(
        f"Raw statistics: questions={total_questions}, correct={correct_answers}"
    )

    # Ensure logical values
    correct_answers = min(correct_answers, total_questions)

    # Ensure at least one question for valid statistics
    if total_questions == 0:
        total_questions = 1
        correct_answers = 1  # Assume correct for better user experience
        logger.info("Adjusted to minimum values: questions=1, correct=1")

    # Calculate time spent based on chapter count (rough estimate)
    estimated_minutes = len(state.chapters) * 3  # Assume ~3 minutes per chapter
    time_spent = f"{estimated_minutes} mins"

    statistics = {
        "chapters_completed": len(state.chapters),
        "questions_answered": total_questions,
        "time_spent": time_spent,
        "correct_answers": correct_answers,
    }

    logger.info(f"Final statistics: {statistics}")
    return statistics


def format_adventure_summary_data(state: AdventureState):
    """Transform AdventureState into React-compatible summary data.

    Args:
        state: The adventure state to process

    Returns:
        Formatted data for the React summary component
    """
    try:
        # Log detailed state information for debugging
        logger.info("\n=== Building Adventure Summary Data ===")
        logger.info(f"Total chapters: {len(state.chapters)}")
        logger.info(f"Story length: {state.story_length}")

        # Check if we have chapter_summaries and lesson_questions
        has_summaries = hasattr(state, "chapter_summaries") and state.chapter_summaries
        has_questions = hasattr(state, "lesson_questions") and state.lesson_questions

        logger.info(f"State has chapter_summaries: {has_summaries}")
        logger.info(f"State has lesson_questions: {has_questions}")

        if has_summaries:
            logger.info(f"Number of summaries in state: {len(state.chapter_summaries)}")
            # Log a few summaries for debugging
            for i, summary in enumerate(state.chapter_summaries[:2]):
                logger.info(f"Summary {i + 1}: {summary[:50]}...")

        if has_questions:
            logger.info(f"Number of questions in state: {len(state.lesson_questions)}")
            # Log a question for debugging
            if state.lesson_questions:
                q = state.lesson_questions[0]
                logger.info(f"First question: {q.get('question', 'No question text')}")

        # Extract data with fallbacks for missing elements
        chapter_summaries = extract_chapter_summaries(state)
        logger.info(f"Extracted {len(chapter_summaries)} chapter summaries")

        # Debug log first summary
        if chapter_summaries:
            logger.info(f"First extracted summary: {chapter_summaries[0]}")

        educational_questions = extract_educational_questions(state)
        logger.info(f"Extracted {len(educational_questions)} educational questions")

        # Debug log first question
        if educational_questions:
            logger.info(f"First extracted question: {educational_questions[0]}")

        statistics = calculate_adventure_statistics(state, educational_questions)
        logger.info(f"Calculated statistics: {statistics}")

        # Build the final summary data structure with snake_case keys
        summary_data = {
            "chapter_summaries": chapter_summaries,
            "educational_questions": educational_questions,
            "statistics": statistics,
        }

        # Log a sample of the final data structure for debugging
        logger.info(f"Summary data structure keys: {summary_data.keys()}")
        logger.info(
            f"Number of chapter summaries in response: {len(summary_data['chapter_summaries'])}"
        )
        logger.info(
            f"Number of questions in response: {len(summary_data['educational_questions'])}"
        )

        logger.info("Successfully built adventure summary data")
        return summary_data

    except Exception as e:
        logger.error(f"Error formatting summary data: {e}")
        # Return minimal valid structure on error with snake_case keys
        return {
            "chapter_summaries": [],
            "educational_questions": [
                {
                    "question": "What did you think of your adventure?",
                    "user_answer": "It was great!",
                    "is_correct": True,
                    "explanation": "We're glad you enjoyed it.",
                }
            ],
            "statistics": {
                "chapters_completed": len(state.chapters) if state else 0,
                "questions_answered": 1,
                "time_spent": "30 mins",
                "correct_answers": 1,
            },
        }


@router.post("/api/store-adventure-state")
async def store_adventure_state(state_data: dict):
    """Store adventure state and return a unique ID."""
    try:
        # Log critical fields to help with debugging
        logger.info("Storing adventure state with the following fields:")
        logger.info(f"Chapters count: {len(state_data.get('chapters', []))}")
        logger.info(
            f"Chapter summaries count: {len(state_data.get('chapter_summaries', []))}"
        )
        logger.info(
            f"Summary chapter titles count: {len(state_data.get('summary_chapter_titles', []))}"
        )
        logger.info(
            f"Lesson questions count: {len(state_data.get('lesson_questions', []))}"
        )

        # Ensure chapter_summaries exists
        if not state_data.get("chapter_summaries"):
            state_data["chapter_summaries"] = []
            logger.info("Created empty chapter_summaries array")

        # Ensure summary_chapter_titles exists
        if not state_data.get("summary_chapter_titles"):
            state_data["summary_chapter_titles"] = []
            logger.info("Created empty summary_chapter_titles array")

        # Process chapters to ensure all have summaries
        if state_data.get("chapters"):
            # Sort chapters by chapter number to ensure correct order
            sorted_chapters = sorted(
                state_data.get("chapters", []), key=lambda x: x.get("chapter_number", 0)
            )

            # Import ChapterManager for summary generation
            from app.services.chapter_manager import ChapterManager

            chapter_manager = ChapterManager()

            for chapter in sorted_chapters:
                chapter_number = chapter.get("chapter_number", 0)
                chapter_type = str(chapter.get("chapter_type", "")).lower()

                # Check if we need to generate a summary for this chapter
                if len(state_data["chapter_summaries"]) < chapter_number:
                    logger.info(
                        f"Missing summary for chapter {chapter_number} ({chapter_type})"
                    )

                    # Add placeholder summaries for any gaps
                    while len(state_data["chapter_summaries"]) < chapter_number - 1:
                        state_data["chapter_summaries"].append(
                            "Chapter summary not available"
                        )
                        # Also add placeholder titles
                        if len(state_data["summary_chapter_titles"]) < len(
                            state_data["chapter_summaries"]
                        ):
                            state_data["summary_chapter_titles"].append(
                                f"Chapter {len(state_data['summary_chapter_titles']) + 1}"
                            )

                    # Generate summary for this chapter
                    try:
                        # Get choice context from next chapter's response if available
                        choice_text = None
                        choice_context = ""

                        # For non-conclusion chapters, try to find choice from next chapter
                        if chapter_type != "conclusion" and chapter_number < len(
                            sorted_chapters
                        ):
                            next_chapter = sorted_chapters[chapter_number]
                            if next_chapter and next_chapter.get("response"):
                                response = next_chapter.get("response", {})
                                if response.get("choice_text"):
                                    choice_text = response.get("choice_text")
                                elif response.get("chosen_answer"):
                                    choice_text = response.get("chosen_answer")
                                    choice_context = (
                                        " (Correct answer)"
                                        if response.get("is_correct")
                                        else " (Incorrect answer)"
                                    )

                        # For conclusion chapter, use placeholder choice
                        if chapter_type == "conclusion":
                            choice_text = "End of story"
                            choice_context = ""
                            logger.info(
                                f"Using placeholder choice for CONCLUSION chapter"
                            )

                        # Generate the summary
                        logger.info(f"Generating summary for chapter {chapter_number}")
                        summary_result = await chapter_manager.generate_chapter_summary(
                            chapter.get("content", ""), choice_text, choice_context
                        )

                        # Extract title and summary
                        title = summary_result.get(
                            "title",
                            f"Chapter {chapter_number}: {chapter_type.capitalize()}",
                        )
                        summary = summary_result.get("summary", "Summary not available")

                        # Add to state data
                        state_data["chapter_summaries"].append(summary)
                        state_data["summary_chapter_titles"].append(title)

                        logger.info(
                            f"Generated summary for chapter {chapter_number}: {summary[:50]}..."
                        )
                        logger.info(
                            f"Generated title for chapter {chapter_number}: {title}"
                        )
                    except Exception as e:
                        logger.error(
                            f"Error generating summary for chapter {chapter_number}: {e}"
                        )
                        # Add fallback summary and title
                        state_data["chapter_summaries"].append(
                            f"Summary for Chapter {chapter_number}"
                        )
                        state_data["summary_chapter_titles"].append(
                            f"Chapter {chapter_number}: {chapter_type.capitalize()}"
                        )
                        logger.info(
                            f"Added fallback summary for chapter {chapter_number}"
                        )

            logger.info(
                f"Processed {len(sorted_chapters)} chapters, ensuring all have summaries"
            )
            logger.info(
                f"Final chapter_summaries count: {len(state_data['chapter_summaries'])}"
            )
            logger.info(
                f"Final summary_chapter_titles count: {len(state_data['summary_chapter_titles'])}"
            )

        # Process lesson questions if needed (existing code)
        if not state_data.get("lesson_questions"):
            logger.info("Extracting lesson questions for state before storing")
            # Log detailed information about chapters to find questions
            logger.info("\n=== ANALYZING CHAPTERS FOR QUESTIONS ===")
            lesson_chapters = []
            for chapter in state_data.get("chapters", []):
                chapter_number = chapter.get("chapter_number", 0)
                chapter_type = chapter.get("chapter_type", "")

                # Check for chapter_type in various formats
                is_lesson = False
                if isinstance(chapter_type, str) and chapter_type.lower() == "lesson":
                    is_lesson = True
                elif (
                    hasattr(chapter_type, "value")
                    and chapter_type.value.lower() == "lesson"
                ):
                    is_lesson = True

                if is_lesson:
                    lesson_chapters.append(chapter_number)
                    logger.info(f"Found LESSON chapter {chapter_number}:")

                    # Check all possible question locations
                    if "question" in chapter:
                        logger.info(
                            f"  - Has 'question' field: {type(chapter['question'])}"
                        )
                        if isinstance(chapter["question"], dict):
                            logger.info(
                                f"  - Question keys: {list(chapter['question'].keys())}"
                            )
                            logger.info(
                                f"  - Question text: {chapter['question'].get('question', 'None')[:50]}..."
                            )
                    else:
                        logger.info(f"  - No 'question' field")

                    # Check chapter_content for question data
                    if "chapter_content" in chapter and chapter["chapter_content"]:
                        if "question" in chapter["chapter_content"]:
                            logger.info(f"  - Has 'chapter_content.question' field")

                    # Check response field
                    if "response" in chapter and chapter["response"]:
                        logger.info(
                            f"  - Has 'response' field: {type(chapter['response'])}"
                        )
                        if hasattr(chapter["response"], "chosen_answer"):
                            logger.info(
                                f"  - Response chosen_answer: {chapter['response'].chosen_answer}"
                            )
                        if hasattr(chapter["response"], "is_correct"):
                            logger.info(
                                f"  - Response is_correct: {chapter['response'].is_correct}"
                            )
                    else:
                        logger.info(f"  - No 'response' field")

            logger.info(
                f"Found {len(lesson_chapters)} LESSON chapters: {lesson_chapters}"
            )
            logger.info("=== END CHAPTER ANALYSIS ===\n")

            # Extract lesson questions (using existing code)
            lesson_questions = []

            # Look for LESSON chapters with questions in a more thorough way
            for chapter in state_data.get("chapters", []):
                chapter_number = chapter.get("chapter_number", 0)
                chapter_type = chapter.get("chapter_type", "")

                # Check for chapter_type in various formats to identify LESSON chapters
                is_lesson = False
                if isinstance(chapter_type, str) and chapter_type.lower() == "lesson":
                    is_lesson = True
                elif (
                    hasattr(chapter_type, "value")
                    and chapter_type.value.lower() == "lesson"
                ):
                    is_lesson = True

                if not is_lesson:
                    # Skip non-LESSON chapters
                    continue

                logger.info(f"Processing LESSON chapter {chapter_number} for questions")

                # Look for question data in various locations
                question_data = None

                # Try direct question field first
                if chapter.get("question"):
                    logger.info(f"Found question in chapter.question field")
                    question_data = chapter.get("question")
                # Try chapter_content.question next
                elif chapter.get("chapter_content") and chapter.get(
                    "chapter_content"
                ).get("question"):
                    logger.info(f"Found question in chapter_content.question field")
                    question_data = chapter.get("chapter_content").get("question")
                # Try scanning content for question format as last resort
                elif chapter.get("content"):
                    logger.info(
                        f"No question field found, scanning content for questions"
                    )
                    content = chapter.get("content", "")
                    # Look for question patterns in content
                    question_match = re.search(r"Question:?\s+([^\?]+\?)", content)
                    if question_match:
                        question_text = question_match.group(1).strip()
                        logger.info(f"Extracted question from content: {question_text}")
                        question_data = {"question": question_text}

                if not question_data:
                    logger.info(f"No question data found in chapter {chapter_number}")
                    continue

                # Get response data if available
                is_correct = False
                chosen_answer = "No answer recorded"

                response = chapter.get("response")
                if response:
                    logger.info(f"Found response for chapter {chapter_number}")
                    # Try different approaches to get chosen_answer and is_correct
                    if hasattr(response, "chosen_answer"):
                        chosen_answer = response.chosen_answer
                        logger.info(
                            f"Got chosen_answer from response object: {chosen_answer}"
                        )
                    elif isinstance(response, dict) and "chosen_answer" in response:
                        chosen_answer = response["chosen_answer"]
                        logger.info(
                            f"Got chosen_answer from response dict: {chosen_answer}"
                        )

                    if hasattr(response, "is_correct"):
                        is_correct = response.is_correct
                        logger.info(
                            f"Got is_correct from response object: {is_correct}"
                        )
                    elif isinstance(response, dict) and "is_correct" in response:
                        is_correct = response["is_correct"]
                        logger.info(f"Got is_correct from response dict: {is_correct}")

                # Create question object in proper format for React app
                question_text = ""
                if isinstance(question_data, dict):
                    question_text = question_data.get("question", "")
                elif hasattr(question_data, "question"):
                    question_text = question_data.question
                else:
                    question_text = str(question_data)

                logger.info(f"Question text: {question_text[:50]}...")

                # Format explanation text
                explanation = ""
                if isinstance(question_data, dict) and "explanation" in question_data:
                    explanation = question_data["explanation"]
                elif hasattr(question_data, "explanation"):
                    explanation = question_data.explanation

                # Create the question object in the proper format for the React app
                question_obj = {
                    "question": question_text,
                    "userAnswer": chosen_answer,
                    "isCorrect": is_correct,
                    "explanation": explanation,
                }

                # Add correct answer if the user's answer was wrong
                if not is_correct:
                    correct_answer = None

                    # Look for correct answer in different places
                    if (
                        isinstance(question_data, dict)
                        and "correct_answer" in question_data
                    ):
                        correct_answer = question_data["correct_answer"]
                    elif hasattr(question_data, "correct_answer"):
                        correct_answer = question_data.correct_answer
                    elif isinstance(question_data, dict) and "answers" in question_data:
                        for answer in question_data["answers"]:
                            if isinstance(answer, dict) and answer.get("is_correct"):
                                correct_answer = answer.get("text", "")
                                break

                    if correct_answer:
                        question_obj["correctAnswer"] = correct_answer
                        logger.info(f"Added correct answer: {correct_answer[:30]}...")

                lesson_questions.append(question_obj)
                logger.info(f"Added complete question from chapter {chapter_number}")

            # Add educational questions from content if none found directly
            if not lesson_questions:
                logger.info(
                    "No questions found in LESSON chapters directly, scanning all chapters for educational content"
                )

                for chapter in state_data.get("chapters", []):
                    chapter_number = chapter.get("chapter_number", 0)
                    content = chapter.get("content", "")

                    # Skip if no significant content
                    if len(content) < 100:
                        continue

                    # Look for educational pattern in content
                    educational_pattern = re.search(
                        r"(?:learn|discover|understand|know)[^\.\?]+(?:\?|\.)", content
                    )
                    if educational_pattern:
                        educational_text = educational_pattern.group(0)
                        # Convert statement to question if needed
                        if not educational_text.endswith("?"):
                            question_text = f"What did we learn about {educational_text.strip().rstrip('.')}?"
                        else:
                            question_text = educational_text

                        logger.info(
                            f"Generated educational question from chapter {chapter_number}: {question_text}"
                        )

                        # Create a simple question object
                        question_obj = {
                            "question": question_text,
                            "userAnswer": "We learned about this topic during our adventure.",
                            "isCorrect": True,
                            "explanation": "The adventure taught us about many educational concepts.",
                        }

                        lesson_questions.append(question_obj)

                        # Stop after finding a few educational elements
                        if len(lesson_questions) >= 3:
                            break

            # If still no questions found, add fallback questions
            if not lesson_questions:
                logger.info(
                    "No questions found in any chapter, adding fallback questions"
                )

                # Add multiple engaging questions about the adventure
                lesson_questions = [
                    {
                        "question": "What did you learn from this adventure?",
                        "userAnswer": "I learned valuable lessons about teamwork and problem-solving",
                        "isCorrect": True,
                        "explanation": "This adventure was designed to teach important concepts through an engaging narrative.",
                    },
                    {
                        "question": "What was your favorite part of the adventure?",
                        "userAnswer": "I enjoyed exploring new places and meeting interesting characters",
                        "isCorrect": True,
                        "explanation": "Adventures are about discovery and new experiences.",
                    },
                    {
                        "question": "Would you like to go on another adventure?",
                        "userAnswer": "Yes! I can't wait for the next one",
                        "isCorrect": True,
                        "explanation": "Great! There are many more adventures waiting for you.",
                    },
                ]

            # Add to state data
            state_data["lesson_questions"] = lesson_questions
            logger.info(f"Added {len(lesson_questions)} questions to state data")

            # Log the first question for verification
            if lesson_questions:
                logger.info(f"First question: {lesson_questions[0]['question']}")
                logger.info(
                    f"First question properties: {list(lesson_questions[0].keys())}"
                )

        # Store the enhanced state
        state_id = await state_storage_service.store_state(state_data)
        logger.info(f"Successfully stored enhanced state with ID: {state_id}")
        return {"state_id": state_id}
    except Exception as e:
        logger.error(f"Error storing adventure state: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/api/get-adventure-state/{state_id}")
async def get_adventure_state(state_id: str):
    """Retrieve adventure state by ID."""
    try:
        state_data = await state_storage_service.get_state(state_id)
        if not state_data:
            raise HTTPException(status_code=404, detail="State not found or expired")
        return state_data
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving adventure state: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/generate-summary/{state_file_id}")
async def generate_summary(state_file_id: str):
    """Generate a summary from a simulation state file."""
    try:
        # This would normally call the generate_chapter_summaries_react.py script
        # For now, we'll just return a message
        return {
            "message": f"Summary generation from state file {state_file_id} would be triggered here.",
            "note": "This endpoint is a placeholder. Implement the actual generation logic in production.",
        }
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


# Route to serve JavaScript files - this must be at the end to avoid catching other routes
@router.get("/{js_file:path}")
async def serve_js_file(js_file: str):
    """Serve JavaScript files from the summary chapter directory."""
    if not js_file.endswith(".js"):
        raise HTTPException(status_code=404, detail="Not found")

    try:
        js_path = os.path.join(SUMMARY_CHAPTER_DIR, js_file)
        if os.path.exists(js_path):
            logger.info(f"Serving JavaScript file from: {js_path}")
            return FileResponse(js_path, media_type="application/javascript")
        else:
            logger.error(f"JavaScript file not found at: {js_path}")
            raise HTTPException(
                status_code=404, detail=f"JavaScript file {js_file} not found"
            )
    except Exception as e:
        logger.error(f"Error serving JavaScript file: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")
