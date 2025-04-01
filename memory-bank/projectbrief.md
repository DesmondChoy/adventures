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
2. User-selected topics and adventure length
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
- Provider abstraction layer (GPT-4o/Gemini compatibility)
- Standardized prompt engineering system
- Response formatting and validation
- Narrative generation with phase-specific guidance

### 3. Content Flow
- First chapter: STORY with agency choice
- Second-to-last chapter: STORY for pivotal choices
- Last chapter: CONCLUSION with resolution (no choices)
- After CONCLUSION: SUMMARY with statistics and chapter recaps
- 50% of remaining chapters: LESSON (educational content)
- 50% of LESSON chapters: REFLECT (follow LESSON chapters)
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
- Progressive enhancement (text first, images as available)
- Asynchronous image generation via Google Imagen
- React-based Summary Chapter
- Browser-based state persistence
- Robust error handling and recovery

## Success Criteria

### Technical Requirements
- Real-time state synchronization
- Consistent chapter flow
- Cross-provider LLM support
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