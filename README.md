# Interactive Educational Storytelling App

An AI-powered educational application that creates interactive, branching stories while seamlessly integrating learning objectives. Built with FastAPI and WebSockets, this application provides real-time story generation and educational content delivery through a state-managed architecture.

## Features

- Dynamic story generation with branching narratives
- Real-time story streaming via WebSockets
- Robust state management using Pydantic models
- LLM-agnostic architecture supporting multiple providers
- Educational content integration with progress tracking
- SQLAlchemy-based persistence layer
- Customizable story configurations (depth levels, narrative elements)

## Technical Architecture

### Core Components

1. **State Management**
   - `StoryState` Pydantic model for centralized state control
   - Tracks depth levels, node progression, and educational metrics
   - Maintains question history and correct answer counts

2. **WebSocket Integration**
   - Real-time story streaming
   - Async handlers for continuous story progression
   - Session management for story continuity

3. **LLM Integration**
   - Provider-agnostic architecture
   - Structured prompt engineering
   - Configurable story generation parameters

4. **Data Layer**
   - SQLAlchemy ORM for data persistence
   - YAML-based story configurations
   - CSV-based educational content mapping

## Prerequisites

- Python 3.11+
- FastAPI 0.105.0+
- OpenAI API key (or other supported LLM provider credentials)
- PostgreSQL (optional, for persistent storage)

## Setup

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file with required credentials:
   ```
   OPENAI_API_KEY=your_api_key_here
   DATABASE_URL=your_database_url  # Optional
   ```
5. Initialize the database:
   ```bash
   python -m app.init_data
   ```
6. Start the application:
   ```bash
   uvicorn app.main:app --reload
   ```

## Project Structure

```
app/
├── data/
│   ├── stories.yaml
│   └── lessons.csv
├── models/
│   ├── story.py
│   └── __init__.py
├── routers/
│   ├── web.py
│   └── websocket.py
├── services/
│   └── llm/
│       ├── providers/
│       ├── base.py
│       ├── providers.py
│       └── prompt_engineering.py
├── templates/
├── static/
├── database.py
├── init_data.py
└── main.py
```

## State Management

The application uses a centralized `StoryState` model that manages:
- Current node/scene identifiers
- Depth levels for story progression
- User choice history
- Educational metrics (correct answers, total questions)
- Question history with detailed tracking

## Development Guidelines

1. State Transformations
   - Keep all state mutations centralized
   - Use Pydantic models for data validation
   - Maintain clear separation between data and logic

2. LLM Integration
   - Follow the provider-agnostic architecture
   - Implement new providers through the base interface
   - Keep prompt engineering separate from business logic

3. Educational Content
   - Map content to story nodes via YAML configuration
   - Track learning progress through state management
   - Maintain separation between story flow and educational elements

## License

MIT License