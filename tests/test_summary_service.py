"""
Tests for the SummaryService class.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import logging
import json

from app.services.summary import (
    SummaryService, 
    StateNotFoundError, 
    SummaryError, 
    ChapterTypeHelper,
    AdventureSummaryDTO
)
from app.models.story import AdventureState, ChapterType, ChapterData, ChapterContent


@pytest.fixture
def mock_state_storage_service():
    """Fixture for mocking the StateStorageService."""
    mock_service = MagicMock()
    mock_service.get_state = AsyncMock()
    mock_service.store_state = AsyncMock(return_value="test-state-id")
    return mock_service


@pytest.fixture
def summary_service(mock_state_storage_service):
    """Fixture for creating a SummaryService with a mock StateStorageService."""
    return SummaryService(mock_state_storage_service)


@pytest.fixture
def sample_chapter():
    """Fixture for creating a sample ChapterData."""
    chapter_content = ChapterContent(
        content="Sample chapter content",
        choices=[]
    )
    
    return ChapterData(
        chapter_number=1,
        content="Sample chapter content",
        chapter_type=ChapterType.STORY,
        chapter_content=chapter_content
    )


@pytest.fixture
def sample_adventure_state(sample_chapter):
    """Fixture for creating a sample AdventureState."""
    state = AdventureState(
        current_chapter_id="test",
        story_length=10,
        chapters=[sample_chapter],
        chapter_summaries=["Chapter 1 summary"],
        summary_chapter_titles=["Chapter 1 Title"],
        lesson_questions=[{
            "question": "Test question?",
            "user_answer": "Test answer",
            "is_correct": True,
            "explanation": "Test explanation"
        }]
    )
    return state


class TestChapterTypeHelper:
    """Tests for the ChapterTypeHelper class."""
    
    def test_get_chapter_type_string_from_enum(self):
        """Test getting chapter type string from ChapterType enum."""
        assert ChapterTypeHelper.get_chapter_type_string(ChapterType.STORY) == "story"
        assert ChapterTypeHelper.get_chapter_type_string(ChapterType.LESSON) == "lesson"
        assert ChapterTypeHelper.get_chapter_type_string(ChapterType.CONCLUSION) == "conclusion"
    
    def test_get_chapter_type_string_from_string(self):
        """Test getting chapter type string from string."""
        assert ChapterTypeHelper.get_chapter_type_string("STORY") == "story"
        assert ChapterTypeHelper.get_chapter_type_string("Lesson") == "lesson"
        assert ChapterTypeHelper.get_chapter_type_string("conclusion") == "conclusion"
    
    def test_is_chapter_type(self):
        """Test checking if a chapter type matches a target type."""
        assert ChapterTypeHelper.is_chapter_type(ChapterType.STORY, ChapterType.STORY)
        assert ChapterTypeHelper.is_chapter_type("story", ChapterType.STORY)
        assert not ChapterTypeHelper.is_chapter_type(ChapterType.LESSON, ChapterType.STORY)
    
    def test_is_lesson_chapter(self):
        """Test checking if a chapter is a LESSON chapter."""
        assert ChapterTypeHelper.is_lesson_chapter(ChapterType.LESSON)
        assert ChapterTypeHelper.is_lesson_chapter("lesson")
        assert not ChapterTypeHelper.is_lesson_chapter(ChapterType.STORY)
    
    def test_is_conclusion_chapter(self):
        """Test checking if a chapter is a CONCLUSION chapter."""
        assert ChapterTypeHelper.is_conclusion_chapter(ChapterType.CONCLUSION)
        assert ChapterTypeHelper.is_conclusion_chapter("conclusion")
        assert not ChapterTypeHelper.is_conclusion_chapter(ChapterType.STORY)


class TestAdventureSummaryDTO:
    """Tests for the AdventureSummaryDTO class."""
    
    def test_to_dict(self):
        """Test conversion to dict."""
        dto = AdventureSummaryDTO(
            chapter_summaries=[{"number": 1, "title": "Test"}],
            educational_questions=[{"question": "Test?"}],
            statistics={"chapters_completed": 1}
        )
        
        result = dto.to_dict()
        assert "chapter_summaries" in result
        assert "educational_questions" in result
        assert "statistics" in result
        assert result["chapter_summaries"][0]["number"] == 1
    
    def test_to_camel_case(self):
        """Test conversion to camelCase."""
        dto = AdventureSummaryDTO(
            chapter_summaries=[{"number": 1, "chapter_type": "story"}],
            educational_questions=[{"user_answer": "Test"}],
            statistics={"chapters_completed": 1}
        )
        
        result = dto.to_camel_case()
        assert "chapterSummaries" in result
        assert "educationalQuestions" in result
        assert "statistics" in result
        assert "chapterType" in result["chapterSummaries"][0]
        assert "userAnswer" in result["educationalQuestions"][0]


class TestSummaryService:
    """Tests for the SummaryService class."""
    
    @pytest.mark.asyncio
    async def test_get_adventure_state_from_id_success(self, summary_service, mock_state_storage_service, sample_adventure_state):
        """Test successfully getting adventure state from ID."""
        # Arrange
        state_id = "test-state-id"
        mock_state_storage_service.get_state.return_value = {"test": "data"}
        
        # Mock AdventureStateManager
        with patch("app.services.summary_service.AdventureStateManager") as mock_state_manager_class:
            mock_state_manager = MagicMock()
            mock_state_manager.get_current_state.return_value = None
            mock_state_manager.reconstruct_state_from_storage.return_value = sample_adventure_state
            mock_state_manager_class.return_value = mock_state_manager
            
            # Act
            result = await summary_service.get_adventure_state_from_id(state_id)
            
            # Assert
            assert result == sample_adventure_state
            mock_state_storage_service.get_state.assert_called_once_with(state_id)
            mock_state_manager.reconstruct_state_from_storage.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_adventure_state_from_id_no_stored_state(self, summary_service, mock_state_storage_service):
        """Test getting adventure state when no stored state exists."""
        # Arrange
        state_id = "non-existent-id"
        mock_state_storage_service.get_state.return_value = None
        
        # Mock AdventureStateManager
        with patch("app.services.summary_service.AdventureStateManager") as mock_state_manager_class:
            mock_state_manager = MagicMock()
            mock_state_manager.get_current_state.return_value = None
            mock_state_manager_class.return_value = mock_state_manager
            
            # Act & Assert
            with pytest.raises(StateNotFoundError):
                await summary_service.get_adventure_state_from_id(state_id)
    
    def test_ensure_conclusion_chapter_no_chapters(self, summary_service):
        """Test ensuring conclusion chapter when there are no chapters."""
        # Arrange
        state = AdventureState(current_chapter_id="test", story_length=10, chapters=[])
        
        # Act
        result = summary_service.ensure_conclusion_chapter(state)
        
        # Assert
        assert result == state
        assert len(result.chapters) == 0
    
    def test_ensure_conclusion_chapter_already_has_conclusion(self, summary_service, sample_adventure_state, sample_chapter):
        """Test ensuring conclusion chapter when one already exists."""
        # Arrange
        conclusion_chapter = ChapterData(
            chapter_number=2,
            content="Conclusion content",
            chapter_type=ChapterType.CONCLUSION,
            chapter_content=ChapterContent(content="Conclusion content", choices=[])
        )
        sample_adventure_state.chapters.append(conclusion_chapter)
        
        # Act
        result = summary_service.ensure_conclusion_chapter(sample_adventure_state)
        
        # Assert
        assert len(result.chapters) == 2
        assert result.chapters[1].chapter_type == ChapterType.CONCLUSION
    
    def test_ensure_conclusion_chapter_sets_last_as_conclusion(self, summary_service, sample_adventure_state, sample_chapter):
        """Test ensuring conclusion chapter sets the last chapter as conclusion."""
        # Arrange
        last_chapter = ChapterData(
            chapter_number=2,
            content="Last chapter",
            chapter_type=ChapterType.STORY,
            chapter_content=ChapterContent(content="Last chapter", choices=[])
        )
        sample_adventure_state.chapters.append(last_chapter)
        
        # Act
        result = summary_service.ensure_conclusion_chapter(sample_adventure_state)
        
        # Assert
        assert len(result.chapters) == 2
        assert result.chapters[1].chapter_type == ChapterType.CONCLUSION
    
    def test_extract_chapter_summaries_with_existing_summaries(self, summary_service, sample_adventure_state):
        """Test extracting chapter summaries when they already exist."""
        # Act
        result = summary_service.extract_chapter_summaries(sample_adventure_state)
        
        # Assert
        assert len(result) == 1
        assert result[0]["number"] == 1
        assert result[0]["summary"] == "Chapter 1 summary"
        assert result[0]["title"] == "Chapter 1 Title"
        assert result[0]["chapter_type"] == "story"
    
    def test_extract_educational_questions_from_state(self, summary_service, sample_adventure_state):
        """Test extracting educational questions from state."""
        # Act
        result = summary_service.extract_educational_questions(sample_adventure_state)
        
        # Assert
        assert len(result) == 1
        assert result[0]["question"] == "Test question?"
        assert result[0]["user_answer"] == "Test answer"
        assert result[0]["is_correct"] is True
        assert result[0]["explanation"] == "Test explanation"
    
    def test_calculate_adventure_statistics(self, summary_service, sample_adventure_state):
        """Test calculating adventure statistics."""
        # Arrange
        questions = [{"is_correct": True}, {"is_correct": False}]
        
        # Act
        result = summary_service.calculate_adventure_statistics(sample_adventure_state, questions)
        
        # Assert
        assert result["chapters_completed"] == 1
        assert result["questions_answered"] == 2
        assert result["correct_answers"] == 1
        assert "time_spent" in result
    
    def test_format_adventure_summary_data(self, summary_service, sample_adventure_state):
        """Test formatting adventure summary data."""
        # Arrange
        with patch.object(summary_service, "extract_chapter_summaries") as mock_extract_summaries, \
             patch.object(summary_service, "extract_educational_questions") as mock_extract_questions, \
             patch.object(summary_service, "calculate_adventure_statistics") as mock_calculate_stats:
            
            mock_extract_summaries.return_value = [{"number": 1, "title": "Test"}]
            mock_extract_questions.return_value = [{"question": "Test?"}]
            mock_calculate_stats.return_value = {"chapters_completed": 1}
            
            # Act
            result = summary_service.format_adventure_summary_data(sample_adventure_state)
            
            # Assert
            assert "chapter_summaries" in result
            assert "educational_questions" in result
            assert "statistics" in result
            assert result["chapter_summaries"] == [{"number": 1, "title": "Test"}]
            assert result["educational_questions"] == [{"question": "Test?"}]
            assert result["statistics"] == {"chapters_completed": 1}
    
    @pytest.mark.asyncio
    async def test_store_adventure_state(self, summary_service, mock_state_storage_service):
        """Test storing adventure state."""
        # Arrange
        state_data = {
            "chapters": [],
            "chapter_summaries": [],
            "summary_chapter_titles": [],
            "lesson_questions": []
        }
        
        # Mock internal methods
        with patch.object(summary_service, "_process_chapter_summaries") as mock_process_summaries, \
             patch.object(summary_service, "_process_lesson_questions") as mock_process_questions:
            
            # Act
            result = await summary_service.store_adventure_state(state_data)
            
            # Assert
            assert result == "test-state-id"
            mock_state_storage_service.store_state.assert_called_once_with(state_data)
            assert not mock_process_summaries.called  # This isn't called because chapters is empty
            assert not mock_process_questions.called  # This isn't called because lesson_questions exists