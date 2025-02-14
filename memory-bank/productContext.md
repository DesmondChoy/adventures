# Product Context

## Purpose
Learning Odyssey transforms traditional education into an engaging, personalized journey by combining structured lessons with dynamic storytelling. The application creates a unique learning experience where educational content and narrative choices alternate seamlessly.

## Problem Space
Traditional educational platforms often lack:
- Dynamic content adaptation
- Engaging narrative integration
- Real-time interaction
- Personalized learning paths

Learning Odyssey solves these challenges through:
1. Dynamic lesson sampling and answer shuffling
2. User-selected lesson topics at start
3. Choice-based narrative progression
4. Real-time state synchronization

## User Experience Flow

1. Initial Interaction
   - User selects lesson topic at landing page
   - First chapter is always a lesson type
   - Question dynamically sampled from selected topic
   - Answer options shuffled for engagement
   - Immediate feedback on answer selection

2. Story Progression
   - Subsequent chapters alternate between lessons and story
   - Story chapters offer narrative choices
   - Lesson chapters sample new questions
   - Answers always shuffled for interactivity
   - Dynamic story length adaptation

3. State Management
   - Real-time state synchronization
   - Consistent user progression tracking
   - Reliable state recovery
   - Cross-provider LLM support

## Key Features

1. Dynamic Question System
   - User-selected lesson topics
   - Random question sampling
   - Answer shuffling for engagement
   - No repeat questions in session
   - Immediate feedback

2. Chapter Flow
   - First chapter always lesson type
   - Alternating chapter types
   - Dynamic story length
   - Choice-based progression

3. State Handling
   - Centralized AdventureState management
   - WebSocket state synchronization
   - Provider-agnostic LLM integration
   - Robust error handling

## Success Metrics

1. Learning Effectiveness
   - Question response accuracy
   - Topic comprehension
   - Learning progression
   - Content retention

2. User Engagement
   - Initial topic selection
   - Answer attempt diversity
   - Session duration
   - Return frequency

3. Technical Performance
   - Question sampling speed
   - Answer shuffling reliability
   - State synchronization accuracy
   - System stability
