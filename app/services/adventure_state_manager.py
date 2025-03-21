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
                # Keep existing chapters not in client_chapters and add new chapters
                updated_chapters = [
                    ch
                    for ch in self.state.chapters
                    if ch.chapter_number
                    not in [c["chapter_number"] for c in client_chapters]
                ] + new_chapters
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

    def append_new_chapter(self, chapter_data: ChapterData) -> None:
        """Appends a new chapter to the AdventureState."""
        if self.state is None:
            raise ValueError("State not initialized.")
        logger.debug(f"Appending new chapter: {chapter_data.chapter_number}")

        # Track agency references in the new chapter
        self.update_agency_references(chapter_data)

        # Append the chapter to the state
        self.state.chapters.append(chapter_data)

    def format_adventure_summary_data(self, state: AdventureState) -> Dict[str, Any]:
        """Format adventure state data for the React summary component.

        Args:
            state: The completed adventure state

        Returns:
            Formatted data for the React summary component
        """
        # Extract chapter summaries with titles
        chapter_summaries = []

        # Verify we have chapter summaries in the state
        if not state.chapter_summaries or len(state.chapter_summaries) == 0:
            logger.warning("No chapter summaries found in AdventureState")
            # We'll continue with an empty list

        # Process each chapter and its summary
        for i, chapter in enumerate(state.chapters, 1):
            # Get the summary for this chapter if available
            summary = ""
            if i <= len(state.chapter_summaries):
                summary = state.chapter_summaries[i - 1]
            else:
                logger.warning(f"No summary found for chapter {i}")
                summary = "Summary not available"

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

                if chapter and chapter.response:
                    response = chapter.response
                    is_correct = response.is_correct
                    chosen_answer = response.chosen_answer
                else:
                    logger.warning(
                        f"Could not find chapter for question: {question_data.get('question')}"
                    )
                    is_correct = False
                    chosen_answer = "No answer"

                question_obj = {
                    "question": question_data.get("question", "Unknown question"),
                    "userAnswer": chosen_answer,
                    "isCorrect": is_correct,
                    "explanation": question_data.get("explanation", ""),
                }

                # Add correct answer if user was wrong
                if not is_correct:
                    correct_answer = question_data.get("correct_answer")
                    if correct_answer:
                        question_obj["correctAnswer"] = correct_answer

                educational_questions.append(question_obj)
        else:
            # Extract questions directly from LESSON chapters
            logger.info("Extracting questions from LESSON chapters")
            for chapter in state.chapters:
                if (
                    chapter.chapter_type == ChapterType.LESSON
                    and chapter.question
                    and chapter.response
                ):
                    question_data = chapter.question
                    response = chapter.response

                    question_obj = {
                        "question": question_data["question"],
                        "userAnswer": response.chosen_answer,
                        "isCorrect": response.is_correct,
                        "explanation": question_data.get("explanation", ""),
                    }

                    # Add correct answer if user was wrong
                    if not response.is_correct:
                        correct_answer = next(
                            (
                                answer["text"]
                                for answer in question_data["answers"]
                                if answer["is_correct"]
                            ),
                            None,
                        )
                        if correct_answer:
                            question_obj["correctAnswer"] = correct_answer

                    educational_questions.append(question_obj)

        # Calculate statistics
        statistics = {
            "chaptersCompleted": len(state.chapters),
            "questionsAnswered": len(educational_questions),
            "timeSpent": "30 mins",  # This could be calculated from timestamps in the future
            "correctAnswers": sum(
                1 for q in educational_questions if q.get("isCorrect", False)
            ),
        }

        return {
            "chapterSummaries": chapter_summaries,
            "educationalQuestions": educational_questions,
            "statistics": statistics,
        }
