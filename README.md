# Learning Odyssey

Where no two stories are ever the same. An AI-powered educational application that creates interactive, branching stories while seamlessly integrating learning objectives.

🚀 **[Try it live](https://learning-odyssey.up.railway.app/)**

## Key Features

- AI-powered interactive storytelling with real-time WebSocket streaming
- Educational content integration with progress tracking and session persistence
- Modern, responsive UI built with Tailwind CSS and vanilla JavaScript
- Production deployment on Railway with automatic scaling

## Technical Stack

### Backend
- FastAPI 0.115.8 with WebSocket support and SQLite database
- Provider-agnostic LLM architecture (currently supporting OpenAI 1.61.0)
- YAML-based story configurations and CSV-based lesson mapping

### Frontend
- Tailwind CSS for responsive design with vanilla JavaScript
- Session-based state management with WebSocket integration
- Interactive choice system with automatic progression

## Quick Start

1. Set up environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Configure and initialize:
   ```bash
   # Create .env file with:
   OPENAI_API_KEY=your_api_key_here
   DATABASE_URL=sqlite:///story_app.db  # For local development

   # Initialize database
   python -m app.init_data
   ```

3. Run the application:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. Deploy to Railway:
   - Fork this repository
   - Connect to Railway
   - Set environment variables
   - Deploy!

## Project Structure

```
app/
├── data/               # Story and lesson configurations
├── models/            # Pydantic models and state management
├── routers/           # Web and WebSocket endpoints
├── services/          # LLM integration and providers
├── templates/         # Frontend interface
└── main.py           # Application entry point
```

## State Management

### Backend
- Centralized `StoryState` model for story progression and metrics
- Educational content tracking and question history
- WebSocket-based state synchronization

### Frontend
- Session-based story persistence and choice history
- Real-time content streaming and formatting
- Error handling and connection recovery

## Development Guidelines

### Architecture
- Follow provider-agnostic LLM integration through `BaseLLMService`
- Maintain separation between story flow and educational content
- Use Pydantic models for data validation and state management

### UI/UX
- Implement progressive enhancement with graceful fallbacks
- Ensure consistent experience across sessions and refreshes
- Follow Tailwind CSS utility-first patterns

## License

MIT License
