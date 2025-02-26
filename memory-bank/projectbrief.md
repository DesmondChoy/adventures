# Project Brief: Learning Odyssey

## Overview
Learning Odyssey is an interactive educational platform that combines dynamic storytelling with structured learning through LLM-powered narrative experiences. The application creates personalized learning journeys where educational content and story-driven choices work together to create an immersive journey, culminating in satisfying narrative resolutions.

## Key Features and Objectives

1.  **State Management (`app/models/story.py`):**
    *   `AdventureState` as the single source of truth.
    *   WebSocket state synchronization.
    *   Dynamic adventure length via `state.story_length`.
    *   `ChapterType` enum (LESSON/STORY/CONCLUSION).
    *   Complete state serialization.
    *   Error recovery mechanisms.

2.  **LLM Integration (`app/services/llm/`):**
    *   Provider abstraction layer.
    *   OpenAI/Gemini compatibility.
    *   Prompt engineering system.
    *   Response standardization.
    *   Narrative resolution generation.

3.  **Content Flow (`app/services/chapter_manager.py`):**
    *   First two chapters: STORY type.
    *   Second-to-last chapter: STORY type.
    *   Last chapter: CONCLUSION type.
    *   50% of remaining chapters: LESSON type.
    *   LESSON chapters: `lessons.csv` + LLM.
    *   STORY chapters: Full LLM generation with choices.
    *   CONCLUSION chapters: Full LLM generation without choices.

4.  **System Architecture:**
    *   FastAPI/WebSocket backend.
    *   Real-time state updates.
    *   Story simulation framework.
    *   Error recovery system.
    *   Question availability validation.

5. **Project Goals:**
    * Personalized learning journeys.
    * Provider-agnostic LLM system.
    * Reliable state management.
    * Automated testing suite.
    * Dynamic content system.
    * Satisfying narrative arcs

## Success Criteria
1. Technical Requirements
   - Real-time state synchronization
   - Consistent chapter flow
   - Cross-provider LLM support
   - Comprehensive test coverage
   - Robust error handling

2. User Experience
   - Strong narrative opening
   - Engaging story progression
   - Meaningful choice impact
   - Effective learning integration
   - Satisfying story conclusions
   - Reliable error recovery
