# Project Brief: Learning Odyssey

## Overview
Learning Odyssey is an interactive educational platform that combines dynamic storytelling with structured learning through LLM-powered narrative experiences. The application creates personalized learning journeys where educational content and story-driven choices work together to create an immersive journey, culminating in satisfying narrative resolutions.

## Key Features and Objectives

1. **State Management (`app/models/story.py`):**
   * `AdventureState` as the single source of truth
   * WebSocket state synchronization
   * Dynamic adventure length via `state.story_length`
   * `ChapterType` enum (LESSON/STORY/REFLECT/CONCLUSION)
   * Complete state serialization
   * Error recovery mechanisms
   * Metadata tracking for agency and story elements

2. **LLM Integration (`app/services/llm/`):**
   * Provider abstraction layer
   * GPT-4o/Gemini compatibility
   * Streamlined prompt engineering system
   * Response standardization
   * Narrative resolution generation
   * Phase-specific guidance for plot development

3. **Content Flow (`app/services/chapter_manager.py`):**
   * First chapter: STORY type with agency choice
   * Second-to-last chapter: STORY type
   * Last chapter: CONCLUSION type
   * 50% of remaining chapters, rounded down: LESSON type
   * 50% of LESSON chapters, rounded down: REFLECT chapters
   * REFLECT chapters only occur immediately after a LESSON chapter
   * STORY chapters must follow REFLECT chapters
   * LESSON chapters: `lessons.csv` + LLM with Story Object Method
   * STORY chapters: Full LLM generation with three choices
   * REFLECT chapters: Narrative-driven reflection on previous LESSON
   * CONCLUSION chapters: Full LLM generation without choices

4. **Agency System:**
   * First chapter choice from four categories (items, companions, roles, abilities)
   * AI-generated images for agency choices
   * Agency evolution throughout the adventure
   * Pivotal role in climax phase
   * Meaningful resolution in conclusion

5. **System Architecture:**
   * FastAPI/WebSocket backend
   * Real-time state updates
   * Story simulation framework
   * Error recovery system
   * Question availability validation
   * Asynchronous image generation
   * Progressive enhancement (text first, images as available)

6. **Project Goals:**
   * Personalized learning journeys
   * Provider-agnostic AI integration
   * Reliable state management
   * Automated testing suite
   * Dynamic content system
   * Satisfying narrative arcs

## Success Criteria
1. Technical Requirements
   * Real-time state synchronization
   * Consistent chapter flow
   * Cross-provider LLM support
   * Comprehensive test coverage
   * Robust error handling
   * Graceful degradation for image generation

2. User Experience
   * Strong narrative opening with agency choice
   * Engaging story progression
   * Meaningful choice impact
   * Effective learning integration
   * Satisfying story conclusions
   * Reliable error recovery
   * Visual representation of agency choices
