from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from typing import Optional
import os
import logging
import json
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
                    "chapterType": "story"
                },
                {
                    "number": 2,
                    "title": "Chapter 2: The Journey",
                    "summary": "This is another sample summary. Real adventures will have actual content here based on your choices.",
                    "chapterType": "story"
                }
            ],
            "educationalQuestions": [{
                "question": "Would you like to go on an educational adventure?",
                "userAnswer": "Yes",
                "isCorrect": True,
                "explanation": "Great! Click the Start button to begin a new adventure."
            }],
            "statistics": {
                "chaptersCompleted": 2,
                "questionsAnswered": 1,
                "timeSpent": "5 mins",
                "correctAnswers": 1
            }
        }
        logger.info("Returning mock data for testing")
        return mock_data

    # If state_id contains multiple values (e.g., from duplicate parameters), use the first one
    if "," in state_id:
        logger.warning(f"Multiple state_id values detected: {state_id}")
        state_id = state_id.split(",")[0]
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
        logger.info(f"chapterSummaries count: {len(summary_data.get('chapterSummaries', []))}")
        logger.info(f"educationalQuestions count: {len(summary_data.get('educationalQuestions', []))}")
        logger.info(f"statistics: {summary_data.get('statistics', {})}")
        
        # Make sure we have the right structure expected by the React app
        expected_structure = {
            "chapterSummaries": summary_data.get("chapterSummaries", []),
            "educationalQuestions": summary_data.get("educationalQuestions", []),
            "statistics": summary_data.get("statistics", {})
        }
        
        logger.info("Returning formatted summary data to React app")
        return expected_structure
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving summary data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error serving summary data: {str(e)}")


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
                detail="No adventure state found. Please complete an adventure to view the summary."
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
            detail="No adventure state found. Please complete an adventure to view the summary."
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
    
    # Track if we've found a CONCLUSION chapter
    has_conclusion = False
    
    # Find the last chapter by number
    last_chapter = max(state.chapters, key=lambda ch: ch.chapter_number)
    logger.info(f"Identified last chapter as chapter {last_chapter.chapter_number}")
    
    # Check all chapters for an existing CONCLUSION chapter
    for ch in state.chapters:
        # Check for existing CONCLUSION chapter
        if (ch.chapter_type == ChapterType.CONCLUSION or 
            str(ch.chapter_type).lower() == "conclusion" or
            (ch.chapter_number == state.story_length and state.story_length > 0)):
            
            has_conclusion = True
            logger.info(f"Found CONCLUSION chapter: {ch.chapter_number}")
            
            # Force set the chapter type to CONCLUSION if it's not already
            if str(ch.chapter_type).lower() != "conclusion":
                logger.warning(f"Chapter {ch.chapter_number} has type {ch.chapter_type} but should be CONCLUSION. Updating to CONCLUSION.")
                ch.chapter_type = ChapterType.CONCLUSION
    
    # If we didn't find a CONCLUSION chapter, mark the last chapter as CONCLUSION
    if not has_conclusion:
        logger.info(f"No CONCLUSION chapter found. Setting last chapter {last_chapter.chapter_number} as CONCLUSION")
        last_chapter.chapter_type = ChapterType.CONCLUSION

    # Special case: If the 10th chapter is missing but we have 9 chapters, treat the 9th as CONCLUSION
    if state.story_length == 10 and len(state.chapters) == 9:
        ninth_chapter = next((ch for ch in state.chapters if ch.chapter_number == 9), None)
        if ninth_chapter:
            logger.info("Found 9 chapters in a 10-chapter story. Treating chapter 9 as CONCLUSION")
            ninth_chapter.chapter_type = ChapterType.CONCLUSION

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
    existing_summaries = getattr(state, 'chapter_summaries', [])
    existing_titles = getattr(state, 'summary_chapter_titles', [])
    
    logger.info(f"Found {len(existing_summaries)} existing summaries and {len(existing_titles)} existing titles")
    
    # Process each chapter
    for chapter in sorted(state.chapters, key=lambda x: x.chapter_number):
        chapter_number = chapter.chapter_number
        logger.info(f"Processing chapter {chapter_number}")
        
        # Get or generate summary
        summary_text = ""
        if chapter_number <= len(existing_summaries):
            summary_text = existing_summaries[chapter_number - 1]
            logger.info(f"Using existing summary for chapter {chapter_number}: {summary_text[:50]}...")
        else:
            # Generate summary from content
            content = chapter.content
            summary_text = f"{content[:150]}..." if len(content) > 150 else content
            logger.warning(f"Generated fallback summary for chapter {chapter_number}")
            
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
                chapter_type_str = str(chapter.chapter_type)
                if hasattr(chapter.chapter_type, 'value'):
                    chapter_type_str = chapter.chapter_type.value
                title = f"Chapter {chapter_number}: {chapter_type_str.capitalize()}"
                logger.info(f"Generated title based on chapter type: {title}")
                
        # Get chapter type as string
        chapter_type_str = "story"  # Default
        if isinstance(chapter.chapter_type, str):
            chapter_type_str = chapter.chapter_type.lower()
        elif hasattr(chapter.chapter_type, 'value'):
            chapter_type_str = chapter.chapter_type.value.lower()
            
        # Create summary object with the correct format for React
        summary_obj = {
            "number": chapter_number,
            "title": title,
            "summary": summary_text,
            "chapterType": chapter_type_str
        }
        
        logger.info(f"Created summary object for chapter {chapter_number}")
        chapter_summaries.append(summary_obj)
        
    # Log details about the chapter summaries
    if chapter_summaries:
        logger.info("\n=== Chapter Summaries Sample Data ===")
        # Log the first chapter summary's keys and values
        first_summary = chapter_summaries[0]
        logger.info(f"First chapter summary keys: {list(first_summary.keys())}")
        logger.info(f"First chapter summary values: number={first_summary['number']}, title=\"{first_summary['title']}\", chapterType={first_summary['chapterType']}")
        logger.info(f"First chapter summary preview: {first_summary['summary'][:100]}...")
        
        # Log the total count and final check
        logger.info(f"Total chapter summaries: {len(chapter_summaries)}")
        
        # Verify all required fields are present in all summaries
        missing_fields = False
        for i, summary in enumerate(chapter_summaries):
            if not all(k in summary for k in ["number", "title", "summary", "chapterType"]):
                missing_fields = True
                logger.warning(f"Chapter summary at index {i} is missing required fields: {list(summary.keys())}")
        
        if not missing_fields:
            logger.info("All chapter summaries have the required fields")
        
    # Final confirmation
    logger.info(f"Successfully extracted {len(chapter_summaries)} chapter summaries")
    return chapter_summaries


def extract_educational_questions(state: AdventureState):
    """Extract educational questions from LESSON chapters.
    
    Args:
        state: The adventure state to process
        
    Returns:
        List of educational question objects
    """
    questions = []
    
    logger.info("\n=== Extracting Educational Questions ===")
    
    # First check if we have lesson_questions in the state
    if hasattr(state, 'lesson_questions') and state.lesson_questions:
        logger.info(f"Using {len(state.lesson_questions)} questions from state.lesson_questions")
        
        for question_data in state.lesson_questions:
            # Process the question data
            is_correct = question_data.get('is_correct', False)
            chosen_answer = question_data.get('chosen_answer', "No answer recorded")
            
            question_obj = {
                "question": question_data.get("question", "Unknown question"),
                "userAnswer": chosen_answer,
                "isCorrect": is_correct,
                "explanation": question_data.get("explanation", "")
            }
            
            # Add correct answer if user was wrong
            if not is_correct:
                correct_answer = question_data.get('correct_answer')
                if not correct_answer:
                    # Try to find in answers array
                    for answer in question_data.get("answers", []):
                        if answer.get("is_correct"):
                            correct_answer = answer.get("text")
                            break
                            
                if correct_answer:
                    question_obj["correctAnswer"] = correct_answer
                    
            questions.append(question_obj)
            logger.info(f"Added question from lesson_questions: {question_obj['question'][:50]}...")
            logger.info(f"Question properties: isCorrect={question_obj['isCorrect']}, userAnswer={question_obj['userAnswer'][:30]}...")
    
    # If no questions yet, extract directly from LESSON chapters
    if not questions:
        logger.info("Extracting questions from LESSON chapters")
        
        for chapter in state.chapters:
            # Check if this is a LESSON chapter with a question
            chapter_type = chapter.chapter_type
            is_lesson = (chapter_type == ChapterType.LESSON or 
                         (isinstance(chapter_type, str) and chapter_type.lower() == "lesson"))
            
            if is_lesson and chapter.question:
                question_data = chapter.question
                logger.info(f"Found question in chapter {chapter.chapter_number}")
                
                # Get response data if available
                is_correct = False
                chosen_answer = "No answer recorded"
                
                if chapter.response:
                    response = chapter.response
                    if hasattr(response, "is_correct"):
                        is_correct = response.is_correct
                    if hasattr(response, "chosen_answer"):
                        chosen_answer = response.chosen_answer
                
                question_obj = {
                    "question": question_data.get("question", "Unknown question"),
                    "userAnswer": chosen_answer,
                    "isCorrect": is_correct,
                    "explanation": question_data.get("explanation", "")
                }
                
                # Add correct answer if user was wrong
                if not is_correct:
                    correct_answer = question_data.get('correct_answer')
                    if not correct_answer:
                        # Try to find in answers array
                        for answer in question_data.get("answers", []):
                            if answer.get("is_correct"):
                                correct_answer = answer.get("text")
                                break
                                
                    if correct_answer:
                        question_obj["correctAnswer"] = correct_answer
                        
                questions.append(question_obj)
                logger.info(f"Added question from chapter {chapter.chapter_number}: {question_obj['question'][:50]}...")
                logger.info(f"Question properties: isCorrect={question_obj['isCorrect']}, userAnswer={question_obj['userAnswer'][:30]}...")
                
    # If still no questions but we have LESSON chapters, add a fallback question
    if not questions:
        # Check if we have any LESSON chapters
        has_lesson_chapters = False
        for chapter in state.chapters:
            chapter_type = chapter.chapter_type
            if (chapter_type == ChapterType.LESSON or 
                (isinstance(chapter_type, str) and chapter_type.lower() == "lesson")):
                has_lesson_chapters = True
                break
                
        if has_lesson_chapters:
            logger.warning("No questions found despite having LESSON chapters, adding fallback question")
            fallback_question = {
                "question": "What did you learn from this adventure?",
                "userAnswer": "The adventure was educational and engaging",
                "isCorrect": True,
                "explanation": "This adventure was designed to teach important concepts while telling an engaging story."
            }
            questions.append(fallback_question)
            logger.info(f"Added fallback question: {fallback_question['question']}")
        else:
            logger.info("No LESSON chapters found, adding standard question")
            standard_question = {
                "question": "Did you enjoy your adventure?",
                "userAnswer": "Yes, the adventure was enjoyable",
                "isCorrect": True,
                "explanation": "We hope you had a great time on this adventure!"
            }
            questions.append(standard_question)
            logger.info(f"Added standard question: {standard_question['question']}")
            
    # Ensure we have questions with the right property names for the React app
    logger.info(f"Total questions extracted: {len(questions)}")
    if questions:
        # Show sample of first question's properties to confirm format
        logger.info(f"First question properties: {list(questions[0].keys())}")
    
    # Make sure we have the exact property names required
    normalized_questions = []
    for q in questions:
        normalized_question = {
            "question": q.get("question", ""),
            "userAnswer": q.get("userAnswer", ""),
            "isCorrect": q.get("isCorrect", False),
            "explanation": q.get("explanation", "")
        }
        
        # Only add correctAnswer if the answer was incorrect
        if not q.get("isCorrect", False) and "correctAnswer" in q:
            normalized_question["correctAnswer"] = q["correctAnswer"]
            
        normalized_questions.append(normalized_question)
    
    logger.info("Successfully extracted and normalized educational questions")    
    return normalized_questions


def calculate_adventure_statistics(state: AdventureState, questions):
    """Calculate adventure statistics with safety checks.
    
    Args:
        state: The adventure state to process
        questions: List of extracted educational questions
        
    Returns:
        Dictionary with adventure statistics
    """
    # Count chapters by type
    chapter_counts = {}
    for chapter in state.chapters:
        chapter_type = str(chapter.chapter_type).lower()
        if hasattr(chapter.chapter_type, 'value'):
            chapter_type = chapter.chapter_type.value.lower()
            
        chapter_counts[chapter_type] = chapter_counts.get(chapter_type, 0) + 1
    
    # Calculate educational statistics
    total_questions = max(len(questions), 1)  # Avoid division by zero
    correct_answers = sum(1 for q in questions if q.get('isCorrect', False))
    
    # Ensure logical values
    correct_answers = min(correct_answers, total_questions)
    
    # Ensure at least one question for valid statistics
    if total_questions == 0:
        total_questions = 1
        correct_answers = 1  # Assume correct for better user experience
    
    return {
        "chaptersCompleted": len(state.chapters),
        "questionsAnswered": total_questions,
        "timeSpent": "30 mins",  # This could be calculated from timestamps in the future
        "correctAnswers": correct_answers
    }


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
        has_summaries = hasattr(state, 'chapter_summaries') and state.chapter_summaries
        has_questions = hasattr(state, 'lesson_questions') and state.lesson_questions
        
        logger.info(f"State has chapter_summaries: {has_summaries}")
        logger.info(f"State has lesson_questions: {has_questions}")
        
        if has_summaries:
            logger.info(f"Number of summaries in state: {len(state.chapter_summaries)}")
            # Log a few summaries for debugging
            for i, summary in enumerate(state.chapter_summaries[:2]):
                logger.info(f"Summary {i+1}: {summary[:50]}...")
        
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
        
        # Build the final summary data structure
        summary_data = {
            "chapterSummaries": chapter_summaries,
            "educationalQuestions": educational_questions,
            "statistics": statistics
        }
        
        # Log a sample of the final data structure for debugging
        logger.info(f"Summary data structure keys: {summary_data.keys()}")
        logger.info(f"Number of chapter summaries in response: {len(summary_data['chapterSummaries'])}")
        logger.info(f"Number of questions in response: {len(summary_data['educationalQuestions'])}")
        
        logger.info("Successfully built adventure summary data")
        return summary_data
        
    except Exception as e:
        logger.error(f"Error formatting summary data: {e}")
        # Return minimal valid structure on error
        return {
            "chapterSummaries": [],
            "educationalQuestions": [{
                "question": "What did you think of your adventure?",
                "userAnswer": "It was great!",
                "isCorrect": True,
                "explanation": "We're glad you enjoyed it."
            }],
            "statistics": {
                "chaptersCompleted": len(state.chapters) if state else 0,
                "questionsAnswered": 1,
                "timeSpent": "30 mins",
                "correctAnswers": 1
            }
        }


@router.post("/api/store-adventure-state")
async def store_adventure_state(state_data: dict):
    """Store adventure state and return a unique ID."""
    try:
        # Log critical fields to help with debugging
        logger.info("Storing adventure state with the following fields:")
        logger.info(f"Chapters count: {len(state_data.get('chapters', []))}")
        logger.info(f"Chapter summaries count: {len(state_data.get('chapter_summaries', []))}")
        logger.info(f"Summary chapter titles count: {len(state_data.get('summary_chapter_titles', []))}")
        logger.info(f"Lesson questions count: {len(state_data.get('lesson_questions', []))}")
        
        # Add chapter summaries if they don't exist
        if not state_data.get('chapter_summaries'):
            logger.info("Generating proper chapter summaries using ChapterManager")
            chapter_summaries = []
            chapter_titles = []
            
            # Import the ChapterManager to generate proper summaries
            from app.services.chapter_manager import ChapterManager
            chapter_manager = ChapterManager()
            
            # Generate summaries for each chapter
            for chapter in sorted(state_data.get('chapters', []), key=lambda x: x.get('chapter_number', 0)):
                chapter_number = chapter.get('chapter_number', 0)
                content = chapter.get('content', "")
                
                # For choice context, look at the next chapter's response if available
                choice_text = None
                choice_context = ""
                
                # Find this chapter's choice from the next chapter's response
                if chapter_number < len(state_data.get('chapters', [])):
                    # Get the next chapter (if not the last chapter)
                    next_chapters = [ch for ch in state_data.get('chapters', []) 
                                    if ch.get('chapter_number', 0) == chapter_number + 1]
                    
                    if next_chapters and next_chapters[0].get('response'):
                        response = next_chapters[0].get('response', {})
                        if response.get('choice_text'):
                            choice_text = response.get('choice_text')
                        elif response.get('chosen_answer'):
                            choice_text = response.get('chosen_answer')
                            choice_context = " (Correct answer)" if response.get('is_correct') else " (Incorrect answer)"
                
                # Generate a proper summary using ChapterManager
                try:
                    logger.info(f"Generating summary for chapter {chapter_number}")
                    summary_result = await chapter_manager.generate_chapter_summary(
                        content, choice_text, choice_context
                    )
                    
                    # Extract title and summary
                    title = summary_result.get("title", f"Chapter {chapter_number}: Adventure")
                    summary = summary_result.get("summary", "")
                    
                    logger.info(f"Generated title for chapter {chapter_number}: {title}")
                    logger.info(f"Generated summary for chapter {chapter_number}: {summary[:50]}...")
                    
                    chapter_titles.append(title)
                    chapter_summaries.append(summary)
                except Exception as e:
                    logger.error(f"Error generating summary for chapter {chapter_number}: {e}")
                    # Fallback to a simple summary
                    title = f"Chapter {chapter_number}: Adventure"
                    if len(content) > 200:
                        summary = f"{content[:200]}..."
                    else:
                        summary = content
                    
                    chapter_titles.append(title)
                    chapter_summaries.append(summary)
                    logger.info(f"Using fallback summary for chapter {chapter_number}")
            
            # Add to state data
            state_data['chapter_summaries'] = chapter_summaries
            state_data['summary_chapter_titles'] = chapter_titles
            logger.info(f"Added {len(chapter_summaries)} generated summaries to state")
        
        # Add lesson questions if they don't exist
        if not state_data.get('lesson_questions'):
            logger.info("Extracting lesson questions for state before storing")
            lesson_questions = []
            
            # Extract questions from lesson chapters
            for chapter in state_data.get('chapters', []):
                chapter_type = chapter.get('chapter_type', "").lower()
                if chapter_type == "lesson" and chapter.get('question'):
                    question_data = chapter.get('question', {})
                    
                    # Get response if available
                    is_correct = False
                    chosen_answer = "No answer recorded"
                    
                    response = chapter.get('response', {})
                    if response:
                        is_correct = response.get('is_correct', False)
                        chosen_answer = response.get('chosen_answer', "No answer recorded")
                    
                    # Process question
                    question_obj = {
                        "question": question_data.get("question", "Unknown question"),
                        "chosen_answer": chosen_answer,
                        "is_correct": is_correct,
                        "explanation": question_data.get("explanation", "")
                    }
                    
                    # Add correct answer
                    correct_answer = None
                    for answer in question_data.get("answers", []):
                        if answer.get("is_correct"):
                            correct_answer = answer.get("text")
                            break
                            
                    if correct_answer:
                        question_obj["correct_answer"] = correct_answer
                        
                    lesson_questions.append(question_obj)
                    logger.info(f"Added question from chapter {chapter.get('chapter_number')}")
            
            # If no questions found, add a fallback
            if not lesson_questions:
                logger.info("No lesson questions found, adding fallback question")
                lesson_questions.append({
                    "question": "What did you learn from this adventure?",
                    "chosen_answer": "I learned many valuable lessons",
                    "is_correct": True,
                    "explanation": "This adventure was designed to teach important concepts through an engaging narrative."
                })
            
            # Add to state data
            state_data['lesson_questions'] = lesson_questions
            logger.info(f"Added {len(lesson_questions)} questions to state")
            
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
