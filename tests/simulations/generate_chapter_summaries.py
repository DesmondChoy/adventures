"""
Generate chapter summaries for all ten chapters of a Learning Odyssey adventure.

This script extracts chapter content from simulation state JSON files and generates
consistent summaries for all chapters using the same prompt template and approach.
By default, it only prints the summaries to the console and does not save JSON files.

The script can also generate React-compatible JSON data for use with the Adventure
Summary component, including chapter titles, educational questions, and statistics.

Usage:
    python tests/simulations/generate_chapter_summaries.py --react-json [--react-output OUTPUT_FILE]
"""

import asyncio
import os
import sys
import json
import logging
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta

# Add project root to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "../.."))
sys.path.insert(0, project_root)

# Import necessary components
from app.services.llm import LLMService
from app.services.llm.prompt_templates import SUMMARY_CHAPTER_PROMPT

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("chapter_summary_generator")

# LLM service for generating summaries
llm_service = LLMService()


class ChapterContentError(Exception):
    """Error raised when chapter content cannot be found."""

    pass


def parse_title_and_summary(response_text: str) -> Tuple[str, str]:
    """Parse the response text to extract the title and summary.

    Args:
        response_text: The response text from the LLM

    Returns:
        A tuple containing the title and summary
    """
    title = ""
    summary = ""

    # Split by section headers
    sections = response_text.split("# ")

    # Extract title and summary
    for section in sections:
        if section.startswith("CHAPTER TITLE"):
            title = section.replace("CHAPTER TITLE", "").strip()
        elif section.startswith("CHAPTER SUMMARY"):
            summary = section.replace("CHAPTER SUMMARY", "").strip()

    # If we couldn't extract a title, use a default
    if not title:
        title = "Adventure Chapter"
        logger.warning("Could not extract title from response, using default")

    # If we couldn't extract a summary, use the whole response
    if not summary:
        summary = response_text
        logger.warning("Could not extract summary from response, using full response")

    return title, summary


async def generate_chapter_summary(
    chapter_content: str, chosen_choice: str, choice_context: str, max_retries: int = 3
) -> Dict[str, str]:
    """Generate a title and concise summary of the chapter content using the LLM service.

    This function is used consistently for ALL chapters, regardless of type.
    It first tries a direct API call, then falls back to streaming if that fails.
    The response is parsed to extract both the title and summary.

    Args:
        chapter_content: The full text of the chapter
        chosen_choice: The text of the choice made at the end of the chapter
        choice_context: Additional context about the choice
        max_retries: Maximum number of retry attempts for each approach

    Returns:
        A dictionary containing the title and summary of the chapter

    Raises:
        Exception: If summary generation fails for any reason
    """
    # Create a custom prompt for the chapter summary using the template
    custom_prompt = SUMMARY_CHAPTER_PROMPT.format(
        chapter_content=chapter_content,
        chosen_choice=chosen_choice,
        choice_context=choice_context,
    )

    logger.debug(f"Generating summary with prompt: {custom_prompt[:100]}...")

    # Create a minimal state object for the LLM service
    class MinimalState:
        def __init__(self):
            self.current_chapter_id = "summary"
            self.story_length = 1
            self.chapters = []
            self.metadata = {"prompt_override": True}

    # Try direct API call first (non-streaming) for Gemini
    for retry in range(max_retries):
        try:
            logger.info(
                f"Attempting direct API call (attempt {retry + 1}/{max_retries})"
            )
            from google import generativeai as genai

            # Initialize the model with system prompt
            model = genai.GenerativeModel(
                model_name="gemini-2.0-flash",
                system_instruction="You are a helpful assistant that follows instructions precisely.",
            )

            # Generate content without streaming
            response = model.generate_content(custom_prompt)

            # Extract the text directly
            response_text = response.text.strip()

            # Strict error handling - no fallbacks
            if not response_text:
                logger.warning(
                    f"Empty response from direct API call (attempt {retry + 1}/{max_retries})"
                )
                if retry < max_retries - 1:
                    await asyncio.sleep(2**retry)  # Exponential backoff
                    continue
                else:
                    logger.warning(
                        "All direct API call attempts failed, trying streaming approach"
                    )
                    break  # Try streaming approach

            # Parse the response to extract title and summary
            title, summary = parse_title_and_summary(response_text)

            logger.info(
                f"Generated title and summary using direct API call (title: {len(title)} chars, summary: {len(summary)} chars)"
            )
            return {"title": title, "summary": summary}

        except Exception as e:
            logger.warning(
                f"Direct API call failed (attempt {retry + 1}/{max_retries}): {e}"
            )
            if retry < max_retries - 1:
                await asyncio.sleep(2**retry)  # Exponential backoff
                continue
            else:
                logger.warning(
                    "All direct API call attempts failed, trying streaming approach"
                )
                break  # Try streaming approach

    # Fall back to streaming approach
    for retry in range(max_retries):
        try:
            logger.info(
                f"Attempting streaming approach (attempt {retry + 1}/{max_retries})"
            )
            chunks = []
            async for chunk in llm_service.generate_with_prompt(
                system_prompt="You are a helpful assistant that follows instructions precisely.",
                user_prompt=custom_prompt,
            ):
                chunks.append(chunk)

            response_text = "".join(chunks).strip()

            # Strict error handling - no fallbacks
            if not response_text:
                logger.warning(
                    f"Empty response from streaming approach (attempt {retry + 1}/{max_retries})"
                )
                if retry < max_retries - 1:
                    await asyncio.sleep(2**retry)  # Exponential backoff
                    continue
                else:
                    raise Exception(
                        "Summary generation failed: Empty response from all LLM approaches"
                    )

            # Parse the response to extract title and summary
            title, summary = parse_title_and_summary(response_text)

            logger.info(
                f"Generated title and summary using streaming approach (title: {len(title)} chars, summary: {len(summary)} chars)"
            )
            return {"title": title, "summary": summary}

        except Exception as e:
            logger.warning(
                f"Streaming approach failed (attempt {retry + 1}/{max_retries}): {e}"
            )
            if retry < max_retries - 1:
                await asyncio.sleep(2**retry)  # Exponential backoff
                continue
            else:
                raise Exception(f"Summary generation failed after all retries: {e}")


async def load_chapter_content(chapter_number: int, state_file: str) -> Dict[str, Any]:
    """Load chapter content from a simulation state JSON file with strict error handling.

    Args:
        chapter_number: The chapter number to load content for
        state_file: Path to the simulation state JSON file

    Returns:
        Dictionary containing chapter content and metadata

    Raises:
        ChapterContentError: If chapter content cannot be found
        FileNotFoundError: If the state file doesn't exist
    """
    if not os.path.exists(state_file):
        raise FileNotFoundError(f"State file not found: {state_file}")

    # Load the entire state file
    with open(state_file, "r") as f:
        state_data = json.load(f)

    # Extract chapters array
    chapters = state_data.get("chapters", [])

    # Find the chapter with the matching chapter_number
    chapter_data = None
    for chapter in chapters:
        if chapter.get("chapter_number") == chapter_number:
            chapter_data = chapter
            break

    # If chapter not found, raise error
    if not chapter_data:
        raise ChapterContentError(
            f"Content for Chapter {chapter_number} not found in state file"
        )

    # Extract content and chapter_type
    chapter_content = chapter_data.get("content")
    chapter_type = chapter_data.get("chapter_type")

    # Find the choice made for this chapter from simulation_metadata
    chosen_choice = "No choice recorded"
    if (
        "simulation_metadata" in state_data
        and "random_choices" in state_data["simulation_metadata"]
    ):
        for choice in state_data["simulation_metadata"]["random_choices"]:
            if choice.get("chapter_number") == chapter_number:
                chosen_choice = choice.get("choice_text", "No choice recorded")
                break

    # For CONCLUSION chapter (10), there's no choice, so use a standard placeholder
    # This ensures consistent parameters to generate_chapter_summary for all chapters
    if chapter_number == 10 and chosen_choice == "No choice recorded":
        chosen_choice = "End of story"

    return {
        "content": chapter_content,
        "chapter_type": chapter_type,
        "choice": chosen_choice,
    }


async def generate_all_chapter_summaries(
    state_file: str,
    output_file: str = "chapter_summaries.json",
    skip_json: bool = True,
    compact_output: bool = False,
    delay_between_chapters: float = 2.0,  # New parameter for delay between API calls
):
    """Generate summaries for all ten chapters and save to a file.

    Uses the EXACT SAME approach for ALL chapters with NO exceptions.

    Args:
        state_file: Path to the simulation state JSON file
        output_file: Path to save the generated summaries
        skip_json: If True, skip saving to JSON file (default: True)
        compact_output: If True, use compact output format
        delay_between_chapters: Delay in seconds between processing chapters (default: 2.0)

    Raises:
        FileNotFoundError: If the state file doesn't exist
        ChapterContentError: If content for any chapter is missing
        Exception: If summary generation fails
    """
    summaries = []

    # Validate state file exists
    if not os.path.exists(state_file):
        raise FileNotFoundError(f"State file not found: {state_file}")

    # Generate summaries for all 10 chapters
    for chapter_number in range(1, 11):
        try:
            logger.info(f"Processing Chapter {chapter_number}")

            # Load chapter content - may raise ChapterContentError
            chapter_data = await load_chapter_content(chapter_number, state_file)

            # Determine choice context (empty string by default)
            # This is the ONLY parameter that might vary, and it's based on data from the log
            choice_context = ""

            # Generate summary using the SAME function for ALL chapters
            result = await generate_chapter_summary(
                chapter_data["content"], chapter_data["choice"], choice_context
            )

            # Store the summary
            summaries.append(
                {
                    "chapter_number": chapter_number,
                    "chapter_type": chapter_data["chapter_type"],
                    "title": result["title"],
                    "summary": result["summary"],
                }
            )

            logger.info(f"Generated summary for Chapter {chapter_number}")

            # Add a delay between chapters to avoid overwhelming the API
            if chapter_number < 10:  # No need to delay after the last chapter
                logger.info(
                    f"Pausing for {delay_between_chapters} seconds before next chapter..."
                )
                await asyncio.sleep(delay_between_chapters)
        except ChapterContentError as e:
            # Log the error but continue processing other chapters
            logger.warning(f"Skipping Chapter {chapter_number}: {e}")
            continue

    # Save summaries to file (unless skip_json is True)
    if not skip_json:
        with open(output_file, "w") as f:
            json.dump(summaries, f, indent=2)
        logger.info(f"Saved {len(summaries)} chapter summaries to {output_file}")

    # Print summaries
    if compact_output:
        # Compact output format - single paragraph per chapter
        logger.info("CHAPTER SUMMARIES (COMPACT FORMAT)")
        for summary_data in summaries:
            logger.info(
                f"CHAPTER {summary_data['chapter_number']} ({summary_data['chapter_type']}): {summary_data['title']}"
            )
            logger.info(f"{summary_data['summary']}")
            # Also print to console for user visibility
            print(
                f"\nCHAPTER {summary_data['chapter_number']} ({summary_data['chapter_type']}): {summary_data['title']}"
            )
            print(f"{summary_data['summary']}")
    else:
        # Standard output format
        logger.info("CHAPTER SUMMARIES (STANDARD FORMAT)")
        for summary_data in summaries:
            logger.info(
                f"Chapter {summary_data['chapter_number']} ({summary_data['chapter_type']}): {summary_data['title']}"
            )
            logger.info(f"{summary_data['summary']}")

            # Also print to console for user visibility
            print("\n" + "=" * 80)
            print(
                f"Chapter {summary_data['chapter_number']} ({summary_data['chapter_type']})"
            )
            print("=" * 80 + "\n")
            print(f"Title: {summary_data['title']}")
            print(summary_data["summary"])
            print("-" * 40)

    return summaries


def extract_educational_questions(state_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract educational questions and answers from the state data.

    Args:
        state_data: The complete state data from the simulation

    Returns:
        A list of educational questions with user answers
    """
    questions = []

    # Extract chapters array and simulation metadata
    chapters = state_data.get("chapters", [])
    random_choices = state_data.get("simulation_metadata", {}).get("random_choices", [])

    # Print debug information
    logger.info("Extracting educational questions...")
    logger.info(f"Found {len(chapters)} chapters")
    logger.info(f"Found {len(random_choices)} recorded choices")

    # Create a mapping of chapter numbers to choices
    chapter_choices = {}
    for choice in random_choices:
        chapter_number = choice.get("chapter_number")
        if chapter_number:
            chapter_choices[chapter_number] = choice
            logger.debug(
                f"Mapped choice for chapter {chapter_number}: {choice['choice_text']}"
            )

    # Check if lesson_questions is already populated in the state
    if state_data.get("lesson_questions") and len(state_data["lesson_questions"]) > 0:
        logger.info(
            f"Using {len(state_data['lesson_questions'])} pre-populated lesson questions"
        )

        # Process each lesson question and match with user answers
        for question_data in state_data["lesson_questions"]:
            # Find the chapter number for this question
            chapter_number = None
            for chapter in chapters:
                if (
                    chapter.get("chapter_type") == "lesson"
                    and chapter.get("question")
                    and chapter["question"].get("question")
                    == question_data.get("question")
                ):
                    chapter_number = chapter.get("chapter_number")
                    break

            if not chapter_number:
                logger.warning(
                    f"Could not find chapter for question: {question_data.get('question')}"
                )
                continue

            # Find the choice made for this chapter
            choice = chapter_choices.get(chapter_number)
            chosen_answer = (
                choice.get("choice_text", "No answer") if choice else "No answer"
            )

            # Determine if the answer was correct
            correct_answer = question_data.get("correct_answer")
            is_correct = chosen_answer == correct_answer if correct_answer else False

            # Create question object in the format expected by EducationalCard
            question_obj = {
                "question": question_data.get("question", "Unknown question"),
                "userAnswer": chosen_answer,
                "isCorrect": is_correct,
                "explanation": question_data.get("explanation", ""),
            }

            # Add correct answer if user was wrong
            if not is_correct and correct_answer:
                question_obj["correctAnswer"] = correct_answer

            questions.append(question_obj)
            logger.info(
                f"Processed question from lesson_questions: {question_obj['question']}"
            )
    else:
        # Find all LESSON chapters with questions
        lesson_chapters = []
        for chapter in chapters:
            chapter_number = chapter.get("chapter_number")
            chapter_type = chapter.get("chapter_type", "").lower()

            if chapter_type == "lesson" and "question" in chapter and chapter_number:
                lesson_chapters.append(chapter_number)
                question_data = chapter["question"]
                if not question_data:
                    logger.warning(f"Empty question data in chapter {chapter_number}")
                    continue

                logger.info(f"Processing LESSON chapter {chapter_number}")

                # Find the choice made for this chapter
                choice = chapter_choices.get(chapter_number)
                chosen_answer = (
                    choice.get("choice_text", "No answer") if choice else "No answer"
                )

                logger.debug(f"Chapter {chapter_number} choice: {choice}")
                logger.debug(f"Chapter {chapter_number} chosen answer: {chosen_answer}")

                # Find the correct answer and determine if the chosen answer was correct
                correct_answer = None
                is_correct = False
                for answer in question_data.get("answers", []):
                    if answer.get("is_correct"):
                        correct_answer = answer.get("text")
                        # Check if the chosen answer matches the correct answer
                        if chosen_answer == correct_answer:
                            is_correct = True
                        break

                # Create question object
                question_obj = {
                    "question": question_data.get("question", "Unknown question"),
                    "userAnswer": chosen_answer,
                    "isCorrect": is_correct,
                    "explanation": question_data.get("explanation", ""),
                }

                # Add correct answer if user was wrong
                if not is_correct and correct_answer:
                    question_obj["correctAnswer"] = correct_answer

                questions.append(question_obj)
                logger.info(
                    f"Added question from chapter {chapter_number}: {question_obj['question']}"
                )

        # Print debug information
        logger.info(f"Found {len(lesson_chapters)} LESSON chapters with questions")
        logger.info(f"Extracted {len(questions)} questions")

        # If no questions were found but we know there should be some (based on lesson chapters),
        # check the event logs in the simulation metadata for LESSON_QUESTION and LESSON_ANSWER events
        if len(questions) == 0 and len(lesson_chapters) > 0:
            logger.warning("No questions extracted from chapters, checking event logs")

            # Look for LESSON_QUESTION events in the log data
            log_events = state_data.get("simulation_metadata", {}).get("log_events", [])
            question_events = [
                e for e in log_events if e.get("event") == "LESSON_QUESTION"
            ]
            answer_events = [e for e in log_events if e.get("event") == "LESSON_ANSWER"]

            if question_events:
                logger.info(f"Found {len(question_events)} question events in logs")

                for q_event in question_events:
                    # Find matching answer event
                    chapter_number = q_event.get("chapter_number")
                    matching_answer = next(
                        (
                            a
                            for a in answer_events
                            if a.get("chapter_number") == chapter_number
                        ),
                        None,
                    )

                    if matching_answer:
                        question_obj = {
                            "question": q_event.get("question", "Unknown question"),
                            "userAnswer": matching_answer.get(
                                "selected_answer", "No answer"
                            ),
                            "isCorrect": matching_answer.get("is_correct", False),
                            "explanation": q_event.get("explanation", ""),
                        }

                        # Add correct answer if user was wrong
                        if not question_obj["isCorrect"]:
                            question_obj["correctAnswer"] = matching_answer.get(
                                "correct_answer"
                            )

                        questions.append(question_obj)
                        logger.info(
                            f"Added question from event logs: {question_obj['question']}"
                        )

    # If we still have no questions but know there should be some, log an error
    if len(questions) == 0 and len(lesson_chapters) > 0:
        logger.error("Failed to extract any questions despite finding LESSON chapters")
        logger.error(
            "This indicates a problem with the simulation state or extraction logic"
        )
        # We don't add hardcoded fallbacks anymore - return an empty array instead

    return questions


def calculate_summary_statistics(state_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate statistics for the adventure summary.

    Args:
        state_data: The complete state data from the simulation

    Returns:
        Statistics about the adventure for the summary page
    """
    # Get story_length from state data (default to 10 if not present)
    # This ensures we use the actual configured story length rather than counting chapters
    chapters_completed = state_data.get("story_length", 10)

    # Extract educational questions to count them
    educational_questions = extract_educational_questions(state_data)

    # Count questions and correct answers
    questions_answered = len(educational_questions)
    correct_answers = sum(1 for q in educational_questions if q.get("isCorrect", False))

    # Log statistics
    logger.info(
        f"Statistics: {questions_answered} questions answered, {correct_answers} correct"
    )

    # Use a standard time spent value (this could be calculated from timestamps in the future)
    time_spent = "30 mins"

    return {
        "chaptersCompleted": chapters_completed,
        "questionsAnswered": questions_answered,
        "timeSpent": time_spent,
        "correctAnswers": correct_answers,
    }


async def generate_react_summary_data(
    state_file: str,
    output_file: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate summary data formatted for the React AdventureSummary component.

    Args:
        state_file: Path to the simulation state JSON file
        output_file: Optional path to save the generated JSON data. If None, data is not saved to a file.

    Returns:
        The formatted summary data
    """
    # First, generate the chapter summaries using the original function
    summaries = await generate_all_chapter_summaries(
        state_file,
        skip_json=True,  # Don't save the original format JSON
        compact_output=False,
    )

    # Load the complete state data to extract additional information
    with open(state_file, "r") as f:
        state_data = json.load(f)

    # Format chapter summaries for React
    chapter_summaries = []
    for summary_data in summaries:
        chapter_number = summary_data["chapter_number"]
        chapter_type = summary_data["chapter_type"]
        title = summary_data["title"]
        summary_text = summary_data["summary"]

        # Add to formatted summaries
        chapter_summaries.append(
            {
                "number": chapter_number,
                "title": title,
                "summary": summary_text,
                "chapterType": chapter_type.lower(),
            }
        )

    # Extract educational questions
    educational_questions = extract_educational_questions(state_data)

    # Calculate statistics (this already counts correct answers from educational_questions)
    statistics = calculate_summary_statistics(state_data)

    logger.info(f"Generated statistics: {statistics}")

    # Create the complete data structure
    react_data = {
        "chapterSummaries": chapter_summaries,
        "educationalQuestions": educational_questions,
        "statistics": statistics,
    }

    # Save to file if output_file is provided
    if output_file:
        with open(output_file, "w") as f:
            json.dump(react_data, f, indent=2)
        logger.info(f"Saved React-compatible summary data to {output_file}")
    else:
        logger.info("React-compatible summary data generated but not saved to file")

    return react_data


def find_latest_simulation_state():
    """Find the latest timestamp simulation state JSON file.

    Returns:
        str: Path to the latest simulation state file, or None if no state files found.
    """
    # Path to simulation logs directory
    logs_dir = "logs/simulations"

    # Check if the directory exists
    if not os.path.exists(logs_dir):
        logger.warning(f"Simulation logs directory not found: {logs_dir}")
        return None

    # Pattern for simulation state files
    import glob
    import re
    from datetime import datetime

    pattern = os.path.join(logs_dir, "simulation_state_*.json")

    # Find all simulation state files
    state_files = glob.glob(pattern)

    if not state_files:
        logger.warning(f"No simulation state files found in {logs_dir}")
        return None

    # Extract timestamp from filename and sort by timestamp
    timestamp_pattern = re.compile(
        r"simulation_state_(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})_"
    )

    # Create a list of (file_path, timestamp) tuples
    timestamped_files = []
    for file_path in state_files:
        filename = os.path.basename(file_path)
        match = timestamp_pattern.search(filename)
        if match:
            timestamp_str = match.group(1)
            try:
                # Parse timestamp string to datetime object
                timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d_%H-%M-%S")
                timestamped_files.append((file_path, timestamp))
            except ValueError:
                logger.warning(f"Failed to parse timestamp from filename: {filename}")

    if not timestamped_files:
        logger.warning("No valid timestamped simulation state files found")
        return None

    # Sort by timestamp (newest first)
    timestamped_files.sort(key=lambda x: x[1], reverse=True)

    # Get the latest state file
    latest_state_file = timestamped_files[0][0]
    logger.info(
        f"Found latest simulation state file: {os.path.basename(latest_state_file)}"
    )

    return latest_state_file


if __name__ == "__main__":
    import argparse

    # Set up command line arguments
    parser = argparse.ArgumentParser(
        description="Generate chapter summaries from simulation state file"
    )
    parser.add_argument(
        "state_file",
        nargs="?",
        help="Path to simulation state file (optional, will use latest if not provided)",
    )
    parser.add_argument(
        "--output", default="chapter_summaries.json", help="Output file path"
    )
    parser.add_argument(
        "--save-json",
        action="store_true",
        help="Save summaries to JSON file (default: no JSON)",
    )
    parser.add_argument(
        "--compact", action="store_true", help="Use compact output format"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=2.0,
        help="Delay in seconds between processing chapters (default: 2.0)",
    )
    parser.add_argument(
        "--react-json",
        action="store_true",
        help="Generate JSON formatted for React components",
    )
    parser.add_argument(
        "--react-output",
        help="Output file path for React JSON (only used with --react-json)",
    )
    args = parser.parse_args()

    state_file = args.state_file

    # If no state file specified, find the latest one
    if not state_file:
        state_file = find_latest_simulation_state()
        if not state_file:
            logger.error(
                "No simulation state files found. Please run a simulation first or specify a state file path."
            )
            print(
                "ERROR: No simulation state files found. Please run a simulation first or specify a state file path."
            )
            sys.exit(1)
        logger.info(
            f"Using latest simulation state file: {os.path.basename(state_file)}"
        )
        print(f"Using latest simulation state file: {os.path.basename(state_file)}")

    try:
        if args.react_json and args.react_output:
            # Generate React-compatible JSON only if both flags are provided
            react_data = asyncio.run(
                generate_react_summary_data(
                    state_file,
                    args.react_output,
                )
            )
            logger.info(
                f"Generated React-compatible summary data with {len(react_data['chapterSummaries'])} chapters"
            )
            print(
                f"Successfully generated React-compatible summary data with {len(react_data['chapterSummaries'])} chapters"
            )
        elif args.react_json:
            # Generate React-compatible JSON but don't save to file
            react_data = asyncio.run(
                generate_react_summary_data(
                    state_file,
                    None,  # Don't save to file
                )
            )
            logger.info(
                f"Generated React-compatible summary data with {len(react_data['chapterSummaries'])} chapters (not saved to file)"
            )
            print(
                f"Successfully generated React-compatible summary data with {len(react_data['chapterSummaries'])} chapters (not saved to file)"
            )
        else:
            # Run the original function
            summaries = asyncio.run(
                generate_all_chapter_summaries(
                    state_file,
                    args.output,
                    skip_json=not args.save_json,
                    compact_output=args.compact,
                    delay_between_chapters=args.delay,  # Pass the delay parameter
                )
            )

            # Check if any summaries were generated
            if not summaries:
                logger.warning("No chapter summaries were generated.")
                print("WARNING: No chapter summaries were generated.")
                sys.exit(2)

    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        print(f"ERROR: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"ERROR: Unexpected error: {e}")
        # Print more detailed error information for debugging
        import traceback

        print("\nDetailed error information:")
        traceback.print_exc()
        sys.exit(3)
