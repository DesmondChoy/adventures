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
1. Pre-defined educational content (`lessons.csv`) with dynamic narrative delivery
2. User-selected topics and adventure length
3. LLM-generated narrative choices and resolutions
4. Real-time state synchronization
5. Consistent story elements and plot development

## User Experience and Features

1. **Initial Setup (`app/routers/web.py`):**
   - Users select a topic and adventure length on the landing page
   - `ChapterManager` determines the chapter sequence
   - The first two chapters are always STORY type for world-building
   - The last chapter is always CONCLUSION type for resolution

2. **Content Delivery (`app/services/websocket_service.py`):**
   - Word-by-word streaming creates natural reading experience
   - Markdown formatting enhances text presentation:
     * Emphasis for important concepts
     * Strong emphasis for key points
     * Code blocks for technical content
   - Controlled pacing through timing delays:
     * Brief pauses between words
     * Longer pauses between paragraphs
   - Real-time rendering with proper formatting

3. **Interactive Elements:**
   - Dynamic choice presentation
   - Real-time progress tracking
   - Immediate feedback on selections
   - Smooth transitions between chapters
   - Clean state management

4. **Adventure Progression (`app/services/chapter_manager.py`):**
    *   Chapter types follow a specific sequence:
        *   First two chapters: STORY (setting/character development)
        *   Second-to-last chapter: STORY (pivotal choices)
        *   Last chapter: CONCLUSION (satisfying resolution)
        *   Remaining chapters: 50% LESSON (subject to available questions)
    *   **LESSON chapters:**
        *   Use questions from `lessons.csv`.
        *   Incorporate an LLM-generated narrative wrapper.
        *   Answers impact future chapters.
    *   **STORY chapters:**
        *   Fully LLM-generated.
        *   Include three narrative choices.
        *   Choices have consequences.
        *   Plot twist elements evolve naturally.
    *   **CONCLUSION chapter:**
        *   Fully LLM-generated.
        *   No choices are required.
        *   Resolves all plot threads.
        *   Provides a "Return to Landing Page" option.

5.  **Content Management (`app/data/`):**
    *   Utilizes a lesson database (`lessons.csv`).
    *   Uses story templates (`new_stories.yaml`).
    *   Generates narratives using LLM.
    *   Ensures no question repetition.
    *   Implements a consequence system.
    *   Story elements management:
        *   Non-random elements (name, description, tone)
        *   Random narrative and sensory elements
        *   Phase-specific plot twist development
        *   Element consistency tracking
        *   Enhanced error validation

6.  **Chapter Structure (`app/services/chapter_manager.py`):**
    *   Optimized for engagement and learning:
        *   Strong opening with two STORY chapters.
        *   Balanced LESSON distribution.
        *   Climactic choice near the end.
        *   Satisfying CONCLUSION.
    *   Maintains narrative continuity.
    *   Implements a choice impact system.
    *   Plot twist progression:
        *   Subtle hints in early phases
        *   Building tension in middle phases
        *   Full revelation in climax phase

7.  **State Management (`app/models/story.py`):**
    *   Centralized `AdventureState`.
    *   Real-time synchronization.
    *   Complete state tracking.
    *   Error recovery.
    *   Cross-provider LLM support.
    *   Metadata tracking:
        *   Element consistency
        *   Plot twist development
        *   Story phase guidance
        *   Enhanced validation
