"""
Simple test script to verify the new prompt structure.
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from typing import Dict, Any, List
from app.models.story import (
    AdventureState,
    ChapterType,
    ChapterData,
    ChapterContent,
    StoryChoice,
    StoryResponse,
)
from app.services.llm.prompt_engineering import build_user_prompt, LessonQuestion


# Create a mock ChapterData for testing
def create_mock_chapter(chapter_number, chapter_type=ChapterType.STORY):
    return ChapterData(
        chapter_number=chapter_number,
        content=f"This is chapter {chapter_number} content",
        chapter_type=chapter_type,
        chapter_content=ChapterContent(
            content=f"This is chapter {chapter_number} content",
            choices=[
                StoryChoice(
                    text=f"Choice A for chapter {chapter_number}", next_chapter="next_a"
                ),
                StoryChoice(
                    text=f"Choice B for chapter {chapter_number}", next_chapter="next_b"
                ),
                StoryChoice(
                    text=f"Choice C for chapter {chapter_number}", next_chapter="next_c"
                ),
            ]
            if chapter_type != ChapterType.CONCLUSION
            else [],
        ),
    )


# Create a properly mocked AdventureState
def create_mock_state():
    # Create chapters 1 and 2 to simulate being on chapter 3
    mock_chapters = [
        create_mock_chapter(1, ChapterType.STORY),
        create_mock_chapter(2, ChapterType.STORY),
    ]

    # Create the state with the base required fields
    state = AdventureState(
        current_chapter_id="chapter_2_a",
        chapters=mock_chapters,
        story_length=10,
        planned_chapter_types=[
            ChapterType.STORY,
            ChapterType.STORY,
            ChapterType.LESSON,
            ChapterType.REASON,
            ChapterType.STORY,
            ChapterType.LESSON,
            ChapterType.STORY,
            ChapterType.STORY,
            ChapterType.STORY,
            ChapterType.CONCLUSION,
        ],
        current_storytelling_phase="Trials",
        selected_narrative_elements={
            "setting_types": "Hidden garden paths lit by luminescent flowers and tiny fireflies",
            "character_archetypes": "Mystical light-wielders who conjure living murals in midair",
            "story_rules": "Only those who share joy can unlock hidden festival secrets",
        },
        selected_theme="Finding beauty in unexpected places and little details",
        selected_moral_teaching="Sharing light with others illuminates everyone's path",
        selected_plot_twist="The festival's light comes from the joy of the participants, not the other way around",
        selected_sensory_details={
            "visuals": "Sparkling confetti bursts that shower the crowds in glittery rainbows",
            "sounds": "Steady beat of drums guiding the nightly color parade",
            "smells": "Fruity scents of color-themed sorbets melting under lantern glow",
        },
        metadata={},
    )

    # Add responses to the chapters to simulate progress
    state.chapters[0].response = StoryResponse(
        chosen_path="next_a", choice_text="Choice A for chapter 1"
    )

    state.chapters[1].response = StoryResponse(
        chosen_path="next_a", choice_text="Choice A for chapter 2"
    )

    return state


# Create a mock lesson question
mock_lesson_question: LessonQuestion = {
    "question": "What is the primary color of the sky during daytime?",
    "answers": [
        {"text": "Blue", "is_correct": True},
        {"text": "Green", "is_correct": False},
        {"text": "Yellow", "is_correct": False},
    ],
    "topic": "Nature",
    "subtopic": "Sky",
    "explanation": "The sky appears blue during the day due to a phenomenon called Rayleigh scattering.",
}

# Generate the prompt
state = create_mock_state()
prompt = build_user_prompt(state, mock_lesson_question)

# Print the prompt
print("\n=== GENERATED PROMPT ===\n")
print(prompt)
print("\n=== END OF PROMPT ===\n")

# Also test the system prompt
from app.services.llm.prompt_engineering import build_system_prompt

system_prompt = build_system_prompt(state)
print("\n=== SYSTEM PROMPT ===\n")
print(system_prompt)
print("\n=== END OF SYSTEM PROMPT ===\n")
