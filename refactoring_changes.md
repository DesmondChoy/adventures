# Refactoring Changes Reference

## app/models/story.py Changes
### Class Renames
- `StoryNode` → `ChapterContent`
- `ChoiceHistory` → `StoryResponse`
- `QuestionHistory` → `LessonResponse`
- `StoryState` → `AdventureState`

### Field Renames
- `next_node` → `next_chapter` (in `StoryChoice`)
- `node_id` → `chosen_path` (in `StoryResponse`)
- `display_text` → `choice_text` (in `StoryResponse`)
- `was_correct` → `is_correct` (in `LessonResponse`)
- `current_node` → `current_chapter_id` (in `AdventureState`)

### Property Renames
- `chapter` → `current_chapter_number`
- `correct_answers` → `correct_lesson_answers`
- `total_questions` → `total_lessons`
- `history` → `story_choices`
- `question_history` → `lesson_responses`
- `previous_content` → `previous_chapter_content`

### Type System Improvements
1. Added `ChapterType` enum:
   ```python
   class ChapterType(str, Enum):
       LESSON = "lesson"
       STORY = "story"
   ```
   Replaces string literals `"lesson"` and `"story"`

2. Added type hints:
   - Method parameters and return types
   - Validator methods
   - Helper methods

### Code Structure Improvements
1. Added helper methods in `AdventureState`:
   ```python
   def _is_lesson_response(self, chapter: ChapterData) -> bool
   def _is_story_response(self, chapter: ChapterData) -> bool
   ```

2. Improved validation logic:
   - Better variable names (`v` → `chapters`)
   - Extracted complex conditions
   - Added explicit type checking
   - Enhanced chapter validation against story_length
   - Added clear validation error messages

3. Enhanced lesson history handling:
   - Removed conditional check for multiple lessons
   - Show all previous lessons in history
   - Consistent history display for both lesson and story chapters
   - Improved narrative continuity

### String Literal Changes
- `"lesson"` → `ChapterType.LESSON`
- `"story"` → `ChapterType.STORY`

### Model Structure
```python
# Core Models
ChapterType (Enum)
  - LESSON
  - STORY

StoryChoice
  - text: str
  - next_chapter: str

StoryResponse
  - chosen_path: str
  - choice_text: str

ChapterContent
  - content: str
  - choices: List[StoryChoice]

LessonResponse
  - question: Dict[str, Any]
  - chosen_answer: str
  - is_correct: bool

ChapterData
  - chapter_number: int
  - content: str
  - chapter_type: ChapterType
  - response: Optional[Union[StoryResponse, LessonResponse]]

AdventureState
  - current_chapter_id: str
  - chapters: List[ChapterData]
  - story_length: int
```

### Key Validation Rules
1. Story chapters must have exactly 3 choices
2. Chapter numbers must be sequential starting from 1
3. Chapter numbers must be positive
4. Choices list cannot be empty
5. Total chapters cannot exceed story_length (default: 3, range: 3-7)
6. Chapter sequence must match expected range (1 to N)

### Type Checking Notes
- Added `type: ignore[union-attr]` for response access in properties
- Added `type: ignore[misc]` for list comprehensions with type narrowing

### Migration Steps
1. Replace string literals with `ChapterType` enum
2. Update field names in all references
3. Update property names in all references
4. Add type hints to method parameters
5. Update validation logic to use new helper methods
6. Update any serialization/deserialization code to handle renamed fields

## app/services/llm/prompt_engineering.py Changes
### Architecture Changes
1. Removed odd/even chapter logic in favor of explicit chapter types:
   - Removed all logic based on chapter numbers being odd/even
   - Now using `ChapterType.LESSON` and `ChapterType.STORY` for explicit chapter type checking
   - Simplified chapter type determination in `build_user_prompt`

2. Simplified state management:
   - Removed redundant state checks
   - Simplified `is_opening` logic to use `state.current_chapter_number == 1`
   - Consolidated chapter state handling in `_build_base_prompt`

### Type System Improvements
1. Added return type annotation for `_build_base_prompt`:
   ```python
   def _build_base_prompt(state: AdventureState) -> tuple[str, str]
   ```

2. Added explicit type hints for collections:
   ```python
   chapter_history: list[str] = []
   ```

3. Added type annotation for loop variables:
   ```python
   for chapter in state.chapters:  # type: ChapterData
   ```

4. Added `LessonQuestion` TypedDict:
   ```python
   class LessonQuestion(TypedDict):
       question: str
       answers: List[Dict[str, Any]]  # List of {text: str, is_correct: bool}
   ```

### Terminology Standardization
1. Changed labels in prompts for consistency:
   - "Educational Progress" → "Lesson Progress"
   - "Q{i}" → "Lesson {i}"
   - "educational question" → "lesson question"
   - "questions answered correctly" → "lessons answered correctly"

2. Updated function and variable names:
   - `_format_educational_answers` → `_format_lesson_answers`
   - All references to "educational" changed to "lesson" in function names and comments
   - Standardized terminology in prompt templates and instructions

### Prompt Structure Improvements
1. Reorganized prompt building:
   - Separated base prompt logic from chapter-specific prompts
   - Improved chapter history formatting with clear separators
   - Added explicit handling for lesson and story responses

2. Enhanced lesson history formatting:
   - Added clear lesson numbering
   - Improved display of correct/incorrect answers
   - Better formatting for multi-lesson history

### Code Cleanup
1. Removed unused variables:
   - Removed `qa_index` variable from `_build_base_prompt`
   - Cleaned up unused imports

2. Simplified conditional logic:
   - Removed redundant checks in `build_user_prompt`
   - Streamlined chapter type determination
   - Simplified lesson history handling

### Type Safety Improvements
1. Added explicit type casting for response objects:
   ```python
   lesson_response = cast(LessonResponse, chapter.response)
   story_response = cast(StoryResponse, chapter.response)
   ```

2. Improved null safety:
   - Added proper null checks for optional parameters
   - Better handling of optional lesson questions
   - Safer access to response properties

### Frontend Integration Notes
1. Response format changes:
   - Lesson progress now shows "X/Y lessons answered correctly"
   - Consistent lesson numbering format throughout the UI
   - Standardized terminology for frontend display

2. State handling changes:
   - Simplified chapter type determination affects frontend routing
   - Clearer distinction between lesson and story chapters
   - More predictable state transitions

3. Prompt structure changes:
   - Choice format remains strictly consistent for frontend parsing
   - Lesson question format standardized for UI display
   - Clear separation between content and interaction elements 

## app/routers/websocket.py Changes

### State Management Improvements
1. AdventureState Initialization:
   - State now initialized using AdventureState Pydantic model with required `current_chapter_id` and `story_length`
   - Chapters list managed through AdventureState.chapters: List[ChapterData]
   - All state access now uses AdventureState's properties and validators

2. Chapter Type Determination:
   - Chapter types read from story_config["chapter_types"] array in stories.yaml
   - Types converted to ChapterType enum (LESSON or STORY)
   - Validation through ChapterData.chapter_type field validator

3. Response Handling:
   - Responses stored in ChapterData.response as Union[StoryResponse, LessonResponse]
   - StoryResponse contains chosen_path and choice_text
   - LessonResponse contains question dict, chosen_answer, and is_correct
   - Validation through ChapterData's Pydantic model

4. History Management:
   - Previous lessons accessed through AdventureState.chapters filtering
   - Each chapter's data stored in ChapterData Pydantic model
   - Question history filtered using: `[ch for ch in state.chapters if ch.type == ChapterType.LESSON]`
   - Responses accessed through ChapterData.response field

### Content Generation
1. Choice Generation:
   - Story choices created as List[StoryChoice] in ChapterContent
   - next_chapter IDs generated using chapter numbers from state.chapters.length
   - Story chapters require exactly 3 choices (validated in ChapterContent)
   - Lesson choices generated from question["answers"] with correct/wrong paths

2. Question Management:
   - Questions excluded using chapter response data: 
     ```python
     exclude_questions=[
         ch.response.question["question"]
         for ch in state.chapters
         if ch.type == ChapterType.LESSON
     ]
     ```
   - Questions stored in LessonResponse.question field
   - Validation through LessonResponse Pydantic model

### WebSocket Communication
1. State Synchronization:
   - Client state updated with complete AdventureState serialization
   - Chapter updates include full ChapterData model fields
   - Choices serialized from ChapterContent.choices list
   - All models use Pydantic's .dict() for serialization

2. Message Structure:
   - "chapter_update" message includes:
     ```python
     {
         "type": "chapter_update",
         "state": {
             "current_chapter_id": str,
             "current_chapter": ChapterData.dict(),
             "choices": List[StoryChoice.dict()]
         }
     }
     ```
   - "story_complete" includes full state with stats from AdventureState properties

### Architecture Improvements
1. Model-Driven Design:
   - All state managed through Pydantic models:
     - AdventureState: Top-level state container
     - ChapterData: Individual chapter state
     - ChapterContent: Chapter content and choices
     - StoryResponse/LessonResponse: User interactions

2. Type Safety:
   - ChapterType enum enforced through Pydantic validators
   - Response types validated through Union type hints
   - Model fields validated through Pydantic field validators

### Migration Notes
1. Client Updates Required:
   - Handle new state structure matching AdventureState model
   - Process ChapterData format for chapter updates
   - Update choice handling to match StoryChoice model

2. Configuration Requirements:
   - stories.yaml must include chapter_types array matching ChapterType enum values
   - Chapter sequence must match AdventureState.story_length
   - All responses must match either StoryResponse or LessonResponse models 