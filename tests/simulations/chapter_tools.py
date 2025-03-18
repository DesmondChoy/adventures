"""
Chapter Tools - Command-line interface for chapter generation and analysis.

This script provides a unified command-line interface for generating and analyzing
chapters for the Learning Odyssey app.

Usage:
    python tests/simulations/chapter_tools.py generate [--category CATEGORY] [--topic TOPIC]
    python tests/simulations/chapter_tools.py analyze [--file FILE] [--latest]
    python tests/simulations/chapter_tools.py batch [--count COUNT]
"""

import asyncio
import argparse
import os
import sys
from datetime import datetime

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

# Import the chapter generator and analysis tools
from tests.simulations.chapter_generator import generate_all_chapters
from tests.simulations.analyze_chapter_state import (
    get_latest_state_file,
    load_state_file,
    print_chapter_summary,
    print_chapter_summaries,
    print_simulation_metadata,
    print_educational_stats,
)
from tests.simulations.batch_generate_chapters import run_batch


async def run_generate(args):
    """Run the chapter generator."""
    print("Starting chapter generator...")
    state = await generate_all_chapters(args.category, args.topic)

    if state is None:
        print("Failed to generate chapters.")
        return 1

    print(f"\nSuccessfully generated {len(state.chapters)} chapters.")
    print(f"State file saved to: {state.save_to_file()}")
    return 0


def run_analyze(args):
    """Run the chapter analyzer."""
    # Determine which file to use
    file_path = None
    if args.file:
        file_path = args.file
    elif args.latest:
        try:
            file_path = get_latest_state_file()
            print(f"Using latest state file: {file_path}")
        except FileNotFoundError as e:
            print(f"Error: {e}")
            return 1
    else:
        try:
            file_path = get_latest_state_file()
            print(f"No file specified, using latest state file: {file_path}")
        except FileNotFoundError:
            print("Error: No state files found. Please specify a file with --file.")
            return 1

    # Load the state file
    try:
        state_data = load_state_file(file_path)
        print(f"Loaded state file: {file_path}")
    except Exception as e:
        print(f"Error loading state file: {e}")
        return 1

    # Determine which information to print
    if args.all or not any([args.summary, args.summaries, args.metadata, args.stats]):
        print_chapter_summary(state_data)
        print_chapter_summaries(state_data)
        print_simulation_metadata(state_data)
        print_educational_stats(state_data)
    else:
        if args.summary:
            print_chapter_summary(state_data)
        if args.summaries:
            print_chapter_summaries(state_data)
        if args.metadata:
            print_simulation_metadata(state_data)
        if args.stats:
            print_educational_stats(state_data)

    return 0


async def run_batch_command(args):
    """Run the batch generator."""
    await run_batch(args.count)
    return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Chapter Tools - Command-line interface for chapter generation and analysis"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Generate command
    generate_parser = subparsers.add_parser("generate", help="Generate chapters")
    generate_parser.add_argument("--category", type=str, help="Specify story category")
    generate_parser.add_argument("--topic", type=str, help="Specify lesson topic")

    # Analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze chapter state file")
    analyze_parser.add_argument("--file", type=str, help="Path to state file")
    analyze_parser.add_argument(
        "--latest", action="store_true", help="Use the latest state file"
    )
    analyze_parser.add_argument(
        "--summary", action="store_true", help="Print chapter summary"
    )
    analyze_parser.add_argument(
        "--summaries", action="store_true", help="Print chapter summaries"
    )
    analyze_parser.add_argument(
        "--metadata", action="store_true", help="Print simulation metadata"
    )
    analyze_parser.add_argument(
        "--stats", action="store_true", help="Print educational statistics"
    )
    analyze_parser.add_argument(
        "--all", action="store_true", help="Print all information"
    )

    # Batch command
    batch_parser = subparsers.add_parser("batch", help="Batch generate chapters")
    batch_parser.add_argument(
        "--count", type=int, default=5, help="Number of chapter sets to generate"
    )

    args = parser.parse_args()

    if args.command == "generate":
        return asyncio.run(run_generate(args))
    elif args.command == "analyze":
        return run_analyze(args)
    elif args.command == "batch":
        return asyncio.run(run_batch_command(args))
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
