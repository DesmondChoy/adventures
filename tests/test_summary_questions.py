"""
Test script to verify educational questions and chapter summaries in the summary chapter.

This test specifically focuses on:
1. Ensuring that questions from lesson chapters are properly extracted and normalized
2. Verifying that the conclusion chapter is properly identified and included in summaries
3. Testing that even in edge cases like partial state, both questions and summaries are provided

Usage:
    python tests/test_summary_questions.py
"""

import os
import sys
import json
import asyncio
import logging
from typing import Dict, Any, List
from enum import Enum

# Add project root to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, ".."))
sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_summary_questions")

# Import the functions to test
from app.routers.summary_router import (
    extract_educational_questions,
    ensure_conclusion_chapter,
    extract_chapter_summaries,
    format_adventure_summary_data,
)
from app.models.story import AdventureState, ChapterData, ChapterType, StoryResponse, LessonResponse, StoryChoice, ChapterContent

# Create a mock ChapterType enum for testing
class MockChapterType(str, Enum):
    LESSON = "lesson"
    STORY = "story"
    CONCLUSION = "conclusion"
    REFLECT = "reflect"
    SUMMARY = "summary"

# Helper function to load test data
def load_test_data(file_path: str) -> Dict[str, Any]:
    """Load test data from a JSON file."""
    logger.info(f"Loading test data from {file_path}")
    with open(file_path, "r") as f:
        data = json.load(f)
    return data

async def test_extract_educational_questions():
    """Test the extract_educational_questions function with various inputs."""
    logger.info("\n=== Testing extract_educational_questions ===")
    
    # Create test cases with different chapter/question combinations
    test_cases = [
        # Test case 1: State with both lesson_questions and chapter questions
        {
            "name": "State with both lesson_questions and chapter questions",
            "lesson_questions": [
                {
                    "question": "Test question 1?",
                    "answers": [
                        {"text": "Correct answer", "is_correct": True},
                        {"text": "Wrong answer", "is_correct": False}
                    ],
                    "explanation": "This is the explanation."
                }
            ],
            "chapters": [
                {
                    "chapter_number": 1,
                    "chapter_type": MockChapterType.LESSON,
                    "content": "Chapter content",
                    "question": {
                        "question": "Chapter question?",
                        "answers": [
                            {"text": "Correct answer", "is_correct": True},
                            {"text": "Wrong answer", "is_correct": False}
                        ],
                        "explanation": "Explanation text"
                    },
                    "response": LessonResponse(
                        question={"question": "Chapter question?"},
                        chosen_answer="Correct answer",
                        is_correct=True
                    )
                }
            ],
            "expected_count": 1  # Should prioritize lesson_questions
        },
        # Test case 2: State with only chapter questions
        {
            "name": "State with only chapter questions",
            "lesson_questions": [],
            "chapters": [
                {
                    "chapter_number": 1,
                    "chapter_type": MockChapterType.LESSON,
                    "content": "Chapter content",
                    "question": {
                        "question": "Chapter question?",
                        "answers": [
                            {"text": "Correct answer", "is_correct": True},
                            {"text": "Wrong answer", "is_correct": False}
                        ],
                        "explanation": "Explanation text"
                    },
                    "response": LessonResponse(
                        question={"question": "Chapter question?"},
                        chosen_answer="Wrong answer",
                        is_correct=False
                    )
                }
            ],
            "expected_count": 1
        },
        # Test case 3: State with no questions but with lesson chapters
        {
            "name": "State with no questions but with lesson chapters",
            "lesson_questions": [],
            "chapters": [
                {
                    "chapter_number": 1,
                    "chapter_type": MockChapterType.LESSON,
                    "content": "Chapter content with no question",
                    "question": None,
                    "response": None
                }
            ],
            "expected_count": 1  # Should generate a fallback question
        },
        # Test case 4: State with no questions and no lesson chapters
        {
            "name": "State with no questions and no lesson chapters",
            "lesson_questions": [],
            "chapters": [
                {
                    "chapter_number": 1,
                    "chapter_type": MockChapterType.STORY,
                    "content": "Story content",
                    "question": None,
                    "response": None,
                    "chapter_content": {
                        "content": "Story content",
                        "choices": [
                            {"text": "Option 1", "next_chapter": "next1"},
                            {"text": "Option 2", "next_chapter": "next2"},
                            {"text": "Option 3", "next_chapter": "next3"}
                        ]
                    }
                }
            ],
            "expected_count": 1  # Should generate a fallback question
        }
    ]
    
    # Run each test case
    for i, test_case in enumerate(test_cases):
        logger.info(f"\nTest case {i+1}: {test_case['name']}")
        
        # Create a mock state object
        mock_state = AdventureState(
            current_chapter_id="test",
            lesson_questions=test_case["lesson_questions"],
            chapters=[]  # Will add chapters manually
        )
        
        # Add chapters to the state
        for chapter_data in test_case["chapters"]:
            # Create chapter content with appropriate choices
            if chapter_data["chapter_type"] == MockChapterType.STORY:
                choices = [
                    StoryChoice(text=f"Option {i+1}", next_chapter=f"next{i+1}")
                    for i in range(3)
                ]
            else:
                choices = []
                
            chapter_content = ChapterContent(
                content=chapter_data["content"],
                choices=choices
            )
            
            # Create a ChapterData object
            chapter = ChapterData(
                chapter_number=chapter_data["chapter_number"],
                content=chapter_data["content"],
                chapter_type=chapter_data["chapter_type"],
                question=chapter_data["question"],
                response=chapter_data["response"],
                chapter_content=chapter_content
            )
            mock_state.chapters.append(chapter)
        
        # Extract educational questions
        questions = extract_educational_questions(mock_state)
        
        # Verify the results
        logger.info(f"Extracted {len(questions)} questions, expected {test_case['expected_count']}")
        
        # Check that we have the expected number of questions
        assert len(questions) == test_case["expected_count"], f"Expected {test_case['expected_count']} questions, got {len(questions)}"
        
        # Check that each question has the required fields
        for q in questions:
            assert "question" in q, "Question is missing 'question' field"
            assert "userAnswer" in q, "Question is missing 'userAnswer' field"
            assert "isCorrect" in q, "Question is missing 'isCorrect' field"
            assert "explanation" in q, "Question is missing 'explanation' field"
            assert isinstance(q["isCorrect"], bool), "isCorrect should be a boolean"
            
            # If answer is incorrect, should have correctAnswer
            if not q["isCorrect"] and "correctAnswer" not in q:
                logger.warning(f"Question is incorrect but has no correctAnswer: {q}")
            
            logger.info(f"Question format correct: {q['question'][:30]}...")
    
    logger.info("\nExtract educational questions test: PASSED")

async def test_ensure_conclusion_chapter():
    """Test the ensure_conclusion_chapter function with various inputs."""
    logger.info("\n=== Testing ensure_conclusion_chapter ===")
    
    # Create test cases with different chapter configurations
    test_cases = [
        # Test case 1: State with an explicit CONCLUSION chapter
        {
            "name": "State with an explicit CONCLUSION chapter",
            "story_length": 10,
            "chapters": [
                {
                    "chapter_number": 1,
                    "chapter_type": MockChapterType.STORY,
                },
                {
                    "chapter_number": 10,
                    "chapter_type": MockChapterType.CONCLUSION,
                }
            ],
            "expected_conclusion_chapter": 10
        },
        # Test case 2: State with no explicit CONCLUSION chapter
        {
            "name": "State with no explicit CONCLUSION chapter",
            "story_length": 10,
            "chapters": [
                {
                    "chapter_number": 1,
                    "chapter_type": MockChapterType.STORY,
                },
                {
                    "chapter_number": 10,
                    "chapter_type": MockChapterType.STORY,
                }
            ],
            "expected_conclusion_chapter": 10
        },
        # Test case 3: State with only 9 chapters in a 10-chapter story
        {
            "name": "State with only 9 chapters in a 10-chapter story",
            "story_length": 10,
            "chapters": [
                {
                    "chapter_number": 1,
                    "chapter_type": MockChapterType.STORY,
                },
                {
                    "chapter_number": 9,
                    "chapter_type": MockChapterType.STORY,
                }
            ],
            "expected_conclusion_chapter": 9
        },
        # Test case 4: State with the last chapter in the middle (non-sequential)
        {
            "name": "State with the last chapter in the middle (non-sequential)",
            "story_length": 10,
            "chapters": [
                {
                    "chapter_number": 1,
                    "chapter_type": MockChapterType.STORY,
                },
                {
                    "chapter_number": 5,
                    "chapter_type": MockChapterType.STORY,
                },
                {
                    "chapter_number": 3,
                    "chapter_type": MockChapterType.STORY,
                }
            ],
            "expected_conclusion_chapter": 5
        }
    ]
    
    # Run each test case
    for i, test_case in enumerate(test_cases):
        logger.info(f"\nTest case {i+1}: {test_case['name']}")
        
        # Create a mock state object
        mock_state = AdventureState(
            current_chapter_id="test",
            story_length=test_case["story_length"],
            chapters=[]  # Will add chapters manually
        )
        
        # Add chapters to the state
        for chapter_data in test_case["chapters"]:
            # Create chapter content with appropriate choices
            if chapter_data["chapter_type"] == MockChapterType.STORY:
                choices = [
                    StoryChoice(text=f"Option {i+1}", next_chapter=f"next{i+1}")
                    for i in range(3)
                ]
            else:
                choices = []
                
            chapter_content = ChapterContent(
                content="Content",
                choices=choices
            )
            
            # Create a ChapterData object
            chapter = ChapterData(
                chapter_number=chapter_data["chapter_number"],
                content="Content",
                chapter_type=chapter_data["chapter_type"],
                question=None,
                response=None,
                chapter_content=chapter_content
            )
            mock_state.chapters.append(chapter)
        
        # Ensure conclusion chapter
        updated_state = ensure_conclusion_chapter(mock_state)
        
        # Find the CONCLUSION chapter
        conclusion_chapter = None
        for chapter in updated_state.chapters:
            if chapter.chapter_type == ChapterType.CONCLUSION:
                conclusion_chapter = chapter
                break
        
        # Verify the results
        assert conclusion_chapter is not None, "No CONCLUSION chapter found"
        assert conclusion_chapter.chapter_number == test_case["expected_conclusion_chapter"], \
            f"Expected conclusion chapter {test_case['expected_conclusion_chapter']}, got {conclusion_chapter.chapter_number}"
        
        logger.info(f"Conclusion chapter correctly identified as chapter {conclusion_chapter.chapter_number}")
    
    logger.info("\nEnsure conclusion chapter test: PASSED")

async def test_extract_chapter_summaries():
    """Test the extract_chapter_summaries function with various inputs."""
    logger.info("\n=== Testing extract_chapter_summaries ===")
    
    # Create test cases with different chapter configurations
    test_cases = [
        # Test case 1: State with existing chapter summaries
        {
            "name": "State with existing chapter summaries",
            "chapter_summaries": [
                "Summary for chapter 1.",
                "Summary for chapter 2."
            ],
            "summary_chapter_titles": [
                "Title for chapter 1",
                "Title for chapter 2"
            ],
            "chapters": [
                {
                    "chapter_number": 1,
                    "chapter_type": MockChapterType.STORY,
                    "content": "Content for chapter 1"
                },
                {
                    "chapter_number": 2,
                    "chapter_type": MockChapterType.CONCLUSION,
                    "content": "Content for chapter 2"
                }
            ],
            "expected_count": 2,
            "expected_types": ["story", "conclusion"]
        },
        # Test case 2: State with no existing summaries
        {
            "name": "State with no existing summaries",
            "chapter_summaries": [],
            "summary_chapter_titles": [],
            "chapters": [
                {
                    "chapter_number": 1,
                    "chapter_type": MockChapterType.STORY,
                    "content": "Content for chapter 1"
                },
                {
                    "chapter_number": 2,
                    "chapter_type": MockChapterType.LESSON,
                    "content": "Content for chapter 2"
                },
                {
                    "chapter_number": 3,
                    "chapter_type": MockChapterType.CONCLUSION,
                    "content": "Content for chapter 3"
                }
            ],
            "expected_count": 3,
            "expected_types": ["story", "lesson", "conclusion"]
        },
        # Test case 3: State with out-of-order chapters
        {
            "name": "State with out-of-order chapters",
            "chapter_summaries": [],
            "summary_chapter_titles": [],
            "chapters": [
                {
                    "chapter_number": 3,
                    "chapter_type": MockChapterType.STORY,
                    "content": "Content for chapter 3"
                },
                {
                    "chapter_number": 1,
                    "chapter_type": MockChapterType.STORY,
                    "content": "Content for chapter 1"
                },
                {
                    "chapter_number": 2,
                    "chapter_type": MockChapterType.CONCLUSION,
                    "content": "Content for chapter 2"
                }
            ],
            "expected_count": 3,
            "expected_types": ["story", "conclusion", "story"]  # In chapter_number order
        }
    ]
    
    # Run each test case
    for i, test_case in enumerate(test_cases):
        logger.info(f"\nTest case {i+1}: {test_case['name']}")
        
        # Create a mock state object
        mock_state = AdventureState(
            current_chapter_id="test",
            story_length=len(test_case["chapters"]),
            chapters=[],
            chapter_summaries=test_case["chapter_summaries"],
            summary_chapter_titles=test_case["summary_chapter_titles"]
        )
        
        # Add chapters to the state
        for chapter_data in test_case["chapters"]:
            # Create chapter content with appropriate choices
            if chapter_data["chapter_type"] == MockChapterType.STORY:
                choices = [
                    StoryChoice(text=f"Option {j+1}", next_chapter=f"next{j+1}")
                    for j in range(3)
                ]
            else:
                choices = []
                
            chapter_content = ChapterContent(
                content=chapter_data["content"],
                choices=choices
            )
            
            # Create a ChapterData object
            chapter = ChapterData(
                chapter_number=chapter_data["chapter_number"],
                content=chapter_data["content"],
                chapter_type=chapter_data["chapter_type"],
                question=None,
                response=None,
                chapter_content=chapter_content
            )
            mock_state.chapters.append(chapter)
        
        # Extract chapter summaries
        summaries = extract_chapter_summaries(mock_state)
        
        # Verify the results
        logger.info(f"Extracted {len(summaries)} summaries, expected {test_case['expected_count']}")
        
        # Check that we have the expected number of summaries
        assert len(summaries) == test_case['expected_count'], \
            f"Expected {test_case['expected_count']} summaries, got {len(summaries)}"
        
        # Check that each summary has the required fields
        for summary in summaries:
            assert "number" in summary, "Summary is missing 'number' field"
            assert "title" in summary, "Summary is missing 'title' field"
            assert "summary" in summary, "Summary is missing 'summary' field"
            assert "chapterType" in summary, "Summary is missing 'chapterType' field"
            
            logger.info(f"Summary {summary['number']}: type={summary['chapterType']}, title=\"{summary['title'][:30]}...\"")
        
        # Sort summaries by chapter number
        sorted_summaries = sorted(summaries, key=lambda s: s["number"])
        
        # Check chapter types
        for i, expected_type in enumerate(test_case["expected_types"]):
            actual_type = sorted_summaries[i]["chapterType"]
            assert actual_type == expected_type, \
                f"Expected chapter {i+1} to have type {expected_type}, got {actual_type}"
    
    logger.info("\nExtract chapter summaries test: PASSED")

async def test_format_adventure_summary_data():
    """Test the format_adventure_summary_data function with various inputs."""
    logger.info("\n=== Testing format_adventure_summary_data ===")
    
    # Create a complete mock state with all required components
    mock_state = AdventureState(
        current_chapter_id="test",
        story_length=3,
        chapters=[],
        chapter_summaries=[
            "Summary for chapter 1.",
            "Summary for chapter 2.",
            "Summary for chapter 3."
        ],
        summary_chapter_titles=[
            "Title for chapter 1",
            "Title for chapter 2",
            "Title for chapter 3"
        ],
        lesson_questions=[
            {
                "question": "Test question 1?",
                "answers": [
                    {"text": "Correct answer", "is_correct": True},
                    {"text": "Wrong answer", "is_correct": False}
                ],
                "explanation": "This is the explanation for question 1."
            },
            {
                "question": "Test question 2?",
                "answers": [
                    {"text": "Correct answer", "is_correct": True},
                    {"text": "Wrong answer", "is_correct": False}
                ],
                "explanation": "This is the explanation for question 2."
            }
        ]
    )
    
    # Add chapters to the state
    chapter_types = [MockChapterType.STORY, MockChapterType.LESSON, MockChapterType.CONCLUSION]
    for i in range(3):
        # Create chapter content with appropriate choices
        if chapter_types[i] == MockChapterType.STORY:
            choices = [
                StoryChoice(text=f"Option {j+1}", next_chapter=f"next{j+1}")
                for j in range(3)
            ]
        else:
            choices = []
            
        chapter_content = ChapterContent(
            content=f"Content for chapter {i+1}",
            choices=choices
        )
        
        # Create a ChapterData object
        chapter = ChapterData(
            chapter_number=i+1,
            content=f"Content for chapter {i+1}",
            chapter_type=chapter_types[i],
            question=None,
            response=None,
            chapter_content=chapter_content
        )
        # Add question to lesson chapter
        if i == 1:  # LESSON chapter
            chapter.question = {
                "question": f"Test question for chapter {i+1}?",
                "answers": [
                    {"text": "Correct answer", "is_correct": True},
                    {"text": "Wrong answer", "is_correct": False}
                ],
                "explanation": f"This is the explanation for chapter {i+1}."
            }
            chapter.response = LessonResponse(
                question=chapter.question,
                chosen_answer="Correct answer",
                is_correct=True
            )
        mock_state.chapters.append(chapter)
    
    # Format adventure summary data
    summary_data = format_adventure_summary_data(mock_state)
    
    # Verify the results
    logger.info(f"Formatted summary data with structure: {list(summary_data.keys())}")
    
    # Check that we have all required sections
    assert "chapterSummaries" in summary_data, "Missing 'chapterSummaries' section"
    assert "educationalQuestions" in summary_data, "Missing 'educationalQuestions' section"
    assert "statistics" in summary_data, "Missing 'statistics' section"
    
    # Check chapter summaries
    chapter_summaries = summary_data["chapterSummaries"]
    assert len(chapter_summaries) == 3, f"Expected 3 chapter summaries, got {len(chapter_summaries)}"
    
    # Verify that the last chapter is correctly identified as CONCLUSION
    last_summary = chapter_summaries[-1]
    assert last_summary["chapterType"] == "conclusion", \
        f"Expected last chapter to have type 'conclusion', got {last_summary['chapterType']}"
    
    # Check educational questions
    questions = summary_data["educationalQuestions"]
    assert len(questions) > 0, "No educational questions found"
    
    # Check that each question has the required fields
    for q in questions:
        assert "question" in q, "Question is missing 'question' field"
        assert "userAnswer" in q, "Question is missing 'userAnswer' field"
        assert "isCorrect" in q, "Question is missing 'isCorrect' field"
        assert "explanation" in q, "Question is missing 'explanation' field"
    
    # Check statistics
    statistics = summary_data["statistics"]
    assert "chaptersCompleted" in statistics, "Statistics missing 'chaptersCompleted'"
    assert "questionsAnswered" in statistics, "Statistics missing 'questionsAnswered'"
    assert "timeSpent" in statistics, "Statistics missing 'timeSpent'"
    assert "correctAnswers" in statistics, "Statistics missing 'correctAnswers'"
    
    logger.info("Statistics: " + ", ".join([f"{k}={v}" for k, v in statistics.items()]))
    logger.info("\nFormat adventure summary data test: PASSED")

async def main():
    """Run all tests."""
    try:
        await test_extract_educational_questions()
        await test_ensure_conclusion_chapter()
        await test_extract_chapter_summaries()
        await test_format_adventure_summary_data()
        
        logger.info("\n=== All tests PASSED ===")
    except AssertionError as e:
        logger.error(f"Test FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(2)

if __name__ == "__main__":
    asyncio.run(main())