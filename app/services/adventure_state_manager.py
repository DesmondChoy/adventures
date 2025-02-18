from app.models.story import (
    AdventureState,
    ChapterData,
    ChapterType,
    StoryChoice,
    StoryResponse,
    LessonResponse,
    ChapterContent,
)
from app.services.chapter_manager import (
    ChapterManager,
)  # Import ChapterManager to reuse logic
import logging

logger = logging.getLogger("story_app")


class AdventureStateManager:
    def __init__(self):
        self.state: AdventureState | None = None
        self.chapter_manager = ChapterManager()  # Instantiate ChapterManager

    def initialize_state(self, story_length: int, lesson_topic: str) -> AdventureState:
        """Initializes and returns a new AdventureState."""
        logger.debug(
            f"Initializing AdventureState with story_length: {story_length}, lesson_topic: {lesson_topic}"
        )
        self.state = self.chapter_manager.initialize_adventure_state(
            story_length, lesson_topic
        )
        return self.state

    def get_current_state(self) -> AdventureState | None:
        """Returns the current AdventureState."""
        return self.state

    def update_state_from_client(self, validated_state: dict) -> None:
        """Updates the current AdventureState based on validated client data."""
        if self.state is None:
            raise ValueError("State not initialized.")

        if "chapters" in validated_state:
            logger.debug("Updating chapters from client state.")
            chapters = []
            for chapter_data in validated_state["chapters"]:
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

                chapter_content = ChapterContent(
                    content=chapter_data["content"],
                    choices=[
                        StoryChoice(**choice)
                        for choice in chapter_data["chapter_content"]["choices"]
                    ],
                )

                chapters.append(
                    ChapterData(
                        chapter_number=len(chapters) + 1,
                        content=chapter_data["content"],
                        chapter_type=chapter_type,
                        response=response,
                        chapter_content=chapter_content,
                        question=chapter_data.get("question"),
                    )
                )
            self.state.chapters = chapters

        if "current_chapter_id" in validated_state:
            logger.debug(
                f"Updating current_chapter_id to: {validated_state['current_chapter_id']}"
            )
            self.state.current_chapter_id = validated_state["current_chapter_id"]

    def append_new_chapter(self, chapter_data: ChapterData) -> None:
        """Appends a new chapter to the AdventureState."""
        if self.state is None:
            raise ValueError("State not initialized.")
        logger.debug(f"Appending new chapter: {chapter_data.chapter_number}")
        self.state.chapters.append(chapter_data)
