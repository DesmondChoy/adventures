# Technical Context

## Technology Stack

### Backend
- **Framework**: FastAPI
  - Async WebSocket support
  - Type safety with Pydantic
  - Real-time state synchronization
  - Automated testing integration

- **State Management**: AdventureState
  - Centralized in `models/story.py`
  - Complete state tracking
  - Question data persistence
  - WebSocket synchronization
  - ChapterType enum support
  - Response handling
  - Error recovery
  - Metadata tracking for element consistency
  - Plot twist phase guidance

- **Language**: Python 3.x
  - Type hints throughout
  - Async/await for WebSocket
  - Provider-agnostic design
  - Automated testing support

### Dependencies
```
fastapi==0.104.1
uvicorn==0.24.0
websockets==12.0
pydantic==2.5.2
sqlalchemy==2.0.23
pyyaml==6.0.1
python-dotenv==1.0.0
pytest==7.4.3
pytest-asyncio==0.21.1
```

## Development Setup

### Environment Requirements
1. Python 3.x installation
2. Virtual environment
3. Dependencies installed via pip
4. LLM provider credentials configured
5. Test environment setup

### Local Development
1. Start server:
   ```bash
   uvicorn app.main:app --reload
   ```
2. Access endpoints:
   - Web: http://localhost:8000
   - WebSocket: ws://localhost:8000/ws
3. Run tests:
   ```bash
   python -m pytest tests/
   ```

### Testing Environment (`tests/simulations/`)
- Story simulation framework (`story_simulation.py`):
  * Primary purpose: Generate test data and logs
  * Random adventure progression
  * Comprehensive DEBUG level logging
  * WebSocket communication validation
  * Error handling and retry logic
  * Test data generation for validation
- State transition validation:
  * AdventureState consistency
  * WebSocket synchronization
  * Recovery mechanism testing
  * Error boundary validation
  * Comprehensive log generation
  * Element consistency validation
  * Plot twist progression testing
- LLM provider compatibility:
  * OpenAI/Gemini cross-testing
  * Response format validation
  * Error handling verification
  * Rate limiting compliance
- WebSocket connection testing:
  * Connection stability
  * State synchronization
  * Error recovery
  * Performance metrics

## Technical Considerations
- **State Management (`app/models/story.py`):** 
  * Real-time WebSocket synchronization
  * Complete state serialization
  * Story length constraints (5-10 chapters)
  * Error recovery system
  * Critical state preservation during client updates:
    - Narrative elements (setting, characters, rules)
    - Sensory details (visuals, sounds, smells)
    - Theme and moral lesson
    - Plot twist and phase guidance
    - Metadata for consistency tracking
  * URL parameters handling:
    - `story_category` and `lesson_topic` passed via URL
    - Not included in `validated_state`
    - Used for initial state setup only

- **LLM Integration (`app/services/llm/`):** 
  * Provider abstraction layer
  * Response standardization
  * Rate limiting implementation
  * Error handling system
  * State handling requirements:
    - Must pass complete AdventureState to build_system_prompt
    - Direct attribute access for prompt construction
    - Story config used only for initial setup
  * Enhanced features:
    - Phase-specific plot twist guidance
    - Element consistency validation
    - Narrative continuity enforcement

- **Story Elements (`app/services/chapter_manager.py`):** 
  * Comprehensive element selection and validation
  * Metadata tracking for consistency
  * Phase-specific plot twist guidance
  * Enhanced error handling with proper recovery mechanisms

## External Dependencies

### LLM Providers (`app/services/llm/providers.py`)
- OpenAI API client
- Gemini API client
- Provider interface
- Response mapping

### Testing Framework (`tests/`)
- pytest (unit tests):
  * Component isolation
  * Mocked dependencies
  * Error scenarios
  * Edge cases
  * Element consistency validation
- pytest-asyncio (async):
  * WebSocket operations
  * LLM service calls
  * State synchronization
  * Timeout handling
- story_simulation.py:
  * End-to-end testing
  * Adventure progression
  * Content validation
  * Error recovery
  * Plot twist progression validation
- State validation:
  * Serialization
  * Persistence
  * Recovery
  * Consistency
  * Element tracking
  * Metadata validation

## Development Tools

### Required
- Python 3.x
- pip package manager
- Git version control
- VS Code with extensions
- LLM provider accounts

### Recommended
- WebSocket client
- SQLite browser
- API testing tools
- Logging tools

## Monitoring

### System Health
- WebSocket connections
- State synchronization
- LLM availability
- Error frequency
- Element consistency

### Performance Metrics
- Response latency
- State update speed
- Content generation time
- Error recovery time
- Metadata tracking overhead

### Testing Coverage
- Story simulations
- State transitions
- Provider compatibility
- Error scenarios
- Element consistency
- Plot twist progression
