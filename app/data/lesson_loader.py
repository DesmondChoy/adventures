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
    """Loads and manages lesson data from multiple CSV files."""

    def __init__(self):
        self._cache = None
        self._lessons_dir = "app/data/lessons"
        self._old_csv_path = "app/data/lessons.csv"

    def load_all_lessons(self) -> pd.DataFrame:
        """Load all lesson data from CSV files in the lessons directory.

        If the new CSV files can't be parsed correctly, falls back to the old CSV file.

        Returns:
            DataFrame containing all lesson data from all CSV files
        """
        if self._cache is not None:
            return self._cache

        # First try to load from the old CSV file
        try:
            logger.debug(f"Trying to load from old CSV file: {self._old_csv_path}")
            old_df = pd.read_csv(self._old_csv_path)
            if "topic" in old_df.columns and len(old_df) > 0:
                logger.info(
                    f"Successfully loaded {len(old_df)} lessons from old CSV file"
                )

                # Add difficulty column if it doesn't exist
                if (
                    "difficulty" not in old_df.columns
                    and "difficulty_level" in old_df.columns
                ):
                    old_df = old_df.rename(columns={"difficulty_level": "difficulty"})
                    logger.debug("Renamed 'difficulty_level' to 'difficulty'")

                # If difficulty column still doesn't exist, add it with default value
                if "difficulty" not in old_df.columns:
                    old_df["difficulty"] = "Reasonably Challenging"
                    logger.debug("Added 'difficulty' column with default value")

                # Convert numeric difficulty values to strings
                if "difficulty" in old_df.columns:
                    # Check if any values are numeric
                    numeric_values = (
                        old_df["difficulty"]
                        .apply(lambda x: isinstance(x, (int, float)))
                        .any()
                    )
                    if numeric_values:
                        # Convert numeric values to string
                        old_df["difficulty"] = old_df["difficulty"].apply(
                            lambda x: "Very Challenging"
                            if (isinstance(x, (int, float)) and x > 1)
                            else "Reasonably Challenging"
                            if isinstance(x, (int, float))
                            else x
                        )
                        logger.debug("Converted numeric difficulty values to strings")

                self._cache = old_df
                return old_df
        except Exception as e:
            logger.debug(f"Could not load from old CSV file: {str(e)}")

        # Get all CSV files in the lessons directory
        csv_files = glob.glob(os.path.join(self._lessons_dir, "*.csv"))

        if not csv_files:
            logger.error(f"No CSV files found in {self._lessons_dir}")
            raise ValueError(f"No lesson data files found in {self._lessons_dir}")

        # Load and combine all CSV files
        dfs = []
        for file_path in csv_files:
            try:
                # Try to extract topic from filename
                filename = os.path.basename(file_path)
                topic_from_filename = filename.split(".")[0].replace("_", " ").title()
                if "-" in topic_from_filename:
                    topic_from_filename = topic_from_filename.split("-")[0].strip()

                logger.debug(f"Extracted topic from filename: {topic_from_filename}")

                # Try to read the file with different encodings
                for encoding in ["utf-8", "latin1", "cp1252"]:
                    try:
                        # Read the file as text
                        with open(file_path, "r", encoding=encoding) as f:
                            content = f.read()

                        # Check if this is a CSV file with proper structure
                        if (
                            "topic" in content
                            and "subtopic" in content
                            and "difficulty" in content
                        ):
                            # Try to parse as regular CSV
                            df = pd.read_csv(file_path, encoding=encoding)
                            if "topic" in df.columns:
                                logger.debug(
                                    f"Successfully parsed {file_path} as regular CSV"
                                )
                                break

                        # If we get here, we need to parse manually
                        logger.debug(f"Parsing {file_path} manually")

                        # Read the file line by line
                        with open(file_path, "r", encoding=encoding) as f:
                            lines = f.readlines()

                        # Parse the data
                        data = []
                        for line in lines[1:]:  # Skip header
                            line = line.strip()
                            if not line:
                                continue

                            # Try to extract data using CSV reader
                            try:
                                row = next(csv.reader([line]))
                                if len(row) >= 8:  # We expect at least 8 columns
                                    data.append(
                                        {
                                            "topic": topic_from_filename,
                                            "subtopic": row[1] if len(row) > 1 else "",
                                            "difficulty": row[2]
                                            if len(row) > 2
                                            else "Reasonably Challenging",
                                            "question": row[3] if len(row) > 3 else "",
                                            "correct_answer": row[4]
                                            if len(row) > 4
                                            else "",
                                            "wrong_answer1": row[5]
                                            if len(row) > 5
                                            else "",
                                            "wrong_answer2": row[6]
                                            if len(row) > 6
                                            else "",
                                            "explanation": row[7]
                                            if len(row) > 7
                                            else "",
                                        }
                                    )
                            except Exception as csv_error:
                                logger.debug(
                                    f"Error parsing line with CSV reader: {str(csv_error)}"
                                )

                                # Try a simpler approach - split by commas
                                parts = []
                                current_part = ""
                                in_quotes = False

                                for char in line:
                                    if char == '"':
                                        in_quotes = not in_quotes
                                    elif char == "," and not in_quotes:
                                        parts.append(current_part.strip())
                                        current_part = ""
                                    else:
                                        current_part += char

                                # Add the last part
                                if current_part:
                                    parts.append(current_part.strip())

                                # If we have enough parts, add to data
                                if len(parts) >= 7:
                                    data.append(
                                        {
                                            "topic": topic_from_filename,
                                            "subtopic": parts[1]
                                            if len(parts) > 1
                                            else "",
                                            "difficulty": parts[2]
                                            if len(parts) > 2
                                            else "Reasonably Challenging",
                                            "question": parts[3]
                                            if len(parts) > 3
                                            else "",
                                            "correct_answer": parts[4]
                                            if len(parts) > 4
                                            else "",
                                            "wrong_answer1": parts[5]
                                            if len(parts) > 5
                                            else "",
                                            "wrong_answer2": parts[6]
                                            if len(parts) > 6
                                            else "",
                                            "explanation": parts[7]
                                            if len(parts) > 7
                                            else "",
                                        }
                                    )

                        # Create DataFrame from parsed data
                        if data:
                            df = pd.DataFrame(data)
                            logger.debug(
                                f"Successfully parsed {file_path} manually: {len(df)} rows"
                            )
                            break
                        else:
                            logger.warning(f"No data extracted from {file_path}")

                    except Exception as encoding_error:
                        logger.debug(
                            f"Error with encoding {encoding} for {file_path}: {str(encoding_error)}"
                        )
                        if encoding == "cp1252":  # Last encoding to try
                            raise

                # Add file name as source for debugging
                df["source_file"] = os.path.basename(file_path)
                dfs.append(df)
                logger.debug(f"Loaded lesson data from {file_path}: {len(df)} rows")
            except Exception as e:
                logger.error(f"Error loading {file_path}: {str(e)}")
                # Continue with other files even if one fails

        # If we couldn't load any data from the new CSV files, try the old CSV file again
        if not dfs:
            logger.warning(
                "Failed to load any lesson data from new CSV files, trying old CSV file"
            )
            try:
                old_df = pd.read_csv(self._old_csv_path)
                if "topic" in old_df.columns and len(old_df) > 0:
                    logger.info(
                        f"Successfully loaded {len(old_df)} lessons from old CSV file"
                    )

                    # Add difficulty column if it doesn't exist
                    if (
                        "difficulty" not in old_df.columns
                        and "difficulty_level" in old_df.columns
                    ):
                        old_df = old_df.rename(
                            columns={"difficulty_level": "difficulty"}
                        )
                        logger.debug("Renamed 'difficulty_level' to 'difficulty'")

                    # If difficulty column still doesn't exist, add it with default value
                    if "difficulty" not in old_df.columns:
                        old_df["difficulty"] = "Reasonably Challenging"
                        logger.debug("Added 'difficulty' column with default value")

                    # Convert numeric difficulty values to strings
                    if "difficulty" in old_df.columns:
                        # Check if any values are numeric
                        numeric_values = (
                            old_df["difficulty"]
                            .apply(lambda x: isinstance(x, (int, float)))
                            .any()
                        )
                        if numeric_values:
                            # Convert numeric values to string
                            old_df["difficulty"] = old_df["difficulty"].apply(
                                lambda x: "Very Challenging"
                                if (isinstance(x, (int, float)) and x > 1)
                                else "Reasonably Challenging"
                                if isinstance(x, (int, float))
                                else x
                            )
                            logger.debug(
                                "Converted numeric difficulty values to strings"
                            )

                    self._cache = old_df
                    return old_df
                else:
                    logger.error(
                        "Old CSV file does not have expected columns or is empty"
                    )
                    raise ValueError("Failed to load any lesson data")
            except Exception as e:
                logger.error(f"Error loading old CSV file: {str(e)}")
                raise ValueError("Failed to load any lesson data")

        # Combine all DataFrames
        combined_df = pd.concat(dfs, ignore_index=True)

        # Standardize column names and values
        if (
            "difficulty_level" in combined_df.columns
            and "difficulty" not in combined_df.columns
        ):
            combined_df = combined_df.rename(columns={"difficulty_level": "difficulty"})

        # Convert numeric difficulty to string if needed
        if "difficulty" in combined_df.columns:
            # Check if any values are numeric
            numeric_values = (
                combined_df["difficulty"]
                .apply(lambda x: isinstance(x, (int, float)))
                .any()
            )
            if numeric_values:
                # Convert numeric values to string
                combined_df["difficulty"] = combined_df["difficulty"].apply(
                    lambda x: "Very Challenging"
                    if (isinstance(x, (int, float)) and x > 1)
                    else "Reasonably Challenging"
                    if isinstance(x, (int, float))
                    else x
                )

        # Cache the result
        self._cache = combined_df

        logger.info(
            f"Loaded all lesson data: {len(combined_df)} total rows from {len(dfs)} files"
        )

        return combined_df

    def get_lessons_by_topic(self, topic: str) -> pd.DataFrame:
        """Get all lessons for a specific topic.

        Args:
            topic: The topic to filter by

        Returns:
            DataFrame containing lessons for the specified topic
        """
        df = self.load_all_lessons()
        filtered_df = df[df["topic"] == topic]
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
        filtered_df = df[df["difficulty"] == difficulty]
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
        df = self.load_all_lessons()
        filtered_df = df[(df["topic"] == topic) & (df["difficulty"] == difficulty)]
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
