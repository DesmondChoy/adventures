# Learning Odyssey

Learning Odyssey is an educational adventure platform built with FastAPI,
WebSockets, Supabase, and Gemini models. It delivers 10-chapter,
story-driven learning sessions where players choose a story world and a
lesson topic, make an agency choice in the opening chapter, answer lesson
questions, revisit ideas in reflect chapters, and finish with a dedicated
summary experience.

## Current Experience

- Storybook-style landing page with Google sign-in and guest access.
- Responsive 3D carousels for story-world and lesson-topic selection, with
  Playwright screenshot coverage for desktop and mobile layouts.
- A fixed 10-chapter adventure structure managed by `AdventureState`,
  covering story, lesson, reflect, and conclusion chapters, followed by a
  separate summary page.
- An agency system introduced in chapter 1 and carried through the story,
  reflect chapters, and conclusion.
- AI-generated text, image prompts, and chapter illustrations with tracked
  character and agency visuals.
- Resume and abandon flows for authenticated and guest adventures backed by
  Supabase persistence.
- A gameplay context ribbon that keeps the active story world and lesson
  topic visible.
- A loading overlay with 45 rotating phrases served by
  `/api/loading-phrases`.
- A once-per-user feedback prompt after chapter 5, with optional follow-up
  contact collection for guest users who leave negative feedback.
- A standalone summary application served under `/adventure/summary`,
  including a chapter timeline, question review, and telemetry-based
  time-spent stats.

## Architecture

- Backend: FastAPI routes in `app/routers/` handle the landing flow,
  WebSocket gameplay, summary APIs, and feedback APIs.
- Adventure orchestration: `AdventureStateManager`, `ChapterManager`, and
  `StateStorageService` manage flow, persistence, reconstruction, and
  server-authoritative state handling. `AdventureState` is the single source
  of truth.
- AI services: `app/services/llm/` routes complex generation work to Gemini
  Flash and lighter work such as summaries, prompt synthesis, and formatting
  to Flash Lite through `LLMServiceFactory`.
- Frontend: Jinja templates and modular ES modules drive login, selection,
  live chapter streaming, resume modals, context ribbon, and feedback UX.
  The summary page is served as a separate built bundle from
  `app/static/summary-chapter/`.
- Persistence and analytics: Supabase stores adventures, telemetry events,
  and user feedback. Telemetry powers summary statistics, and the optional
  `feedback-notify` Edge Function can send feedback emails through Resend.
- Testing: pytest covers backend services and data loaders, simulation
  scripts exercise the WebSocket flow end-to-end, and Playwright guards the
  carousel UI on desktop and mobile.

## Content Library

### Story worlds

- Circus & Carnival Capers (`circus_and_carnival_capers`)
- Clockwork Sky City (`clockwork_sky_city`)
- Dream Library of Lost Stories (`dream_library_of_lost_stories`)
- Enchanted Forest Tales (`enchanted_forest_tales`)
- Festival of Lights & Colors (`festival_of_lights_and_colors`)
- Jade Mountain (`jade_mountain`)
- Living Inside Your Own Drawing (`living_inside_your_own_drawing`)
- Tiny World Under the Floorboards (`tiny_world_under_the_floorboards`)
- Underwater Kingdom of Sunken Ships
  (`underwater_kingdom_of_sunken_ships`)
- Whispering Desert Oasis (`whispering_desert_oasis`)

### Lesson topics

- Ancient Civilizations
- Astronomy
- Dinosaurs and Prehistoric Life
- Farm Animals
- Human Body
- Inventions and Inventors
- Music and Sound
- Oceans and Marine Life
- Singapore History
- Volcanoes Earthquakes and Weather

## Getting Started

### Prerequisites

- Python 3.10 or newer
- Node.js and npm
- A Supabase project
- A Google API key for Gemini-based text and image generation

### Local setup

1. Create and activate the virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Install Python dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Install Node-based tooling used for Playwright and summary bundle
   maintenance:

   ```bash
   npm install
   ```

4. Create a local `.env` file in the repository root.

5. Apply the Supabase schema if you are provisioning a project from scratch:

   ```bash
   npx supabase login
   npx supabase link --project-ref <project-ref>
   npx supabase db push
   ```

6. Start the app:

   ```bash
   python -m uvicorn app.main:app --reload
   ```

7. Open `http://127.0.0.1:8000/`.

### Environment variables

| Variable | Required | Purpose |
| --- | --- | --- |
| `SECRET_KEY` | Yes | Session middleware secret. The app refuses to start without it. |
| `GOOGLE_API_KEY` | Yes | Gemini text generation and image-generation workflows. |
| `SUPABASE_URL` | Yes | Supabase project URL injected into the backend and templates. |
| `SUPABASE_ANON_KEY` | Yes | Browser-side Supabase client for login and client flows. |
| `SUPABASE_SERVICE_KEY` | Yes | Server-side Supabase access for adventures, telemetry, and feedback storage. |
| `SUPABASE_JWT_SECRET` | Yes | JWT verification for authenticated summary, resume, and WebSocket flows. |
| `APP_ENVIRONMENT` | Recommended | Environment label stored with telemetry and feedback records. |
| `OPENAI_API_KEY` | Optional | Alternate LLM client support present in the codebase. |
| `ALLOWED_HOSTS` | Optional | Comma-separated host allowlist for `TrustedHostMiddleware`. |
| `PROXY_TRUSTED_HOSTS` | Optional | Comma-separated trusted proxy hosts for proxy-header handling. |
| `CORS_ALLOW_ORIGINS` | Optional | Comma-separated CORS allowlist. Defaults to local dev origins. |
| `CORS_ALLOW_CREDENTIALS` | Optional | Enables or disables credentialed CORS requests. |
| `HTTPS_ONLY` | Optional | Forces secure session cookies when enabled. |
| `RESEND_API_KEY` | Optional | Supabase Edge Function secret for feedback notification email delivery. |
| `FEEDBACK_NOTIFICATION_EMAIL` | Optional | Supabase Edge Function secret for the feedback notification recipient. |

The app runtime loads local `.env` values in development. Keep `.env` and
`.env.*` untracked and out of Docker build contexts; see
`docs/security/deployment-model.md` for the deployment policy.

## Common Commands

Run commands from the repository root with `.venv` activated. For pytest,
prefer `python -m pytest` over bare `pytest` if your shell does not place the
repo root on `PYTHONPATH`.

### Daily development

| Task | Command |
| --- | --- |
| Start the FastAPI app | `python -m uvicorn app.main:app --reload` |
| Run the full Python test suite | `python -m pytest` |
| Run a focused test module | `python -m pytest tests/test_summary_service.py -q` |
| Run deployment guardrails locally | `bash tools/check_deployment_security.sh` |

### Browser regression

| Task | Command |
| --- | --- |
| Run carousel visual regression tests | `npm run test:visual:carousel` |
| Refresh carousel screenshots | `npm run test:visual:carousel:update` |

### Simulations and summary tooling

| Task | Command |
| --- | --- |
| Fully automated simulation run with server management | `python tests/simulations/run_test_analysis.py --runs 3` |
| Analyze the most recent simulation log only | `python tests/simulations/run_test_analysis.py --analyze-only` |
| Run raw WebSocket simulations against an existing server | `python tests/simulations/adventure_test_runner.py --runs 5 --host localhost --port 8000` |
| Generate one reusable full-adventure state file | `python tests/simulations/generate_all_chapters.py --category enchanted_forest_tales --topic "Singapore History"` |
| Generate chapter summaries from the latest saved simulation state | `python tests/simulations/generate_chapter_summaries.py --compact` |
| Generate React-compatible summary JSON | `python tests/simulations/generate_chapter_summaries.py --react-json --react-output tests/summary_data.json` |
| Preview the summary page with saved simulation data | `python tests/test_summary_chapter.py --state-file logs/simulations/simulation_state_<timestamp>_<run_id>.json --port 8001` |
| Validate the summary button flow | `python tests/test_summary_button_flow.py --compare` |

### Utilities

| Task | Command |
| --- | --- |
| Analyze large files by line count | `python tools/code_complexity_analyzer.py -s code -n 20` |
| Generate optimized image variants | `python tools/optimize_images.py app/static/images/stories` |
| Rebuild a colocated summary app checkout | `python tools/build_summary_app.py --mode production --skip-install` |

The repository already includes the served summary bundle in
`app/static/summary-chapter/`, so most local development does not need to
rebuild it.

## HTTP and WebSocket Surface

### UI routes

| Route | Purpose |
| --- | --- |
| `GET /` | Landing page with Google login and guest entry. |
| `GET /select` | Story-world and lesson-topic selection flow. |
| `GET /adventure/summary` | Standalone summary front-end. |
| `GET /api/loading-phrases` | Returns the rotating loader phrase list. |

### Adventure state and summary APIs

| Route | Purpose |
| --- | --- |
| `GET /api/user/current-adventure` | Returns the current authenticated user's incomplete adventure, if any. |
| `GET /api/adventure/active_by_client_uuid/{client_uuid}` | Looks up an active guest-linked adventure for the authenticated user. |
| `POST /api/adventure/{adventure_id}/abandon` | Abandons an incomplete adventure owned by the authenticated user. |
| `GET /adventure/api/adventure-summary?state_id=<uuid>` | Returns summary data for a completed adventure. |
| `POST /adventure/api/store-adventure-state` | Stores or updates an adventure state record for an authenticated user. |
| `GET /adventure/api/get-adventure-state/{state_id}` | Fetches a stored adventure state by ID. |

### Feedback APIs

| Route | Purpose |
| --- | --- |
| `POST /api/feedback` | Stores positive or negative feedback for an adventure. |
| `GET /api/feedback/check` | Returns whether the current user or guest client has already submitted feedback. |

### WebSocket gameplay endpoint

The live adventure flow runs through:

```text
/ws/story/{story_category}/{lesson_topic}
```

Supported query parameters:

- `client_uuid`: guest identity and guest-resume tracking
- `difficulty`: optional lesson difficulty hint
- `token`: authenticated JWT for secure ownership checks
- `resume_adventure_id`: explicit adventure ID to resume

The server enforces ownership checks for resumed authenticated adventures,
keeps the authoritative state for summary reveal, and applies an in-memory
concurrent-connection limit per client IP.

## Repository Layout

- `app/`
  - FastAPI app, routers, data loaders, services, templates, and frontend
    assets.
- `app/data/`
  - Story YAML files and lesson CSV files.
- `app/services/llm/`
  - Prompt construction, provider integrations, and model routing.
- `app/services/websocket/`
  - Choice processing, content generation, streaming, image orchestration, and
    summary reveal.
- `app/services/summary/`
  - Summary DTOs, chapter/question/stat processors, and the summary service.
- `app/static/summary-chapter/`
  - Served summary front-end bundle plus runtime patches.
- `tests/`
  - pytest coverage, simulation tooling, Playwright coverage, and state
    fixtures.
- `supabase/migrations/`
  - Schema changes for adventures, telemetry, auth ownership, and feedback.
- `supabase/functions/feedback-notify/`
  - Optional email notification function for feedback submissions.
- `tools/`
  - Guardrail checks, complexity analysis, image optimization, and summary
    bundle tooling.

## Deployment and Security

Production deploys flow from GitHub to Railway. The `Procfile` runs:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers
```

Deployment security policy lives in `docs/security/deployment-model.md`.
Repository guardrails are enforced by
`.github/workflows/deployment-security-guardrails.yml`, which runs
`bash tools/check_deployment_security.sh` on pull requests and on pushes to
`main` and `master`.

If you are working on simulation tooling, the detailed command reference lives
in `tests/simulations/README.md`.
