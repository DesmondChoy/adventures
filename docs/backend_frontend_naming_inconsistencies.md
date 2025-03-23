# Backend to Frontend Naming Inconsistencies

## Context

The Learning Odyssey application uses a Python FastAPI backend with a React frontend. The backend primarily uses snake_case naming conventions (typical for Python), while the frontend uses camelCase (typical for JavaScript/React). This document identifies the naming inconsistencies between these two systems and how they're currently handled.

### Current Implementation Flow

1. **Backend State Management**:
   - The `AdventureState` model in `app/models/story.py` defines the core data structure using snake_case
   - Data is processed and transformed in various functions in `app/routers/summary_router.py`
   - The API endpoint `/adventure/api/adventure-summary` returns data to the React frontend

2. **Frontend Consumption**:
   - The React app expects data in camelCase format
   - Components in the React app consume this data and display it to users
   - The frontend is built and served from `app/static/summary-chapter/`

### Data Structure Comparison

Below is a detailed comparison of the data structures at different stages of the process:

#### Chapter Summaries

**1. Backend AdventureState (snake_case):**
```python
# In AdventureState (app/models/story.py)
chapter_summaries: List[str] = [
    "In this chapter, the hero encountered a mysterious forest...",  # Chapter 1
    "The journey continued as our hero learned about...",           # Chapter 2
    # ... more chapter summaries
]

summary_chapter_titles: List[str] = [
    "Chapter 1: The Beginning",
    "Chapter 2: The Journey",
    # ... more chapter titles
]
```

**2. API Response (camelCase):**
```json
"chapterSummaries": [
    {
        "number": 1,
        "title": "Chapter 1: The Beginning",
        "summary": "In this chapter, the hero encountered a mysterious forest...",
        "chapterType": "story"
    },
    {
        "number": 2,
        "title": "Chapter 2: The Journey",
        "summary": "The journey continued as our hero learned about...",
        "chapterType": "lesson"
    }
]
```

**3. Frontend Consumption (camelCase):**
```javascript
// In React component
chapterSummaries.map((chapter) => (
    <ChapterCard
        number={chapter.number}
        title={chapter.title}
        summary={chapter.summary}
        chapterType={chapter.chapterType}
    />
))
```

#### Educational Questions

**1. Backend AdventureState (snake_case):**
```python
# In AdventureState (app/models/story.py)
lesson_questions: List[Dict[str, Any]] = [
    {
        "question": "What is the capital of France?",
        "answers": [
            {"text": "London", "is_correct": False},
            {"text": "Paris", "is_correct": True},
            {"text": "Berlin", "is_correct": False}
        ],
        "chosen_answer": "Paris",
        "is_correct": True,
        "explanation": "Paris is the capital and largest city of France."
    }
]
```

**2. API Response (camelCase):**
```json
"educationalQuestions": [
    {
        "question": "What is the capital of France?",
        "userAnswer": "Paris",
        "isCorrect": true,
        "explanation": "Paris is the capital and largest city of France."
    },
    {
        "question": "Which planet is known as the Red Planet?",
        "userAnswer": "Venus",
        "isCorrect": false,
        "explanation": "Mars is known as the Red Planet due to its reddish appearance.",
        "correctAnswer": "Mars"
    }
]
```

**3. Frontend Consumption (camelCase):**
```javascript
// In React component
educationalQuestions.map((question) => (
    <QuestionCard
        question={question.question}
        userAnswer={question.userAnswer}
        isCorrect={question.isCorrect}
        explanation={question.explanation}
        correctAnswer={question.correctAnswer}
    />
))
```

#### Statistics

**1. Backend Calculation (snake_case):**
```python
# In calculate_adventure_statistics() function
statistics = {
    "chapters_completed": len(state.chapters),
    "questions_answered": total_questions,
    "time_spent": time_spent,
    "correct_answers": correct_answers
}
```

**2. API Response (camelCase):**
```json
"statistics": {
    "chaptersCompleted": 10,
    "questionsAnswered": 3,
    "timeSpent": "30 mins",
    "correctAnswers": 2
}
```

**3. Frontend Consumption (camelCase):**
```javascript
// In React component
<StatisticCard title="Chapters Completed" value={statistics.chaptersCompleted} />
<StatisticCard title="Questions Answered" value={statistics.questionsAnswered} />
<StatisticCard title="Time Spent" value={statistics.timeSpent} />
<StatisticCard title="Correct Answers" value={statistics.correctAnswers} />
```

## Identified Inconsistencies

### 1. Snake Case vs. Camel Case Field Names

| Backend (Snake Case) | Frontend (Camel Case) | Handling Function |
|----------------------|----------------------|-------------------|
| `chapter_summaries` | `chapterSummaries` | `format_adventure_summary_data()` |
| `chosen_answer` | `userAnswer` | `extract_educational_questions()` |
| `is_correct` | `isCorrect` | `extract_educational_questions()` |
| `correct_answer` | `correctAnswer` | `extract_educational_questions()` |
| `chapter_type` | `chapterType` | `extract_chapter_summaries()` |
| `chapters_completed` | `chaptersCompleted` | `calculate_adventure_statistics()` |
| `questions_answered` | `questionsAnswered` | `calculate_adventure_statistics()` |
| `correct_answers` | `correctAnswers` | `calculate_adventure_statistics()` |
| `time_spent` | `timeSpent` | `calculate_adventure_statistics()` |

### 2. Field Name Differences (Beyond Case)

| Backend Field | Frontend Field | Handling Function |
|---------------|---------------|-------------------|
| `chosen_answer` | `userAnswer` | `extract_educational_questions()` |
| `lesson_questions` | `educationalQuestions` | `format_adventure_summary_data()` |

### 3. Consistent Field Names (Same in Both)

| Field Name | Used In |
|------------|---------|
| `question` | Both backend and frontend |
| `explanation` | Both backend and frontend |
| `number` | Both backend and frontend (for chapter summaries) |
| `title` | Both backend and frontend (for chapter summaries) |
| `summary` | Both backend and frontend (for chapter summaries) |

## Current Handling Approaches

### 1. Explicit Field Renaming in API Response

The most common approach is explicit field renaming when creating the API response objects:

```python
# In extract_educational_questions() (app/routers/summary_router.py)
question_obj = {
    "question": question_text,
    "userAnswer": user_answer,  # Renamed from chosen_answer
    "isCorrect": is_correct,    # Case changed from is_correct
    "explanation": explanation
}

# Add correct answer if the user was wrong
if not is_correct:
    question_obj["correctAnswer"] = correct_answer  # Case changed from correct_answer
```

### 2. Direct Camel Case Usage in Python

In some cases, particularly in the `calculate_adventure_statistics()` function, camelCase is used directly in the Python code:

```python
# In calculate_adventure_statistics() (app/routers/summary_router.py)
statistics = {
    "chaptersCompleted": len(state.chapters),  # Direct camelCase in Python
    "questionsAnswered": total_questions,      # Direct camelCase in Python
    "timeSpent": time_spent,                   # Direct camelCase in Python
    "correctAnswers": correct_answers          # Direct camelCase in Python
}
```

### 3. Conversion in Multiple Places

The conversion from snake_case to camelCase happens in multiple functions:

- `extract_chapter_summaries()`
- `extract_educational_questions()`
- `calculate_adventure_statistics()`
- `format_adventure_summary_data()`

This approach works but lacks centralization, which could lead to inconsistencies or maintenance challenges.

## Potential Solutions

### 1. Centralized Conversion Utility

Create a utility function that automatically converts between snake_case and camelCase:

```python
def to_camel_case(snake_str):
    """Convert a snake_case string to camelCase."""
    components = snake_str.split('_')
    return components[0] + ''.join(x.title() for x in components[1:])

def snake_to_camel_dict(d):
    """Recursively convert all keys in a dictionary from snake_case to camelCase."""
    if not isinstance(d, dict):
        return d
    
    result = {}
    for key, value in d.items():
        # Skip keys that start with underscore (private attributes)
        if isinstance(key, str) and not key.startswith('_'):
            camel_key = to_camel_case(key)
            
            # Handle nested dictionaries and lists
            if isinstance(value, dict):
                result[camel_key] = snake_to_camel_dict(value)
            elif isinstance(value, list):
                result[camel_key] = [
                    snake_to_camel_dict(item) if isinstance(item, dict) else item 
                    for item in value
                ]
            else:
                result[camel_key] = value
        else:
            # Keep the key as is if it's not a string or starts with underscore
            result[key] = value
    
    return result
```

### 2. Standardize on One Convention

Choose one convention (likely camelCase for API responses) and ensure all data follows this convention at the API boundary:

```python
@router.get("/api/adventure-summary")
async def get_adventure_summary(state_id: Optional[str] = None):
    # ... existing code ...
    
    # Format the adventure state data
    summary_data = format_adventure_summary_data(adventure_state)
    
    # Convert all keys from snake_case to camelCase
    camel_case_data = snake_to_camel_dict(summary_data)
    
    return camel_case_data
```

### 3. Use FastAPI's Response Models

Define Pydantic models with field aliases to handle the conversion automatically:

```python
from pydantic import BaseModel, Field

class EducationalQuestion(BaseModel):
    question: str
    user_answer: str = Field(alias="userAnswer")
    is_correct: bool = Field(alias="isCorrect")
    explanation: str
    correct_answer: Optional[str] = Field(default=None, alias="correctAnswer")
    
    class Config:
        populate_by_name = True
        allow_population_by_field_name = True
```

## Recommendation

The recommended approach is to implement a centralized conversion utility that can be applied consistently at the API boundary. This would:

1. Allow backend code to use snake_case consistently (following Python conventions)
2. Ensure frontend receives camelCase consistently (following JavaScript conventions)
3. Reduce manual field mapping and potential for errors
4. Improve maintainability by centralizing the conversion logic
5. Make it easier to add new fields in the future

This approach respects the conventions of each language while providing a clean, consistent interface between them.
