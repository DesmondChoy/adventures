# Learning Odyssey: Where Adventure Ignites Lifelong Learning

**Learning Odyssey is revolutionizing education by merging the immersive power of AI-driven storytelling with deeply personalized learning.** We create uniquely engaging experiences for children that traditional methods can't match, tackling the critical challenge of student disengagement and fostering a genuine love for knowledge through compelling narrative arcs and reflective learning.

🚀 **[Try it live!](https://learning-odyssey.up.railway.app/)**

## Your Epic Journey Starts Here: How It Works

Imagine an education that feels like your favorite adventure game, complete with rising action, pivotal choices, and a satisfying resolution. That's Learning Odyssey.

1.  **Launch Your Quest:** Choose a captivating story world – from mystical forests to ancient mountains – and select an educational topic you're curious about, like the wonders of the human body or the secrets of farm animals.
2.  **Define Your Destiny:** Early in your adventure, you'll make a pivotal **Agency** choice. Will you wield a unique magical artifact, gain a loyal fantastical companion, master an extraordinary skill, or step into a heroic role? This choice becomes your signature, evolving with you and unlocking new possibilities as your story unfolds.
3.  **Shape Your Story:** Your decisions are the compass guiding your narrative. Every choice you make, every challenge you overcome, directly influences the path ahead as the **plot deepens, leading to unique turning points, a thrilling climax, and a satisfying conclusion** to your unique tale.
4.  **Learn Without Limits:** Educational concepts are seamlessly woven into the fabric of your adventure. Characters you meet will spark your curiosity, and challenges will test your knowledge in fun, interactive ways. The journey includes **dedicated REFLECT chapters, prompting deeper thought** on what you've learned.
5.  **See Your World Come Alive:** AI-generated images bring characters, breathtaking scenes, and your evolving Agency to life with stunning, consistent visuals that adapt to your story.
6.  **Adventure on Your Terms:** Life is an adventure too! Pause your quest at any time and resume your learning journey whenever you're ready, with all your progress saved.
7.  **Save Your Saga & Track Your Triumphs:** With optional user accounts (Google or Guest), you can securely save your unique adventures and pick up right where you left off. Never lose your progress on an epic quest!
8.  **Celebrate Your Achievements:** Conclude your epic journey with a personalized adventure summary, recapping your unique story, choices, and the knowledge you've gained.

## Why Learning Odyssey? The Difference We Make.

Learning Odyssey isn't just another educational app; it's a thoughtfully engineered platform designed for impact:

*   **Deep Engagement Through Agency & Narrative:** We combat passive learning by empowering users. Children actively shape their narrative – experiencing a story that builds suspense and resolves meaningfully – fostering ownership and sustained interest.
*   **Scalable, Dynamic, Personalized Content:** Our advanced AI narrative engine ensures that **virtually no two adventures are ever the same.** By dynamically generating story paths, character interactions, and visual elements based on user choices and their evolving Agency, we deliver unparalleled personalization and replayability at scale – a true breakthrough in interactive learning.
*   **True Integration of Learning & Play:** We solve the core challenge of making learning 'invisible' and fun. Education is an intrinsic, exciting part of the adventure, not a separate chore. Our **carefully crafted narrative arcs, complete with rising action, climactic moments, and thoughtful resolutions, are designed to mirror compelling real-world storytelling,** ensuring learning is both engaging and memorable. This is further enhanced by opportunities for guided reflection on new knowledge.
*   **Addressing a Critical Market Need:** Designed to tackle the engagement gap in traditional education, Learning Odyssey offers a solution for parents and educators seeking effective, captivating learning tools for the digital age.

## Key Features: Powering the Adventure

*   **Hyper-Personalized Adventures:** At its heart, Learning Odyssey crafts a unique journey for every child. The combination of AI-driven narratives, dynamic branching choices, and the evolving Agency system means each playthrough is a distinct and personal experience, complete with its own plot developments.
*   **Immersive AI Storytelling:** Dynamic narratives, powered by advanced AI, adapt in real-time to user choices. Experience a story that **builds suspense, presents meaningful turning points, and resolves in a fulfilling way,** creating a deeply engaging and replayable experience.
*   **Interactive Challenges & Meaningful Choices:** The "Agency" system and narrative branches ensure that decisions have tangible consequences, influencing the story's direction and fostering critical thinking through a well-paced plot.
*   **Dynamic & Evolving Visuals:** State-of-the-art AI image generation provides a rich visual tapestry for the adventure, with characters and scenes maintaining consistency and evolving with the narrative.
*   **Reflective Learning Chapters:** Dedicated "REFLECT" chapters go beyond simple quizzes, encouraging users to think critically about the educational content they've encountered, deepening comprehension and retention.
*   **Save & Resume Your Quests:** Our robust platform (powered by Supabase) offers the convenience of saving your progress. Optional user accounts (Google or Guest) make it easy to return to your adventures anytime, anywhere, demonstrating a production-ready experience.
*   **Comprehensive Adventure Recap:** A detailed summary chapter reinforces learning by allowing users to reflect on their entire narrative arc, from initial choices to the final resolution, and review their educational achievements.

## Technical Snapshot: Engineered for Innovation

The robust and scalable architecture of Learning Odyssey is designed for growth and continuous improvement. A Python/FastAPI backend ensures efficient AI integration and real-time responsiveness via WebSockets, supporting sophisticated narrative structures and learning flows. Supabase provides a flexible and secure cloud-based foundation for user data, persistent adventures, and telemetry. This modern stack allows for rapid iteration and the seamless incorporation of emerging AI capabilities.

### Architecture Overview
```mermaid
graph TD
    Client[Web Client] <--> WSR[WebSocket Router]
    WSR <--> WSC[WebSocket Core]
    
    %% WebSocket Service Components
    WSC <--> CP[Choice Processor]
    WSC <--> CG[Content Generator]
    WSC <--> SH[Stream Handler]
    WSC <--> IG[Image Generator]
    WSC <--> SG[Summary Generator]
    
    CP <--> ASM[Adventure State Manager]
    CG <--> ASM
    ASM <--> AS[AdventureState]
    ASM <--> CM[Chapter Manager]
    CM <--> LLM[LLM Service]
    CM <--> DB[(Supabase DB)] %% Updated from (Database)
    IG <--> IMG[Image Generation Service]
    CM <--> SL[Story Loader]
    SL <--> SF[(Story Files)]
    LLM <--> PF[Paragraph Formatter]
    
    %% React Summary Components
    Client <--> SR[Summary Router]
    SR <--> RSUM[React Summary App]
    SR <--> SAPI[Summary API]
    SAPI <--> SGEN[Summary Generator]
    SGEN <--> AS

    subgraph Client Side
        LP[localStorage/Supabase Auth] <--> CSM[Client Auth/State Manager] %% Updated
        CSM <--> Client
    end

    subgraph Core State
        AS
    end

    subgraph WebSocket Services
        WSC
        CP
        CG
        SH
        IG
        SG
    end

    subgraph Core Services
        ASM
        CM
        LLM
        IMG
        PF
    end

    subgraph Content Sources
        CSV[lessons/*.csv] --> CM
        LLM --> CM
        IMG --> IG
        SF --> SL
    end
    
    subgraph React Summary
        RSUM
        SAPI
        SGEN
    end
    
    subgraph Templates
        BL[Base Layout]
        PC[Page Components]
        UI[UI Components]
        Client --> BL
        BL --> PC
        PC --> UI
    end
```

## Recent Enhancements: Continual Evolution

Learning Odyssey is a living project, constantly evolving to deliver a richer experience:

*   **🚀 Latest: Future-Proof AI Integration:** Successfully migrated to Google's unified `google-genai` SDK, ensuring access to the latest AI capabilities and improved stability while maintaining 100% backward compatibility.
*   **🎉 Complete Supabase Integration - PRODUCTION READY:** Full implementation of user authentication (Google OAuth & Guest), persistent adventure state, comprehensive telemetry tracking, and robust adventure resumption with custom modal flows. All four phases completed with thorough testing and bug fixes.
*   **Enhanced User Experience:** Custom modal system for adventure management, consistent chapter display across all components, and seamless resumption flows for both authenticated and guest users.
*   **Improved Visual Consistency:** Characters and agency elements now maintain more consistent and evolving visual appearances throughout your adventure with advanced prompt synthesis and character tracking.
*   **Modular Frontend Architecture:** Complete ES6 module refactoring for improved maintainability, testability, and code organization across all JavaScript components.
*   **Enterprise-Ready Data Management:** Row-level security (RLS) policies, comprehensive telemetry analytics, and robust state persistence ensuring data integrity and user privacy.

## Setup (For Developers)

1.  Clone the repository.
2.  Create and activate a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # Linux/Mac
    # or
    .\venv\Scripts\activate  # Windows
    ```
3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
4.  Create a `.env` file with required environment variables:
    ```env
    # API key for LLM and image generation (both use the same key with Google)
    GOOGLE_API_KEY=your_google_key
    # Or alternatively use OpenAI for LLM (image generation still requires Google)
    OPENAI_API_KEY=your_openai_key

    # Supabase credentials (obtain from your Supabase project)
    SUPABASE_URL=your_supabase_url
    SUPABASE_ANON_KEY=your_supabase_anon_key
    SUPABASE_SERVICE_KEY=your_supabase_service_key
    SUPABASE_JWT_SECRET=your_supabase_jwt_secret 
    # Ensure this JWT secret matches the one in your Supabase project settings (Auth > JWT Settings)
    ```
5.  Apply Supabase database migrations (if you're setting up the DB for the first time):
    ```bash
    npx supabase login
    npx supabase link --project-ref your-project-ref
    npx supabase db push
    ```
6.  Run the application:
    ```bash
    uvicorn app.main:app --reload
    ```

## Project Structure

The project is organized into several key components:

*   **Backend (`app/`)**: Contains the FastAPI application, including:
    *   `models/`: Data structures like `AdventureState`.
    *   `routers/`: API and WebSocket endpoint definitions.
    *   `services/`: Core logic for LLMs, state management, content generation, Supabase interaction, etc.
    *   `static/`: Frontend assets (CSS, JS, images), including the React summary app.
    *   `templates/`: Jinja2 HTML templates.
*   **Content Sources (`app/data/`)**:
    *   `lessons/`: CSV files for educational content.
    *   `stories/`: YAML files defining story categories and narrative elements.
*   **Supabase (`supabase/`)**: Database migration files.
*   **Tests (`tests/`)**: Automated tests and simulation scripts.
*   **WIP & Memory Bank (`wip/`, `memory-bank/`)**: Documents for ongoing work and project knowledge.

## Testing

The project includes a testing framework to ensure reliability:

*   **Simulation Framework**: End-to-end testing of adventure generation.
*   **Test Coverage**: Includes chapter sequences, state transitions, and summary generation.
*   **Running Tests**:
    ```bash
    # Example: Run the complete adventure simulation
    python tests/simulations/generate_all_chapters.py
    ```

## Technical Considerations

Learning Odyssey's dynamic nature requires sequential chapter generation, as each chapter builds upon previous events and choices. The narrative is generated in real-time, following a structured arc designed for engagement. To manage this, the platform uses robust WebSocket communication, client-side and server-side (Supabase) state persistence, and graceful degradation to ensure a smooth learning journey. This thoughtful engineering ensures a reliable and engaging platform ready for future growth.
