#!/usr/bin/env python
"""
Code Complexity Analyzer - A utility to identify files that need refactoring

This script analyzes files in a repository to find which ones have the most lines,
helping identify potential candidates for refactoring due to excessive code size.
It can count total lines, non-blank lines, and code lines (excluding comments).

Usage:
    python tools/code_complexity_analyzer.py [options]

Options:
    -p, --path PATH         Path to the repository (default: current directory)
    -e, --extensions EXT    File extensions to include (e.g., py js html)
                            If not specified, includes common code file types
    -s, --sort TYPE         Sort by: total, non-blank, or code lines (default: total)
    -n, --number N          Number of files to display (default: 20)

Examples:
    # Basic usage (top 20 files by total lines)
    python tools/code_complexity_analyzer.py

    # Sort by code lines (excluding comments)
    python tools/code_complexity_analyzer.py -s code

    # Only analyze Python files
    python tools/code_complexity_analyzer.py -e py

    # Analyze HTML and CSS files, sorted by non-blank lines, showing top 10
    python tools/code_complexity_analyzer.py -e html css -s non-blank -n 10
"""

import os
import sys
import re
import argparse


def count_lines(repo_path, extensions=None):
    results = []

    # Default file extensions to include if none specified
    default_extensions = {
        ".py",
        ".js",
        ".html",
        ".css",
        ".md",
        ".yaml",
        ".yml",
        ".csv",
        ".txt",
        ".json",
    }

    # Use provided extensions or default ones
    valid_extensions = set(extensions) if extensions else default_extensions

    # Directories to exclude
    exclude_dirs = {".git", "__pycache__", "venv", "env", ".venv", "node_modules"}

    # Comment patterns by file extension
    comment_patterns = {
        ".py": [r"^\s*#.*$", r'^\s*""".*?"""$', r"^\s*'''.*?'''$"],
        ".js": [r"^\s*//.*$", r"^\s*/\*.*?\*/\s*$"],
        ".html": [r"^\s*<!--.*?-->\s*$"],
        ".css": [r"^\s*/\*.*?\*/\s*$"],
    }

    for root, dirs, files in os.walk(repo_path):
        # Skip excluded directories
        dirs[:] = [d for d in dirs if d not in exclude_dirs]

        for file in files:
            file_path = os.path.join(root, file)
            file_ext = os.path.splitext(file)[1].lower()

            # Only process files with valid extensions
            if file_ext in valid_extensions:
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.readlines()
                        total_lines = len(content)

                        # Count non-blank lines
                        non_blank_lines = sum(1 for line in content if line.strip())

                        # Count code lines (non-blank, non-comment)
                        code_lines = non_blank_lines

                        # Apply comment filtering for supported file types
                        if file_ext in comment_patterns:
                            for pattern in comment_patterns[file_ext]:
                                code_lines -= sum(
                                    1 for line in content if re.match(pattern, line)
                                )

                        results.append(
                            (file_path, total_lines, non_blank_lines, code_lines)
                        )
                except (UnicodeDecodeError, IsADirectoryError, PermissionError):
                    # Skip binary files and other unreadable files
                    pass

    # Sort by total line count in descending order
    results.sort(key=lambda x: x[1], reverse=True)
    return results


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Analyze code complexity to identify files that may need refactoring"
    )
    parser.add_argument(
        "-p",
        "--path",
        default=".",
        help="Path to the repository (default: current directory)",
    )
    parser.add_argument(
        "-e",
        "--extensions",
        nargs="+",
        help="File extensions to include (e.g., .py .js .html)",
    )
    parser.add_argument(
        "-s",
        "--sort",
        choices=["total", "non-blank", "code"],
        default="total",
        help="Sort by: total, non-blank, or code lines (default: total)",
    )
    parser.add_argument(
        "-n",
        "--number",
        type=int,
        default=20,
        help="Number of files to display (default: 20)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()

    # Process extensions if provided
    extensions = (
        [ext if ext.startswith(".") else f".{ext}" for ext in args.extensions]
        if args.extensions
        else None
    )

    # Get line counts
    results = count_lines(args.path, extensions)

    # Sort based on user preference
    if args.sort == "non-blank":
        results.sort(key=lambda x: x[2], reverse=True)
        sort_label = "non-blank line count"
        sort_index = 2
    elif args.sort == "code":
        results.sort(key=lambda x: x[3], reverse=True)
        sort_label = "code line count"
        sort_index = 3
    else:  # default to total
        results.sort(key=lambda x: x[1], reverse=True)
        sort_label = "total line count"
        sort_index = 1

    # Print top N files
    print(f"\nTop {args.number} files by {sort_label}:")
    print("-" * 100)
    print(f"{'Rank':<6}{'Total':<10}{'Non-Blank':<12}{'Code':<10}{'File Path'}")
    print("-" * 100)

    for i, (file_path, total_lines, non_blank_lines, code_lines) in enumerate(
        results[: args.number], 1
    ):
        print(
            f"{i:<6}{total_lines:<10}{non_blank_lines:<12}{code_lines:<10}{file_path}"
        )

    # Print summary
    total_files = len(results)
    total_all_lines = sum(total for _, total, _, _ in results)
    total_non_blank = sum(non_blank for _, _, non_blank, _ in results)
    total_code = sum(code for _, _, _, code in results)

    print("\nSummary:")
    print(f"Total files analyzed: {total_files}")
    print(f"Total lines: {total_all_lines}")
    print(f"Total non-blank lines: {total_non_blank}")
    print(f"Total code lines: {total_code}")

    # If we have results, show the file with the most lines according to sort preference
    if results:
        top_file = results[0]
        file_path, total_lines, non_blank_lines, code_lines = top_file

        print(f"\nFile with the most {args.sort} lines: {file_path}")
        print(f"  Total lines: {total_lines}")
        print(f"  Non-blank lines: {non_blank_lines}")
        print(f"  Code lines: {code_lines}")

        # Show extensions analyzed if custom extensions were provided
        if extensions:
            print(f"\nExtensions analyzed: {', '.join(extensions)}")
