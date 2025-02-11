import os
import sys
import random
import re

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

import asyncio
import yaml
import logging
import pytest
import pandas as pd
from app.models.story import AdventureState, ChapterType, ChapterData, LessonResponse, ChapterContent, StoryChoice
from app.services.llm import LLMService
from app.services.chapter_manager import ChapterManager
from app.services.llm.prompt_engineering import build_system_prompt, build_user_prompt
from app.init_data import sample_question

# Configure logging to show everything
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)

# Create logger for this test
logger = logging.getLogger(__name__)

def validate_story_choices(content: str) -> bool:
    """Validate that story choices follow the required format.
    
    Rules:
    1. Must start with <CHOICES> on its own line
    2. Must have exactly three choices (A, B, C)
    3. Each choice must be on a single line
    4. Must end with </CHOICES> on its own line
    5. Choices must be meaningful and distinct
    """
    # Extract choices section
    choices_match = re.search(r'<CHOICES>\n(.*?)\n</CHOICES>', content, re.DOTALL)
    if not choices_match:
        logger.error("Missing or malformed choices section")
        return False
        
    choices_text = choices_match.group(1)
    choices = [line.strip() for line in choices_text.split('\n') if line.strip()]
    
    # Validate number of choices
    if len(choices) != 3:
        logger.error(f"Expected 3 choices, found {len(choices)}")
        return False
    
    # Validate choice format and content
    choice_pattern = r'^Choice [ABC]: .{10,}'  # At least 10 chars of content
    for i, choice in enumerate(['A', 'B', 'C']):
        if not re.match(choice_pattern, choices[i]):
            logger.error(f"Invalid format for Choice {choice}: {choices[i]}")
            return False
            
        # Check for duplicate choices
        for j, other_choice in enumerate(choices):
            if i != j and choices[i].split(': ', 1)[1] == other_choice.split(': ', 1)[1]:
                logger.error(f"Duplicate choice content found: {choices[i]}")
                return False
    
    return True

@pytest.fixture
def story_config():
    """Load story configuration for testing."""
    with open("app/data/stories.yaml", "r") as f:
        story_data = yaml.safe_load(f)
        config = story_data["story_categories"]["magical_realms"]
        return config

@pytest.fixture
def lesson_data():
    """Load lesson data for testing."""
    return pd.read_csv("app/data/lessons.csv")

@pytest.fixture
def llm_service():
    """Initialize LLM service for testing."""
    return LLMService()

@pytest.fixture
def chapter_manager():
    """Initialize chapter manager for testing."""
    return ChapterManager()

def get_available_story_lengths():
    """Get the available story lengths from the app configuration."""
    # These values should match what's offered to users in the app
    return [3, 5, 7]  # Quick, Medium, Long quests

def get_random_story_length():
    """Get a random story length from the available options."""
    return random.choice(get_available_story_lengths())

@pytest.fixture
def initial_state():
    """Create initial adventure state for testing with random story length."""
    return AdventureState(
        current_chapter_id="start",
        story_length=get_random_story_length(),
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
async def test_story_generation_flow(story_config, llm_service, chapter_manager, initial_state, lesson_data):
    """Test the complete story generation flow with prompts and responses using random questions."""
    # Get a random lesson topic from available topics
    lesson_topic = random.choice(lesson_data["topic"].unique())
    
    # Set up chapter types based on available questions for the topic
    available_questions = chapter_manager.count_available_questions(lesson_topic)
    chapter_types = chapter_manager.determine_chapter_types(initial_state.story_length, available_questions)
    story_config["chapter_types"] = chapter_types
    
    print("\nStarting Story Generation Test")
    print("Story length:", initial_state.story_length)
    print("Lesson topic:", lesson_topic)
    print("Chapter types:", [ct.value for ct in chapter_types])
    
    # First Chapter (Lesson)
    system_prompt = build_system_prompt(story_config)
    
    # Get a question from the actual question pool
    test_question = sample_question(lesson_topic)
    
    first_user_prompt = build_user_prompt(
        initial_state,
        lesson_question=test_question
    )
    
    # Collect content without printing
    first_chapter_content = ""
    async for chunk in llm_service.generate_story_stream(
        story_config,
        initial_state,
        question=test_question,
    ):
        first_chapter_content += chunk
    
    # Print the complete chapter content once
    print_section("FIRST CHAPTER - Content", first_chapter_content)
    
    # Update state with first chapter response
    chapter_content = ChapterContent(
        content=first_chapter_content,
        choices=[
            StoryChoice(text=answer["text"], next_chapter=f"choice_{i}")
            for i, answer in enumerate(test_question["answers"])
        ]
    )
    
    lesson_response = LessonResponse(
        question=test_question,
        chosen_answer=next(answer["text"] for answer in test_question["answers"] if answer["is_correct"]),
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
    second_user_prompt = build_user_prompt(initial_state)
    
    # Collect content without printing
    second_chapter_content = ""
    async for chunk in llm_service.generate_story_stream(
        story_config,
        initial_state
    ):
        second_chapter_content += chunk
    
    # Print the complete chapter content once
    print_section("SECOND CHAPTER - Content", second_chapter_content)
    
    # Verify content and structure
    assert len(initial_state.chapters) > 0, "Should have generated at least one chapter"
    assert "<CHOICES>" in second_chapter_content, "Second chapter should include choices"
    assert validate_story_choices(second_chapter_content), "Story choices should follow the required format"

if __name__ == "__main__":
    # Create fixtures manually when running directly
    with open("app/data/stories.yaml", "r") as f:
        story_data = yaml.safe_load(f)
        story_config = story_data["story_categories"]["magical_realms"]
    
    llm_service = LLMService()
    chapter_manager = ChapterManager()
    lesson_data = pd.read_csv("app/data/lessons.csv")
    initial_state = AdventureState(
        current_chapter_id="start",
        story_length=get_random_story_length(),
        chapters=[]
    )
    
    # Run the test
    asyncio.run(test_story_generation_flow(
        story_config=story_config,
        llm_service=llm_service,
        chapter_manager=chapter_manager,
        initial_state=initial_state,
        lesson_data=lesson_data
    )) 