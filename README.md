# Learning Odyssey

An AI-powered interactive storytelling app where every journey is unique. Seamlessly blend narrative adventures with educational content.

🚀 **[Try it live](https://learning-odyssey.up.railway.app/)**

- Real-time WebSocket communication
- Structured logging system
- AI/LLM integration (Multi-provider support: OpenAI, Google Gemini)
- Modern web interface with dynamic loading
- Middleware stack for request tracking and logging

## Tech Stack

- **Backend**: FastAPI, Python 3.x
- **Frontend**: HTML, CSS, WebSocket
- **Database**: SQLAlchemy with SQLite
- **AI Integration**: 
  - OpenAI GPT-4o
  - Google Gemini
- **Logging**: Structured logging with JSON format

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
├── routers/            # API routes and WebSocket handlers
├── services/           # Business logic and LLM services
├── middleware/         # Custom middleware components
├── templates/          # HTML templates
├── static/             # Static assets (CSS, JS)
└── utils/              # Utility functions
```

## Development

- Run tests: `pytest`
- View logs: Check `logs/app.log`
- Development server runs on `http://localhost:8000`
