# Product Context

## Purpose
Learning Odyssey transforms traditional education into an engaging, personalized adventure by combining structured lessons with dynamic storytelling. The application creates a unique learning experience where educational content and narrative choices work together to create an immersive journey.

## Problem Space
Traditional educational platforms often lack:
- Dynamic content adaptation
- Engaging narrative integration
- Real-time interaction
- Personalized learning paths

Learning Odyssey solves these challenges through:
1. Pre-defined educational content (lessons.csv) with dynamic narrative delivery
2. User-selected topics and adventure length
3. LLM-generated narrative choices
4. Real-time state synchronization

## User Experience Flow

1. Initial Setup (`app/routers/web.py`)
   - Topic selection at landing page
   - Adventure length selection
   - ChapterManager determines sequence
   - First chapter enforced as LESSON type
   - Last chapter enforced as LESSON type

2. Adventure Progression (`app/services/chapter_manager.py`)
   - Chapter types follow MAX_LESSON_RATIO (40%)
   - LESSON chapters:
     - Questions from lessons.csv
     - LLM narrative wrapper
     - Answer impact on future chapters
   - STORY chapters:
     - Full LLM generation
     - Three narrative choices
     - Choice consequences

3. State Management
   - Real-time state synchronization
   - Narrative continuity enforcement
   - Progress tracking
   - Cross-provider LLM support

## Key Features

1. Content Management (`app/data/`)
   - Lesson database (lessons.csv)
   - Story templates (stories.yaml)
   - LLM narrative generation
   - No question repetition
   - Consequence system

2. Chapter Structure (`app/services/chapter_manager.py`)
   - First/last chapters: LESSON type
   - Middle chapters: MAX_LESSON_RATIO (40%)
   - Narrative continuity
   - Choice impact system

3. State Management (`app/models/story.py`)
   - AdventureState centralization
   - Real-time synchronization
   - Complete state tracking
   - Error recovery

## Success Metrics

1. Learning Effectiveness
   - LESSON response accuracy
   - Topic understanding
   - Knowledge progression
   - Content retention

2. User Engagement
   - Topic selection patterns
   - STORY choice diversity
   - Session completion rate
   - Return frequency

3. System Performance
   - Content generation speed
   - State sync reliability
   - Error recovery time
   - System uptime
