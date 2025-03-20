"""
Generate chapter summaries for all ten chapters of a Learning Odyssey adventure
and format them for use with the React summary component.

This script extends generate_chapter_summaries.py to output data in a format
compatible with the React AdventureSummary component.

Usage:
    python tests/simulations/generate_chapter_summaries_react.py <state_file> [--output OUTPUT_FILE]
    python tests/simulations/generate_chapter_summaries_react.py <state_file> --react-json [--output OUTPUT_FILE]

Examples:
    python tests/simulations/generate_chapter_summaries_react.py logs/simulations/simulation_state_2025-03-18_23-54-29_d92bc8a8.json
    python tests/simulations/generate_chapter_summaries_react.py logs/simulations/simulation_state_2025-03-18_23-54-29_d92bc8a8.json --react-json
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

# Import from the original script
from tests.simulations.generate_chapter_summaries import (
    generate_all_chapter_summaries,
    find_latest_simulation_state,
    load_chapter_content,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("chapter_summary_react_generator")


def generate_chapter_title(chapter_number: int, chapter_type: str, content: str) -> str:
    """Generate a title for a chapter based on its content.

    Args:
        chapter_number: The chapter number
        chapter_type: The type of chapter (STORY, LESSON, etc.)
        content: The chapter content

    Returns:
        A title for the chapter
    """
    # Default titles based on chapter type
    default_titles = {
        "STORY": f"Chapter {chapter_number}: Adventure Continues",
        "LESSON": f"Chapter {chapter_number}: Learning Moment",
        "REFLECT": f"Chapter {chapter_number}: Time to Reflect",
        "CONCLUSION": f"Chapter {chapter_number}: The Conclusion",
        "SUMMARY": f"Chapter {chapter_number}: Adventure Summary",
    }

    # Try to extract a title from the content
    # Look for patterns like "Chapter X: Title" or just the first sentence
    title_match = re.search(r"(?:Chapter\s+\d+\s*:\s*)?([A-Z][^\.!?]*[\.!?])", content)
    if title_match:
        # Clean up the extracted title
        title = title_match.group(1).strip()
        # Remove any trailing punctuation
        title = re.sub(r"[\.!?]$", "", title)
        # Limit length
        if len(title) > 50:
            title = title[:47] + "..."
        return f"Chapter {chapter_number}: {title}"

    # Fall back to default title
    return default_titles.get(chapter_type, f"Chapter {chapter_number}")


def extract_educational_questions(state_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract educational questions and answers from the state data.

    Args:
        state_data: The complete state data from the simulation

    Returns:
        A list of educational questions with user answers
    """
    questions = []

    # Extract chapters array
    chapters = state_data.get("chapters", [])

    # Find all LESSON chapters with questions and responses
    for chapter in chapters:
        if (
            chapter.get("chapter_type") == "LESSON"
            and "response" in chapter
            and "question" in chapter
        ):
            question_data = chapter["question"]
            response_data = chapter["response"]

            if not question_data or not response_data:
                continue

            # Find the correct answer
            correct_answer = None
            for answer in question_data.get("answers", []):
                if answer.get("is_correct"):
                    correct_answer = answer.get("text")
                    break

            # Create question object
            question_obj = {
                "question": question_data.get("question", "Unknown question"),
                "userAnswer": response_data.get("chosen_answer", "No answer"),
                "isCorrect": response_data.get("is_correct", False),
                "explanation": question_data.get("explanation", ""),
            }

            # Add correct answer if user was wrong
            if not question_obj["isCorrect"] and correct_answer:
                question_obj["correctAnswer"] = correct_answer

            questions.append(question_obj)

    return questions


def calculate_statistics(state_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate statistics from the state data.

    Args:
        state_data: The complete state data from the simulation

    Returns:
        Statistics about the adventure
    """
    # Extract chapters array
    chapters = state_data.get("chapters", [])

    # Count chapters completed
    chapters_completed = len(chapters)

    # Count lesson questions and correct answers
    questions_answered = 0
    correct_answers = 0

    for chapter in chapters:
        if chapter.get("chapter_type") == "LESSON" and "response" in chapter:
            questions_answered += 1
            if chapter["response"].get("is_correct", False):
                correct_answers += 1

    # Estimate time spent (45 minutes for a complete adventure)
    # This is just a placeholder - in a real implementation, you'd use actual timing data
    if chapters_completed > 0:
        minutes_spent = int(45 * (chapters_completed / 10))
        time_spent = f"{minutes_spent} mins"
    else:
        time_spent = "0 mins"

    return {
        "chaptersCompleted": chapters_completed,
        "questionsAnswered": questions_answered,
        "timeSpent": time_spent,
        "correctAnswers": correct_answers,
    }


async def generate_react_summary_data(
    state_file: str,
    output_file: str = "adventure_summary_react.json",
) -> Dict[str, Any]:
    """Generate summary data formatted for the React AdventureSummary component.

    Args:
        state_file: Path to the simulation state JSON file
        output_file: Path to save the generated JSON data

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
        summary_text = summary_data["summary"]

        # Load the original chapter content to generate a title
        try:
            chapter_data = await load_chapter_content(chapter_number, state_file)
            chapter_content = chapter_data["content"]

            # Generate a title for the chapter
            title = generate_chapter_title(
                chapter_number, chapter_type, chapter_content
            )

            # Add to formatted summaries
            chapter_summaries.append(
                {
                    "number": chapter_number,
                    "title": title,
                    "summary": summary_text,
                    "chapterType": chapter_type,
                }
            )
        except Exception as e:
            logger.warning(f"Error processing chapter {chapter_number}: {e}")
            # Use a fallback title if we can't load the content
            chapter_summaries.append(
                {
                    "number": chapter_number,
                    "title": f"Chapter {chapter_number}",
                    "summary": summary_text,
                    "chapterType": chapter_type,
                }
            )

    # Extract educational questions
    educational_questions = extract_educational_questions(state_data)

    # Calculate statistics
    statistics = calculate_statistics(state_data)

    # Create the complete data structure
    react_data = {
        "chapterSummaries": chapter_summaries,
        "educationalQuestions": educational_questions,
        "statistics": statistics,
    }

    # Save to file
    with open(output_file, "w") as f:
        json.dump(react_data, f, indent=2)

    logger.info(f"Saved React-compatible summary data to {output_file}")

    return react_data


if __name__ == "__main__":
    import argparse

    # Set up command line arguments
    parser = argparse.ArgumentParser(
        description="Generate chapter summaries formatted for React components"
    )
    parser.add_argument(
        "state_file",
        nargs="?",
        help="Path to simulation state file (optional, will use latest if not provided)",
    )
    parser.add_argument(
        "--output", default="adventure_summary_react.json", help="Output file path"
    )
    parser.add_argument(
        "--react-json",
        action="store_true",
        help="Generate JSON formatted for React components",
    )
    args = parser.parse_args()

    state_file = args.state_file

    # If no state file specified, find the latest one
    if not state_file:
        state_file = find_latest_simulation_state()
        if not state_file:
            print(
                "ERROR: No simulation state files found. Please run a simulation first or specify a state file path."
            )
            sys.exit(1)
        print(f"Using latest simulation state file: {os.path.basename(state_file)}")

    try:
        if args.react_json:
            # Generate React-compatible JSON
            react_data = asyncio.run(
                generate_react_summary_data(
                    state_file,
                    args.output,
                )
            )
            print(
                f"Generated React-compatible summary data with {len(react_data['chapterSummaries'])} chapters"
            )
        else:
            # Use the original function
            summaries = asyncio.run(
                generate_all_chapter_summaries(
                    state_file,
                    args.output,
                    skip_json=False,
                )
            )
            print(f"Generated {len(summaries)} chapter summaries")

    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        # Print more detailed error information for debugging
        import traceback

        print("\nDetailed error information:")
        traceback.print_exc()
        sys.exit(3)
