# Architectural Decisions

## Caching Constraints

### Why Traditional Caching Won't Work
Our story generation system has fundamental constraints that make traditional caching approaches (like those used in e-readers or video streaming) ineffective:

1. **LLM-Dependent Content Generation**
```mermaid
flowchart TD
    A[User Makes Choice] --> B[Send to Server]
    B --> C[LLM Generates Next Chapter]
    C --> D[Based on:]
    D --> E[Previous Chapters]
    D --> F[User's Choice]
    D --> G[Story Context]
    D --> H[Educational Goals]
```

**Key Constraints:**
- Each chapter requires real-time LLM generation
- Content depends on previous chapters and choices
- Cannot pre-generate or predict next chapters
- Must maintain server connection for content generation

2. **Dynamic Content Requirements**
```mermaid
flowchart TD
    A[Story State] --> B{Chapter Type}
    B -->|LESSON| C[Adapt to User's Understanding]
    B -->|STORY| D[React to Previous Choices]
    B -->|CONCLUSION| E[Wrap Up All Threads]
    C --> F[Cannot Cache]
    D --> F
    E --> F
```

**Key Constraints:**
- Story progression is choice-dependent
- Each choice affects subsequent chapter content
- Educational content adapts to user responses
- State must be maintained server-side

3. **State Dependencies**
```mermaid
flowchart TD
    A[Chapter Generation] --> B[Requires:]
    B --> C[Complete History]
    B --> D[User Choices]
    B --> E[Learning Progress]
    B --> F[Story Elements]
    B --> G[Plot Development]
```

**Key Constraints:**
- Each new chapter depends on complete history
- Cannot predict which path user will choose
- Must track educational progress
- Need to maintain narrative consistency

### What We Can Do Instead

1. **State Persistence**
```mermaid
flowchart TD
    A[Client State] --> B[localStorage]
    B --> C[Stores:]
    C --> D[Chapter History]
    C --> E[User Choices]
    C --> F[Learning Progress]
    C --> G[Story Elements]
```

2. **Connection Management**
```mermaid
flowchart TD
    A[Connection Lost] --> B[Save State]
    B --> C[Attempt Reconnect]
    C -->|Success| D[Resume from Last State]
    C -->|Fail| E[Retry with Backoff]
```

3. **Error Recovery**
```mermaid
flowchart TD
    A[Error Occurs] --> B[Save Progress]
    B --> C[Attempt Recovery]
    C -->|Success| D[Resume Story]
    C -->|Fail| E[Show Clear Message]
```

## Implementation Impact

### Client-Side
- Must maintain complete state history
- Cannot rely on caching for content
- Need robust connection management
- Must handle reconnection gracefully

### Server-Side
- Must maintain session state
- Cannot pre-generate content
- Need efficient state restoration
- Must validate restored state

### User Experience
- Cannot work offline
- Must handle connection drops
- Need clear error messages
- Should attempt silent recovery

## Future Considerations

1. **Connection Quality Management**
- Monitor connection strength
- Warn before likely disconnections
- Save state more frequently when connection weak

2. **HTTP Fallback**
- Consider HTTP fallback for critical operations
- Maintain at least basic functionality
- Ensure state consistency

3. **Progressive Enhancement**
- Start with basic functionality
- Add features based on connection
- Maintain core story experience
