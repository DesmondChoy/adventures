# Project Brief: Learning Odyssey

## Overview
Learning Odyssey is an interactive educational platform that combines dynamic storytelling with structured learning through LLM-powered narrative experiences. The application creates personalized learning journeys that integrate educational content with user-driven story choices, culminating in satisfying narrative resolutions.

## Problem Space
Traditional educational platforms often lack:
- Dynamic content adaptation
- Engaging narrative integration
- Real-time interaction
- Personalized learning paths

Learning Odyssey solves these challenges through:
1. Pre-defined educational content with dynamic narrative delivery
2. User-selected story worlds and lesson topics within a fixed 10-chapter flow
3. LLM-generated narrative choices and resolutions
4. Real-time state synchronization
5. Agency system with meaningful character choices

## Key Features

### 1. State Management System
- `AdventureState` as the single source of truth
- WebSocket state synchronization
- Dynamic chapter flow via `state.story_length` and `state.planned_chapter_types`
- Comprehensive serialization and recovery

### 2. LLM Integration
- Explicit use-case routing: GPT-5.6 Luna for story and image-scene text,
  Gemini Flash Lite for support tasks
- OpenAI Responses structured outputs for chapter narrative and choice fields
- Pydantic validation with up to three generation attempts
- Standardized prompt engineering with phase-specific narrative guidance

### 3. Content Flow
- First chapter: STORY with agency choice
- Second-to-last chapter: STORY for pivotal choices
- Last chapter: CONCLUSION with resolution (no choices)
- After CONCLUSION: SUMMARY with statistics and chapter recaps
- Exactly three LESSON chapters and one REFLECT chapter in each 10-chapter plan
- REFLECT chapters only after LESSON chapters
- STORY chapters must follow REFLECT chapters

### 4. Agency System
- First chapter choice from four categories (items, companions, roles, abilities)
- AI-generated images for agency choices
- Agency evolution throughout the adventure
- Pivotal role in climax phase
- Meaningful resolution in conclusion

### 5. Technical Architecture
- FastAPI backend with WebSocket real-time communication
- Structured chapter generation before word-by-word delivery; images remain
  progressive enhancements
- Asynchronous image generation via Gemini 3.1 Flash Image (Nano Banana 2) with square 1K output
- React-based Summary Chapter
- Browser state plus server-authoritative Supabase persistence, retryable saves,
  and visible terminal save failures
- Sticky reader header with chapter progress and responsive context ticker
- Robust error handling and recovery

## Core Development Principles

- **Dynamic Content Integrity:** Narrative content is AI-generated and variable. Application logic and tests MUST NOT hardcode narrative elements. Rely on state structure (`AdventureState`), metadata, and defined types (`ChapterType`) for validation and control. Handle narrative content as dynamic data flowing through a defined structure.

## Success Criteria

### Technical Requirements
- Real-time state synchronization
- Consistent chapter flow
- Provider-specific LLM routing with validated output contracts
- Comprehensive test coverage
- Robust error handling
- Graceful degradation

### User Experience
- Strong narrative opening with agency choice
- Engaging story progression with meaningful choice impact
- Effective educational integration through narrative wrapper
- Satisfying conclusions with agency resolution
- Comprehensive summary chapter
- Reliable error recovery
- Visual representation through AI-generated images
- Word-by-word streaming for natural reading
- Responsive design for desktop and mobile
- Persistent state across sessions
