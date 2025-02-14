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
  - WebSocket synchronization
  - ChapterType enum support

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

### Testing Environment
- Automated story simulation
- State transition validation
- Cross-provider LLM testing
- WebSocket connection testing

## Technical Constraints

### State Management
- Complete state tracking required
- Real-time synchronization needed
- Recovery mechanisms essential
- Cross-provider compatibility

### LLM Integration
- Provider-agnostic implementation
- Response standardization
- Error handling requirements
- Rate limiting considerations

### Testing Requirements
- Automated story simulation
- State validation
- Flow verification
- Error checking

## External Dependencies

### LLM Providers
- OpenAI API integration
- Gemini API integration
- Provider abstraction layer
- Response standardization

### Testing Framework
- pytest for unit tests
- pytest-asyncio for async
- Story simulation framework
- State validation tools

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

### Story Flow
- Narrative preservation checks
- Lesson context verification
- Choice context validation
- State consistency checks

### State Management
- WebSocket monitoring
- State transition logging
- Recovery verification
- Error tracking

### LLM Integration
- Provider response logging
- Prompt verification
- Error case testing
- Performance monitoring

## Monitoring

### State Tracking
- WebSocket connection status
- State synchronization
- Recovery events
- Error rates

### Performance
- LLM response times
- State transition speed
- WebSocket latency
- Resource utilization

### Testing Metrics
- Story simulation success
- State validation results
- Provider compatibility
- Error recovery rates
