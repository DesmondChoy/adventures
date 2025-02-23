# Learning Odyssey

This app aims to promote learning and curiosity by weaving together educational content and engaging narratives. 

🚀 **[Try it live](https://learning-odyssey.up.railway.app/)**


## How It Works

1. **Educational Journey**
   - Choose your setting, lesson topic and adventure length
   - Every adventure is unique and choices (story paths or correct/incorrect answers) affects the narrative
   - Characters in the story encourage curiousity and learning
   - WIP: Users can upload their own settings and/or lesson topics.

2. **Technical Innovation**
   - LLM-powered dynamic storytelling
   - Real-time WebSocket state management
   - Provider-agnostic AI integration
   - Robust error recovery system

## Tech Stack

- **Backend**: FastAPI, Python 3.x
  - Real-time WebSocket communication
  - Structured logging system
  - Middleware stack for request tracking
  - State management and synchronization

- **AI Integration**: 
  - Provider-agnostic implementation with GPT-4o / Gemini support

- **Architecture**:
  - WebSocket for real-time updates
  - SQLAlchemy with SQLite
  - Modern web interface
  - Comprehensive error handling

## Setup

1. Clone the repository
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   .\venv\Scripts\activate  # Windows
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Create a `.env` file with required environment variables:
   ```
   # Choose one of these API keys based on your preferred provider
   OPENAI_API_KEY=your_openai_key
   GOOGLE_API_KEY=your_google_key
   ```
5. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```

## Project Structure

```
app/
├── main.py             # Application entry point
├── models/            
│   └── story.py       # State management and data models
├── routers/           
│   ├── web.py         # Web routes
│   └── websocket.py   # WebSocket handlers
├── services/          
│   ├── chapter_manager.py  # Content flow control
│   └── llm/           # LLM integration services
├── data/              
│   ├── lessons.csv    # Educational content
│   └── new_stories.yaml   # Story templates
├── middleware/         # Custom middleware components
├── templates/          # HTML templates
├── static/            # Static assets (CSS, JS)
└── utils/             # Utility functions
```

The project structure reflects our focus on:
- Clear separation of concerns
- Modular component design
- Maintainable codebase
- Scalable architecture

## Testing

- **Story Simulation Framework**:
  - Automated adventure progression with random choices
  - Comprehensive DEBUG-level logging for validation
  - Real-time WebSocket communication testing
  - Robust error handling with retry mechanisms