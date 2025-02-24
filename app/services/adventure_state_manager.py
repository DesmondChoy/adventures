import re
import logging
from typing import Dict, Any
from app.models.story import (
    AdventureState,
    ChapterData,
    ChapterType,
    StoryChoice,
    StoryResponse,
    LessonResponse,
    ChapterContent,
)
from app.services.chapter_manager import ChapterManager

logger = logging.getLogger("story_app")


class StateValidationError(Exception):
    """Raised when state validation fails."""

    pass


class ElementConsistencyError(Exception):
    """Raised when element consistency validation fails."""

    pass


class AdventureStateManager:
    def __init__(self):
        self.state: AdventureState | None = None
        self.chapter_manager = ChapterManager()  # Instantiate ChapterManager

    def initialize_state(
        self, story_length: int, lesson_topic: str, story_category: str
    ) -> AdventureState:
        """Initializes and returns a new AdventureState."""
        logger.debug(
            f"Initializing AdventureState with story_length: {story_length}, lesson_topic: {lesson_topic}, story_category: {story_category}"
        )
        self.state = self.chapter_manager.initialize_adventure_state(
            story_length, lesson_topic, story_category
        )
        return self.state

    def get_current_state(self) -> AdventureState | None:
        """Returns the current AdventureState."""
        return self.state

    def validate_element_consistency(self, chapter_data: Dict[str, Any]) -> None:
        """Validates that story elements remain consistent throughout the adventure.

        Args:
            chapter_data: The chapter data to validate

        Raises:
            ElementConsistencyError: If element consistency validation fails
        """
        try:
            # Verify narrative elements are being used consistently
            content = chapter_data.get("content", "")
            for element_type, element in self.state.selected_narrative_elements.items():
                if element.lower() in content.lower():
                    logger.debug(f"Found narrative element {element_type}: {element}")

            # Check sensory details integration
            for detail_type, detail in self.state.selected_sensory_details.items():
                if detail.lower() in content.lower():
                    logger.debug(f"Found sensory detail {detail_type}: {detail}")

            # Verify theme and moral teaching alignment
            if self.state.selected_theme.lower() in content.lower():
                logger.debug(f"Theme found: {self.state.selected_theme}")
            if self.state.selected_moral_teaching.lower() in content.lower():
                logger.debug(
                    f"Moral teaching found: {self.state.selected_moral_teaching}"
                )

        except Exception as e:
            logger.error(f"Element consistency validation failed: {e}")
            raise ElementConsistencyError(f"Element consistency validation failed: {e}")

    def validate_plot_twist_progression(self, chapter_data: Dict[str, Any]) -> None:
        """Validates that the plot twist develops appropriately based on story phase.

        Args:
            chapter_data: The chapter data to validate

        Raises:
            StateValidationError: If plot twist progression validation fails
        """
        try:
            current_phase = self.state.current_storytelling_phase
            content = chapter_data.get("content", "")
            plot_twist = self.state.selected_plot_twist

            # Phase-specific validation
            if current_phase == "Exposition":
                # Should only have subtle hints
                if plot_twist.lower() in content.lower():
                    logger.warning("Plot twist too obvious in Exposition phase")
            elif current_phase == "Rising":
                # Should start connecting previous hints
                if not any(
                    hint in content.lower()
                    for hint in self.state.metadata.get("previous_hints", [])
                ):
                    logger.warning(
                        "Missing connection to previous hints in Rising phase"
                    )
            elif current_phase == "Climax":
                # Should have clear plot twist revelation
                if plot_twist.lower() not in content.lower():
                    logger.warning("Missing plot twist revelation in Climax phase")

            # Update hint tracking in metadata
            hints = self.state.metadata.get("previous_hints", [])
            hints.append(content)
            self.state.metadata["previous_hints"] = hints

        except Exception as e:
            logger.error(f"Plot twist progression validation failed: {e}")
            raise StateValidationError(f"Plot twist progression validation failed: {e}")

    def update_state_from_client(self, validated_state: dict) -> None:
        """Updates the current AdventureState based on validated client data.

        Args:
            validated_state: The validated state data from client

        Raises:
            ValueError: If state is not initialized
            StateValidationError: If state validation fails
            ElementConsistencyError: If element consistency validation fails
        """
        if self.state is None:
            raise ValueError("State not initialized.")

        # Store critical state properties that need to be preserved
        preserved_state = {
            "selected_narrative_elements": self.state.selected_narrative_elements,
            "selected_sensory_details": self.state.selected_sensory_details,
            "selected_theme": self.state.selected_theme,
            "selected_moral_teaching": self.state.selected_moral_teaching,
            "selected_plot_twist": self.state.selected_plot_twist,
            "metadata": self.state.metadata,
            "planned_chapter_types": self.state.planned_chapter_types,
            "story_length": self.state.story_length,
            "current_storytelling_phase": self.state.current_storytelling_phase,
        }

        try:
            if "chapters" in validated_state:
                logger.debug("Updating chapters from client state.")
                chapters = []
                for chapter_data in validated_state["chapters"]:
                    # Debug raw incoming data
                    logger.debug(f"Raw chapter data: {chapter_data}")
                    # Validate element consistency and plot twist progression
                    self.validate_element_consistency(chapter_data)
                    self.validate_plot_twist_progression(chapter_data)

                    chapter_type = ChapterType(chapter_data["chapter_type"])

                    response = None
                    if "response" in chapter_data and chapter_data["response"]:
                        if chapter_type == ChapterType.STORY:
                            response = StoryResponse(
                                chosen_path=chapter_data["response"]["chosen_path"],
                                choice_text=chapter_data["response"]["choice_text"],
                            )
                        else:  # ChapterType.LESSON
                            response = LessonResponse(
                                question=chapter_data["response"]["question"],
                                chosen_answer=chapter_data["response"]["chosen_answer"],
                                is_correct=chapter_data["response"]["is_correct"],
                            )

                    # Handle chapter content with proper choice preservation
                    content = chapter_data.get("content", "")
                    choices = []

                    # First try to get choices from chapter_content
                    if "chapter_content" in chapter_data:
                        logger.debug("Found chapter_content, checking for choices")
                        content = chapter_data["chapter_content"].get(
                            "content", content
                        )
                        if isinstance(chapter_data["chapter_content"], dict):
                            logger.debug(
                                f"Chapter content structure: {chapter_data['chapter_content'].keys()}"
                            )
                            if "choices" in chapter_data["chapter_content"]:
                                logger.debug(
                                    f"Found choices in chapter_content: {chapter_data['chapter_content']['choices']}"
                                )
                                for choice in chapter_data["chapter_content"][
                                    "choices"
                                ]:
                                    logger.debug(f"Processing choice: {choice}")
                                    choices.append(
                                        StoryChoice(
                                            text=choice["text"],
                                            next_chapter=choice.get("next_chapter")
                                            or choice.get("id", ""),
                                        )
                                    )
                                logger.debug(
                                    f"Parsed {len(choices)} choices from chapter_content"
                                )

                    # If no choices found in chapter_content, try getting from the root level
                    if not choices and "choices" in chapter_data:
                        logger.debug(
                            f"Found choices at root level: {chapter_data['choices']}"
                        )
                        for choice in chapter_data["choices"]:
                            logger.debug(f"Processing root choice: {choice}")
                            choices.append(
                                StoryChoice(
                                    text=choice["text"],
                                    next_chapter=choice.get("next_chapter")
                                    or choice.get("id", ""),
                                )
                            )
                        logger.debug(f"Parsed {len(choices)} choices from root level")

                    # For story chapters, ensure we have exactly 3 choices
                    if chapter_type == ChapterType.STORY:
                        # First try to parse from content if we don't have choices
                        if len(choices) == 0 and "chapter_content" in chapter_data:
                            content_str = chapter_data["chapter_content"].get(
                                "content", content
                            )
                            choices_match = re.search(
                                r"<CHOICES>\s*(.*?)\s*</CHOICES>",
                                content_str,
                                re.DOTALL | re.IGNORECASE,
                            )
                            if choices_match:
                                choices_text = choices_match.group(1).strip()
                                choice_matches = re.finditer(
                                    r"Choice\s*([ABC])\s*:\s*([^\n]+)",
                                    choices_text,
                                    re.IGNORECASE | re.MULTILINE,
                                )
                                choices = []
                                for i, match in enumerate(choice_matches):
                                    choices.append(
                                        StoryChoice(
                                            text=match.group(2).strip(),
                                            next_chapter=f"chapter_{chapter_data['chapter_number']}_{i}",
                                        )
                                    )

                        # If we still don't have exactly 3 choices, generate defaults
                        if len(choices) != 3:
                            logger.warning(
                                f"Story chapter {chapter_data['chapter_number']} has {len(choices)} choices, generating defaults"
                            )
                            # Keep any existing choices
                            existing_choices = choices[:3]
                            # Generate defaults for remaining slots
                            for i in range(len(existing_choices), 3):
                                existing_choices.append(
                                    StoryChoice(
                                        text=f"Continue with path {i + 1}",
                                        next_chapter=f"chapter_{chapter_data['chapter_number']}_{i}",
                                    )
                                )
                            choices = existing_choices

                    logger.debug(
                        f"Final choices before creating ChapterContent: {choices}"
                    )
                    chapter_content = ChapterContent(content=content, choices=choices)
                    logger.debug(
                        f"Created ChapterContent with {len(chapter_content.choices)} choices"
                    )

                    # Create new chapter data
                    new_chapter = ChapterData(
                        chapter_number=len(chapters) + 1,
                        content=chapter_data["content"],
                        chapter_type=chapter_type,
                        response=response,
                        chapter_content=chapter_content,
                        question=chapter_data.get("question"),
                    )
                    logger.debug(f"Created new chapter with type: {chapter_type}")
                    logger.debug(
                        f"Chapter content has {len(chapter_content.choices)} choices"
                    )
                    logger.debug(
                        f"Chapter choices: {[choice.text for choice in chapter_content.choices]}"
                    )

                    chapters.append(new_chapter)
                self.state.chapters = chapters

            if "current_chapter_id" in validated_state:
                logger.debug(
                    f"Updating current_chapter_id to: {validated_state['current_chapter_id']}"
                )
                self.state.current_chapter_id = validated_state["current_chapter_id"]

            # Restore preserved state properties
            for key, value in preserved_state.items():
                setattr(self.state, key, value)

            logger.debug("Preserved critical state properties during update")
        except Exception as e:
            logger.error(f"Error updating state: {e}")
            # Restore preserved state to maintain consistency
            for key, value in preserved_state.items():
                setattr(self.state, key, value)
            raise StateValidationError(f"Failed to update state: {e}")

    def append_new_chapter(self, chapter_data: ChapterData) -> None:
        """Appends a new chapter to the AdventureState."""
        if self.state is None:
            raise ValueError("State not initialized.")
        logger.debug(f"Appending new chapter: {chapter_data.chapter_number}")
        self.state.chapters.append(chapter_data)
