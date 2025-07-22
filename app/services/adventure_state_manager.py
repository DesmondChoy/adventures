import re
import logging
from typing import Dict, Any, Optional
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
from app.services.telemetry_service import get_telemetry_service

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
        self,
        story_length: int,
        lesson_topic: str,
        story_category: str,
        difficulty: str = None,
    ) -> AdventureState:
        """Initializes and returns a new AdventureState.

        Args:
            story_length: The number of chapters in the story
            lesson_topic: The topic of the lessons
            story_category: The selected story category
            difficulty: Optional difficulty level for lessons ("Reasonably Challenging" or "Very Challenging")

        Returns:
            The initialized AdventureState
        """
        # TODO: Implement difficulty toggle in UI to allow users to select difficulty level
        logger.debug(
            f"Initializing AdventureState with story_length: {story_length}, lesson_topic: {lesson_topic}, story_category: {story_category}, difficulty: {difficulty}"
        )
        self.state = self.chapter_manager.initialize_adventure_state(
            story_length, lesson_topic, story_category, difficulty
        )

        # Store difficulty in metadata if provided
        if difficulty:
            self.state.metadata["difficulty"] = difficulty
            logger.debug(f"Set difficulty level to: {difficulty}")

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
                client_chapters = validated_state["chapters"]
                new_chapters = []

                for client_chapter in client_chapters:
                    # Validate element consistency and plot twist progression
                    self.validate_element_consistency(client_chapter)
                    self.validate_plot_twist_progression(client_chapter)

                    chapter_number = client_chapter["chapter_number"]
                    # Find existing chapter in self.state.chapters
                    existing_chapter = next(
                        (
                            ch
                            for ch in self.state.chapters
                            if ch.chapter_number == chapter_number
                        ),
                        None,
                    )

                    if existing_chapter:
                        # Update existing chapter with client data, preserving response
                        logger.debug(f"Updating existing chapter {chapter_number}")
                        existing_chapter.content = client_chapter["content"]

                        # Update chapter_content
                        client_chapter_content = client_chapter.get(
                            "chapter_content", {}
                        )
                        choices = []

                        # Process choices from chapter_content
                        if isinstance(client_chapter_content, dict):
                            logger.debug(
                                f"Chapter content structure: {client_chapter_content.keys()}"
                            )
                            content = client_chapter_content.get(
                                "content", existing_chapter.chapter_content.content
                            )

                            # Try to get choices from chapter_content
                            if "choices" in client_chapter_content:
                                logger.debug(
                                    f"Found choices in chapter_content: {client_chapter_content['choices']}"
                                )
                                for choice in client_chapter_content["choices"]:
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

                            # For story chapters, ensure we have exactly 3 choices
                            if existing_chapter.chapter_type == ChapterType.STORY:
                                # If no choices found, try parsing from content
                                if len(choices) == 0:
                                    content_str = content
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
                                                    next_chapter=f"chapter_{chapter_number}_{i}",
                                                )
                                            )

                                # If still don't have exactly 3 choices, generate defaults
                                if len(choices) != 3:
                                    logger.warning(
                                        f"Story chapter {chapter_number} has {len(choices)} choices, generating defaults"
                                    )
                                    existing_choices = choices[:3]
                                    for i in range(len(existing_choices), 3):
                                        existing_choices.append(
                                            StoryChoice(
                                                text=f"Continue with path {i + 1}",
                                                next_chapter=f"chapter_{chapter_number}_{i}",
                                            )
                                        )
                                    choices = existing_choices

                            existing_chapter.chapter_content = ChapterContent(
                                content=content,
                                choices=choices,
                            )

                        if "question" in client_chapter:
                            existing_chapter.question = client_chapter["question"]

                        # Preserve existing response
                        logger.debug(
                            f"Preserving response for chapter {chapter_number}"
                        )
                        new_chapters.append(existing_chapter)
                    else:
                        # Create new chapter
                        logger.debug(f"Creating new chapter {chapter_number}")
                        chapter_type = self.state.planned_chapter_types[
                            chapter_number - 1
                        ]
                        choices = []

                        # Process chapter content for new chapter
                        client_chapter_content = client_chapter.get(
                            "chapter_content", {}
                        )
                        content = client_chapter_content.get(
                            "content", client_chapter.get("content", "")
                        )

                        if (
                            isinstance(client_chapter_content, dict)
                            and "choices" in client_chapter_content
                        ):
                            for choice in client_chapter_content["choices"]:
                                choices.append(
                                    StoryChoice(
                                        text=choice["text"],
                                        next_chapter=choice.get("next_chapter")
                                        or choice.get("id", ""),
                                    )
                                )

                        # For story chapters, ensure 3 choices
                        if chapter_type == ChapterType.STORY and len(choices) != 3:
                            existing_choices = choices[:3]
                            for i in range(len(existing_choices), 3):
                                existing_choices.append(
                                    StoryChoice(
                                        text=f"Continue with path {i + 1}",
                                        next_chapter=f"chapter_{chapter_number}_{i}",
                                    )
                                )
                            choices = existing_choices

                        # Handle response for new chapter
                        response = None
                        if "response" in client_chapter and client_chapter["response"]:
                            if chapter_type == ChapterType.STORY:
                                response = StoryResponse(
                                    chosen_path=client_chapter["response"][
                                        "chosen_path"
                                    ],
                                    choice_text=client_chapter["response"][
                                        "choice_text"
                                    ],
                                )
                            else:  # ChapterType.LESSON
                                # For new LESSON chapters, response should be None
                                # It will be set in process_choice()
                                response = None

                        new_chapter = ChapterData(
                            chapter_number=chapter_number,
                            content=client_chapter["content"],
                            chapter_type=chapter_type,
                            response=response,
                            chapter_content=ChapterContent(
                                content=content,
                                choices=choices,
                            ),
                            question=client_chapter.get("question"),
                        )
                        new_chapters.append(new_chapter)

                # Update self.state.chapters
                # Keep all existing chapters and add only truly new chapters
                client_chapter_numbers = [c["chapter_number"] for c in client_chapters]
                max_existing_chapter = max([ch.chapter_number for ch in self.state.chapters]) if self.state.chapters else 0
                
                # Only add chapters that are truly new (higher chapter number than existing)
                truly_new_chapters = [
                    ch for ch in new_chapters 
                    if ch.chapter_number > max_existing_chapter
                ]
                
                # Update existing chapters if they're included in client_chapters
                for existing_ch in self.state.chapters:
                    for new_ch in new_chapters:
                        if existing_ch.chapter_number == new_ch.chapter_number:
                            # Update the existing chapter with new data
                            existing_ch.content = new_ch.content
                            existing_ch.chapter_type = new_ch.chapter_type
                            existing_ch.response = new_ch.response
                            existing_ch.chapter_content = new_ch.chapter_content
                            existing_ch.question = new_ch.question
                
                updated_chapters = self.state.chapters + truly_new_chapters
                self.state.chapters = sorted(
                    updated_chapters, key=lambda x: x.chapter_number
                )

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

    def update_agency_references(self, chapter_data: ChapterData) -> None:
        """Track references to the agency element in chapters.

        Args:
            chapter_data: The chapter data to check for agency references
        """
        if self.state is None or "agency" not in self.state.metadata:
            return

        agency = self.state.metadata["agency"]
        content = chapter_data.content

        # Check if agency is referenced
        agency_name = agency.get("name", "")
        agency_type = agency.get("type", "")

        has_reference = (
            agency_name.lower() in content.lower()
            or agency_type.lower() in content.lower()
        )

        # Track references
        if "references" not in agency:
            agency["references"] = []

        agency["references"].append(
            {
                "chapter": chapter_data.chapter_number,
                "has_reference": has_reference,
                "chapter_type": chapter_data.chapter_type.value,
            }
        )

        # Log warning if no reference found
        if not has_reference:
            logger.warning(
                f"No reference to agency element ({agency_name}) found in chapter {chapter_data.chapter_number}"
            )
        else:
            logger.debug(
                f"Found reference to agency element ({agency_name}) in chapter {chapter_data.chapter_number}"
            )

    def update_character_visuals(
        self, state: AdventureState, updated_visuals: Dict[str, str]
    ) -> None:
        """Update character visuals dictionary in the AdventureState.

        Args:
            state: The current adventure state
            updated_visuals: Dictionary with updated character visual descriptions
        """
        # Get chapter number for logging
        chapter_number = len(state.chapters)

        if not updated_visuals:
            logger.warning(
                f"[CHAPTER {chapter_number}] No updated character visuals to apply"
            )
            return

        # Ensure the character_visuals attribute exists in state
        if not hasattr(state, "character_visuals"):
            logger.warning(
                f"[CHAPTER {chapter_number}] State doesn't have character_visuals attribute, creating it"
            )
            # Add the attribute dynamically
            setattr(state, "character_visuals", {})

        # Get the current visuals
        current_visuals = getattr(state, "character_visuals", {})

        # Ensure it's a dictionary
        if not isinstance(current_visuals, dict):
            logger.warning(
                f"[CHAPTER {chapter_number}] character_visuals is not a dictionary (type: {type(current_visuals)}), reinitializing"
            )
            state.character_visuals = {}
            current_visuals = state.character_visuals

        logger.info(
            f"[CHAPTER {chapter_number}] AdventureState.character_visuals AFTER update:"
        )

        if not current_visuals:
            logger.info(
                f"[CHAPTER {chapter_number}] Initializing character_visuals with first updates"
            )
            state.character_visuals = updated_visuals

            # Log all new entries
            for char_name, description in updated_visuals.items():
                logger.info(
                    f'[CHAPTER {chapter_number}] NEW: "{char_name}" - "{description}"'
                )

            logger.info(
                f"[CHAPTER {chapter_number}] Summary: {len(updated_visuals)} new, 0 updated, 0 unchanged"
            )
            return

        # Update with new or changed visuals
        new_count = 0
        updates_count = 0
        unchanged_count = 0

        for char_name, visual_desc in updated_visuals.items():
            # New character
            if char_name not in current_visuals:
                current_visuals[char_name] = visual_desc
                new_count += 1
                logger.info(
                    f'[CHAPTER {chapter_number}] NEW: "{char_name}" - "{visual_desc}"'
                )
            # Updated character
            elif current_visuals[char_name] != visual_desc:
                old_desc = current_visuals[char_name]
                current_visuals[char_name] = visual_desc
                updates_count += 1
                logger.info(f'[CHAPTER {chapter_number}] UPDATED: "{char_name}"')
                logger.info(f'[CHAPTER {chapter_number}]   BEFORE: "{old_desc}"')
                logger.info(f'[CHAPTER {chapter_number}]   AFTER:  "{visual_desc}"')
            # Unchanged character
            else:
                unchanged_count += 1
                logger.info(
                    f'[CHAPTER {chapter_number}] UNCHANGED: "{char_name}" - "{visual_desc}"'
                )

        logger.info(
            f"[CHAPTER {chapter_number}] Summary: {new_count} new, {updates_count} updated, {unchanged_count} unchanged"
        )

    def append_new_chapter(self, chapter_data: ChapterData) -> None:
        """Appends a new chapter to the AdventureState."""
        if self.state is None:
            raise ValueError("State not initialized.")
        
        logger.info(f"[CHAPTER CREATION] Appending new chapter: {chapter_data.chapter_number}")
        logger.info(f"[CHAPTER CREATION] Chapter type: {chapter_data.chapter_type}")
        logger.info(f"[CHAPTER CREATION] Current chapters before append: {len(self.state.chapters)}")
        logger.info(f"[CHAPTER CREATION] Current storytelling phase: {self.state.current_storytelling_phase}")

        # Track agency references in the new chapter
        self.update_agency_references(chapter_data)

        # Append the chapter to the state
        self.state.chapters.append(chapter_data)
        
        logger.info(f"[CHAPTER CREATION] Chapter appended! Total chapters now: {len(self.state.chapters)}")
        
        # CHECK IF ADVENTURE SHOULD BE COMPLETE
        if len(self.state.chapters) >= self.state.story_length:
            logger.info(f"[CHAPTER CREATION] Adventure reached target length ({len(self.state.chapters)}/{self.state.story_length})")
            if chapter_data.chapter_type == ChapterType.CONCLUSION:
                logger.info(f"[CHAPTER CREATION] Final chapter is CONCLUSION - adventure should be complete!")
            else:
                logger.warning(f"[CHAPTER CREATION] Final chapter is {chapter_data.chapter_type} instead of CONCLUSION!")
        else:
            logger.info(f"[CHAPTER CREATION] Adventure not complete yet ({len(self.state.chapters)}/{self.state.story_length})")

    async def reconstruct_state_from_storage(
        self, stored_state: Dict[str, Any]
    ) -> Optional[AdventureState]:
        """Reconstruct an AdventureState object from stored state data.

        This method handles retrieving state from storage and properly reconstructing it,
        ensuring all required fields have valid values that pass validation.

        Args:
            stored_state: The state data retrieved from storage

        Returns:
            A properly reconstructed AdventureState object, or None if reconstruction fails
        """
        if not stored_state:
            logger.error("Cannot reconstruct state: stored_state is empty or None")
            return None

        try:
            logger.info("Reconstructing AdventureState from stored data")
            logger.debug(f"Stored state keys: {list(stored_state.keys())}")

            # Ensure required narrative elements are present
            narrative_elements = stored_state.get("selected_narrative_elements", {})
            if not narrative_elements or not isinstance(narrative_elements, dict):
                logger.warning("Missing or invalid narrative elements, using defaults")
                narrative_elements = {
                    "settings": "Default Setting",
                    "characters": "Default Characters",
                    "objects": "Default Objects",
                    "events": "Default Events",
                }
            elif not all(
                k in narrative_elements
                for k in ["settings", "characters", "objects", "events"]
            ):
                # Fill in any missing keys with defaults
                defaults = {
                    "settings": "Default Setting",
                    "characters": "Default Characters",
                    "objects": "Default Objects",
                    "events": "Default Events",
                }
                for key, default_value in defaults.items():
                    if key not in narrative_elements:
                        narrative_elements[key] = default_value
                        logger.warning(
                            f"Added missing narrative element '{key}' with default value"
                        )

            # Ensure required sensory details are present
            sensory_details = stored_state.get("selected_sensory_details", {})
            if not sensory_details or not isinstance(sensory_details, dict):
                logger.warning("Missing or invalid sensory details, using defaults")
                sensory_details = {
                    "visuals": "Default Visual",
                    "sounds": "Default Sound",
                    "smells": "Default Smell",
                    "textures": "Default Texture",
                }
            elif not all(
                k in sensory_details
                for k in ["visuals", "sounds", "smells", "textures"]
            ):
                # Fill in any missing keys with defaults
                defaults = {
                    "visuals": "Default Visual",
                    "sounds": "Default Sound",
                    "smells": "Default Smell",
                    "textures": "Default Texture",
                }
                for key, default_value in defaults.items():
                    if key not in sensory_details:
                        sensory_details[key] = default_value
                        logger.warning(
                            f"Added missing sensory detail '{key}' with default value"
                        )

            # Ensure required string fields are not empty
            required_string_fields = {
                "selected_theme": "Adventure Theme",
                "selected_moral_teaching": "Moral Teaching",
                "selected_plot_twist": "Plot Twist",
                "current_storytelling_phase": "Conclusion",
            }

            for field, default_value in required_string_fields.items():
                if field not in stored_state or not stored_state[field]:
                    logger.warning(
                        f"Missing or empty required field '{field}', using default value"
                    )
                    stored_state[field] = default_value

            # Ensure chapters array exists and is properly formatted
            chapters = stored_state.get("chapters", [])
            if not isinstance(chapters, list):
                logger.warning("Invalid chapters format, using empty list")
                chapters = []

            # Process chapters to ensure they have valid chapter_content
            for chapter in chapters:
                # Ensure chapter_content exists and has required fields
                if "chapter_content" not in chapter or not chapter["chapter_content"]:
                    logger.warning(
                        f"Missing chapter_content for chapter {chapter.get('chapter_number', 'unknown')}, creating default"
                    )
                    chapter["chapter_content"] = {
                        "content": chapter.get("content", ""),
                        "choices": [],
                    }
                elif "choices" not in chapter["chapter_content"]:
                    logger.warning(
                        f"Missing choices in chapter_content for chapter {chapter.get('chapter_number', 'unknown')}, creating empty list"
                    )
                    chapter["chapter_content"]["choices"] = []

                # Handle chapter_type case sensitivity and ensure chapter 10 is CONCLUSION
                if "chapter_type" in chapter:
                    chapter_number = chapter.get("chapter_number", 0)

                    # Log the original chapter type for debugging
                    logger.debug(
                        f"Original chapter_type for chapter {chapter_number}: {chapter['chapter_type']} (type: {type(chapter['chapter_type'])})"
                    )

                    # Convert chapter_type to proper ChapterType enum
                    if isinstance(chapter["chapter_type"], str):
                        chapter_type_str = chapter["chapter_type"].lower()
                        logger.debug(
                            f"Converted chapter_type to lowercase: {chapter_type_str}"
                        )

                        # Map the lowercase string to proper ChapterType enum
                        try:
                            # Map string to ChapterType enum
                            if chapter_type_str == "lesson":
                                chapter["chapter_type"] = ChapterType.LESSON
                                logger.debug(
                                    f"Mapped string 'lesson' to ChapterType.LESSON enum for chapter {chapter_number}"
                                )
                            elif chapter_type_str == "story":
                                chapter["chapter_type"] = ChapterType.STORY
                                logger.debug(
                                    f"Mapped string 'story' to ChapterType.STORY enum for chapter {chapter_number}"
                                )
                            elif chapter_type_str == "conclusion":
                                chapter["chapter_type"] = ChapterType.CONCLUSION
                                logger.info(
                                    f"Found CONCLUSION chapter: {chapter_number}"
                                )
                            elif chapter_type_str == "reflect":
                                chapter["chapter_type"] = ChapterType.REFLECT
                                logger.debug(
                                    f"Mapped string 'reflect' to ChapterType.REFLECT enum for chapter {chapter_number}"
                                )
                            elif chapter_type_str == "summary":
                                chapter["chapter_type"] = ChapterType.SUMMARY
                                logger.debug(
                                    f"Mapped string 'summary' to ChapterType.SUMMARY enum for chapter {chapter_number}"
                                )
                            else:
                                # Default to STORY if not recognized
                                logger.warning(
                                    f"Unrecognized chapter_type '{chapter_type_str}' for chapter {chapter_number}, defaulting to STORY"
                                )
                                chapter["chapter_type"] = ChapterType.STORY
                        except Exception as e:
                            logger.warning(
                                f"Error converting chapter_type to enum: {e}"
                            )
                            # Keep as string but ensure lowercase
                            chapter["chapter_type"] = chapter_type_str

                # Special handling for the last chapter - force it to be CONCLUSION
                chapter_number = chapter.get("chapter_number")
                if chapter_number == stored_state.get("story_length", 10):
                    logger.info(
                        f"Setting last chapter {chapter_number} type to ChapterType.CONCLUSION (was: {chapter.get('chapter_type', 'unknown')})"
                    )
                    chapter["chapter_type"] = ChapterType.CONCLUSION

                # For story chapters, ensure exactly 3 choices
                if (
                    chapter.get("chapter_type") == ChapterType.STORY
                    and len(chapter["chapter_content"]["choices"]) != 3
                ):
                    logger.warning(
                        f"Story chapter {chapter.get('chapter_number', 'unknown')} has {len(chapter['chapter_content']['choices'])} choices, adjusting to 3"
                    )
                    choices = chapter["chapter_content"]["choices"][:3]
                    while len(choices) < 3:
                        choices.append(
                            {
                                "text": f"Option {len(choices) + 1}",
                                "next_chapter": f"chapter_{chapter.get('chapter_number', 0)}_{len(choices)}",
                            }
                        )
                    chapter["chapter_content"]["choices"] = choices

            # Ensure other required fields exist
            if "story_length" not in stored_state:
                stored_state["story_length"] = 10
                logger.warning("Missing story_length, using default value of 10")

            # Handle planned_chapter_types - ensure they exist and are converted to ChapterType enum
            if (
                "planned_chapter_types" not in stored_state
                or not stored_state["planned_chapter_types"]
            ):
                # CORRUPTION FIX: If we have existing chapters but no planned_chapter_types,
                # attempt to reconstruct the sequence from chapter content and types
                if chapters and len(chapters) > 0:
                    logger.warning(f"CORRUPTION DETECTED: Adventure has {len(chapters)} chapters but missing planned_chapter_types - attempting reconstruction")
                    
                    # Try to reconstruct planned_chapter_types by analyzing existing chapters
                    reconstructed_types = []
                    for i, chapter in enumerate(chapters):
                        chapter_number = chapter.get('chapter_number', i + 1)
                        chapter_content = chapter.get('content', '')
                        chapter_question = chapter.get('question')
                        current_type = chapter.get('chapter_type', 'story')
                        
                        # Determine correct type based on content analysis
                        if chapter_number == stored_state.get('story_length', 10):
                            # Last chapter should be CONCLUSION
                            correct_type = ChapterType.CONCLUSION
                            chapter['chapter_type'] = 'conclusion'
                            logger.info(f"CORRUPTION FIX: Set chapter {chapter_number} to CONCLUSION")
                        elif chapter_question is not None:
                            # Has a question - should be LESSON
                            correct_type = ChapterType.LESSON  
                            chapter['chapter_type'] = 'lesson'
                            logger.info(f"CORRUPTION FIX: Set chapter {chapter_number} to LESSON (has question)")
                        elif 'reflect' in chapter_content.lower() or 'reflection' in chapter_content.lower():
                            # Content suggests reflection - should be REFLECT
                            correct_type = ChapterType.REFLECT
                            chapter['chapter_type'] = 'reflect'
                            logger.info(f"CORRUPTION FIX: Set chapter {chapter_number} to REFLECT (reflection content)")
                        else:
                            # Default to STORY
                            correct_type = ChapterType.STORY
                            chapter['chapter_type'] = 'story'
                            if current_type != 'story':
                                logger.info(f"CORRUPTION FIX: Set chapter {chapter_number} to STORY")
                        
                        reconstructed_types.append(correct_type)
                    
                    # If we can't reconstruct the full sequence properly, regenerate it
                    story_length = stored_state.get('story_length', 10)
                    if len(reconstructed_types) < story_length:
                        logger.warning(f"CORRUPTION FIX: Could only reconstruct {len(reconstructed_types)}/{story_length} types - regenerating proper distribution")
                        from app.services.chapter_manager import ChapterManager
                        try:
                            # Use proper chapter distribution instead of defaulting to STORY
                            available_questions = 3  # Default minimum
                            proper_types = ChapterManager.determine_chapter_types(story_length, available_questions)
                            
                            # Preserve any existing chapter types we successfully identified
                            for i, existing_type in enumerate(reconstructed_types):
                                if i < len(proper_types):
                                    proper_types[i] = existing_type
                            
                            reconstructed_types = proper_types
                            logger.warning(f"CORRUPTION FIX: Used proper chapter distribution: {[ct.value for ct in reconstructed_types]}")
                        except Exception as e:
                            logger.error(f"CORRUPTION FIX: Failed to generate proper types: {e}")
                            # Fallback: extend with minimal valid sequence
                            while len(reconstructed_types) < story_length:
                                if len(reconstructed_types) == story_length - 1:
                                    reconstructed_types.append(ChapterType.CONCLUSION)
                                else:
                                    reconstructed_types.append(ChapterType.STORY)
                    
                    stored_state["planned_chapter_types"] = reconstructed_types
                    logger.warning(f"CORRUPTION FIX: Reconstructed planned_chapter_types from {len(chapters)} existing chapters")
                    logger.info(f"CORRUPTION FIX: Reconstructed sequence: {[ct.value for ct in reconstructed_types]}")
                else:
                    # Use ChapterType enum values for default sequence (no existing chapters)
                    stored_state["planned_chapter_types"] = [
                        ChapterType.STORY,
                        ChapterType.LESSON,
                        ChapterType.STORY,
                        ChapterType.LESSON,
                        ChapterType.REFLECT,
                        ChapterType.STORY,
                        ChapterType.LESSON,
                        ChapterType.STORY,
                        ChapterType.LESSON,
                        ChapterType.CONCLUSION,
                    ]
                    logger.warning("Missing planned_chapter_types, using default sequence")
            else:
                # Convert existing planned_chapter_types to ChapterType enum
                planned_chapter_types = []
                for chapter_type in stored_state["planned_chapter_types"]:
                    if isinstance(chapter_type, str):
                        # Convert string to ChapterType enum
                        chapter_type_str = chapter_type.lower()
                        try:
                            if chapter_type_str == "lesson":
                                planned_chapter_types.append(ChapterType.LESSON)
                            elif chapter_type_str == "story":
                                planned_chapter_types.append(ChapterType.STORY)
                            elif chapter_type_str == "conclusion":
                                planned_chapter_types.append(ChapterType.CONCLUSION)
                            elif chapter_type_str == "reflect":
                                planned_chapter_types.append(ChapterType.REFLECT)
                            elif chapter_type_str == "summary":
                                planned_chapter_types.append(ChapterType.SUMMARY)
                            else:
                                # Default to STORY for unrecognized types
                                logger.warning(
                                    f"Unrecognized planned chapter type: {chapter_type_str}, using STORY"
                                )
                                planned_chapter_types.append(ChapterType.STORY)
                        except Exception as e:
                            logger.warning(
                                f"Error converting planned chapter type: {e}"
                            )
                            # Keep as lowercase string if conversion fails
                            planned_chapter_types.append(chapter_type_str)
                    else:
                        # Keep as is if already a ChapterType enum
                        planned_chapter_types.append(chapter_type)

                stored_state["planned_chapter_types"] = planned_chapter_types
                logger.info(f"Converted planned_chapter_types to ChapterType enums")

            if "metadata" not in stored_state:
                stored_state["metadata"] = {}
                logger.warning("Missing metadata, using empty dict")

            # Generate chapter summaries if they don't exist
            chapter_summaries = stored_state.get("chapter_summaries", [])
            summary_chapter_titles = stored_state.get("summary_chapter_titles", [])

            # REMOVED: Summary generation during state reconstruction
            # State reconstruction should be read-only and never modify stored data
            # All summaries should be generated during the adventure flow, not during reconstruction
            if (not chapter_summaries or len(chapter_summaries) == 0) and chapters:
                logger.warning(
                    "No chapter summaries found during reconstruction - using empty lists. "
                    "Summaries should have been generated during adventure flow."
                )
                chapter_summaries = []
                summary_chapter_titles = []

            # REMOVED: Lesson question extraction during state reconstruction
            # State reconstruction should be read-only and never modify stored data
            # All lesson questions should be captured during the adventure flow, not during reconstruction
            lesson_questions = stored_state.get("lesson_questions", [])

            if (not lesson_questions or len(lesson_questions) == 0) and chapters:
                logger.warning(
                    "No lesson questions found during reconstruction - using empty list. "
                    "Questions should have been captured during adventure flow."
                )
                lesson_questions = []

            # Create a valid state with all required fields
            valid_state = {
                "current_chapter_id": stored_state.get("current_chapter_id", ""),
                "chapters": chapters,
                "story_length": stored_state["story_length"],
                "selected_narrative_elements": narrative_elements,
                "selected_sensory_details": sensory_details,
                "selected_theme": stored_state["selected_theme"],
                "selected_moral_teaching": stored_state["selected_moral_teaching"],
                "selected_plot_twist": stored_state["selected_plot_twist"],
                "planned_chapter_types": stored_state["planned_chapter_types"],
                "current_storytelling_phase": stored_state[
                    "current_storytelling_phase"
                ],
                "chapter_summaries": stored_state.get(
                    "chapter_summaries", chapter_summaries
                ),
                "summary_chapter_titles": stored_state.get(
                    "summary_chapter_titles", summary_chapter_titles
                ),
                "lesson_questions": stored_state.get(
                    "lesson_questions", lesson_questions
                ),
                "metadata": stored_state["metadata"],
            }

            # Convert the valid state dict to an AdventureState object
            try:
                reconstructed_state = AdventureState.parse_obj(valid_state)
                logger.info(
                    "Successfully reconstructed AdventureState from stored data"
                )
                self.state = reconstructed_state  # Set the internal state
                return self.state  # Return the set state
            except Exception as e:
                logger.error(
                    f"Error creating AdventureState from valid_state: {str(e)}"
                )
                logger.debug(f"Valid state that caused error: {valid_state}")
                return None

        except Exception as e:
            logger.error(f"Error reconstructing state from storage: {str(e)}")
            return None

    async def format_adventure_summary_data(self, state: AdventureState, adventure_id: Optional[str] = None) -> Dict[str, Any]:
        """Format adventure state data for the React summary component.

        Args:
            state: The completed adventure state

        Returns:
            Formatted data for the React summary component
        """
        # Log detailed state information for debugging
        logger.info("\n=== DEBUG: AdventureState Summary Data ===")
        logger.info(f"Total chapters: {len(state.chapters)}")
        logger.info(
            f"Number of chapter summaries: {len(state.chapter_summaries) if hasattr(state, 'chapter_summaries') else 0}"
        )
        logger.info(
            f"Number of summary chapter titles: {len(state.summary_chapter_titles) if hasattr(state, 'summary_chapter_titles') else 0}"
        )
        logger.info(
            f"Number of lesson questions: {len(state.lesson_questions) if hasattr(state, 'lesson_questions') else 0}"
        )

        # If we have chapters but no summaries, that's a problem
        if len(state.chapters) > 0 and (
            not hasattr(state, "chapter_summaries") or len(state.chapter_summaries) == 0
        ):
            logger.warning("State has chapters but no chapter summaries!")

        # If we have lesson chapters but no questions, that's a problem
        # Check using both enum comparison and string comparison for case-insensitivity
        lesson_chapters = [
            ch
            for ch in state.chapters
            if ch.chapter_type == ChapterType.LESSON
            or (
                isinstance(ch.chapter_type, str) and ch.chapter_type.lower() == "lesson"
            )
        ]
        logger.info(f"Found {len(lesson_chapters)} lesson chapters during analysis")

        # Log each chapter's type for debugging
        for idx, ch in enumerate(state.chapters):
            chapter_type = ch.chapter_type
            if isinstance(chapter_type, str):
                chapter_type_str = chapter_type
            else:
                chapter_type_str = (
                    chapter_type.value
                    if hasattr(chapter_type, "value")
                    else str(chapter_type)
                )
            logger.info(
                f"Chapter {idx + 1} type: {chapter_type_str} (type: {type(chapter_type)})"
            )

        if len(lesson_chapters) > 0 and (
            not hasattr(state, "lesson_questions") or len(state.lesson_questions) == 0
        ):
            logger.warning(
                f"State has {len(lesson_chapters)} lesson chapters but no lesson questions!"
            )

        logger.info("=========================================\n")
        # Extract chapter summaries with titles
        chapter_summaries = []

        # Verify we have chapter summaries in the state
        if not state.chapter_summaries or len(state.chapter_summaries) == 0:
            logger.warning("No chapter summaries found in AdventureState")
            # Generate more meaningful placeholder summaries for each chapter
            state.chapter_summaries = []
            state.summary_chapter_titles = []

            # Sort chapters by chapter number to ensure correct order
            for ch in sorted(state.chapters, key=lambda x: x.chapter_number):
                # Get a snippet of content for the summary
                content_snippet = (
                    ch.content[:200] + "..." if len(ch.content) > 200 else ch.content
                )
                summary = f"In this chapter: {content_snippet}"
                state.chapter_summaries.append(summary)

                # Create a title based on chapter type
                chapter_type_str = ""
                if isinstance(ch.chapter_type, str):
                    chapter_type_str = ch.chapter_type.capitalize()
                else:
                    chapter_type_str = (
                        ch.chapter_type.value.capitalize()
                        if hasattr(ch.chapter_type, "value")
                        else str(ch.chapter_type).capitalize()
                    )

                title = f"Chapter {ch.chapter_number}: {chapter_type_str} Chapter"
                state.summary_chapter_titles.append(title)

            logger.info(
                f"Generated {len(state.chapter_summaries)} placeholder summaries and titles"
            )

        # Process each chapter and its summary
        for i, chapter in enumerate(state.chapters, 1):
            # Get the summary for this chapter if available
            summary = ""
            if i <= len(state.chapter_summaries):
                summary = state.chapter_summaries[i - 1]
            else:
                logger.warning(f"No summary found for chapter {i}")
                summary = f"Summary for Chapter {i}"

            # Get title from summary_chapter_titles if available, otherwise extract from summary
            title = f"Chapter {i}"
            summary_text = summary

            # Use stored title if available
            if hasattr(state, "summary_chapter_titles") and i <= len(
                state.summary_chapter_titles
            ):
                title = state.summary_chapter_titles[i - 1]
            # Fall back to extraction if needed
            elif ":" in summary and len(summary.split(":", 1)[0]) < 50:
                title = summary.split(":", 1)[0].strip()
                summary_text = summary.split(":", 1)[1].strip()
            else:
                # Generate a generic title if we couldn't extract one
                title = (
                    f"Chapter {i}: {chapter.chapter_type.value.capitalize()} Chapter"
                )

            chapter_summaries.append(
                {
                    "number": i,
                    "title": title,
                    "summary": summary_text,
                    "chapterType": chapter.chapter_type.value,
                }
            )

        # Extract educational questions
        educational_questions = []

        # First check if we have lesson_questions in the state
        if state.lesson_questions and len(state.lesson_questions) > 0:
            logger.info(
                f"Using {len(state.lesson_questions)} questions from state.lesson_questions"
            )

            for question_data in state.lesson_questions:
                # Find the chapter that contains this question
                chapter = next(
                    (
                        ch
                        for ch in state.chapters
                        if ch.chapter_type == ChapterType.LESSON
                        and ch.question
                        and ch.question.get("question") == question_data.get("question")
                    ),
                    None,
                )

                # Process the question data
                is_correct = False
                chosen_answer = "No answer recorded"

                # Try to extract from question_data first
                if "is_correct" in question_data:
                    is_correct = question_data["is_correct"]
                    logger.debug(f"Using is_correct from question_data: {is_correct}")

                if "chosen_answer" in question_data:
                    chosen_answer = question_data["chosen_answer"]
                    logger.debug(
                        f"Using chosen_answer from question_data: {chosen_answer}"
                    )
                # If not in question_data, try to get from chapter.response
                elif chapter and chapter.response:
                    # Check if response is a LessonResponse or has the right attributes
                    response = chapter.response
                    if hasattr(response, "is_correct"):
                        is_correct = response.is_correct
                        logger.debug(
                            f"Using is_correct from chapter response: {is_correct}"
                        )
                    if hasattr(response, "chosen_answer"):
                        chosen_answer = response.chosen_answer
                        logger.debug(
                            f"Using chosen_answer from chapter response: {chosen_answer}"
                        )

                question_obj = {
                    "question": question_data.get("question", "Unknown question"),
                    "userAnswer": chosen_answer,
                    "isCorrect": is_correct,
                    "explanation": question_data.get("explanation", ""),
                }

                # Add correct answer if user was wrong
                if not is_correct:
                    # Try to find correct answer in question_data
                    correct_answer = None
                    if "correct_answer" in question_data:
                        correct_answer = question_data["correct_answer"]
                        logger.debug(f"Using correct_answer directly: {correct_answer}")
                    else:
                        # Look in answers array
                        for answer in question_data.get("answers", []):
                            if answer.get("is_correct"):
                                correct_answer = answer.get("text")
                                logger.debug(
                                    f"Found correct answer in answers array: {correct_answer}"
                                )
                                break

                    if correct_answer:
                        question_obj["correctAnswer"] = correct_answer

                educational_questions.append(question_obj)
                logger.info(f"Added question: {question_obj['question']}")

        # If no questions yet, extract directly from LESSON chapters
        if len(educational_questions) == 0:
            logger.info(
                "No questions from lesson_questions array, extracting from LESSON chapters"
            )
            for chapter in state.chapters:
                # Get chapter type and handle both enum and string representations for case-insensitivity
                chapter_type = chapter.chapter_type
                is_lesson = chapter_type == ChapterType.LESSON or (
                    isinstance(chapter_type, str) and chapter_type.lower() == "lesson"
                )

                logger.debug(
                    f"Checking chapter {chapter.chapter_number}: type={chapter_type}, is_lesson={is_lesson}"
                )

                if is_lesson and chapter.question:
                    question_data = chapter.question
                    logger.debug(
                        f"Processing question from chapter: {question_data.get('question')}"
                    )

                    # Get response if available
                    is_correct = False
                    chosen_answer = "No answer recorded"

                    if chapter.response:
                        response = chapter.response
                        if hasattr(response, "is_correct"):
                            is_correct = response.is_correct
                        if hasattr(response, "chosen_answer"):
                            chosen_answer = response.chosen_answer
                        logger.debug(
                            f"Found response: correct={is_correct}, answer={chosen_answer}"
                        )

                    question_obj = {
                        "question": question_data.get("question", "Unknown question"),
                        "userAnswer": chosen_answer,
                        "isCorrect": is_correct,
                        "explanation": question_data.get("explanation", ""),
                    }

                    # Add correct answer if user was wrong
                    if not is_correct:
                        correct_answer = None
                        if "correct_answer" in question_data:
                            correct_answer = question_data["correct_answer"]
                        else:
                            for answer in question_data.get("answers", []):
                                if answer.get("is_correct"):
                                    correct_answer = answer.get("text")
                                    break

                        if correct_answer:
                            question_obj["correctAnswer"] = correct_answer
                            logger.debug(f"Added correct answer: {correct_answer}")

                    educational_questions.append(question_obj)
                    logger.info(
                        f"Added question from LESSON chapter: {question_obj['question']}"
                    )

        # If we still have no questions but have LESSON chapters, add a fallback question
        if len(educational_questions) == 0:
            logger.warning("No questions found, adding fallback question")
            educational_questions.append(
                {
                    "question": "What did you learn from this adventure?",
                    "userAnswer": "The adventure was completed successfully",
                    "isCorrect": True,
                    "explanation": "This adventure was designed to teach important educational concepts while telling an engaging story.",
                }
            )
            logger.info("Added fallback question")

        # Calculate statistics - exclude SUMMARY chapters from user-visible count
        user_chapters = [
            chapter for chapter in state.chapters 
            if chapter.chapter_type != ChapterType.SUMMARY
        ]
        
        # Calculate actual time spent if adventure_id is available
        time_spent = "-- mins"
        if adventure_id:
            try:
                from uuid import UUID
                time_spent = await get_telemetry_service().get_adventure_total_duration(UUID(adventure_id))
            except Exception as e:
                logger.warning(f"Failed to get actual duration, using fallback: {e}")
        
        statistics = {
            "chaptersCompleted": len(user_chapters),
            "questionsAnswered": len(educational_questions),
            "timeSpent": time_spent,
            "correctAnswers": sum(
                1 for q in educational_questions if q.get("isCorrect", False)
            ),
        }

        # Ensure we don't have more correct answers than questions
        if statistics["correctAnswers"] > statistics["questionsAnswered"]:
            logger.warning(
                f"More correct answers ({statistics['correctAnswers']}) than questions ({statistics['questionsAnswered']}), adjusting"
            )
            statistics["correctAnswers"] = statistics["questionsAnswered"]

        # Ensure we have at least one question for the statistics
        if statistics["questionsAnswered"] == 0:
            logger.warning("No questions found, setting to 1 for statistics")
            statistics["questionsAnswered"] = 1
            statistics["correctAnswers"] = (
                1  # Assume correct for better user experience
            )

        logger.info(
            f"Final summary data: {len(chapter_summaries)} chapters, {len(educational_questions)} questions"
        )

        return {
            "chapterSummaries": chapter_summaries,
            "educationalQuestions": educational_questions,
            "statistics": statistics,
        }
