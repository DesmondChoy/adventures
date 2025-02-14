# Project Brief: Learning Odyssey

## Overview
Learning Odyssey is an interactive educational platform that combines dynamic storytelling with structured learning through LLM-powered narrative experiences. The application creates personalized learning journeys where each chapter alternates between lessons and story-driven choices.

## Core Requirements

1. State Management
   - Centralized `AdventureState` in `app/models/story.py`
   - Complete state synchronization via WebSocket
   - Dynamic story length handling via `state.story_length`
   - Chapter type management using `ChapterType` enum

2. LLM Integration
   - Provider-agnostic implementation
   - Cross-provider compatibility (OpenAI and Gemini)
   - Robust prompt engineering in `prompt_engineering.py`
   - Abstract provider differences in service layer

3. Story & Lesson Flow
   - First chapter always lesson type with dynamic question sampling
   - Alternating lesson and story chapters
   - Dynamic question sampling and answer shuffling
   - Choice-based narrative progression

4. System Architecture
   - FastAPI backend with WebSocket support
   - Real-time state synchronization
   - Automated story flow testing
   - Comprehensive error handling

## Project Goals
1. Create engaging, personalized learning experiences
2. Maintain provider-agnostic LLM integration
3. Ensure robust state management and synchronization
4. Provide automated testing and validation
5. Enable dynamic content adaptation

## Success Criteria
- Seamless state synchronization
- Consistent story and lesson flow
- Provider-independent LLM operation
- Comprehensive test coverage
- Automated story flow validation
- Real-time user interaction handling
