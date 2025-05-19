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

*   **[FAILED] Test Case 3: Resume Adventure (Failed 2025-05-19)**
    *   **Goal:** Verify an incomplete adventure can be resumed successfully, displaying the content of the chapter the user was on before disconnection.
    *   **Implementation Attempts & Debugging (2025-05-19):**
        1.  **Dedicated `client_uuid` Column:**
            *   **Action:** Added a dedicated `client_uuid TEXT` column to the `adventures` table via migration (`20250519080600_add_client_uuid_to_adventures.sql`).
            *   **Action:** Modified `StateStorageService.store_state()` to populate this new column.
            *   **Action:** Modified `StateStorageService.get_active_adventure_id()` to query this new column.
            *   **Result:** This successfully allowed `get_active_adventure_id` to find the existing adventure record.
        2.  **`AdventureStateManager` Fix:**
            *   **Action:** Modified `AdventureStateManager.reconstruct_state_from_storage()` to correctly set `self.state` with the reconstructed state.
            *   **Result:** This ensured that upon WebSocket connection, the `state_manager` instance within `websocket_router.py` holds the loaded state.
    *   **Observed Behavior (Post-Above Fixes - Attempt 2025-05-19):**
        *   User played through 3 chapters. Disconnected (refreshed page).
        *   **Positive:**
            *   Terminal logs confirmed `get_active_adventure_id` found the correct active adventure ID using the new `client_uuid` column.
            *   Logs confirmed `StateStorageService.get_state` retrieved the state for this ID.
            *   Logs confirmed `AdventureStateManager.reconstruct_state_from_storage` successfully reconstructed the state, and `websocket_router.py` logged "Successfully reconstructed and set state from storage upon connection." and "Loaded state indicates current chapter is 4" (meaning 3 chapters were complete).
        *   **Negative:**
            *   The adventure effectively restarted by generating and displaying content for Chapter 4, even though the UI indicated Chapter 3. The user was expecting to see the content of Chapter 3 again, awaiting their choice.
            *   A new adventure row was *not* created for the *same adventure ID*, but the existing adventure was incorrectly advanced.
            *   Terminal logs showed the client sent a message with `Choice data: start` upon reconnection.
            *   Crucial log line after successful state load: `State is None but adventure_id <id> exists. Re-initializing.` **This log was from a previous attempt and is no longer appearing after the `AdventureStateManager` fix.** The current issue is that even with the state correctly loaded, the "start" message from the client causes the router to proceed as if starting the *next* part of the adventure.
            *   User's key observation: "What should be happening is after reconnecting, it loads the text in Chapter 3 ... and no prompts should be sent to the LLM for any story generation."
    *   **Confirmed Cause (Current):**
        *   The server correctly identifies and loads the existing adventure state.
        *   However, when the client reconnects, it appears to send an initial message that includes `choice: "start"`.
        *   The server-side WebSocket logic in `app/routers/websocket_router.py`, upon receiving this "start" message, proceeds to generate the *next* chapter (e.g., Chapter 4 if Chapter 3 was the last completed one) instead of re-sending the content of the incomplete chapter the user was on (Chapter 3). The logic for handling a "start" choice when a state *already exists* doesn't differentiate between starting a brand new adventure segment versus resuming an incomplete chapter.
    *   **Next Steps (Detailed for next assistant):**
        1.  **Primary Goal:** Modify the server-side WebSocket logic to proactively re-send the content of the *current incomplete chapter* (the one the user was viewing before disconnection) immediately after a successful state load on reconnection, *before* processing further messages from the client like "start".
        2.  **Investigate Client-Side Message on Reconnect (Informational):**
            *   Briefly examine `app/templates/index.html` (JavaScript) to understand what message it sends upon WebSocket reconnection, particularly if an `adventure_id` is present in `localStorage`. This is to confirm if it always sends `choice: "start"`.
            *   *Note: Modifying client-side might be out of scope if the primary fix can be server-side, but understanding it is useful.*
        3.  **Modify `app/routers/websocket_router.py`:**
            *   Locate the section after `loaded_state_from_storage = await state_manager.reconstruct_state_from_storage(stored_state)` succeeds.
            *   **Determine Chapter to Resend:**
                *   The `loaded_state_from_storage.current_chapter_number` indicates the *next* chapter to be generated. The chapter the user was on is `loaded_state_from_storage.current_chapter_number - 1`.
                *   Retrieve this `ChapterData` object from `loaded_state_from_storage.chapters`. Let's call it `chapter_to_display`.
            *   **Verify it's Incomplete:** Check if `chapter_to_display` is indeed the one awaiting user action (e.g., it's the last chapter in the `chapters` list and its `response` attribute is `None` or not set).
            *   **Proactively Send Chapter:** If it's the correct chapter to resume:
                *   Log the intent to resend this chapter.
                *   Call `stream_and_send_chapter` (from `app/services/websocket_service.py`) to send its content. This will require `stream_and_send_chapter` to be enhanced (see next point).
                *   Example snippet (conceptual):
                    ```python
                    # Inside websocket_router.py, after state is loaded_state_from_storage
                    if loaded_state_from_storage:
                        # ... (existing logging and 'adventure_loaded' message) ...
                        
                        chapter_number_to_resume = loaded_state_from_storage.current_chapter_number - 1
                        if chapter_number_to_resume > 0 and \
                           chapter_number_to_resume <= len(loaded_state_from_storage.chapters):
                            
                            chapter_to_display = loaded_state_from_storage.chapters[chapter_number_to_resume - 1] # 0-indexed
                            
                            # Condition to check if this chapter needs to be re-sent (e.g., no response yet)
                            if not chapter_to_display.response and chapter_to_display.chapter_type != ChapterType.CONCLUSION:
                                logger.info(f"Resuming adventure: Re-sending content for Chapter {chapter_to_display.chapter_number}")
                                # Prepare arguments for stream_and_send_chapter
                                # chapter_content_data should be chapter_to_display.chapter_content.dict()
                                # sampled_question_data should be chapter_to_display.question.dict() if it exists
                                await stream_and_send_chapter(
                                    websocket=websocket,
                                    chapter_content_data=chapter_to_display.chapter_content.dict() if chapter_to_display.chapter_content else {'content': chapter_to_display.content, 'choices': []},
                                    sampled_question_data=chapter_to_display.question.dict() if chapter_to_display.question else None,
                                    state=loaded_state_from_storage,
                                    is_resumption=True # New flag
                                )
                                connection_data["resumed_session_just_sent_chapter"] = True # Flag to handle initial client message
                            else:
                                logger.info(f"Chapter {chapter_to_display.chapter_number} already has a response or is conclusion. Waiting for client message.")
                        # ...
                    ```
        4.  **Enhance `stream_and_send_chapter` in `app/services/websocket_service.py`:**
            *   Add a new optional parameter: `is_resumption: bool = False`.
            *   Add parameters for pre-fetched data: `chapter_content_data: Optional[Dict[str, Any]] = None`, `sampled_question_data: Optional[Dict[str, Any]] = None`.
            *   If `is_resumption` is `True`:
                *   The function must use `chapter_content_data` (which would be the `ChapterContent` of the chapter to resume, passed as a dict) and `sampled_question_data` (if any) directly.
                *   It should **bypass** any new LLM calls for content generation or new question sampling.
                *   Its primary role in this mode is to format the existing `content` and `choices` (from `chapter_content_data`) and `question` (from `sampled_question_data`) for streaming to the client.
        5.  **Handle Initial Client Message Post-Resumption in `websocket_router.py`:**
            *   In the main `while True:` message loop:
                *   If `connection_data.get("resumed_session_just_sent_chapter")` is `True` and the incoming `choice_data` from the client is "start":
                    *   Log that this initial "start" message is being ignored due to resumption.
                    *   Set `connection_data["resumed_session_just_sent_chapter"] = False`.
                    *   `continue` to the next iteration of the loop, effectively skipping processing for this specific "start" message.
                *   Otherwise, process messages as normal.
        6.  **Testing:** After these changes, thoroughly re-test Test Case 3.

*   **[IN PROGRESS] Test Case 4: Complete Adventure**
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

*   **[ ] Test Case 5: Summary Retrieval**
    *   **Goal:** Verify the summary page correctly loads the state from Supabase.
    *   **User Actions:**
        1.  After completing Test Case 4, the application should navigate to the summary page URL (e.g., `/adventure/summary?state_id=...`).
        2.  Verify the summary page loads and displays content.
        3.  Check the application's terminal logs for activity related to the `/adventure/api/adventure-summary` endpoint.
    *   **Cline Verification Questions:**
        *   "Did the summary page load successfully using the correct `adventure_id` in the URL?"
        *   "Did you see logs indicating the state was retrieved successfully for the summary API endpoint (e.g., 'Successfully retrieved state with ID: ...')?"

*   **[ ] Test Case 6: Multiple Incomplete Adventures (Optional)**
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

This plan provides a structured approach. 

## Current Status (As of 2025-05-19)

**Phase 2 (Persistent Adventure State) is significantly advanced. Key infrastructure for persistence is in place, but a critical issue with the adventure resumption logic (Test Case 3) remains the primary blocker.**

**Key Achievements in Phase 2 (Relevant to Persistence/Resumption):**
- Supabase project setup, library integration, and secure environment variable configuration completed.
- `adventures` table schema defined and migrated, including `environment` column and recently added dedicated `client_uuid` column (`20250519080600_add_client_uuid_to_adventures.sql`).
- `StateStorageService` (`app/services/state_storage_service.py`):
    - Refactored to use Supabase.
    - `store_state` updated to populate the dedicated `client_uuid` column.
    - `get_active_adventure_id` updated to query using the dedicated `client_uuid` column, successfully finding existing adventures.
- `AdventureStateManager` (`app/services/adventure_state_manager.py`):
    - `reconstruct_state_from_storage` method fixed to correctly set its internal `self.state` with the loaded adventure state. This ensures the WebSocket router has access to the loaded state.
- Integration of state storage into WebSocket/API flows for initial save, progress updates, and completion marking is largely in place.

**Outstanding Issue & Current Focus:**
- **Adventure Resumption Failure (Test Case 3):**
    - **Current Behavior:** Although the server now correctly identifies and loads the previous adventure state upon a client's reconnection (thanks to the `client_uuid` column and `AdventureStateManager` fixes), it then incorrectly processes an initial message from the client (which appears to be `choice: "start"`). Instead of re-displaying the content of the chapter the user was on before disconnecting, the server generates and sends the *next* chapter's content.
    - **Example:** If user was on Chapter 3 (awaiting choice), upon reconnect, Chapter 4's content is generated and sent, while UI might still show Chapter 3.
    - **Root Cause:** The server-side WebSocket logic in `app/routers/websocket_router.py` does not yet proactively re-send the last incomplete chapter's state upon successful resumption. It reacts to the client's initial message (e.g., "start") by advancing the (correctly loaded) state.

**Immediate Next Steps (To Resolve Test Case 3):**

1.  **Modify Server-Side WebSocket Logic (`app/routers/websocket_router.py` and `app/services/websocket_service.py`):**
    *   **Goal:** Implement logic for the server to proactively re-send the content of the *current incomplete chapter* to the client immediately after a successful state load on reconnection.
    *   **Tasks:**
        1.  **In `app/routers/websocket_router.py`:**
            *   After `loaded_state_from_storage` is successfully obtained, determine the actual chapter data that the user was viewing before disconnection (e.g., `loaded_state_from_storage.chapters[loaded_state_from_storage.current_chapter_number - 2]`, ensuring bounds checking).
            *   Verify this chapter is incomplete (e.g., `response` is `None`).
            *   Call an enhanced `stream_and_send_chapter` function (from `app/services/websocket_service.py`) to send this specific chapter's existing content and choices.
            *   Set a flag (e.g., `connection_data["resumed_session_just_sent_chapter"] = True`).
        2.  **In `app/services/websocket_service.py` (enhance `stream_and_send_chapter`):**
            *   Add new parameters: `is_resumption: bool = False`, `chapter_content_data: Optional[Dict[str, Any]] = None`, `sampled_question_data: Optional[Dict[str, Any]] = None`.
            *   If `is_resumption` is `True`, the function must use `chapter_content_data` and `sampled_question_data` directly, bypassing LLM calls for new content/questions. It should format and stream this existing data.
        3.  **In `app/routers/websocket_router.py` (main message loop):**
            *   If `connection_data.get("resumed_session_just_sent_chapter")` is `True` and the first incoming message from the client has `choice: "start"`, ignore this message, log it, and reset the flag. This prevents the initial "start" from incorrectly advancing the just-resumed chapter.

2.  **Thoroughly Re-Test Test Case 3:** After implementing the above, verify that resuming an adventure correctly displays the chapter the user was on, awaiting their input, and that no new/next chapter content is prematurely generated.

3.  **Complete Remaining Phase 2 Testing:** Once Test Case 3 is definitively PASSED:
    *   Test Case 4: Complete Adventure
    *   Test Case 5: Summary Retrieval
    *   Test Case 6: Multiple Incomplete Adventures (Optional)

4.  **Proceed to Phase 3 (Telemetry):** After all Phase 2 functionality, including robust resumption, is fully validated.

5.  **Evaluate Phase 4 (User Authentication):** Based on product requirements after Phase 3.
