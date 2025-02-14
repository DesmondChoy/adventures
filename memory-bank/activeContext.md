# Active Context

## Current Focus
The project is implementing core Learning Odyssey features with emphasis on adventure flow and content generation:

1. Adventure Flow Implementation
   - Landing page topic and length selection
   - Chapter type determination (ChapterManager)
   - Content source management:
     - Lesson Chapters: lessons.csv questions + LLM narrative wrapper
     - Story Chapters: Full LLM generation
   - Narrative continuity enforcement

2. Content Management
   - Lesson database (lessons.csv) integration
   - LLM narrative generation for both chapter types:
     - Lesson chapters: Contextual narrative around predefined questions
     - Story chapters: Complete narrative with choices
   - Story choice generation and validation
   - Consequence system implementation
   - History tracking

3. State Synchronization
   - Adventure progression tracking
   - Narrative continuity maintenance
   - WebSocket communication
   - Error handling

## Recent Changes
- Chapter type determination logic (40% max lessons)
- Content source integration (lessons.csv)
- LLM narrative generation system:
  * Lesson chapters require narrative context for questions
  * Story chapters have full narrative freedom
- Adventure state tracking enhancements
- Consequence system implementation
- Critical prompt debugging insight:
  * Perfect state management is useless if data isn't passed to prompt
  * Always verify what's actually in the prompt before assuming LLM guidance issues
  * Common issue: Optional parameters not being utilized

## Active Decisions

### Architecture
1. Content Flow
   - Lesson content:
     * Questions from lessons.csv
     * Narrative wrapper from LLM
     * Must maintain story continuity
   - Story content:
     * Full LLM generation
     * Three narrative choices
   - Track chapter outcomes
   - Maintain narrative continuity

2. State Management
   - Adventure history tracking
   - Choice/answer recording
   - Progress monitoring
   - Error recovery

3. Testing Approach
   - Content integration validation
   - Narrative generation verification
   - State consistency checks
   - Error scenario coverage
   - Prompt data flow validation

### Implementation
1. Initial Experience
   - Topic selection UI
   - Question sampling logic
   - Answer shuffling algorithm
   - Feedback mechanism
   - State updates

2. Flow Control
   - First chapter enforcement (lesson type with narrative)
   - Dynamic sampling
   - Answer randomization
   - Progress tracking
   - Error handling

3. Validation
   - Topic selection
   - Question sampling
   - Answer shuffling
   - State consistency
   - Error recovery
   - Prompt data completeness

## Current Considerations

### Technical
1. Question Handling
   - Sampling efficiency
   - Shuffle reliability
   - Duplicate prevention
   - Error cases

2. State Management
   - History tracking
   - Selection validation
   - Progress monitoring
   - Recovery procedures

3. Testing
   - Flow validation
   - State verification
   - Error coverage
   - Performance metrics
   - Prompt data verification

### Product
1. User Experience
   - Topic selection
   - Question presentation within narrative
   - Answer interaction
   - Feedback clarity

2. Learning
   - Question relevance
   - Answer effectiveness
   - Progress visibility
   - Engagement metrics

3. System
   - Response times
   - State reliability
   - Error handling
   - Recovery procedures
   - Prompt data flow

## Next Steps

### Immediate
1. Testing
   - Question sampling tests
   - Shuffle validation
   - State verification
   - Error scenarios
   - Prompt data validation

2. Implementation
   - Topic selection refinement
   - Sampling optimization
   - Shuffle improvements
   - Error handling
   - Prompt data flow fixes

3. Documentation
   - Flow documentation
   - State management
   - Testing procedures
   - Error handling
   - Prompt debugging guide

### Short Term
1. Features
   - Enhanced sampling
   - Improved shuffling
   - Better feedback
   - Error recovery
   - Robust prompt data flow

2. Testing
   - Comprehensive scenarios
   - Performance metrics
   - Error coverage
   - State validation
   - Prompt completeness checks

3. Documentation
   - System architecture
   - Flow patterns
   - Testing guides
   - Recovery procedures
   - Prompt debugging procedures
