import asyncio
import sys
import os
import json

# Add the project root to the Python path to allow imports
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, "../.."))
sys.path.insert(0, project_root)

from tests.debug_summary_chapter import (
    extract_chapter_summaries_from_log,
    create_test_state,
    generate_summary_content,
    find_latest_simulation_log,
)


async def show_summary_from_log(log_file_path):
    try:
        # Extract chapter summaries from log
        print(f"Extracting summaries from: {log_file_path}")
        all_summaries, lesson_questions = extract_chapter_summaries_from_log(
            log_file_path
        )
        print(f"Found {len(all_summaries)} chapter summaries")
        print(f"Found {len(lesson_questions)} lesson questions")

        # Process summaries to get unique ones for each chapter
        # The EVENT:CHAPTER_SUMMARY events in the log include chapter_number
        # We'll use this to organize summaries by chapter
        chapter_summaries = {}

        # Track which chapters we've found summaries for
        found_chapters = set()

        # STANDARDIZED APPROACH: First, prioritize EVENT:CHAPTER_SUMMARY logs
        # This is the primary standardized format for all chapter summaries
        with open(log_file_path, "r") as f:
            for line in f:
                # Extract from individual CHAPTER_SUMMARY events
                if "EVENT:CHAPTER_SUMMARY" in line:
                    try:
                        data = json.loads(line)
                        if "chapter_number" in data and "summary" in data:
                            chapter_num = data["chapter_number"]
                            summary = data["summary"]
                            # Store the latest summary for each chapter
                            chapter_summaries[chapter_num] = summary
                            found_chapters.add(chapter_num)

                            # Log when we find Chapter 10 summary specifically
                            if chapter_num == 10:
                                print(
                                    f"Found Chapter 10 summary in EVENT:CHAPTER_SUMMARY (primary standardized format)"
                                )
                    except (json.JSONDecodeError, KeyError):
                        pass

                # Extract from STORY_COMPLETE event
                if "EVENT:STORY_COMPLETE" in line:
                    try:
                        data = json.loads(line)
                        if "final_state" in data:
                            # Parse the final_state JSON string
                            final_state_str = data["final_state"]
                            final_state_data = json.loads(final_state_str)

                            # Check if this final state contains chapter_summaries
                            if (
                                "chapter_summaries" in final_state_data
                                and final_state_data["chapter_summaries"]
                            ):
                                # Map summaries to chapter numbers (only for chapters we haven't found yet)
                                story_complete_summaries = final_state_data[
                                    "chapter_summaries"
                                ]
                                for i, summary in enumerate(
                                    story_complete_summaries, 1
                                ):
                                    if i not in found_chapters:
                                        chapter_summaries[i] = summary
                                        found_chapters.add(i)
                                        print(
                                            f"Found Chapter {i} summary in STORY_COMPLETE event (fallback)"
                                        )
                                print(
                                    f"Extracted {len(story_complete_summaries)} chapter summaries from STORY_COMPLETE event"
                                )
                    except Exception as e:
                        print(f"Error parsing STORY_COMPLETE: {e}")
                        pass

                # Extract from FINAL_CHAPTER_SUMMARIES event (added in the standardized logging)
                if "EVENT:FINAL_CHAPTER_SUMMARIES" in line:
                    try:
                        data = json.loads(line)
                        if "chapter_summaries" in data:
                            # Get the array of chapter summaries
                            final_summaries = data["chapter_summaries"]
                            if isinstance(final_summaries, list) and final_summaries:
                                # Map summaries to chapter numbers (only for chapters we haven't found yet)
                                for i, summary in enumerate(final_summaries, 1):
                                    if i not in found_chapters:
                                        chapter_summaries[i] = summary
                                        found_chapters.add(i)
                                        print(
                                            f"Found Chapter {i} summary in EVENT:FINAL_CHAPTER_SUMMARIES (fallback)"
                                        )

                                # Log specifically for Chapter 10
                                if (
                                    len(final_summaries) >= 10
                                    and 10 not in found_chapters
                                ):
                                    print(
                                        f"Found Chapter 10 summary in EVENT:FINAL_CHAPTER_SUMMARIES (fallback)"
                                    )

                                print(
                                    f"Extracted {len(final_summaries)} chapter summaries from FINAL_CHAPTER_SUMMARIES event"
                                )
                    except Exception as e:
                        print(f"Error parsing FINAL_CHAPTER_SUMMARIES: {e}")
                        pass

                # Extract final chapter content for chapter 10 (supporting both old and new formats)
                # Note: We only use this as a last resort if we haven't found Chapter 10 summary through
                # the standardized EVENT:CHAPTER_SUMMARY format or other structured events
                if 10 not in found_chapters:
                    # First try to find any log entry with Chapter 10 content
                    if "Final chapter content" in line or "Chapter 10 content" in line:
                        try:
                            # First check if this is a debug log (not a proper summary)
                            if "Chapter 10 content preview:" in line:
                                # Skip debug logs that contain raw content previews
                                continue

                            data = json.loads(line)
                            if "message" in data:
                                # Extract the content from the message
                                message = data["message"]

                                # Handle old format
                                if message.startswith("Final chapter content:"):
                                    content = message[
                                        len("Final chapter content:") :
                                    ].strip()
                                    print("Found old format 'Final chapter content'")
                                # Handle new standardized format (but only if it's not a preview)
                                elif (
                                    message.startswith("Chapter 10 summary:")
                                    and "preview" not in message
                                ):
                                    content = message[
                                        len("Chapter 10 summary:") :
                                    ].strip()
                                    print("Found new format 'Chapter 10 summary'")
                                else:
                                    # Skip if neither format matches
                                    continue

                                # Only use this as a fallback if we haven't found Chapter 10 yet
                                if 10 not in found_chapters:
                                    # Create a summary for chapter 10 from the content
                                    # Use a more robust sentence splitting approach
                                    import re

                                    # Split on periods followed by space or newline, preserving the period
                                    sentences = re.split(r"\.(?=\s|\n|$)", content)
                                    # Filter out empty sentences and join with periods
                                    valid_sentences = [
                                        s.strip() for s in sentences if s.strip()
                                    ]
                                    # Take up to 5 sentences for a more comprehensive summary
                                    summary = ". ".join(valid_sentences[:5])
                                    # Ensure the summary ends with a period
                                    if summary and not summary.endswith("."):
                                        summary += "."

                                    # Add the summary to chapter_summaries
                                    chapter_summaries[10] = summary
                                    found_chapters.add(10)
                                    print(
                                        "Extracted chapter 10 summary from chapter content (fallback)"
                                    )
                        except Exception as e:
                            print(f"Error parsing Final chapter content: {e}")
                            pass

                    # Also look for chapter content in EVENT:CHAPTER_CONTENT logs
                    elif "EVENT:CHAPTER_CONTENT" in line:
                        try:
                            data = json.loads(line)
                            if (
                                "chapter_number" in data
                                and data["chapter_number"] == 10
                            ):
                                content = data.get("content", "")
                                if content:
                                    # Use a more robust sentence splitting approach
                                    import re

                                    # Split on periods followed by space or newline, preserving the period
                                    sentences = re.split(r"\.(?=\s|\n|$)", content)
                                    # Filter out empty sentences and join with periods
                                    valid_sentences = [
                                        s.strip() for s in sentences if s.strip()
                                    ]
                                    # Take up to 5 sentences for a more comprehensive summary
                                    summary = ". ".join(valid_sentences[:5])
                                    # Ensure the summary ends with a period
                                    if summary and not summary.endswith("."):
                                        summary += "."

                                    # Add the summary to chapter_summaries
                                    chapter_summaries[10] = summary
                                    found_chapters.add(10)
                                    print(
                                        "Extracted chapter 10 summary from EVENT:CHAPTER_CONTENT (fallback)"
                                    )
                        except Exception as e:
                            print(f"Error parsing EVENT:CHAPTER_CONTENT: {e}")
                            pass

        # If we couldn't extract chapter numbers, use the first 10 unique summaries
        if not chapter_summaries and all_summaries:
            # Get unique summaries while preserving order
            unique_summaries = []
            for summary in all_summaries:
                if summary not in unique_summaries:
                    unique_summaries.append(summary)

            # Use up to 10 unique summaries
            for i, summary in enumerate(unique_summaries[:10], 1):
                chapter_summaries[i] = summary

        # Final check specifically for Chapter 10
        if 10 not in chapter_summaries or not chapter_summaries[10]:
            # Look for raw chapter content in the log file
            with open(log_file_path, "r") as f:
                conclusion_content = ""
                for line in f:
                    if (
                        "Chapter 10 (Conclusion)" in line
                        or "CONCLUSION chapter content" in line
                    ):
                        # Try to extract the content after this marker
                        parts = line.split("Chapter 10 (Conclusion)")
                        if len(parts) > 1:
                            conclusion_content = parts[1].strip()
                        else:
                            parts = line.split("CONCLUSION chapter content")
                            if len(parts) > 1:
                                conclusion_content = parts[1].strip()

                if conclusion_content:
                    # Use a more robust sentence splitting approach
                    import re

                    # Split on periods followed by space or newline, preserving the period
                    sentences = re.split(r"\.(?=\s|\n|$)", conclusion_content)
                    # Filter out empty sentences and join with periods
                    valid_sentences = [s.strip() for s in sentences if s.strip()]
                    # Take up to 5 sentences for a more comprehensive summary
                    summary = ". ".join(valid_sentences[:5])
                    # Ensure the summary ends with a period
                    if summary and not summary.endswith("."):
                        summary += "."

                    chapter_summaries[10] = summary
                    print(
                        "Extracted chapter 10 summary from raw content (last resort fallback)"
                    )

        # Ensure we have exactly 10 chapters
        summaries = []
        for i in range(1, 11):
            if i in chapter_summaries:
                summaries.append(chapter_summaries[i])
            else:
                # Create a more descriptive dummy summary for missing chapters
                if i == 10:  # Special case for conclusion chapter
                    dummy_summary = "In the conclusion chapter, the adventure reached its resolution. The protagonist faced the final challenge and completed their journey, bringing closure to the story and reflecting on the lessons learned along the way."
                else:
                    dummy_summary = f"This is a placeholder summary for Chapter {i}. The actual chapter summary was not found in the log file. This chapter would have continued the adventure's progression toward its conclusion."
                summaries.append(dummy_summary)
                print(f"Added descriptive placeholder for Chapter {i}")

        print(f"Processed {len(summaries)} chapter summaries for the summary chapter")
    except ValueError as e:
        print(f"Error: {e}")
        return

    # Create test state with these summaries
    state = await create_test_state(summaries)

    # Add lesson questions to the state
    state.lesson_questions = lesson_questions

    # Generate summary content
    summary_content = await generate_summary_content(state)

    # If we have lesson questions, add them to the summary content
    if lesson_questions:
        # Find the Learning Report section
        learning_report_index = summary_content.find("## Learning Report")

        # If Learning Report section not found, add it
        if learning_report_index == -1:
            # Add Learning Report section at the end of the summary content
            summary_content += "\n\n# Learning Report"
            learning_report_index = summary_content.find("# Learning Report")

        # Extract everything before the Learning Report section
        before_learning_report = summary_content[
            : learning_report_index + len("# Learning Report")
        ]

        # Create a new Learning Report section with the lesson questions
        learning_report = "\n\nDuring your adventure, you encountered the following educational questions:\n\n"
        for i, question in enumerate(lesson_questions, 1):
            learning_report += f"{i}. **Question**: {question['question']}\n"
            learning_report += f"   **Topic**: {question['topic']}"
            if question["subtopic"]:
                learning_report += f" - {question['subtopic']}"

            # Add chosen answer if available
            if "chosen_answer" in question and question["chosen_answer"]:
                learning_report += f"\n   **Your Answer**: {question['chosen_answer']} "
                if "is_correct" in question:
                    learning_report += (
                        f"({'Correct' if question['is_correct'] else 'Incorrect'})"
                    )

                # Only show correct answer if the user's answer was incorrect
                if "is_correct" in question and not question["is_correct"]:
                    learning_report += (
                        f"\n   **Correct Answer**: {question['correct_answer']}"
                    )

            # Add explanation if available (always show regardless of correctness)
            if "explanation" in question and question["explanation"]:
                learning_report += f"\n   **Explanation**: {question['explanation']}"

            learning_report += "\n\n"

        # Add thank you message at the end
        learning_report += "Thank you for joining us on this learning odyssey!"

        # We don't need any content after the Learning Report section
        after_learning_report = ""

        # Combine everything
        summary_content = (
            before_learning_report + learning_report + after_learning_report
        )

    # Display the summary
    print("\n" + "=" * 80)
    print("SUMMARY CHAPTER CONTENT")
    print("=" * 80 + "\n")
    print(summary_content)
    print("\n" + "=" * 80)


if __name__ == "__main__":
    log_file = None

    # Allow specifying a specific log file via command line
    if len(sys.argv) > 1:
        log_file = sys.argv[1]
        # Make sure the specified log file exists
        if not os.path.exists(log_file):
            print(f"Error: Specified log file not found: {log_file}")
            sys.exit(1)
    else:
        # Find the latest simulation log file
        log_file = find_latest_simulation_log()
        if not log_file:
            print(
                "Error: No simulation log files found. Please run a simulation first or specify a log file path."
            )
            sys.exit(1)
        print(f"Using latest simulation log: {os.path.basename(log_file)}")

    asyncio.run(show_summary_from_log(log_file))
