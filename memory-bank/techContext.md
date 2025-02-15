# Technical Context

## Technology Stack

### Backend
- **Framework**: FastAPI
  - Async WebSocket support
  - Type safety with Pydantic
  - Real-time state synchronization
  - Automated testing integration

- **State Management**: AdventureState
  - Centralized in models/story.py
  - Complete state tracking
  - Question data persistence
  - WebSocket synchronization
  - ChapterType enum support
  - Response handling
  - Error recovery

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
- Story simulation framework (story_simulation.py):
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

## Technical Constraints

### State Management (`app/models/story.py`)
- AdventureState as single source of truth
- Real-time WebSocket synchronization
- Complete state serialization
- Error recovery system

### LLM Integration (`app/services/llm/`)
- Provider abstraction layer
- Response standardization
- Rate limiting implementation
- Error handling system

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
- State validation:
  * Serialization
  * Persistence
  * Recovery
  * Consistency

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

## Debugging Tools

### Story Flow (`app/services/chapter_manager.py`)
- ChapterType validation
- Content source verification
- Narrative continuity checks
- State transition logging

### State Management (`app/models/story.py`)
- WebSocket monitoring
- State serialization checks
- Recovery validation
- Error tracking

### Content Flow (`app/services/chapter_manager.py`)
- LESSON/STORY validation
- Content sampling verification
- Response validation
- Performance monitoring

### LLM Integration (`app/services/llm/`)
- Provider response logging
- Prompt verification
- Error tracking
- Performance metrics

## Monitoring

### System Health
- WebSocket connections
- State synchronization
- LLM availability
- Error frequency

### Performance Metrics
- Response latency
- State update speed
- Content generation time
- Error recovery time

### Testing Coverage
- Story simulations
- State transitions
- Provider compatibility
- Error scenarios
