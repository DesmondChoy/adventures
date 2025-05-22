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

- [x] **3. Integrate into WebSocket/API Flow:**
    *   [x] **Revise `StateStorageService` for Upsert & Resume:**
        *   [x] Modified `store_state` to accept an optional `adventure_id` parameter for upsert operations.
        *   [x] Implemented upsert logic: if `adventure_id` is provided, update existing record; if not, insert new record.
        *   [x] Added a new `get_active_adventure_id(user_identifier)` method to find incomplete adventures for a user.
    *   [x] **Adventure Start & Resume:**
        *   [x] On WebSocket connect, check for an existing active adventure for the user (using `StateStorageService.get_active_adventure_id`).
        *   [x] If active adventure found, load state using `StateStorageService.get_state` and store `adventure_id` in connection scope.
        *   [x] If no active adventure, create initial `AdventureState`, save immediately using `StateStorageService.store_state` to get the persistent `adventure_id`, and store ID in connection scope.
    *   [x] **Adventure Progress:**
        *   [x] Implemented periodic saves after each significant state update (e.g., chapter completion, choice made).
        *   [x] Call `StateStorageService.store_state` with the current `adventure_id` and state data to update the record.
        *   [x] Ensure `is_complete` remains `false` during these updates.
    *   [x] **Adventure Completion:**
        *   [x] In the relevant function (`choice_processor.py`), after the final `AdventureState` is ready:
            *   [x] Call `StateStorageService.store_state` one last time, passing the final state, `adventure_id`, and ensuring `is_complete` is set to `true`.
            *   [x] Send the `adventure_id` back to the client in the `summary_ready` message.
    *   [x] **Summary Retrieval (`summary_router.py`):**
        *   [x] Ensured the `/adventure/api/adventure-summary` endpoint receives the `adventure_id` (as `state_id` query param).
        *   [x] Updated the endpoint to use the refactored `StateStorageService.get_state` to fetch the `state_data` from Supabase using the provided `adventure_id`.

- [x] **4. Add Environment Column for Data Differentiation:**
    *   [x] **Goal:** Differentiate between data generated during local development and data from production users.
    *   [x] **Database Migration:** Created a new migration (`20250407130602_add_environment_column.sql`) to add an `environment TEXT NULL DEFAULT 'unknown'` column to the `adventures` table. Applied the migration using `npx supabase db push`.
    *   [x] **Environment Variables:**
        *   Added `APP_ENVIRONMENT="development"` to the local `.env` file.
        *   Instructed user to add `APP_ENVIRONMENT="production"` to Railway environment variables.
    *   [x] **Code Update:** Modified `StateStorageService.store_state` to read the `APP_ENVIRONMENT` variable (`os.getenv("APP_ENVIRONMENT", "unknown")`) and include its value in the `record` dictionary saved to the `environment` column in Supabase.

### Debugging Notes (Phase 2 Completion)

During local testing after completing Phase 2, the following issues were identified and resolved:

1.  **Issue:** Supabase table `adventures` was not being populated. Logs showed `Could not find the 'client_uuid' column of 'adventures' in the schema cache`.
    *   **Cause:** `StateStorageService.store_state` was attempting to insert data into a `client_uuid` column, which does not exist in the defined schema (the `client_uuid` is stored within the `state_data` JSONB). The `get_active_adventure_id` method was also incorrectly trying to query this non-existent column.
    *   **Fix:**
        *   Removed the `client_uuid` key from the `record` dictionary being inserted/updated in `store_state`.
        *   Updated `get_active_adventure_id` to query the JSONB field using the correct path: `state_data->'metadata'->>'client_uuid'`.

2.  **Issue:** The `lesson_topic` column in the `adventures` table was NULL upon initial adventure creation.
    *   **Cause:** `StateStorageService.store_state` extracted `lesson_topic` only from `state_data.metadata`, which wasn't populated during the very first save operation.
    *   **Fix:**
        *   Modified `StateStorageService.store_state` signature to accept `lesson_topic` as an optional parameter.
        *   Updated the `record` preparation logic to prioritize the passed `lesson_topic` parameter.
        *   Modified `websocket_router.py` to pass the `lesson_topic` from the URL directly to `store_state` during the initial save.

3.  **Issue:** Logs showed `Error finding active adventure: BaseSelectRequestBuilder.order() got an unexpected keyword argument 'options'`.
    *   **Cause:** Incorrect syntax used for descending order in the `get_active_adventure_id` query.
    *   **Fix:** Corrected the `.order()` call in `get_active_adventure_id` to use `desc=True` instead of `options={"ascending": False}`.

4.  **Issue:** `lesson_topic` became NULL after the first chapter load, while `completed_chapter_count` incremented to 1.
    *   **Cause:** An automatic state save occurred after Chapter 1 generation but before user choice. During this save, `store_state` re-extracted `lesson_topic` from `state_data.metadata` (where it wasn't explicitly stored after initialization), resulting in NULL. The `completed_chapter_count` correctly reflected `len(state.chapters) == 1`.
    *   **Fix:** Modified `StateStorageService.store_state` so that when updating an existing record (`adventure_id` is present), only `state_data`, `is_complete`, and `completed_chapter_count` are included in the update payload. This prevents overwriting the initially set `lesson_topic` and `story_category`.

5.  **Issue:** Summary chapter page (`/adventure/summary?state_id=...`) failed to load with a 500 Internal Server Error. Logs showed `Unexpected error serving summary data: 'StateStorageService' object has no attribute '_memory_cache'`.
    *   **Cause:** A debug log line in `app/services/summary/service.py` within the `get_adventure_state_from_id` method was attempting to access `self.state_storage_service._memory_cache`. This attribute was removed when `StateStorageService` was refactored to use Supabase, causing an `AttributeError` that crashed the API endpoint.
    *   **Fix:** Removed the outdated debug log line (`logger.info(f"Memory cache keys before retrieval: {list(self.state_storage_service._memory_cache.keys())}")`) from `app/services/summary/service.py`.

These fixes ensure the application correctly interacts with the defined Supabase schema and handles initial state creation properly.

## Phase 2 Testing Plan (Collaborative Approach)

This section outlines the manual testing steps to verify the Phase 2 Supabase integration. This requires collaboration: Cline (AI) will manage the backend server and ask verification questions, while the User will interact with the web application and check the Supabase dashboard/application logs.

**General Setup (Cline's Role - Act Mode):**
1.  Start the local FastAPI development server (e.g., `uvicorn app.main:app --reload`).
2.  Provide the local URL (e.g., `http://127.0.0.1:8000`) to the User.

**Test Cases:**

*   **[x] Test Case 1: New Adventure & Initial Save (Passed 2025-04-27)**
    *   **Goal:** Verify a new adventure is created in Supabase upon starting.
    *   **User Actions:**
        1.  Open the provided local URL in a browser.
        2.  Select a Story Category and Lesson Topic.
        3.  Click "Start Adventure".
        4.  Wait for the first chapter content to load.
        5.  Open the Supabase dashboard, navigate to the Table Editor, and view the `adventures` table.
        6.  Check the application's terminal logs.
    *   **Cline Verification Questions:**
        *   "Is there a new row in the `adventures` table?"
        *   "Does the new row have the correct `story_category` and `lesson_topic` you selected?"
        *   "Is the `is_complete` column `false` for the new row?"
        *   "Did you see any errors in the terminal logs related to `store_state`?"
    *   **Result:** Passed. New row created correctly with expected initial data. No errors logged.

*   **[x] Test Case 2: Progress & Mid-Adventure Save (Passed 2025-04-27)**
    *   **Goal:** Verify adventure state is updated in Supabase during progress.
    *   **User Actions:**
        1.  Continue the adventure from Test Case 1 for 1-2 chapters, making choices.
        2.  Re-check the corresponding row for this adventure in the Supabase `adventures` table.
        3.  Check the application's terminal logs.
    *   **Cline Verification Questions:**
        *   "Has the `updated_at` timestamp changed for the adventure row compared to Test Case 1?"
        *   "Has the `completed_chapter_count` increased correctly (e.g., to 1 or 2)?"
        *   "If you inspect the `state_data` JSON, does it contain the details of the chapter(s) you just completed?"
        *   "Did you see any errors in the terminal logs during the save operations?"
    *   **Result:** Passed. `updated_at`, `completed_chapter_count`, and `state_data` updated correctly in Supabase. No errors logged.

*   **[PASSED] Test Case 3: Resume Adventure (Passed 2025-05-19)**
    *   **Goal:** Verify an incomplete adventure can be resumed successfully, displaying the content of the chapter the user was on before disconnection.
    *   **Fix Implemented (2025-05-19):**
        1.  Enhanced `app/services/websocket/stream_handler.py` (`stream_chapter_content` function) to accept resumption-specific parameters. When resuming, it now uses pre-existing chapter data and bypasses new LLM calls and image generation for the resumed chapter.
        2.  Modified `app/routers/websocket_router.py`:
            *   Upon successful state load on reconnection, it now proactively calls the enhanced `stream_chapter_content` to re-send the last incomplete chapter's content.
            *   It now correctly handles and ignores the initial "start" message from the client post-resumption, preventing premature chapter advancement.
            *   Resolved an `AttributeError: 'dict' object has no attribute 'dict'` that occurred when preparing data for `stream_chapter_content` during resumption (specifically with `chapter_to_display_data.question`).
            *   Resolved an `ImportError` for `ChapterChoice` by correcting it to `StoryChoice` in `app/services/websocket/stream_handler.py`.
    *   **Result (Updated 2025-05-20):** Adventure text and choice resumption now works correctly, including for the final CONCLUSION chapter (Chapter 10). The application re-sends the content of the chapter the user was on before disconnection (or sends `story_complete` if resuming at CONCLUSION). For chapters 1-9, no new content/image is generated until the user makes a choice for the resumed chapter. For Chapter 10 resumption, image generation is currently re-triggered by the `send_story_complete` flow (see "Future Enhancements & Observations" section for more details).

*   **[x] Test Case 4: Complete Adventure (Passed 2025-05-20)**
    *   **Goal:** Verify the adventure is marked as complete in Supabase.
    *   **User Actions:**
        1.  Play through an entire adventure until the CONCLUSION chapter is finished.
        2.  Click the button to trigger the summary generation (e.g., "Take a Trip Down Memory Lane").
        3.  Wait for the `summary_ready` message/navigation trigger.
        4.  Check the adventure's row in the Supabase `adventures` table.
        5.  Check the application's terminal logs.
    *   **Cline Verification Questions:**
        *   "Is the `is_complete` flag now set to `true` in the Supabase table for that adventure row?"
        *   "Did you see any errors during the final state save in the logs?"

*   **[x] Test Case 5: Summary Retrieval (Passed 2025-05-20)**
    *   **Goal:** Verify the summary page correctly loads the state from Supabase.
    *   **User Actions:**
        1.  After completing Test Case 4, the application should navigate to the summary page URL (e.g., `/adventure/summary?state_id=...`).
        2.  Verify the summary page loads and displays content.
        3.  Check the application's terminal logs for activity related to the `/adventure/api/adventure-summary` endpoint.
    *   **Cline Verification Questions:**
        *   "Did the summary page load successfully using the correct `adventure_id` in the URL?"
        *   "Did you see logs indicating the state was retrieved successfully for the summary API endpoint (e.g., 'Successfully retrieved state with ID: ...')?"

*   **[x] Test Case 6: Multiple Incomplete Adventures (Optional) (Passed 2025-05-20)**
    *   **Goal:** Verify the system correctly identifies and resumes the specific adventure requested.
    *   **User Actions:**
        1.  Start Adventure A (e.g., Story 1 / Lesson 1), complete 2 chapters, then disconnect (close tab).
        2.  Start Adventure B (e.g., Story 2 / Lesson 2), complete 3 chapters, then disconnect (close tab).
        3.  Attempt to resume Adventure A by selecting Story 1 / Lesson 1. Observe the loaded chapter. Disconnect.
        4.  Attempt to resume Adventure B by selecting Story 2 / Lesson 2. Observe the loaded chapter.
    *   **Cline Verification Questions:**
        *   "When you tried to resume Adventure A, did it load Chapter 3?"
        *   "When you tried to resume Adventure B, did it load Chapter 4?"

**Monitoring:** Throughout all tests, both User and Cline should monitor the application terminal logs for any unexpected errors or warnings, particularly those related to `StateStorageService` or Supabase interactions.


## Phase 3: Telemetry (Supabase Database) - *Deferred until Persistent State (including resume) is complete*

- [x] **1. Define Database Schema (`telemetry_events` table):**
    *   [x] Using Supabase CLI migrations, create a table named `telemetry_events`. This approach provides version control for database schema changes.
    *   [x] **Setup Steps:**
        *   [x] Create a new migration (`npx supabase migration new create_telemetry_events_table_manual` - manual approach due to Docker issue, then `npx supabase db push` to apply `20250520134659_create_telemetry_events_table_manual.sql`)
        *   [x] Define the table schema in the generated SQL file (`20250520134659_create_telemetry_events_table_manual.sql` created and populated)
        *   [x] Apply the migration (`npx supabase db push` executed successfully)
    *   [x] **Define Columns:** (Ensured by migration `20250520134659_create_telemetry_events_table_manual.sql`)
        *   `id` (BIGSERIAL, Primary Key - using sequence for high insert rate)
        *   `event_name` (TEXT, Not Null) - e.g., 'adventure_started', 'chapter_viewed', 'choice_made', 'summary_viewed'.
        *   `adventure_id` (UUID, Nullable, Foreign Key -> `adventures.id` - *optional if event is not adventure-specific*)
        *   `user_id` (UUID, Nullable - *links to `auth.users` if Auth implemented*)
        *   `timestamp` (TimestampTZ, default: `now()`)
        *   `metadata` (JSONB, Nullable) - Store event-specific details (e.g., `{"chapter_number": 1, "story_category": "...", "lesson_topic": "..."}`, `{"chapter_number": 3, "duration_ms": 45000}`, `{"choice_index": 0}`).

- [x] **2. Integrate Telemetry Logging in Backend:**
    *   [x] Create a utility function or service (e.g., `log_telemetry(event_name, adventure_id=None, user_id=None, metadata=None)`). This function will insert a record into the `telemetry_events` table using the Supabase client. (Implemented as `TelemetryService` in `app/services/telemetry_service.py`)
    *   [x] Call this logging function at relevant points in the code:
        *   [x] **Adventure Start:** Log 'adventure_started' with chosen topics. (Integrated in `app/routers/websocket_router.py`)
        *   [x] **Chapter View:** Log 'chapter_viewed' when sending chapter content. (Integrated in `app/services/websocket/stream_handler.py`)
        *   [x] **Choice Made:** Log 'choice_made' when processing a user choice. (Integrated in `app/services/websocket/choice_processor.py`)
        *   [x] **Summary Viewed:** Log 'summary_viewed' when the summary API is successfully called. (Integrated in `app/routers/summary_router.py`)

### Debugging Notes (Phase 3 Completion)

During the implementation and testing of Phase 3 (Telemetry), the following issues were identified and resolved:

1.  **Issue:** `ModuleNotFoundError: No module named 'supabase_py_async'` on application startup.
    *   **Cause:** `TelemetryService` was incorrectly trying to import `supabase_py_async` instead of using the project's standard `supabase-py` library (imported as `supabase`).
    *   **Fix:** Modified `app/services/telemetry_service.py` to import `create_client` and `Client` from the `supabase` package, aligning it with existing dependencies.

2.  **Issue:** Error logged: `"Could not find the 'environment' column of 'telemetry_events' in the schema cache"` when trying to log telemetry events.
    *   **Cause:** The `TelemetryService` was attempting to write to an `environment` column that was not defined in the `telemetry_events` table schema.
    *   **Fix:**
        *   Created a new Supabase migration (`supabase/migrations/20250520222700_add_environment_to_telemetry_events.sql`) to add an `environment TEXT NULL DEFAULT 'unknown'` column to the `telemetry_events` table.
        *   Applied the migration using `npx supabase db push`.

3.  **Issue:** Error logged: `"object APIResponse[~_ReturnT] can't be used in 'await' expression"` when `TelemetryService` logged events, although data was still inserted.
    *   **Cause:** The `.execute()` method of the `supabase-py` client for insert operations was returning a non-awaitable `APIResponse` object directly, causing a `TypeError` when `await` was used on it.
    *   **Fix:** Removed the `await` keyword from the `.execute()` call for insert operations within `app/services/telemetry_service.py`, as the operation appeared to complete successfully regardless.

4.  **Issue:** Error logged: `'AdventureState' object has no attribute 'story_category'` (and similarly for `lesson_topic`) when logging `chapter_viewed` events.
    *   **Cause:** The `chapter_viewed` event logging in `app/services/websocket/stream_handler.py` was attempting to access `state.story_category` and `state.lesson_topic` directly, but these attributes are not defined on the `AdventureState` model.
    *   **Fix:**
        *   Modified the `stream_chapter_content` function in `app/services/websocket/stream_handler.py` to accept `story_category` and `lesson_topic` as explicit parameters.
        *   Updated the calls to `stream_chapter_content` in `app/routers/websocket_router.py` to pass these parameters.
        *   The telemetry metadata now correctly uses these passed-in values.
        *   Confirmed that `memory-bank/techContext.md` correctly does not list these as direct attributes of `AdventureState`, so no documentation update was needed for that specific point.

These fixes ensure that telemetry events are logged reliably and without errors.

### Phase 3.1: Enhance `telemetry_events` Table and Logging

- [x] **Goal:** Add dedicated columns for `chapter_type`, `chapter_number`, and `event_duration_seconds` (formerly `event_duration_ms`) to the `telemetry_events` table for improved queryability and analytics. Implement logging for these new columns. (Note: User has cleared existing telemetry data, so no backfilling is required).

**Implementation Steps (Completed):**

- [x] **1. Database Schema Migration (SQL):**
    *   [x] **Action:** Create a new Supabase migration file (`supabase/migrations/20250521132807_add_detailed_telemetry_columns.sql`).
    *   [x] **SQL Content:**
        ```sql
        -- Add chapter_type column
        ALTER TABLE public.telemetry_events
        ADD COLUMN chapter_type TEXT NULL;

        COMMENT ON COLUMN public.telemetry_events.chapter_type IS 'The type of chapter the event relates to (e.g., story, lesson, reflect, conclusion, summary).';

        -- Add chapter_number column
        ALTER TABLE public.telemetry_events
        ADD COLUMN chapter_number INTEGER NULL;

        COMMENT ON COLUMN public.telemetry_events.chapter_number IS 'The specific chapter number within the adventure that this event pertains to.';

        -- Add event_duration_seconds column (formerly event_duration_ms)
        ALTER TABLE public.telemetry_events
        ADD COLUMN event_duration_seconds INTEGER NULL;

        COMMENT ON COLUMN public.telemetry_events.event_duration_seconds IS 'For events like choice_made, this can store the duration (in seconds) spent on the preceding chapter. For other events, it might be NULL or represent event processing time.';
        ```
    *   [x] **Apply Migration:** Run `npx supabase db push` in the terminal from the project root to apply the schema changes to your Supabase database.
        *   A second migration (`supabase/migrations/20250521133918_change_duration_to_seconds.sql`) was created and applied to rename `event_duration_ms` to `event_duration_seconds` and update its comment.

- [x] **2. Backend Code Updates for `chapter_type` and `chapter_number`:**
    *   [x] **Target File:** `app/services/telemetry_service.py`
        *   [x] **Action:** Modify the `TelemetryService.log_event` method.
            *   Update the method signature to include:
                ```python
                async def log_event(
                    self,
                    event_name: str,
                    adventure_id: Optional[UUID] = None,
                    user_id: Optional[UUID] = None,
                    metadata: Optional[Dict[str, Any]] = None,
                    chapter_type: Optional[str] = None,       # New parameter
                    chapter_number: Optional[int] = None,      # New parameter
                    event_duration_seconds: Optional[int] = None # Changed from event_duration_ms
                ):
                ```
            *   Update the `record` dictionary within `log_event` to include these new fields directly:
                ```python
                record = {
                    # ... existing fields like event_name, adventure_id, user_id, timestamp, environment, metadata ...
                    "chapter_type": chapter_type,
                    "chapter_number": chapter_number,
                    "event_duration_seconds": event_duration_seconds, # Changed from event_duration_ms
                }
                ```

    *   [x] **Target File:** `app/services/websocket/choice_processor.py` (specifically in the `process_non_start_choice` function where `choice_made` events are logged)
        *   [x] **Action:** When preparing to call `telemetry_service.log_event` for a `choice_made` event:
            *   Pass `previous_chapter.chapter_type.value` as the `chapter_type` argument.
            *   Pass `previous_chapter.chapter_number` as the `chapter_number` argument.
        *   **Example Snippet (conceptual):**
            ```python
            await telemetry_service.log_event(
                event_name="choice_made",
                adventure_id=UUID(current_adventure_id) if current_adventure_id else None,
                user_id=None,
                metadata=event_metadata, # Ensure this metadata itself no longer needs to redundantly store chapter_type/number if they are top-level
                chapter_type=previous_chapter.chapter_type.value,
                chapter_number=previous_chapter.chapter_number,
                event_duration_seconds=calculated_duration_seconds # Changed from event_duration_ms
            )
            ```

    *   [x] **Target File:** `app/services/websocket/stream_handler.py` (specifically in the `stream_chapter_content` function where `chapter_viewed` events are logged)
        *   [x] **Action:** When preparing to call `telemetry_service.log_event` for a `chapter_viewed` event:
            *   Identify the current chapter being streamed (e.g., `current_chapter = state.chapters[-1]`).
            *   Pass `current_chapter.chapter_type.value` as the `chapter_type` argument.
            *   Pass `current_chapter.chapter_number` as the `chapter_number` argument.
        *   **Note:** Ensure `story_category` and `lesson_topic` are also passed correctly if they are not already.

    *   [x] **Target File:** `app/routers/websocket_router.py` (where `adventure_started` events are logged)
        *   [x] **Action:** When logging `adventure_started`:
            *   `chapter_type` and `chapter_number` will likely be `None` or not applicable for this event. Pass `None`.

    *   [x] **Target File:** `app/routers/summary_router.py` (where `summary_viewed` events are logged)
        *   [x] **Action:** When logging `summary_viewed`:
            *   `chapter_type` could be set to the string `"summary"`.
            *   `chapter_number` could be `None`.

- [x] **3. Backend Code Updates for `event_duration_seconds` (Implementing Approach 1):**
    *   [x] **Goal:** Log the time spent on a chapter. This duration will be logged with the `choice_made` event and will represent the time elapsed since the previous `chapter_viewed` event for that chapter.

    *   [x] **Target File:** `app/services/telemetry_service.py` (if not already done in step 2)
        *   [x] **Action:** Modify the `TelemetryService.log_event` method signature:
            *   Change `event_duration_ms: Optional[int] = None` to `event_duration_seconds: Optional[int] = None`.
            *   Update the `record` dictionary within `log_event` to include `event_duration_seconds` (key changed from `event_duration_ms`).

    *   [x] **Target File:** `app/services/websocket/stream_handler.py` (function `stream_chapter_content`)
        *   [x] **Action:** Store the start timestamp when a chapter's content begins streaming.
            *   Import `time` at the top of the file: `import time`.
            *   Within `stream_chapter_content`, before or alongside logging the `chapter_viewed` event, and after ensuring `connection_data` is available and is a dictionary:
                ```python
                # Assuming 'connection_data' is accessible and is a dict
                if connection_data and isinstance(connection_data, dict):
                    connection_data['current_chapter_start_time_ms'] = int(time.time() * 1000)
                    logger.debug(f"Stored chapter start time for adventure_id {connection_data.get('adventure_id')}, chapter {state.chapters[-1].chapter_number if state.chapters else 'N/A'}")
                else:
                    logger.warning("'connection_data' not available or not a dict in stream_handler, cannot store chapter start time.")
                ```
                *(Ensure `connection_data` is properly passed to or accessible by `stream_chapter_content` if it's not already. This usually comes from the WebSocket connection scope or is passed through.)*

    *   [x] **Target File:** `app/services/websocket/choice_processor.py` (function `process_non_start_choice`)
        *   [x] **Action:** Calculate duration and pass it when logging the `choice_made` event.
            *   Import `time` at the top of the file: `import time`.
            *   Within `process_non_start_choice`, before calling `telemetry_service.log_event` for `choice_made`:
                ```python
                calculated_duration_ms: Optional[int] = None
                if connection_data and isinstance(connection_data, dict):
                    start_time_ms = connection_data.pop('current_chapter_start_time_ms', None)
                    if start_time_ms is not None:
                        current_time_ms = int(time.time() * 1000)
                        calculated_duration_ms = current_time_ms - start_time_ms
                        logger.info(f"Calculated time spent on chapter {previous_chapter.chapter_number}: {calculated_duration_ms} ms")
                    else:
                        logger.warning(f"Could not find 'current_chapter_start_time_ms' in connection_data for chapter {previous_chapter.chapter_number}. Duration will be null.")
                else:
                    logger.warning("'connection_data' not available or not a dict in choice_processor, cannot calculate duration.")

                # ... then, when calling log_event for 'choice_made':
                calculated_duration_seconds: Optional[int] = None
                if calculated_duration_ms is not None:
                    calculated_duration_seconds = round(calculated_duration_ms / 1000)

                await telemetry_service.log_event(
                    # ... other parameters like event_name, adventure_id, chapter_type, chapter_number ...
                    event_duration_seconds=calculated_duration_seconds, # Pass the calculated duration in seconds
                    metadata=event_metadata # Ensure metadata is still passed for other details
                )
                ```
        *   **Important Note for the implementing assistant:** The `event_duration_seconds` logged with a `choice_made` event here represents the time spent on the *preceding chapter* (i.e., the time from when its content was sent until this choice was made), converted to seconds.

- [x] **4. Testing:**
    *   [x] After implementing these changes, thoroughly test the telemetry logging:
        *   Start new adventures.
        *   Progress through different chapter types (STORY, LESSON).
        *   Verify in the Supabase `telemetry_events` table that:
            *   The new columns (`chapter_type`, `chapter_number`, `event_duration_seconds`) are populated correctly for relevant events.
            *   `event_duration_seconds` has plausible values (in seconds) for `choice_made` events.
            *   Other events correctly have `NULL` or appropriate values for these new columns.

**Completion Note (2025-05-21):** Phase 3.1 is complete. The `event_duration_ms` column was successfully renamed to `event_duration_seconds`, and all related backend code was updated to calculate and store this duration in seconds. Testing confirmed the correct population of new telemetry columns.

- [x] **3. Analytics:** *(Completed 2025-05-21, per user confirmation)*
    *   [x] Use SQL queries directly in the Supabase dashboard or connect a BI tool to analyze the data in `adventures` and `telemetry_events` tables.
    *   [x] Define key metrics and create corresponding SQL queries (e.g., topic popularity, average adventure length, common drop-off points). Example Queries:
        *   `SELECT story_category, COUNT(*) FROM adventures GROUP BY story_category ORDER BY COUNT(*) DESC;`
        *   `SELECT event_name, COUNT(*) FROM telemetry_events WHERE timestamp > now() - interval '7 days' GROUP BY event_name;`
        *   Analyze `metadata` JSONB fields for deeper insights.

## Phase 4: Optional User Authentication (Supabase Auth) - Detailed Plan

This phase implements optional user authentication using Supabase Auth, allowing users to sign in with Google or continue as an anonymous (Supabase-managed) guest.

**Key Decisions Made:**
*   **Login Page:** A new dedicated login page will be created at the root path (`/`).
*   **Carousel Page Path:** The existing adventure selection (carousel) page will move to `/select`.
*   **JWT Handling:** Session management and JWT persistence across pages will rely on the Supabase JS client library's default behavior using browser localStorage.
*   **Foreign Key Behavior:** When a user is deleted from `auth.users`, the `user_id` in the `adventures` and `telemetry_events` tables will be `SET NULL`.

**Implementation Steps:**

**0. Create Basic Landing/Login Page (Cline - Act Mode)**
    *   [x] **0.1. New HTML File:** Create `app/templates/pages/login.html`. (Used existing `app/static/landing/index.html` and moved to `app/templates/pages/login.html`, then adapted).
        *   This page will serve as the initial entry point for users.
    *   [x] **0.2. New FastAPI Route:**
        *   Modify `app/routers/web.py`.
        *   Create a route to serve `login.html` at `/`.
        *   Update the existing route for `app/templates/pages/index.html` (the carousel page) to serve it at `/select`.
    *   [x] **0.3. Basic Structure for `login.html`:**
        *   Include a title (e.g., "Welcome to Learning Odyssey").
        *   Add a "Login with Google" button.
        *   Add a "Continue as Guest" button.
        *   Minimal styling, to be enhanced later during a full landing page overhaul. (Button colors adjusted based on feedback).
    *   [x] **0.4. Ensure Supabase JS Client is available on `login.html`:**
        *   The page should include or extend a base template that initializes the Supabase JS client (similar to how `base.html` does for the current `index.html`). (Supabase client init script added directly to `login.html` and configured to use Jinja variables for keys).

**1. Configure Supabase Auth (User Task - Requires Supabase Dashboard & Google Cloud Console Access)** *(User confirmed completed 2025-05-22)*
    *   [x] **1.1. Enable Google Provider:**
        *   In the Supabase project dashboard (Authentication -> Providers), enable "Google".
        *   This requires setting up OAuth 2.0 credentials in Google Cloud Console:
            *   Create/use a Google Cloud Project.
            *   Enable necessary APIs (e.g., Google Identity Platform).
            *   Configure the OAuth Consent Screen.
            *   Create OAuth 2.0 Client ID credentials (Application type: Web application).
                *   **Authorized JavaScript origins:** Add your app's URLs (e.g., `http://localhost:8000`, production URL).
                *   **Authorized redirect URIs:** Add the redirect URI provided by Supabase (e.g., `https://<your-supabase-project-ref>.supabase.co/auth/v1/callback`).
            *   Copy the generated Client ID and Client Secret into the Supabase Google provider settings.
    *   [x] **1.2. Enable Anonymous Sign-ins:**
        *   In the Supabase project dashboard (Authentication -> Providers or Settings), enable "Anonymous sign-ins".
    *   [x] **1.3. Obtain JWT Signing Secret (or JWKS URL):**
        *   In the Supabase project dashboard (Project Settings -> API -> JWT Settings), find the JWT signing secret or the JWKS URI. This will be needed for backend JWT verification. Store this securely (e.g., as `SUPABASE_JWT_SECRET` in `.env` and Railway).

**2. Implement Frontend Logic (Cline - Act Mode)**
    *   [x] **2.1. Authentication UI on `login.html`:** (Effectively completed as part of Step 0.3. UI elements for login buttons are present.)
    *   [x] **2.2. Supabase JS Client Auth Logic on `login.html`:** (Core logic implemented and functional after client initialization fixes on 2025-05-22. Includes button listeners for `signInWithOAuth` and `signInAnonymously`, and an `onAuthStateChange` handler for redirects. Guest warning display is also present.)
        *   In a script tag within `login.html` or an included JS file:
            *   Attach event listener to "Login with Google" button to call `supabase.auth.signInWithOAuth({ provider: 'google' })`.
            *   Attach event listener to "Continue as Guest" button to call `supabase.auth.signInAnonymously()`.
            *   Implement `supabase.auth.onAuthStateChange((event, session) => { ... })`:
                *   If `event === 'SIGNED_IN'`:
                    *   Redirect the user to `/select` (the carousel page).
                *   If `event === 'SIGNED_OUT'`:
                    *   (User is on login page, perhaps show a "Logged out" message or simply ensure login buttons are active).
            *   Display a warning message for anonymous users (e.g., "As a guest, your adventure progress is tied to this browser session.").
    *   [x] **2.3. Auth Handling on Carousel Page (`/select` - `app/templates/pages/index.html` & `app/templates/components/scripts.html`):** (Verified existing implementation covers requirements as of 2025-05-22)
        *   On page load, use `supabase.auth.getSession()` to retrieve the current session.
        *   If no active session (or token is invalid/expired), redirect user back to `/` (login page).
        *   If a session exists, extract the `access_token` (JWT).
        *   Modify `WebSocketManager` (or equivalent script) to pass this JWT when establishing the WebSocket connection (e.g., as a query parameter: `ws://.../ws/story/.../?token=JWT_HERE`).
        *   Implement a logout button/mechanism that calls `supabase.auth.signOut()` and redirects to `/`.
        *   Update UI to display user status (e.g., "Logged in as user@example.com" or "Playing as Guest") and the logout button.

### Debugging Log and Current Status (Phase 4 Frontend - Step 2 as of 2025-05-22 PM)

Work on implementing the frontend logic for user authentication (Step 2) has involved significant debugging. Here's a summary:

**Initial Problem Encountered:**
*   Buttons on the landing page (`/`, served by `app/templates/pages/login.html`) were unresponsive.
*   The browser console initially showed:
    *   Warnings: "Supabase URL not configured. Using placeholder..."
    *   Warnings: "Supabase Anon Key not configured. Using placeholder..."
    *   Error: "TypeError: Cannot read properties of undefined (reading 'createClient')"
    *   This indicated issues with Supabase client initialization, likely due to missing credentials in the JavaScript.

**Investigation and Actions Taken:**

1.  **Server-Side Verification (`.env`, `app/main.py`, `app/routers/web.py`):**
    *   User confirmed `.env` file has correct `SUPABASE_URL` and `SUPABASE_ANON_KEY`.
    *   Confirmed `load_dotenv()` is called at the start of `app/main.py`.
    *   Added debug logging to `app/routers/web.py` for the `/` and `/select` routes.
    *   **Result:** Python server logs clearly showed that `os.getenv()` was correctly retrieving the Supabase URL and Key, and these non-empty values were being passed into the Jinja template context for `pages/login.html` and `pages/index.html`.

2.  **Client-Side Investigation - `app/templates/pages/login.html`:**
    *   **Initial Analysis:** The "View Page Source" for `/` revealed that Jinja *was* correctly rendering the actual Supabase URL and Key into the script block within `login.html` (this was from an older version of the script in `login.html` that had hardcoded values, which was misleading initially, but later confirmed Jinja was working for `{{ supabase_url }}`).
    *   **Identified Issues in `login.html` script:**
        1.  Flawed `if` conditions for checking if URL/Key were placeholders were incorrectly triggering console warnings.
        2.  The Supabase client initialization `supabase = supabase.createClient(...)` was using a locally declared, uninitialized `supabase` variable instead of the global `window.supabase` (the Supabase library object from the CDN). This was causing the "TypeError" and the "Could not initialize authentication" alert.
    *   **Server-Side Fix:** A `jinja2.exceptions.TemplateSyntaxError: unexpected '.'` occurred due to a JavaScript comment in `login.html` containing `{{...}}`. This was fixed by rephrasing the comment.
    *   **Client-Side Fix:** The script in `login.html` was updated (on 2025-05-22) to:
        *   Correctly use `window.supabase.createClient(...)` for initialization.
        *   Store the client instance in `loginPageSupabaseClient`.
        *   Update subsequent auth calls (button listeners, `onAuthStateChange`) to use `loginPageSupabaseClient`.
        *   Refine the checks for whether Jinja rendered the URL/Key.

### Not implemented yet

3.  **Client-Side Investigation - `app/templates/base.html` (Caching Issue):**
    *   **Hypothesis:** The initial errors and warnings might also be related to `base.html` (which `login.html` extends) not having the Supabase credentials or its script failing, or the browser serving a cached version of `base.html`.
    *   **Action:** The script in `base.html` was simplified to *only* contain `console.log` statements to print the raw and default-filtered values of `{{ supabase_url }}` and `{{ supabase_anon_key }}`, with all other Supabase client initialization logic commented out.
    *   **User Verification:** User confirmed the `base.html` file on disk contains this simplified debug script.
    *   **Result:** Despite server restarts, hard refreshes, and Incognito mode, the browser console **does not show these new `[DEBUG base.html]...` log lines.** It continues to show the old warnings and errors (from a previous state of `base.html`'s script) with their original line numbers.
    *   **Conclusion:** This strongly indicates the browser is not loading the current version of `base.html`.

**Current Status (after `login.html` script update):**
*   The server starts without the `TemplateSyntaxError`.
*   When loading the landing page (`/`):
    *   The Python server logs confirm correct Supabase URL/Key are fetched and sent to the template context.
    *   The browser console now shows (from the updated `login.html` script):
        *   Warning: "Supabase URL or Anon Key was not properly rendered by Jinja in login.html, or they are empty."
        *   Error: "Supabase client instance (loginPageSupabaseClient) is null. Login buttons will not function."
    *   The login buttons are still not working.
    *   The `[DEBUG base.html]` logs (from the simplified `base.html` debug script) were **initially not appearing** in the console, indicating a caching issue.
    *   The "Could not initialize authentication" alert from `login.html` was occurring.

**Debugging Steps and Resolutions (2025-05-22 Evening):**

1.  **Verified Jinja Rendering to `login.html`:**
    *   User confirmed via "View Page Source" that `LOGIN_PAGE_SUPABASE_URL` and `LOGIN_PAGE_SUPABASE_ANON_KEY` in `login.html` were correctly rendered with actual credential values by Jinja.

2.  **Diagnosed Flawed JS Condition in `login.html`:**
    *   Added granular `console.log` statements to the `if` condition in `login.html`'s script.
    *   **Finding:** The condition `LOGIN_PAGE_SUPABASE_URL !== '{{ supabase_url }}'` (and similarly for the key) was evaluating to `false` because `LOGIN_PAGE_SUPABASE_URL` held the *actual URL*, not the literal placeholder string. This incorrectly caused the overall condition to fail.
    *   **Fix (Applied 2025-05-22):** Corrected the `if` condition in `login.html` to `if (LOGIN_PAGE_SUPABASE_URL && LOGIN_PAGE_SUPABASE_URL !== '' && LOGIN_PAGE_SUPABASE_ANON_KEY && LOGIN_PAGE_SUPABASE_ANON_KEY !== '')`.
    *   **Result:** `loginPageSupabaseClient` in `login.html` now initializes successfully. "Login with Google" button became functional. "Continue as Guest" initially led to an infinite redirect loop.

3.  **Addressed `base.html` Caching/Loading and Client Initialization:**
    *   **Action 1:** Added a unique "cache-breaker" `console.log` line to `app/templates/base.html`.
    *   **User Verification:** Confirmed the new cache-breaker log and other `[DEBUG base.html]` logs (showing correct Jinja-rendered URL/Key) appeared in the console when `login.html` (which redirects to `/select`, which uses `base.html`) was loaded. This indicated `base.html` was now loading its latest script.
    *   **Action 2 (Applied 2025-05-22):** Uncommented and refined the Supabase client initialization logic within `app/templates/base.html`. This script now attempts to create a Supabase client instance using the Jinja-provided URL/Key and assign it to the global `window.supabase`.
    *   **Result:** The "Continue as Guest" button on `login.html` no longer causes an infinite redirect loop. Users can sign in anonymously and are correctly redirected to `/select`, which now appears to function correctly with the session.

**Current Status (End of 2025-05-22):**
*   The foundational Supabase JavaScript client initialization issues on both `login.html` (local client) and `base.html` (global client for other pages like `/select`) are **resolved**.
*   Both "Login with Google" and "Continue as Guest" functionalities on `login.html` appear to be working, redirecting to `/select` without an infinite loop.
*   This completes the initial troubleshooting and unblocks further work on Step 2.3.

**Next Steps (Proceeding with Phase 4, Step 2.3):**

The following tasks from Step 2.3 ("Auth Handling on Carousel Page (`/select`)") are now the focus:

1.  **On page load for `/select`, use `window.supabase.auth.getSession()` to retrieve the current session.**
    *   If no active session (or token is invalid/expired), redirect the user back to `/` (login page).
2.  **If a session exists, extract the `access_token` (JWT).**
3.  **Modify `WebSocketManager` (or equivalent script for `/select`) to pass this JWT when establishing the WebSocket connection.** (e.g., as a query parameter: `ws://.../ws/story/.../?token=JWT_HERE`).
4.  **Implement a logout button/mechanism on `/select` that calls `window.supabase.auth.signOut()` and then redirects to `/`.**
5.  **Update UI on `/select` to display user status (e.g., "Logged in as user@example.com" or "Playing as Guest") and the logout button.**

This detailed logging should help us understand if the issue is server-side template rendering/caching or client-side script execution and caching.

**3. Implement Backend Logic (Cline - Act Mode)**
    *   [ ] **3.1. Add `PyJWT` to `requirements.txt`:**
        *   And run `pip install -r requirements.txt`.
    *   [ ] **3.2. Create JWT Verification Dependency:**
        *   Create `app/auth/dependencies.py`.
        *   Implement a FastAPI dependency `get_current_user_id_optional(token: Optional[str] = Query(None)) -> Optional[UUID]:`
            *   If `token` is provided:
                *   Verify the JWT using `PyJWT` and the `SUPABASE_JWT_SECRET` (or JWKS).
                *   If valid, extract and return the `user_id` (from `sub` claim, cast to UUID).
                *   If invalid, log a warning and return `None` (or raise HTTPException if auth becomes mandatory for some routes later).
            *   If no `token`, return `None`.
    *   [ ] **3.3. Integrate Auth into WebSocket Router (`app/routers/websocket_router.py`):**
        *   Update the WebSocket endpoint (`@router.websocket("/ws/story/{story_category}/{lesson_topic}")`) to accept the `token` as an optional query parameter.
        *   In the connection logic, call `get_current_user_id_optional(token)` to get the `user_id`.
        *   Store this `user_id` (which can be `None`) in the `connection_data` dictionary (e.g., `connection_data["user_id"] = user_id`).
    *   [ ] **3.4. Pass `user_id` to Services:**
        *   **`StateStorageService` (`app/services/state_storage_service.py`):**
            *   Ensure `store_state` method correctly uses the `user_id` passed to it (already an optional param).
            *   Modify `get_active_adventure_id(client_uuid: str, user_id: Optional[UUID] = None)`:
                *   Prioritize querying by `user_id` if provided.
                *   If `user_id` is `None`, fall back to querying by `client_uuid` (from `state_data->'metadata'->>'client_uuid'`) for non-authenticated users or legacy data.
        *   **`TelemetryService` (`app/services/telemetry_service.py`):**
            *   Ensure `log_event` method correctly uses the `user_id` passed to it (already an optional param).
        *   **Update Callers:** Modify `websocket_router.py` to pass `connection_data.get("user_id")` to these service methods.
    *   [ ] **3.5. Update Database Interactions in Services:**
        *   `StateStorageService.store_state`: When preparing the `record` for Supabase, include the `user_id` if it's not `None`.
        *   `TelemetryService.log_event`: When preparing the `record` for Supabase, include the `user_id` if it's not `None`.

**4. Update Database Schema/RLS (Cline - Act Mode)**
    *   [ ] **4.1. Create Supabase Migration:**
        *   Run `npx supabase migration new add_auth_fks_and_rls` (or similar name).
        *   In the generated SQL file, add:
            ```sql
            -- Link adventures.user_id to auth.users
            ALTER TABLE public.adventures
            ADD CONSTRAINT fk_adventures_auth_users FOREIGN KEY (user_id)
            REFERENCES auth.users (id) ON DELETE SET NULL;

            COMMENT ON COLUMN public.adventures.user_id IS 'Links to the authenticated user in auth.users table. SET NULL on user deletion.';

            -- Link telemetry_events.user_id to auth.users
            ALTER TABLE public.telemetry_events
            ADD CONSTRAINT fk_telemetry_events_auth_users FOREIGN KEY (user_id)
            REFERENCES auth.users (id) ON DELETE SET NULL;

            COMMENT ON COLUMN public.telemetry_events.user_id IS 'Links to the authenticated user in auth.users table. SET NULL on user deletion.';

            -- Ensure RLS is enabled on telemetry_events (already enabled on adventures)
            ALTER TABLE public.telemetry_events ENABLE ROW LEVEL SECURITY;

            -- RLS Policies for 'adventures' table
            -- Drop old service key policy if it was too broad
            -- Example: DROP POLICY IF EXISTS "Allow backend access via service key" ON public.adventures;

            -- Allow service_role full access (bypasses other RLS)
            CREATE POLICY "Adventures service_role full access" ON public.adventures
            FOR ALL USING (true) WITH CHECK (true); -- Or specify TO service_role if preferred

            CREATE POLICY "Users can select their own or guest adventures" ON public.adventures
            FOR SELECT USING (auth.uid() = user_id OR user_id IS NULL);

            CREATE POLICY "Users can insert adventures for themselves or as guest" ON public.adventures
            FOR INSERT WITH CHECK (auth.uid() = user_id OR user_id IS NULL); -- For anonymous Supabase users, auth.uid() is their anon ID

            CREATE POLICY "Users can update their own adventures" ON public.adventures
            FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
            
            CREATE POLICY "Users can delete their own adventures" ON public.adventures
            FOR DELETE USING (auth.uid() = user_id);

            -- RLS Policies for 'telemetry_events' table
            -- Allow service_role full access
            CREATE POLICY "Telemetry service_role full access" ON public.telemetry_events
            FOR ALL USING (true) WITH CHECK (true); -- Or specify TO service_role

            CREATE POLICY "Users can insert their own telemetry" ON public.telemetry_events
            FOR INSERT WITH CHECK (auth.uid() = user_id OR user_id IS NULL);
            
            -- Generally, select/update/delete on telemetry might be restricted or admin-only
            CREATE POLICY "Users can select their own telemetry" ON public.telemetry_events
            FOR SELECT USING (auth.uid() = user_id OR user_id IS NULL);
            ```
    *   [ ] **4.2. Apply Migration:**
        *   Run `npx supabase db push`.

**5. Testing (User & Cline - Collaborative)**
    *   [ ] Test Google Login flow.
    *   [ ] Test "Continue as Guest" (Supabase anonymous sign-in) flow.
    *   [ ] Verify `user_id` is populated in `adventures` and `telemetry_events` for authenticated and Supabase anonymous users.
    *   [ ] Verify `user_id` is `NULL` for adventures/telemetry created by truly unauthenticated flows (if any remain possible, or for legacy data).
    *   [ ] Test adventure resumption for Google users.
    *   [ ] Test adventure resumption for Supabase anonymous users.
    *   [ ] Test RLS policies (e.g., ensure one user cannot access another's data if they tried to manipulate client-side calls, though our app flow doesn't directly allow this).
    *   [ ] Test logout functionality (redirects to `/`, session cleared).
    *   [ ] Test behavior if user tries to access `/select` without being logged in (should redirect to `/`).

## Considerations & Next Steps

*   [ ] **User Identification:** Define how to identify users for resuming adventures (e.g., session ID, browser fingerprint, anonymous user ID from Supabase Auth, full user ID). This is critical for the `get_active_adventure_id` method to work properly.
*   [ ] **Error Handling:** Implement robust error handling for all Supabase interactions (DB writes/reads, auth).
*   [ ] **Data Migration:** Plan how to handle any existing state data (if applicable, though current state is transient).
*   [ ] **Testing:** Update existing tests and create new ones to cover Supabase interactions, periodic saves, and resume functionality.
*   [ ] **Scalability:** Monitor Supabase usage and scale the database plan if necessary. Consider database indexing for performance as data grows.
*   [ ] **Security:** Ensure RLS policies are correctly implemented if data access needs restriction beyond backend service key access. Review Supabase security best practices.
*   [ ] **Client-side State:** Decide how much state still needs to be managed client-side (e.g., current chapter content being streamed) vs. relying solely on backend/DB state.

This plan provides a structured approach. 

## Current Status (As of 2025-05-20)

**Phase 2 (Persistent Adventure State) is now complete and validated.** All planned test cases, including adventure creation, progress saving, resumption (including at Chapter 10/CONCLUSION), adventure completion marking, and summary retrieval, have passed. The system correctly handles state persistence and resumption using Supabase.

**Key Fixes and Achievements in Phase 2 (Relevant to Persistence/Resumption):**
- Supabase project setup, library integration, and secure environment variable configuration completed.
- `adventures` table schema defined and migrated, including `environment` and `client_uuid` columns.
- `StateStorageService` (`app/services/state_storage_service.py`):
    - Refactored to use Supabase.
    - `store_state` method enhanced with an `explicit_is_complete` parameter for precise control over when an adventure is marked complete.
    - `get_active_adventure_id` updated for correct querying.
- `AdventureStateManager` (`app/services/adventure_state_manager.py`):
    - `reconstruct_state_from_storage` method fixed.
- WebSocket Router (`app/routers/websocket_router.py`):
    - Logic updated to correctly save state with `explicit_is_complete=False` after CONCLUSION chapter content generation, allowing resumption.
    - Logic added to handle client "start" messages appropriately when resuming at a completed CONCLUSION chapter (re-sends `story_complete`).
- Choice Processor (`app/services/websocket/choice_processor.py`):
    - `generate_conclusion_chapter_summary` updated to call `store_state` with `explicit_is_complete=True` when the summary is revealed.
- Integration of state storage into WebSocket/API flows for initial save, progress updates, and completion marking is robust.
- All Phase 2 test cases (1-6) have passed.

**Immediate Next Steps:**

1.  **Proceed to Phase 3 (Telemetry):** Define schema, integrate logging, and plan analytics. *(Phase 3.1 completed 2025-05-21)*
2.  **Evaluate Phase 4 (User Authentication):** Based on product requirements after Phase 3.
3.  **Address Future Enhancements & Observations:** Review items noted for future consideration (e.g., image re-generation consistency on resume).


## Future Enhancements & Observations (Post-Phase 2)

### Image Handling on Chapter Resume

#### Current Behaviors

- **Chapter 10 (CONCLUSION):**
    - When resuming at Chapter 10, the image is **re-generated on each refresh**. This is because the resumption flow uses `send_story_complete`, which always triggers image generation.
    - This behavior has been observed and is considered acceptable. Some users find the consistent re-generation "strangely consistent."

- **Chapters 1-9:**
    - When resuming at chapters 1-9, the system uses `stream_chapter_content` with `is_resumption=True`.
    - In this flow, **new image generation is bypassed** for speed and to avoid unnecessary processing.
    - However, the original image for the resumed chapter is **not currently re-displayed** to the user.

#### To-Do / Known Issue

- **Resuming Chapter Image Display (Chapters 1-9):**
    - **Goal:** When resuming an adventure at chapters 1-9, display the original image associated with that chapter.
    - **Current Limitation:** The image is not re-displayed because image generation is skipped and the original image is not retrieved.

#### Future Considerations

- **Consistent Image Re-generation:**
    - Consider extending the image re-generation logic (currently only for Chapter 10) to chapters 1-9 for a more dynamic and consistent user experience.
    - This would involve modifying `stream_chapter_content` to optionally trigger image generation when `is_resumption=True`, and updating client-side handling.
    - Estimated complexity: Low-to-medium, as it mainly involves adapting existing logic.

#### Potential Solutions (for Chapters 1-9 Image Display)

1. **Store Image Base64 in `ChapterData` (Medium Complexity)**
    - Add an optional field (e.g., `image_base64: Optional[str]`) to the `ChapterData` model in `app/models/story.py`.
    - When generating an image for a chapter, store its base64 representation in this field within the `AdventureState`.
    - On resumption, retrieve this base64 string and send it to the client for display.
    - *Considerations:* Increases the size of `state_data` in Supabase. To optimize, you could store only the most recent chapter's image, at the cost of not supporting images for earlier chapters if navigating back.

2. **Use Supabase Storage for Images (Higher Complexity, More Scalable)**
    - Add an optional field (e.g., `image_url: Optional[str]`) to the `ChapterData` model.
    - When an image is generated, upload it to a Supabase Storage bucket.
    - Store the public or signed URL in the `image_url` field within `AdventureState`.
    - On resumption, send this URL to the client, which can then load the image via an `<img>` tag.
    - *Considerations:* This approach is more scalable for many images and large files, keeps `state_data` smaller, but requires setting up Supabase Storage and managing image uploads/URLs.

---
