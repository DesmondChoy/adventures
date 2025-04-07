# Supabase Integration Plan for Learning Odyssey

This document outlines the steps required to integrate Supabase into the Learning Odyssey application, focusing on achieving Persistent Adventure State and enabling detailed Telemetry, with optional User Authentication (Google/Anonymous).

## Phase 1: Prerequisites & Setup

- [x] **1. Create Supabase Project & Find API Keys:**
    *   [x] **Create Project:** Go to [supabase.com](https://supabase.com/) and create a new project if you haven't already. Choose a region close to your users.
    *   [x] **Navigate to API Settings:** Once the project is ready, go to the project dashboard. In the left sidebar, click the gear icon (Project Settings), then click "API".
    *   **Identify Keys:** On the API page, you will find:
        *   **Project URL:** A URL like `https://<your-project-ref>.supabase.co`. You'll need this.
        *   **Project API Keys:**
            *   `anon` **public:** This is your public API key. It's safe to expose in your frontend code (like JavaScript). It grants access based on your Row Level Security (RLS) rules. Copy this key.
            *   `service_role` **secret:** This is your secret backend key. **Treat this like a password.** It bypasses all security rules (RLS) and gives full admin access. **NEVER expose this key in frontend code or commit it to GitHub.** Copy this key securely.

- [x] **2. Install Supabase Libraries:**
    *   [x] **Backend (Python):** Add `supabase-py` to `requirements.txt` and install (`pip install supabase-py`). *(Note: Corrected package name)*
    *   [x] **Frontend (JavaScript):** Add the Supabase JS client library (`@supabase/supabase-js`) via CDN script tag in `base.html` or relevant template.
        ```html
        <!-- Example: Add to base.html or relevant template -->
        <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
        <script>
          const SUPABASE_URL = 'YOUR_SUPABASE_URL';
          const SUPABASE_ANON_KEY = 'YOUR_SUPABASE_ANON_KEY';
          const supabase = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
        </script>
        ```

- [x] **3. Configure Environment Variables (Secure Key Storage):**
    *   **Goal:** Your backend code needs the `Project URL` and the secret `service_role` key to interact with Supabase securely. The public `anon` key is needed for the frontend. We will use environment variables for secure storage.
    *   [x] **Local Development (`.env` file):**
        *   [x] Create a file named `.env` in the root directory of your project (the same level as `requirements.txt`).
        *   [x] **IMPORTANT:** Add `.env` to your `.gitignore` file immediately. This prevents accidentally committing your secret key to GitHub. If `.gitignore` doesn't exist, create it and add `.env` on a new line.
        *   [x] Add the following lines to your `.env` file, replacing the placeholders with your actual values:
            ```dotenv
            # .env file (DO NOT COMMIT TO GITHUB)
            SUPABASE_URL=https://<your-project-ref>.supabase.co
            SUPABASE_SERVICE_KEY=your_secret_service_role_key_paste_here
            SUPABASE_ANON_KEY=your_public_anon_key_paste_here
            ```
        *   [x] **Install `python-dotenv`:** Add `python-dotenv` to your `requirements.txt` and run `pip install -r requirements.txt`. This library allows your Python code to load variables from the `.env` file automatically during local development. *(Already present)*
        *   [x] **Load Variables in Python:** Early in your application startup (e.g., in `app/main.py` or a config file), load the variables: *(Already present)*
            ```python
            from dotenv import load_dotenv
            import os

            load_dotenv() # Loads variables from .env into environment

            # Example of accessing them:
            supabase_url = os.getenv("SUPABASE_URL")
            supabase_key = os.getenv("SUPABASE_SERVICE_KEY")
            ```
    *   [x] **Production Deployment (Railway):**
        *   [x] Go to your project dashboard on Railway.
        *   [x] Navigate to your FastAPI service settings.
        *   [x] Find the "Variables" section.
        *   [x] Add the following variables, pasting the correct values from your Supabase project:
            *   `SUPABASE_URL`: `https://<your-project-ref>.supabase.co`
            *   `SUPABASE_SERVICE_KEY`: `your_secret_service_role_key_paste_here`
            *   `SUPABASE_ANON_KEY`: `your_public_anon_key_paste_here`
        *   Railway will automatically make these environment variables available to your running application, so your Python code using `os.getenv()` will work correctly in production without needing the `.env` file or `python-dotenv`.
    *   [x] **Frontend `anon` Key Handling:**
        *   [x] In your FastAPI route that renders the main HTML page (e.g., in `app/routers/web.py`), fetch the keys from the environment variables and pass them to the template context:
            ```python
            # Example in app/routers/web.py
            import os
            from fastapi import Request
            from fastapi.templating import Jinja2Templates

            templates = Jinja2Templates(directory="app/templates")

            @router.get("/")
            async def read_root(request: Request):
                supabase_anon_key = os.getenv("SUPABASE_ANON_KEY")
                supabase_url = os.getenv("SUPABASE_URL")
                return templates.TemplateResponse("pages/index.html", {
                    "request": request,
                    "supabase_anon_key": supabase_anon_key,
                    "supabase_url": supabase_url
                })
            ```
        *   [x] In your template (`base.html` or wherever the Supabase JS client is initialized), use the passed variables:
            ```html
            <!-- Example in base.html -->
            <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
            <script>
              const SUPABASE_URL = '{{ supabase_url }}'; // Use Jinja variable
              const SUPABASE_ANON_KEY = '{{ supabase_anon_key }}'; // Use Jinja variable
              const supabase = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
              // ... rest of your frontend JS
            </script>
            ```

## Phase 2: Persistent Adventure State (Supabase Database)

- [x] **1. Define Database Schema (`adventures` table):**
    *   [x] Using Supabase CLI migrations, created a table named `adventures` with version control for database schema changes.
    *   [x] **Setup Steps:**
        *   [x] Installed Supabase CLI locally (`npm install supabase`)
        *   [x] Authenticated with Supabase (`npx supabase login`)
        *   [x] Linked project to Supabase instance (`npx supabase link --project-ref zgipcnqauuwlalucjwqk`)
        *   [x] Created a new migration (`npx supabase migration new create_adventures_table`)
        *   [x] Defined the table schema in the generated SQL file (`20250407101938_create_adventures_table.sql`)
        *   [x] Applied the migration (`npx supabase db push`)
    *   [x] **Defined Columns (Hybrid Approach):**
        *   `id` (UUID, Primary Key, default: `gen_random_uuid()`)
        *   `user_id` (UUID, Nullable - *will link to `auth.users` if Auth is implemented*)
        *   `state_data` (JSONB, Not Null) - Stores the complete `AdventureState` JSON for full state reconstruction.
        *   `story_category` (TEXT, Nullable) - Extracted for easier querying and filtering.
        *   `lesson_topic` (TEXT, Nullable) - Extracted for easier querying and filtering.
        *   `is_complete` (BOOLEAN, default: `false`) - To distinguish in-progress vs. completed adventures.
        *   `completed_chapter_count` (INTEGER, Nullable) - Number of chapters completed, useful for engagement metrics.
        *   `created_at` (TimestampTZ, default: `now()`)
        *   `updated_at` (TimestampTZ, default: `now()`) - With automatic update trigger
    *   [x] **Schema Approach:** Implemented the hybrid approach that balances simplicity with query needs:
        *   Keeps the full state in `state_data` for easy reconstruction
        *   Extracts key fields as dedicated columns for efficient filtering and analytics
        *   Allows for future schema evolution by adding more columns as needed
    *   [x] **Configured Row Level Security (RLS):** 
        *   Enabled RLS on the table
        *   Created a policy allowing backend access via service key
        *   Added appropriate grants for the service_role
        *   Added comments to document table and columns

- [x] **2. Refactor Backend `StateStorageService` (`app/services/state_storage_service.py`):**
    *   [x] Initialized the Supabase client using environment variables in the `__init__` method:
        *   Added imports for `os`, `supabase`, and `load_dotenv`
        *   Used `load_dotenv()` to load environment variables
        *   Retrieved `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` using `os.getenv()`
        *   Created the Supabase client instance with proper error handling
    *   [x] Modified `store_state` method:
        *   [x] Updated signature to accept `user_id` (optional parameter)
        *   [x] Removed code related to `_memory_cache`
        *   [x] Added logic to extract key fields from the state data:
            *   `state_data`: The entire serialized state object
            *   `story_category`: From state metadata
            *   `lesson_topic`: From state metadata
            *   `is_complete`: Based on last chapter type (CONCLUSION or SUMMARY)
            *   `completed_chapter_count`: From `len(chapters)`
        *   [x] Constructed a record dictionary with all fields
        *   [x] Used Supabase client to insert the record
        *   [x] Added error handling with try/except
        *   [x] Extracted and returned the generated UUID from the response
    *   [x] Modified `get_state` method:
        *   [x] Removed code related to `_memory_cache`
        *   [x] Used Supabase client to query the record by ID
        *   [x] Added error handling
        *   [x] Extracted and returned the `state_data` field if found
    *   [x] Modified `cleanup_expired` method:
        *   [x] Updated to delete expired records from Supabase based on timestamp
    *   [x] Removed singleton pattern:
        *   [x] Removed `_memory_cache`, `_instance`, and `_initialized` class variables
        *   [x] Removed `__new__` method
        *   [x] Simplified `__init__` method to just initialize the Supabase client

- [ ] **3. Integrate into WebSocket/API Flow:**
    *   [ ] **Revise `StateStorageService` for Upsert & Resume:**
        *   [ ] Modify `store_state` to accept an optional `adventure_id` parameter for upsert operations.
        *   [ ] Implement upsert logic: if `adventure_id` is provided, update existing record; if not, insert new record.
        *   [ ] Add a new `get_active_adventure_id(user_identifier)` method to find incomplete adventures for a user.
    *   [ ] **Adventure Start & Resume:**
        *   [ ] On WebSocket connect, check for an existing active adventure for the user (using `StateStorageService.get_active_adventure_id`).
        *   [ ] If active adventure found, load state using `StateStorageService.get_state` and store `adventure_id` in connection scope.
        *   [ ] If no active adventure, create initial `AdventureState`, save immediately using `StateStorageService.store_state` to get the persistent `adventure_id`, and store ID in connection scope.
    *   [ ] **Adventure Progress:**
        *   [ ] Implement periodic saves after each significant state update (e.g., chapter completion, choice made).
        *   [ ] Call `StateStorageService.store_state` with the current `adventure_id` and state data to update the record.
        *   [ ] Ensure `is_complete` remains `false` during these updates.
    *   [ ] **Adventure Completion:**
        *   [ ] In the relevant function (`summary_generator.py` or `core.py`), after the final `AdventureState` is ready:
            *   [ ] Call `StateStorageService.store_state` one last time, passing the final state, `adventure_id`, and ensuring `is_complete` is set to `true`.
            *   [ ] Send the `adventure_id` back to the client in the `summary_ready` message.
    *   [ ] **Summary Retrieval (`summary_router.py`):**
        *   [ ] Ensure the `/adventure/api/adventure-summary` endpoint receives the `adventure_id` (as `state_id` query param).
        *   [ ] Update the endpoint to use the refactored `StateStorageService.get_state` to fetch the `state_data` from Supabase using the provided `adventure_id`.

## Phase 3: Telemetry (Supabase Database) - *Deferred until Persistent State (including resume) is complete*

- [ ] **1. Define Database Schema (`telemetry_events` table):**
    *   [ ] Using Supabase CLI migrations, create a table named `telemetry_events`. This approach provides version control for database schema changes.
    *   [ ] **Setup Steps:**
        *   [ ] Create a new migration (`supabase migration new create_telemetry_events_table`)
        *   [ ] Define the table schema in the generated SQL file
        *   [ ] Apply the migration (`supabase migration up`)
    *   [ ] **Define Columns:**
        *   `id` (BIGSERIAL, Primary Key - using sequence for high insert rate)
        *   `event_name` (TEXT, Not Null) - e.g., 'adventure_started', 'chapter_viewed', 'choice_made', 'summary_viewed'.
        *   `adventure_id` (UUID, Nullable, Foreign Key -> `adventures.id` - *optional if event is not adventure-specific*)
        *   `user_id` (UUID, Nullable - *links to `auth.users` if Auth implemented*)
        *   `timestamp` (TimestampTZ, default: `now()`)
        *   `metadata` (JSONB, Nullable) - Store event-specific details (e.g., `{"chapter_number": 1, "story_category": "...", "lesson_topic": "..."}`, `{"chapter_number": 3, "duration_ms": 45000}`, `{"choice_index": 0}`).

- [ ] **2. Integrate Telemetry Logging in Backend:**
    *   [ ] Create a utility function or service (e.g., `log_telemetry(event_name, adventure_id=None, user_id=None, metadata=None)`). This function will insert a record into the `telemetry_events` table using the Supabase client.
    *   [ ] Call this logging function at relevant points in the code:
        *   [ ] **Adventure Start:** Log 'adventure_started' with chosen topics.
        *   [ ] **Chapter View:** Log 'chapter_viewed' when sending chapter content.
        *   [ ] **Choice Made:** Log 'choice_made' when processing a user choice.
        *   [ ] **Summary Viewed:** Log 'summary_viewed' when the summary API is successfully called.

- [ ] **3. Analytics:**
    *   [ ] Use SQL queries directly in the Supabase dashboard or connect a BI tool to analyze the data in `adventures` and `telemetry_events` tables.
    *   [ ] Define key metrics and create corresponding SQL queries (e.g., topic popularity, average adventure length, common drop-off points). Example Queries:
        *   `SELECT story_category, COUNT(*) FROM adventures GROUP BY story_category ORDER BY COUNT(*) DESC;`
        *   `SELECT event_name, COUNT(*) FROM telemetry_events WHERE timestamp > now() - interval '7 days' GROUP BY event_name;`
        *   Analyze `metadata` JSONB fields for deeper insights.

## Phase 4: Optional User Authentication (Supabase Auth) - *Deferred until Persistent State (including resume) is complete*

- [ ] **1. Configure Supabase Auth:**
    *   [ ] Enable the Google provider in the Supabase project dashboard (requires setting up OAuth credentials in Google Cloud Console).
    *   [ ] Enable Anonymous sign-ins in the Supabase dashboard settings.

- [ ] **2. Implement Frontend Logic:**
    *   [ ] Add UI elements for "Login with Google" and "Continue as Guest".
    *   [ ] Use the Supabase JS client library:
        *   [ ] Implement `supabase.auth.signInWithOAuth({ provider: 'google' })` for Google login button.
        *   [ ] Implement `supabase.auth.signInAnonymously()` for guest access button.
    *   [ ] Implement logic to listen for authentication state changes (`onAuthStateChange`) to update the UI (e.g., show user email, hide login buttons) and get the `user_id` and session token.
    *   [ ] Display the warning message for anonymous users.
    *   [ ] Ensure the user's auth token (JWT) is sent with requests to the backend (e.g., in the `Authorization: Bearer <token>` header for API calls, potentially passed via WebSocket connection parameters).

- [ ] **3. Implement Backend Logic:**
    *   [ ] Add middleware or dependency injection in FastAPI to verify the JWT sent from the frontend and extract the `user_id`. (Libraries like `AuthX` or custom dependencies using `PyJWT` and Supabase public key can work).
    *   [ ] Pass the validated `user_id` to the `StateStorageService` and telemetry logging functions when available.
    *   [ ] Update database interactions (`adventures`, `telemetry_events`) to store the `user_id`.

- [ ] **4. Update Database Schema/RLS:**
    *   [ ] Using Supabase CLI migrations, update the database schema and implement RLS policies:
        *   [ ] Create a new migration (`supabase migration new add_auth_foreign_keys_and_rls`)
        *   [ ] Define the SQL to add foreign key constraints linking `user_id` columns in `adventures` and `telemetry_events` to the `auth.users` table
        *   [ ] Define the SQL to implement Row Level Security (RLS) policies (e.g., `CREATE POLICY "Users can manage their own adventures." ON adventures FOR ALL USING (auth.uid() = user_id);`)
        *   [ ] Apply the migration (`supabase migration up`)

## Considerations & Next Steps

*   [ ] **User Identification:** Define how to identify users for resuming adventures (e.g., session ID, browser fingerprint, anonymous user ID from Supabase Auth, full user ID). This is critical for the `get_active_adventure_id` method to work properly.
*   [ ] **Error Handling:** Implement robust error handling for all Supabase interactions (DB writes/reads, auth).
*   [ ] **Data Migration:** Plan how to handle any existing state data (if applicable, though current state is transient).
*   [ ] **Testing:** Update existing tests and create new ones to cover Supabase interactions, periodic saves, and resume functionality.
*   [ ] **Scalability:** Monitor Supabase usage and scale the database plan if necessary. Consider database indexing for performance as data grows.
*   [ ] **Security:** Ensure RLS policies are correctly implemented if data access needs restriction beyond backend service key access. Review Supabase security best practices.
*   [ ] **Client-side State:** Decide how much state still needs to be managed client-side (e.g., current chapter content being streamed) vs. relying solely on backend/DB state.

This plan provides a structured approach. We will now focus on completing Phase 2 (Persistent State including resume functionality) before moving to Telemetry or Authentication.
