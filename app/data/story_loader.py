from typing import Dict, Any, List, Optional
import os
import yaml
import logging
from pathlib import Path

logger = logging.getLogger("story_app")


class StoryLoader:
    """Service for loading and managing story data from individual YAML files."""

    def __init__(self, stories_dir: str = "app/data/stories"):
        """Initialize the story loader with the directory containing story files.

        Args:
            stories_dir: Path to the directory containing story YAML files
        """
        self.stories_dir = stories_dir
        self._story_data = None  # Cache for loaded story data

    def load_all_stories(self, refresh: bool = False) -> Dict[str, Any]:
        """Load all story data from individual YAML files.

        Args:
            refresh: If True, reload data from disk even if cached

        Returns:
            Dict containing all story categories and their data

        Raises:
            ValueError: If the stories directory doesn't exist or if loading fails
        """
        # Return cached data if available and refresh not requested
        if self._story_data is not None and not refresh:
            return self._story_data

        # Ensure the stories directory exists
        if not os.path.isdir(self.stories_dir):
            error_msg = f"Stories directory not found: {self.stories_dir}"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Initialize the combined data structure
        combined_data = {"story_categories": {}}

        try:
            # Get all YAML files in the directory
            story_files = [
                f for f in os.listdir(self.stories_dir) if f.endswith((".yaml", ".yml"))
            ]

            if not story_files:
                logger.warning(f"No story files found in {self.stories_dir}")

            # Load each file and add to the combined data
            for filename in story_files:
                story_id = Path(filename).stem  # Get filename without extension
                file_path = os.path.join(self.stories_dir, filename)

                logger.debug(f"Loading story from {file_path}")

                with open(file_path, "r", encoding="utf-8") as f:
                    story_data = yaml.safe_load(f)

                # Add to the combined data
                combined_data["story_categories"][story_id] = story_data

            # Cache the loaded data
            self._story_data = combined_data

            logger.info(
                f"Successfully loaded {len(combined_data['story_categories'])} stories",
                extra={"story_ids": list(combined_data["story_categories"].keys())},
            )

            return combined_data

        except Exception as e:
            error_msg = f"Failed to load story data: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ValueError(error_msg)

    def get_story_category(self, category_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific story category by ID.

        Args:
            category_id: The ID of the story category to retrieve

        Returns:
            The story category data or None if not found
        """
        all_stories = self.load_all_stories()
        return all_stories["story_categories"].get(category_id)

    def get_available_categories(self) -> List[str]:
        """Get a list of all available story category IDs.

        Returns:
            List of story category IDs
        """
        all_stories = self.load_all_stories()
        return list(all_stories["story_categories"].keys())
