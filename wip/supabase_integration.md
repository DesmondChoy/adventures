# Supabase Integration Plan for Learning Odyssey

This document outlines the steps required to integrate Supabase into the Learning Odyssey application, focusing on achieving Persistent Adventure State and enabling detailed Telemetry, with optional User Authentication (Google/Anonymous).

## Phase 1: Prerequisites & Setup

1.  **Create Supabase Project:**
    *   Set up a new project on [supabase.com](https://supabase.com/).
    *   Note down the Project URL and `anon` key (public key).
    *   Securely store the `service_role` key (secret key for backend use).

2.  **Install Supabase Libraries:**
    *   **Backend (Python):** Add `supabase-py` to `requirements.txt` and install (`pip install supabase-py`).
    *   **Frontend (JavaScript):** Add the Supabase JS client library (`@supabase/supabase-js`) to the frontend. Since the frontend is currently within Jinja templates, this might involve adding a script tag or integrating it if a JS build process exists for parts like the Summary Chapter.
        ```html
        <!-- Example: Add to base.html or relevant template -->
        <script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2"></script>
        <script>
          const SUPABASE_URL = 'YOUR_SUPABASE_URL';
          const SUPABASE_ANON_KEY = 'YOUR_SUPABASE_ANON_KEY';
          const supabase = supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
        </script>
        ```

3.  **Configure Environment Variables:**
    *   Add `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` to the application's environment configuration (e.g., `.env` file, deployment environment variables).

## Phase 2: Persistent Adventure State (Supabase Database)

1.  **Define Database Schema (`adventures` table):**
    *   Using the Supabase SQL Editor or dashboard UI, create a table named `adventures`.
    *   **Columns:**
        *   `id` (UUID, Primary Key, default: `gen_random_uuid()`)
        *   `user_id` (UUID, Nullable - *will link to `auth.users` if Auth is implemented*)
        *   `state_data` (JSONB, Not Null) - Stores the complete `AdventureState` JSON.
        *   `story_category` (TEXT, Nullable) - Extracted for easier querying.
        *   `lesson_topic` (TEXT, Nullable) - Extracted for easier querying.
        *   `is_complete` (BOOLEAN, default: `false`) - To distinguish in-progress vs. completed.
        *   `created_at` (TimestampTZ, default: `now()`)
        *   `updated_at` (TimestampTZ, default: `now()`)
    *   **Row Level Security (RLS):** Initially, RLS can be disabled for backend access using the service key. If frontend access or user-specific access is needed later, RLS policies will be required.

2.  **Refactor Backend `StateStorageService` (`app/services/state_storage_service.py`):**
    *   Initialize the Supabase client using environment variables.
    *   Modify `store_state`:
        *   Accept `user_id` (optional for now).
        *   Instead of writing to `_memory_cache`, construct a record with `state_data`, `user_id`, `story_category`, `lesson_topic`, `is_complete=true`.
        *   Use the Supabase client (`supabase.table('adventures').insert(record).execute()`) to insert the record.
        *   Return the generated `id` (UUID) of the adventure record.
    *   Modify `get_state`:
        *   Accept `state_id` (which is the adventure `id`).
        *   Use the Supabase client (`supabase.table('adventures').select('state_data').eq('id', state_id).maybe_single().execute()`) to fetch the record.
        *   Return the `state_data` field if found.
    *   Remove the in-memory cache (`_memory_cache`) and related singleton logic if no longer needed for other purposes.

3.  **Integrate into WebSocket/API Flow:**
    *   **Adventure Start:** When an adventure begins, potentially create an initial record in `adventures` with `is_complete=false`. Store the `adventure_id` on the client.
    *   **Adventure Progress (Optional):** Decide if in-progress state needs saving to Supabase periodically or only on completion. Saving periodically enables cross-device resume but increases DB writes. *Initial focus can be saving only on completion.*
    *   **Adventure Completion:**
        *   In the flow where the "Take a Trip Down Memory Lane" button is handled (`summary_generator.py` or `core.py`), after the final `AdventureState` is ready:
            *   Call the refactored `StateStorageService.store_state`, passing the final state and the current `user_id` (if available).
            *   The `state_id` returned by `store_state` is now the `adventure.id` (UUID).
            *   Send this `adventure.id` back to the client in the `summary_ready` message.
    *   **Summary Retrieval (`summary_router.py`):**
        *   The `/adventure/api/adventure-summary` endpoint will receive the `adventure.id` (as `state_id` query param).
        *   Use the refactored `StateStorageService.get_state` (which now queries Supabase) to fetch the `state_data` using the provided `adventure.id`.

## Phase 3: Telemetry (Supabase Database)

1.  **Define Database Schema (`telemetry_events` table):**
    *   Create a table named `telemetry_events`.
    *   **Columns:**
        *   `id` (BIGSERIAL, Primary Key - using sequence for high insert rate)
        *   `event_name` (TEXT, Not Null) - e.g., 'adventure_started', 'chapter_viewed', 'choice_made', 'summary_viewed'.
        *   `adventure_id` (UUID, Nullable, Foreign Key -> `adventures.id` - *optional if event is not adventure-specific*)
        *   `user_id` (UUID, Nullable - *links to `auth.users` if Auth implemented*)
        *   `timestamp` (TimestampTZ, default: `now()`)
        *   `metadata` (JSONB, Nullable) - Store event-specific details (e.g., `{"chapter_number": 1, "story_category": "...", "lesson_topic": "..."}`, `{"chapter_number": 3, "duration_ms": 45000}`, `{"choice_index": 0}`).

2.  **Integrate Telemetry Logging in Backend:**
    *   Create a utility function or service for logging telemetry events. This function will take `event_name`, `adventure_id`, `user_id`, and `metadata` and insert a record into the `telemetry_events` table using the Supabase client.
    *   Call this logging function at relevant points in the code:
        *   **Adventure Start:** Log 'adventure_started' with chosen topics (`adventure_id`, `user_id`, metadata: `{story_category, lesson_topic}`).
        *   **Chapter View:** When sending a chapter to the client, log 'chapter_viewed' (`adventure_id`, `user_id`, metadata: `{chapter_number, chapter_type}`). *Calculating duration might require client-side logic or timing between events.*
        *   **Choice Made:** When receiving a choice, log 'choice_made' (`adventure_id`, `user_id`, metadata: `{chapter_number, choice_index/text}`).
        *   **Summary Viewed:** When the summary API is successfully called, log 'summary_viewed' (`adventure_id`, `user_id`).

3.  **Analytics:**
    *   Use SQL queries directly in the Supabase dashboard or connect a BI tool to analyze the data in `adventures` and `telemetry_events` tables.
    *   Example Queries:
        *   `SELECT story_category, COUNT(*) FROM adventures GROUP BY story_category ORDER BY COUNT(*) DESC;`
        *   `SELECT event_name, COUNT(*) FROM telemetry_events WHERE timestamp > now() - interval '7 days' GROUP BY event_name;`
        *   Analyze `metadata` JSONB fields for deeper insights.

## Phase 4: Optional User Authentication (Supabase Auth)

*(Implement after Persistent State is working)*

1.  **Configure Supabase Auth:**
    *   Enable the Google provider in the Supabase project dashboard (requires setting up OAuth credentials in Google Cloud Console).
    *   Enable Anonymous sign-ins in the Supabase dashboard settings.

2.  **Implement Frontend Logic:**
    *   Add UI elements for "Login with Google" and "Continue as Guest".
    *   Use the Supabase JS client library:
        *   `supabase.auth.signInWithOAuth({ provider: 'google' })` for Google login.
        *   `supabase.auth.signInAnonymously()` for guest access.
    *   Implement logic to listen for authentication state changes (`onAuthStateChange`) to update the UI and get the `user_id`.
    *   Display the warning message for anonymous users.
    *   Ensure the user's auth token (JWT) is sent with requests to the backend (e.g., in the Authorization header).

3.  **Implement Backend Logic:**
    *   Add middleware or dependency injection in FastAPI to verify the JWT sent from the frontend and extract the `user_id`. Supabase libraries might offer helpers for this.
    *   Pass the validated `user_id` to the `StateStorageService` and telemetry logging functions.
    *   Update database interactions (`adventures`, `telemetry_events`) to store the `user_id`.

4.  **Update Database Schema/RLS:**
    *   Ensure the `user_id` columns in `adventures` and `telemetry_events` are correctly linked (potentially as foreign keys) to the `auth.users` table created by Supabase Auth.
    *   Implement Row Level Security (RLS) policies if needed (e.g., "Users can only select/update their own adventures").

## Considerations & Next Steps

*   **Error Handling:** Implement robust error handling for all Supabase interactions (DB writes/reads, auth).
*   **Data Migration:** Plan how to handle any existing state data (if applicable, though current state is transient).
*   **Testing:** Update existing tests and create new ones to cover Supabase interactions and authentication flows.
*   **Scalability:** Monitor Supabase usage and scale the database plan if necessary. Consider database indexing for performance as data grows.
*   **Security:** Ensure RLS policies are correctly implemented if data access needs restriction beyond backend service key access. Review Supabase security best practices.
*   **Client-side State:** Decide how much state still needs to be managed client-side (e.g., current chapter content being streamed) vs. relying solely on backend/DB state.

This plan provides a structured approach. We should tackle Persistent State first, then Telemetry, and finally Authentication if desired.
