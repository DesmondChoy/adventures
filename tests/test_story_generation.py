import os
import sys

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

import asyncio
import yaml
import logging
import pytest
from app.models.story import AdventureState, ChapterType, ChapterData, LessonResponse, ChapterContent, StoryChoice
from app.services.llm import LLMService
from app.services.chapter_manager import ChapterManager
from app.services.llm.prompt_engineering import build_system_prompt, build_user_prompt

# Configure logging to show everything
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)

# Create logger for this test
logger = logging.getLogger(__name__)

@pytest.fixture
def story_config():
    """Load story configuration for testing."""
    with open("app/data/stories.yaml", "r") as f:
        story_data = yaml.safe_load(f)
        return story_data["story_categories"]["magical_realms"]

@pytest.fixture
def llm_service():
    """Initialize LLM service for testing."""
    return LLMService()

@pytest.fixture
def chapter_manager():
    """Initialize chapter manager for testing."""
    return ChapterManager()

@pytest.fixture
def initial_state():
    """Create initial adventure state for testing."""
    return AdventureState(
        current_chapter_id="start",
        story_length=3,  # Quick Quest
        chapters=[]
    )

def print_section(title: str, content: str):
    """Print a section with a title and content."""
    print(f"\n{'='*80}")
    print(f"{title:^80}")
    print('='*80)
    print(content.strip())
    print('='*80)

@pytest.mark.asyncio
async def test_story_generation_flow(story_config, llm_service, chapter_manager, initial_state):
    """Test the complete story generation flow with prompts and responses."""
    # Set up chapter types
    chapter_types = chapter_manager.determine_chapter_types(initial_state.story_length, available_questions=5)
    story_config["chapter_types"] = chapter_types
    
    print("\nStarting Story Generation Test")
    print("Story length:", initial_state.story_length)
    print("Chapter types:", [ct.value for ct in chapter_types])
    
    # First Chapter (Lesson)
    print_section("FIRST CHAPTER - System Prompt", build_system_prompt(story_config))
    
    first_user_prompt = build_user_prompt(
        initial_state,
        lesson_question={"question": "What is the heart's main function?", "answers": [
            {"text": "To pump blood throughout the body", "is_correct": True},
            {"text": "To digest food", "is_correct": False},
            {"text": "To filter air", "is_correct": False}
        ]}
    )
    print_section("FIRST CHAPTER - User Prompt", first_user_prompt)
    
    print_section("FIRST CHAPTER - LLM Response", "")
    first_chapter_content = ""
    async for chunk in llm_service.generate_story_stream(
        story_config,
        initial_state,
        question={"question": "What is the heart's main function?", "answers": [
            {"text": "To pump blood throughout the body", "is_correct": True},
            {"text": "To digest food", "is_correct": False},
            {"text": "To filter air", "is_correct": False}
        ]},
    ):
        first_chapter_content += chunk
        print(chunk, end="", flush=True)
    
    # Update state with first chapter response
    chapter_content = ChapterContent(
        content=first_chapter_content,
        choices=[
            StoryChoice(text="To pump blood throughout the body", next_chapter="correct"),
            StoryChoice(text="To digest food", next_chapter="wrong1"),
            StoryChoice(text="To filter air", next_chapter="wrong2")
        ]
    )
    
    lesson_response = LessonResponse(
        question={
            "question": "What is the heart's main function?",
            "answers": [
                {"text": "To pump blood throughout the body", "is_correct": True},
                {"text": "To digest food", "is_correct": False},
                {"text": "To filter air", "is_correct": False}
            ]
        },
        chosen_answer="To pump blood throughout the body",
        is_correct=True
    )
    
    initial_state.chapters.append(
        ChapterData(
            chapter_number=1,
            content=first_chapter_content,
            chapter_type=ChapterType.LESSON,
            response=lesson_response,
            chapter_content=chapter_content
        )
    )
    
    # Second Chapter (Story)
    print_section("SECOND CHAPTER - System Prompt", build_system_prompt(story_config))
    
    second_user_prompt = build_user_prompt(initial_state)
    print_section("SECOND CHAPTER - User Prompt", second_user_prompt)
    
    print_section("SECOND CHAPTER - LLM Response", "")
    second_chapter_content = ""
    async for chunk in llm_service.generate_story_stream(
        story_config,
        initial_state
    ):
        second_chapter_content += chunk
        print(chunk, end="", flush=True)
    
    # Verify content
    assert "heart" in first_chapter_content.lower(), "First chapter should mention the heart"
    assert "function" in first_chapter_content.lower(), "First chapter should lead to the question about function"
    assert "<CHOICES>" in second_chapter_content, "Second chapter should include choices"
    assert all(f"Choice {c}:" in second_chapter_content for c in "ABC"), "Second chapter should have all three choices"

if __name__ == "__main__":
    # Create fixtures manually when running directly
    with open("app/data/stories.yaml", "r") as f:
        story_data = yaml.safe_load(f)
        story_config = story_data["story_categories"]["magical_realms"]
    
    llm_service = LLMService()
    chapter_manager = ChapterManager()
    initial_state = AdventureState(
        current_chapter_id="start",
        story_length=3,
        chapters=[]
    )
    
    # Run the test
    asyncio.run(test_story_generation_flow(
        story_config=story_config,
        llm_service=llm_service,
        chapter_manager=chapter_manager,
        initial_state=initial_state
    )) 