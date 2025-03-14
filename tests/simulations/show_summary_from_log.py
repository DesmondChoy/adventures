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
)


async def show_summary_from_log(log_file_path):
    try:
        # Extract chapter summaries from log
        print(f"Extracting summaries from: {log_file_path}")
        summaries, lesson_questions = extract_chapter_summaries_from_log(log_file_path)
        print(f"Found {len(summaries)} chapter summaries")
        print(f"Found {len(lesson_questions)} lesson questions")

        # If we have some summaries but not 10, add dummy summaries for the missing ones
        if len(summaries) < 10:
            print(
                f"Found {len(summaries)} chapter summaries, but need 10. Adding dummy summaries for the missing chapters."
            )
            existing_count = len(summaries)
            for i in range(existing_count + 1, 11):
                summaries.append(
                    f"This is a dummy summary for Chapter {i}. It was created because this chapter summary was not found in the log file."
                )
            print(f"Added {10 - existing_count} dummy summaries")
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
        if learning_report_index != -1:
            # Extract everything before the Learning Report section
            before_learning_report = summary_content[
                : learning_report_index + len("## Learning Report")
            ]

            # Find the default "You didn't encounter any educational questions" message
            default_message_index = summary_content.find(
                "You didn't encounter any educational questions", learning_report_index
            )

            # Extract everything after the Learning Report section but before the default message
            if default_message_index != -1:
                # Find the start of the paragraph containing the default message
                paragraph_start = summary_content.rfind(
                    "\n\n", learning_report_index, default_message_index
                )
                if paragraph_start == -1:
                    paragraph_start = learning_report_index + len("## Learning Report")

                # Find the end of the paragraph containing the default message
                paragraph_end = summary_content.find("\n\n", default_message_index)
                if paragraph_end == -1:
                    paragraph_end = len(summary_content)

                # Extract content before and after the default message paragraph
                before_default = summary_content[
                    learning_report_index + len("## Learning Report") : paragraph_start
                ]
                after_default = summary_content[paragraph_end:]

                # Combine to skip the default message
                after_learning_report = after_default
            else:
                # If default message not found, just get everything after the Learning Report header
                after_learning_report_index = summary_content.find(
                    "\n\n", learning_report_index
                )
                if after_learning_report_index == -1:
                    after_learning_report = ""
                else:
                    after_learning_report = summary_content[
                        after_learning_report_index:
                    ]

            # Create a new Learning Report section with the lesson questions
            learning_report = "\n\nDuring your adventure, you encountered the following educational questions:\n\n"
            for i, question in enumerate(lesson_questions, 1):
                learning_report += f"{i}. **Question**: {question['question']}\n"
                learning_report += f"   **Topic**: {question['topic']}"
                if question["subtopic"]:
                    learning_report += f" - {question['subtopic']}"
                learning_report += (
                    f"\n   **Correct Answer**: {question['correct_answer']}\n\n"
                )

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
    # Default log file path - using a relative path that works from the project root
    # This handles running the script from either the project root or the tests/simulations directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, "../.."))
    default_log_path = os.path.join(
        project_root, "logs/simulations/simulation_2025-03-11_23-36-15_8e1a3e7c.log"
    )

    log_file = default_log_path

    # Allow specifying a different log file via command line
    if len(sys.argv) > 1:
        log_file = sys.argv[1]

    # Make sure the log file exists
    if not os.path.exists(log_file):
        print(f"Error: Log file not found: {log_file}")
        sys.exit(1)

    asyncio.run(show_summary_from_log(log_file))
