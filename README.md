# Learning Odyssey

This app aims to promote learning and curiosity by weaving together educational content and engaging narratives. 

🚀 **[Try it live](https://learning-odyssey.up.railway.app/)**


## How It Works

1. **Educational Journey**
   - Choose your setting and lesson topic
   - Every adventure is unique and choices (story paths or correct/incorrect answers) affects the narrative
   - Characters in the story encourage curiosity and learning
   - Make a pivotal agency choice in the first chapter that evolves throughout your journey
   - See visual representations of your agency choices through AI-generated images
   - WIP: Users can upload their own settings and/or lesson topics.

2. **Technical Innovation**
   - LLM-powered dynamic storytelling with agency system and AI-generated images
   - Real-time WebSocket state management with robust error recovery and connection handling
   - Provider-agnostic AI integration with standardized configuration
   - Advanced narrative techniques (Story Object Method, phase-specific guidance, plot twist development)
   - Comprehensive state tracking with client-side persistence and metadata management

## Architecture Overview

```mermaid
graph TD
    Client[Web Client] <--> WSR[WebSocket Router]
    WSR <--> WSS[WebSocket Service]
    WSS <--> ASM[Adventure State Manager]
    ASM <--> AS[AdventureState]
    ASM <--> CM[Chapter Manager]
    CM <--> LLM[LLM Service]
    CM <--> DB[(Database)]
    WSS <--> IMG[Image Generation Service]

    subgraph Client Side
        LP[localStorage] <--> CSM[Client State Manager]
        CSM <--> Client
    end

    subgraph Core State
        AS
    end

    subgraph Services
        WSS
        ASM
        CM
        LLM
        IMG
    end

    subgraph Routing
        WSR
    end

    subgraph Content Sources
        CSV[lessons.csv] --> CM
        LLM --> CM
        IMG --> WSS
    end
```

## Tech Stack

- **Backend**: FastAPI, Python 3.x with WebSocket communication, structured logging, and middleware for request tracking
- **AI Integration**: Provider-agnostic implementation supporting GPT-4o/Gemini for text and Gemini Imagen for image generation
- **Architecture**: Real-time WebSocket updates, SQLite database, comprehensive error handling, and asynchronous processing
- **Frontend**: Modular CSS organization, 3D carousel with animations, responsive design, word-by-word content streaming with Markdown support, and progressive enhancement for images

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
   # API key for LLM and image generation (both use the same key with Google)
   GOOGLE_API_KEY=your_google_key
   # Or alternatively use OpenAI for LLM (image generation still requires Google)
   OPENAI_API_KEY=your_openai_key
   ```
5. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```

## Project Structure

```
app/
├── main.py                        # Application entry point
├── models/            
│   └── story.py                   # State management and data models
├── routers/           
│   ├── web.py                     # Web routes
│   └── websocket_router.py        # WebSocket routing and connection management
├── services/          
│   ├── adventure_state_manager.py # State management and validation
│   ├── chapter_manager.py         # Content flow control
│   ├── image_generation_service.py # AI image generation for agency choices
│   ├── websocket_service.py       # WebSocket business logic
│   └── llm/                       # LLM integration with prompt engineering
├── data/              
│   ├── lessons.csv                # Educational content
│   └── new_stories.yaml           # Story templates and elements
├── middleware/                    # Custom middleware components
├── templates/                     # HTML templates
├── static/
│   ├── css/
│   │   ├── typography.css         # Typography system
│   │   ├── theme.css              # Color variables and theme
│   │   └── carousel.css           # 3D carousel component
│   └── images/                    # Static assets
└── utils/                         # Utility functions
```

The project structure reflects our focus on:
- Clear separation of concerns
- Modular component design
- Maintainable codebase
- Scalable architecture

## Testing

The project includes a comprehensive testing framework focused on end-to-end validation:

- **Simulation Framework**: Automated adventure progression with random choices, comprehensive logging, and standardized prefixes for parsing (`CHAPTER_TYPE`, `CHOICE`, `LESSON`, `STATS`)
- **Test Coverage**: Functionality testing (chapter sequences, lesson ratios, state transitions) and error handling (detection, recovery, logging)
- **Running Tests**: Simple command-line interface with options for full workflow, specific story/topic testing, or analysis of existing logs

```bash
# Run the complete workflow (server, simulation, tests)
python tests/simulations/run_simulation_tests.py
```


## Technical Constraints

Learning Odyssey faces unique caching constraints due to its sequential storytelling nature. Each chapter requires the prior chapter to be complete before it can be generated, as the narrative builds upon previous events and choices. This means the entire adventure must be generated sequentially in real-time, with no ability to pre-cache future content. While theoretically possible to pre-generate all possible branches, this approach quickly becomes impractical as the adventure length and number of choices increase—each additional choice point exponentially multiplies the number of possible paths. Since each user's path through the story is unique based on their choices and educational responses, the system cannot feasibly pre-generate all potential outcomes, making traditional caching approaches ineffective.

To address these sequential generation challenges, we've implemented several solutions. Client-side state persistence using localStorage maintains the complete chapter history and user choices, ensuring continuity even during connection issues. Our connection management system employs exponential backoff (1s to 30s) with automatic state restoration to maintain the narrative flow. For error recovery, we prioritize preserving the user's progress and implement graceful degradation with fallbacks for features like image generation, ensuring the educational journey can continue even when certain components encounter issues.
