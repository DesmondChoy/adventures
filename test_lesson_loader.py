"""
Test script for the LessonLoader class.

This script tests the functionality of the LessonLoader class to ensure it can:
1. Load lessons from both the old CSV file and the new directory structure
2. Filter lessons by topic and difficulty
3. Handle various file encodings and formats
4. Standardize difficulty levels
"""

import pandas as pd
from app.data.lesson_loader import LessonLoader


def main():
    """Test the LessonLoader class functionality."""
    # Create a LessonLoader instance
    loader = LessonLoader()

    # Load all lessons
    df = loader.load_all_lessons()

    # Print basic information about the loaded data
    print(f"Loaded {len(df)} lessons from {len(df['topic'].unique())} topics")
    print(f"Difficulties: {df['difficulty'].unique()}")

    # Test filtering by topic
    topic = "Human Body"
    topic_df = loader.get_lessons_by_topic(topic)
    print(f"{topic} lessons: {len(topic_df)}")

    # Test filtering by difficulty
    difficulty = "Very Challenging"
    difficulty_df = loader.get_lessons_by_difficulty(difficulty)
    print(f"{difficulty} lessons: {len(difficulty_df)}")

    # Test filtering by both topic and difficulty
    combined_df = loader.get_lessons_by_topic_and_difficulty(topic, difficulty)
    print(f"{topic} {difficulty} lessons: {len(combined_df)}")


if __name__ == "__main__":
    main()
