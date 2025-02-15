# Project Brief: Learning Odyssey

## Overview
Learning Odyssey is an interactive educational platform that combines dynamic storytelling with structured learning through LLM-powered narrative experiences. The application creates personalized learning journeys where each chapter alternates between lessons and story-driven choices.

## Core Requirements

1. State Management (`app/models/story.py`)
   - AdventureState as single source of truth
   - WebSocket state synchronization
   - Dynamic length via state.story_length
   - ChapterType enum (LESSON/STORY)

2. LLM Integration (`app/services/llm/`)
   - Provider abstraction layer
   - OpenAI/Gemini compatibility
   - Prompt engineering system
   - Response standardization

3. Content Flow (`app/services/chapter_manager.py`)
   - First/last chapters: LESSON type
   - Middle chapters: MAX_LESSON_RATIO (40%)
   - LESSON chapters: lessons.csv + LLM
   - STORY chapters: Full LLM generation

4. System Architecture
   - FastAPI/WebSocket backend
   - Real-time state updates
   - Story simulation framework
   - Error recovery system

## Project Goals
1. Personalized learning journeys
2. Provider-agnostic LLM system
3. Reliable state management
4. Automated testing suite
5. Dynamic content system

## Success Criteria
1. Technical Requirements
   - Real-time state synchronization
   - Consistent LESSON/STORY flow
   - Cross-provider LLM support
   - Comprehensive test coverage

2. User Experience
   - Engaging narrative continuity
   - Meaningful choice impact
   - Effective learning integration
   - Reliable error recovery
