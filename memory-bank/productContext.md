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
3. LLM-generated narrative choices and resolutions
4. Real-time state synchronization

## User Experience Flow

1. Initial Setup (`app/routers/web.py`)
   - Topic selection at landing page
   - Adventure length selection
   - ChapterManager determines sequence
   - First two chapters: Always STORY for world-building
   - Last chapter: Always CONCLUSION for resolution

2. Adventure Progression (`app/services/chapter_manager.py`)
   - Chapter types follow new sequencing:
     - First two chapters: STORY (setting/character development)
     - Second-to-last chapter: STORY (pivotal choices)
     - Last chapter: CONCLUSION (satisfying resolution)
     - Remaining chapters: 50% LESSON (subject to available questions)
   - LESSON chapters:
     - Questions from lessons.csv
     - LLM narrative wrapper
     - Answer impact on future chapters
   - STORY chapters:
     - Full LLM generation
     - Three narrative choices
     - Choice consequences
   - CONCLUSION chapter:
     - Full LLM generation
     - No choices required
     - Resolves all plot threads
     - Return to Landing Page option

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
   - Optimized for engagement and learning:
     * Strong opening with two STORY chapters
     * Balanced LESSON distribution
     * Climactic choice near the end
     * Satisfying CONCLUSION
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
