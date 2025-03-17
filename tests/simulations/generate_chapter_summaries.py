"""
Generate chapter summaries for all ten chapters of a Learning Odyssey adventure.

This script extracts chapter content from simulation log files and generates
consistent summaries for all chapters using the same prompt template and approach.
By default, it only prints the summaries to the console and does not save JSON files.

Usage:
    python tests/simulations/generate_chapter_summaries.py <log_file> [--output OUTPUT_FILE]
    python tests/simulations/generate_chapter_summaries.py <log_file> --save-json [--output OUTPUT_FILE]
    python tests/simulations/generate_chapter_summaries.py <log_file> --compact

Example:
    python tests/simulations/generate_chapter_summaries.py logs/simulations/simulation_2025-03-17_12345678.log
"""

import asyncio
import os
import sys
import json
import logging
from typing import List, Dict, Any, Optional

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


async def generate_chapter_summary(
    chapter_content: str, chosen_choice: str, choice_context: str, max_retries: int = 3
) -> str:
    """Generate a concise summary of the chapter content using the LLM service.

    This function is used consistently for ALL chapters, regardless of type.
    It first tries a direct API call, then falls back to streaming if that fails.

    Args:
        chapter_content: The full text of the chapter
        chosen_choice: The text of the choice made at the end of the chapter
        choice_context: Additional context about the choice
        max_retries: Maximum number of retry attempts for each approach

    Returns:
        A concise summary of the chapter

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
            summary = response.text.strip()

            # Strict error handling - no fallbacks
            if not summary:
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

            logger.info(
                f"Generated summary using direct API call ({len(summary)} chars)"
            )
            return summary

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

            summary = "".join(chunks).strip()

            # Strict error handling - no fallbacks
            if not summary:
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

            logger.info(
                f"Generated summary using streaming approach ({len(summary)} chars)"
            )
            return summary

        except Exception as e:
            logger.warning(
                f"Streaming approach failed (attempt {retry + 1}/{max_retries}): {e}"
            )
            if retry < max_retries - 1:
                await asyncio.sleep(2**retry)  # Exponential backoff
                continue
            else:
                raise Exception(f"Summary generation failed after all retries: {e}")


async def load_chapter_content(chapter_number: int, log_file: str) -> Dict[str, Any]:
    """Load chapter content from a simulation log file with strict error handling.

    Args:
        chapter_number: The chapter number to load content for
        log_file: Path to the simulation log file

    Returns:
        Dictionary containing chapter content and metadata

    Raises:
        ChapterContentError: If chapter content cannot be found
        FileNotFoundError: If the log file doesn't exist
    """
    if not os.path.exists(log_file):
        raise FileNotFoundError(f"Log file not found: {log_file}")

    chapter_content = None
    chapter_type = None
    chosen_choice = None

    with open(log_file, "r") as f:
        for line in f:
            # Look for chapter content in STATE_TRANSITION events
            if "EVENT:STATE_TRANSITION" in line:
                try:
                    data = json.loads(line)
                    if "state" in data:
                        state_data = json.loads(data["state"])
                        if "current_chapter" in state_data:
                            chapter_info = state_data["current_chapter"]
                            current_chapter_number = chapter_info.get("chapter_number")

                            if current_chapter_number == chapter_number:
                                chapter_content = chapter_info.get("content")
                                chapter_type = chapter_info.get("chapter_type")
                except Exception as e:
                    logger.error(f"Error parsing log line: {e}")

            # Look for choice selection events for this chapter
            if "EVENT:CHOICE_SELECTED" in line:
                try:
                    data = json.loads(line)
                    if data.get("chapter_number") == chapter_number:
                        chosen_choice = data.get("choice_text")
                except Exception as e:
                    logger.error(f"Error parsing choice event: {e}")

    # Strict error handling - no fallbacks
    if not chapter_content:
        raise ChapterContentError(
            f"Content for Chapter {chapter_number} not found in log file"
        )

    # For CONCLUSION chapter (10), there's no choice, so use a standard placeholder
    # This ensures consistent parameters to generate_chapter_summary for all chapters
    if chapter_number == 10 and not chosen_choice:
        chosen_choice = "End of story"

    # If no choice was found for any chapter, use a standard placeholder
    if not chosen_choice:
        chosen_choice = "No choice recorded"

    return {
        "content": chapter_content,
        "chapter_type": chapter_type,
        "choice": chosen_choice,
    }


async def generate_all_chapter_summaries(
    log_file: str,
    output_file: str = "chapter_summaries.json",
    skip_json: bool = True,
    compact_output: bool = False,
):
    """Generate summaries for all ten chapters and save to a file.

    Uses the EXACT SAME approach for ALL chapters with NO exceptions.

    Args:
        log_file: Path to the simulation log file
        output_file: Path to save the generated summaries
        skip_json: If True, skip saving to JSON file (default: True)
        compact_output: If True, use compact output format

    Raises:
        FileNotFoundError: If the log file doesn't exist
        ChapterContentError: If content for any chapter is missing
        Exception: If summary generation fails
    """
    summaries = []

    # Validate log file exists
    if not os.path.exists(log_file):
        raise FileNotFoundError(f"Log file not found: {log_file}")

    # Generate summaries for all 10 chapters
    for chapter_number in range(1, 11):
        try:
            logger.info(f"Processing Chapter {chapter_number}")

            # Load chapter content - may raise ChapterContentError
            chapter_data = await load_chapter_content(chapter_number, log_file)

            # Determine choice context (empty string by default)
            # This is the ONLY parameter that might vary, and it's based on data from the log
            choice_context = ""

            # Generate summary using the SAME function for ALL chapters
            summary = await generate_chapter_summary(
                chapter_data["content"], chapter_data["choice"], choice_context
            )

            # Store the summary
            summaries.append(
                {
                    "chapter_number": chapter_number,
                    "chapter_type": chapter_data["chapter_type"],
                    "summary": summary,
                }
            )

            logger.info(f"Generated summary for Chapter {chapter_number}")
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
        print("\nCHAPTER SUMMARIES\n")
        for summary_data in summaries:
            print(
                f"CHAPTER {summary_data['chapter_number']} ({summary_data['chapter_type']}): {summary_data['summary']}"
            )
    else:
        # Standard output format
        print("\n" + "=" * 80)
        print("CHAPTER SUMMARIES")
        print("=" * 80 + "\n")

        for summary_data in summaries:
            print(
                f"Chapter {summary_data['chapter_number']} ({summary_data['chapter_type']}):"
            )
            print(summary_data["summary"])
            print("-" * 40 + "\n")

    return summaries


def find_latest_simulation_log():
    """Find the latest timestamp simulation log file.

    Returns:
        str: Path to the latest simulation log file, or None if no logs found.
    """
    # Path to simulation logs directory
    logs_dir = "logs/simulations"

    # Check if the directory exists
    if not os.path.exists(logs_dir):
        logger.warning(f"Simulation logs directory not found: {logs_dir}")
        return None

    # Pattern for simulation log files
    import glob
    import re
    from datetime import datetime

    pattern = os.path.join(logs_dir, "simulation_*.log")

    # Find all simulation log files
    log_files = glob.glob(pattern)

    if not log_files:
        logger.warning(f"No simulation log files found in {logs_dir}")
        return None

    # Extract timestamp from filename and sort by timestamp
    timestamp_pattern = re.compile(r"simulation_(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})_")

    # Create a list of (file_path, timestamp) tuples
    timestamped_files = []
    for file_path in log_files:
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
        logger.warning("No valid timestamped simulation log files found")
        return None

    # Sort by timestamp (newest first)
    timestamped_files.sort(key=lambda x: x[1], reverse=True)

    # Get the latest log file
    latest_log_file = timestamped_files[0][0]
    logger.info(f"Found latest simulation log: {os.path.basename(latest_log_file)}")

    return latest_log_file


if __name__ == "__main__":
    import argparse

    # Set up command line arguments
    parser = argparse.ArgumentParser(
        description="Generate chapter summaries from simulation log"
    )
    parser.add_argument(
        "log_file",
        nargs="?",
        help="Path to simulation log file (optional, will use latest if not provided)",
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
    args = parser.parse_args()

    log_file = args.log_file

    # If no log file specified, find the latest one
    if not log_file:
        log_file = find_latest_simulation_log()
        if not log_file:
            print(
                "ERROR: No simulation log files found. Please run a simulation first or specify a log file path."
            )
            sys.exit(1)
        print(f"Using latest simulation log: {os.path.basename(log_file)}")

    try:
        # Run the async function
        summaries = asyncio.run(
            generate_all_chapter_summaries(
                log_file,
                args.output,
                skip_json=not args.save_json,
                compact_output=args.compact,
            )
        )

        # Check if any summaries were generated
        if not summaries:
            print("WARNING: No chapter summaries were generated.")
            sys.exit(2)

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
