"""
Lesson loader for Learning Odyssey.

This module provides functionality for loading lesson data from multiple CSV files
in the lessons directory. It combines the data into a single DataFrame and provides
methods for accessing lessons by topic and difficulty.
"""

import os
import pandas as pd
import logging
import glob
import csv
from typing import Optional, List

logger = logging.getLogger("story_app")


class LessonLoader:
    """Loads and manages lesson data from multiple CSV files in the lessons directory."""

    def __init__(self):
        self._cache = None
        self._lessons_dir = "app/data/lessons"

    def load_all_lessons(self) -> pd.DataFrame:
        """Load all lesson data from CSV files in the lessons directory.

        Returns:
            DataFrame containing all lesson data from all CSV files
        """
        if self._cache is not None:
            return self._cache

        # Get all CSV files in the lessons directory
        csv_files = glob.glob(os.path.join(self._lessons_dir, "*.csv"))

        if not csv_files:
            logger.error(f"No CSV files found in {self._lessons_dir}")
            raise ValueError(f"No lesson data files found in {self._lessons_dir}")

        # Load and combine all CSV files
        dfs = []

        for file_path in csv_files:
            try:
                # Extract topic from filename for logging
                filename = os.path.basename(file_path)
                topic_from_filename = filename.split(".")[0].replace("_", " ").title()
                logger.debug(f"Loading lessons from {topic_from_filename}")

                # Try different encodings
                for encoding in ["utf-8", "latin1", "cp1252"]:
                    try:
                        # Use pandas to read the CSV file with proper quoting
                        df = pd.read_csv(
                            file_path,
                            encoding=encoding,
                            quotechar='"',
                            doublequote=True,
                        )

                        # Add source file column
                        df["source_file"] = filename

                        # Log the topics found in this file
                        if "topic" in df.columns:
                            unique_topics = df["topic"].unique()
                            logger.debug(f"Topics in {filename}: {unique_topics}")

                            # Log the count of lessons for each topic
                            for topic in unique_topics:
                                topic_count = len(df[df["topic"] == topic])
                                logger.debug(
                                    f"Found {topic_count} lessons for topic '{topic}' in {filename}"
                                )

                        dfs.append(df)
                        logger.debug(
                            f"Successfully parsed {file_path} with encoding {encoding}"
                        )
                        break

                    except Exception as e:
                        logger.debug(
                            f"Error parsing {file_path} with encoding {encoding}: {str(e)}"
                        )
                        if encoding == "cp1252":  # Last encoding to try
                            logger.error(
                                f"Failed to parse {file_path} with any encoding"
                            )
                            raise

            except Exception as e:
                logger.error(f"Error loading {file_path}: {str(e)}")
                # Continue with other files even if one fails

        # If we couldn't load any data, raise an error
        if not dfs:
            logger.error(
                "Failed to load any lesson data from CSV files in the lessons directory"
            )
            raise ValueError(
                "Failed to load any lesson data from CSV files in the lessons directory"
            )

        # Combine all DataFrames
        combined_df = pd.concat(dfs, ignore_index=True)

        # Log the total number of lessons for each topic
        if "topic" in combined_df.columns:
            unique_topics = combined_df["topic"].unique()
            logger.debug(f"All topics: {unique_topics}")

            for topic in unique_topics:
                topic_count = len(combined_df[combined_df["topic"] == topic])
                logger.debug(f"Total lessons for topic '{topic}': {topic_count}")

        # Standardize difficulty values
        if "difficulty" in combined_df.columns:
            # Convert numeric difficulty to string if needed
            numeric_values = (
                combined_df["difficulty"]
                .apply(lambda x: isinstance(x, (int, float)))
                .any()
            )
            if numeric_values:
                combined_df["difficulty"] = combined_df["difficulty"].apply(
                    lambda x: "Very Challenging"
                    if (isinstance(x, (int, float)) and x > 1)
                    else "Reasonably Challenging"
                    if isinstance(x, (int, float))
                    else x
                )

        # Cache the result
        self._cache = combined_df

        logger.info(f"Loaded all lesson data: {len(combined_df)} total rows")

        return combined_df

    def get_lessons_by_topic(self, topic: str) -> pd.DataFrame:
        """Get all lessons for a specific topic.

        Args:
            topic: The topic to filter by

        Returns:
            DataFrame containing lessons for the specified topic
        """
        df = self.load_all_lessons()

        # Log all unique topics for debugging
        unique_topics = df["topic"].unique()
        logger.debug(f"Available topics: {unique_topics}")

        # Case-insensitive matching
        filtered_df = df[df["topic"].str.lower() == topic.lower()]

        # If no matches, try with stripped whitespace
        if len(filtered_df) == 0:
            logger.debug(
                f"No exact matches for '{topic}', trying with stripped whitespace"
            )
            filtered_df = df[
                df["topic"].str.lower().str.strip() == topic.lower().strip()
            ]

        # If still no matches, try with partial matching
        if len(filtered_df) == 0:
            logger.debug(
                f"No matches with stripped whitespace, trying partial matching"
            )
            filtered_df = df[df["topic"].str.lower().str.contains(topic.lower())]

        logger.debug(f"Found {len(filtered_df)} lessons for topic '{topic}'")
        return filtered_df

    def get_lessons_by_difficulty(self, difficulty: str) -> pd.DataFrame:
        """Get all lessons with a specific difficulty.

        Args:
            difficulty: The difficulty level to filter by

        Returns:
            DataFrame containing lessons with the specified difficulty
        """
        df = self.load_all_lessons()

        # Log all unique difficulties for debugging
        unique_difficulties = df["difficulty"].unique()
        logger.debug(f"Available difficulties: {unique_difficulties}")

        # Case-insensitive matching
        filtered_df = df[df["difficulty"].str.lower() == difficulty.lower()]

        # If no matches, try with stripped whitespace
        if len(filtered_df) == 0:
            logger.debug(
                f"No exact matches for difficulty '{difficulty}', trying with stripped whitespace"
            )
            filtered_df = df[
                df["difficulty"].str.lower().str.strip() == difficulty.lower().strip()
            ]

        logger.debug(f"Found {len(filtered_df)} lessons with difficulty '{difficulty}'")
        return filtered_df

    def get_lessons_by_topic_and_difficulty(
        self, topic: str, difficulty: str
    ) -> pd.DataFrame:
        """Get lessons filtered by both topic and difficulty.

        Args:
            topic: The topic to filter by
            difficulty: The difficulty level to filter by

        Returns:
            DataFrame containing lessons matching both topic and difficulty
        """
        # First get lessons by topic using the robust topic matching
        topic_df = self.get_lessons_by_topic(topic)

        # Then filter by difficulty (case-insensitive)
        filtered_df = topic_df[topic_df["difficulty"].str.lower() == difficulty.lower()]

        logger.debug(
            f"Found {len(filtered_df)} lessons for topic '{topic}' with difficulty '{difficulty}'"
        )
        return filtered_df

    def get_available_topics(self) -> List[str]:
        """Get a list of all available topics.

        Returns:
            List of unique topic names
        """
        df = self.load_all_lessons()
        topics = df["topic"].unique().tolist()
        logger.debug(f"Available topics: {topics}")
        return topics

    def get_available_difficulties(self) -> List[str]:
        """Get a list of all available difficulty levels.

        Returns:
            List of unique difficulty levels
        """
        df = self.load_all_lessons()
        difficulties = df["difficulty"].unique().tolist()
        logger.debug(f"Available difficulties: {difficulties}")
        return difficulties

    def clear_cache(self) -> None:
        """Clear the cached lesson data."""
        self._cache = None
        logger.debug("Lesson data cache cleared")
