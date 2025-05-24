# Supabase Integration Plan for Learning Odyssey

This document outlines the plan and progress for integrating Supabase into the Learning Odyssey application.

## Current Project Status & Immediate Focus (As of 2025-05-23)

*   **Overall Progress:** Supabase integration is divided into multiple phases.
*   **Completed Phases:**
    *   **Phase 1: Prerequisites & Setup:** Fully complete.
    *   **Phase 2: Persistent Adventure State (Supabase Database):** Fully complete and validated. Adventures are persistent, and resumption is functional.
    *   **Phase 3: Telemetry (Supabase Database):** Fully complete and validated. Telemetry for key events is being logged, including detailed columns for analytics.
*   **Currently In Progress: Phase 4: Optional User Authentication (Supabase Auth)**
    *   **Frontend Foundation (Steps 0, 1, 2.1, 2.2, 2.3):** Complete. This includes:
        *   Creation of login page (`/`) and migration of carousel page to (`/select`).
        *   Supabase Auth provider configuration (Google & Anonymous).
        *   Frontend logic on `login.html` for Google/Guest sign-in and redirection.
        *   Frontend logic on `/select` (carousel page) for session checking, redirecting unauthenticated users, JWT extraction for WebSockets, logout, and user status display. (Verified 2025-05-22 that existing code met these requirements).
*   **Immediate Next Steps for Phase 4:**
    *   **Focus on Step 3: Implement Backend Logic** for JWT verification and integration into services.
    *   Followed by **Step 4: Update Database Schema/RLS**.
    *   Conclude with **Step 5: Comprehensive Testing**.

---

## Phase 1: Prerequisites & Setup
*Brief: All prerequisite steps for Supabase project creation, API key retrieval, library installation, and environment variable configuration (local and production) are complete.*

- [x] **1. Create Supabase Project & Find API Keys**
- [x] **2. Install Supabase Libraries** (Backend: `supabase-py`, Frontend: `@supabase/supabase-js`)
- [x] **3. Configure Environment Variables** (Secure key storage for `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `SUPABASE_ANON_KEY` via `.env` and Railway; frontend key handling via Jinja templates)

---

## Phase 2: Persistent Adventure State (Supabase Database)
*Brief: This phase successfully implemented persistent storage for adventure states using the Supabase database, enabling adventure resumption. All implementation steps and testing were completed.*

- [x] **1. Define Database Schema (`adventures` table):**
    *   Created `adventures` table via Supabase CLI migrations with columns for `id`, `user_id`, `state_data` (JSONB for full state), `story_category`, `lesson_topic`, `is_complete`, `completed_chapter_count`, `created_at`, `updated_at`, and `environment`.
    *   RLS enabled with a service key policy.
- [x] **2. Refactor Backend `StateStorageService` (`app/services/state_storage_service.py`):**
    *   Refactored to use Supabase client, removing in-memory storage.
    *   Methods `store_state` (with upsert), `get_state`, `cleanup_expired`, and `get_active_adventure_id` implemented.
- [x] **3. Integrate into WebSocket/API Flow:**
    *   Integrated state saving on adventure start, periodic saves during progress, and final save on completion.
    *   Adventure resumption logic implemented in WebSocket connection handling.
- [x] **4. Add Environment Column for Data Differentiation:**
    *   Added `environment` column to `adventures` table to distinguish `development` vs. `production` data.
- [x] **Debugging & Testing:** All identified issues during Phase 2 development were resolved, and all test cases (New Adventure, Progress Save, Resume Adventure, Complete Adventure, Summary Retrieval, Multiple Incomplete Adventures) passed successfully as of 2025-05-20.

---

## Phase 3: Telemetry (Supabase Database)
*Brief: This phase successfully implemented telemetry logging to the Supabase database for key user and system events. All implementation and testing were completed.*

- [x] **1. Define Database Schema (`telemetry_events` table):**
    *   Created `telemetry_events` table via Supabase CLI migrations with columns for `id`, `event_name`, `adventure_id`, `user_id`, `timestamp`, `metadata` (JSONB), `environment`, `chapter_type`, `chapter_number`, and `event_duration_seconds`.
- [x] **2. Integrate Telemetry Logging in Backend:**
    *   Implemented `TelemetryService` (`app/services/telemetry_service.py`) to log events.
    *   Integrated calls to `log_event` for 'adventure_started', 'chapter_viewed', 'choice_made', and 'summary_viewed'.
- [x] **3. Enhance `telemetry_events` Table and Logging (Phase 3.1):**
    *   Added dedicated columns for `chapter_type`, `chapter_number`, and `event_duration_seconds` for improved analytics.
    *   Updated backend code to populate these new columns.
    *   Duration logging implemented for time spent on chapters.
- [x] **4. Analytics & Testing:**
    *   All identified issues during Phase 3 development were resolved.
    *   Basic analytics queries defined and data logging validated as of 2025-05-21.

---

## Phase 4: Optional User Authentication (Supabase Auth) - Detailed Plan

This phase implements optional user authentication using Supabase Auth, allowing users to sign in with Google or continue as an anonymous (Supabase-managed) guest.

**Key Decisions Made:**
*   **Login Page:** A new dedicated login page created at `/`.
*   **Carousel Page Path:** The existing adventure selection (carousel) page moved to `/select`.
*   **JWT Handling:** Session management and JWT persistence across pages rely on the Supabase JS client library's default behavior (browser localStorage).
*   **Foreign Key Behavior:** When a user is deleted from `auth.users`, the `user_id` in `adventures` and `telemetry_events` tables will be `SET NULL`.

**Implementation Steps:**

**0. Create Basic Landing/Login Page**
    *   [x] **0.1. New HTML File:** `app/templates/pages/login.html` created and adapted.
    *   [x] **0.2. New FastAPI Route:** Routes for `/` (login) and `/select` (carousel) configured in `app/routers/web.py`.
    *   [x] **0.3. Basic Structure for `login.html`:** Includes title, "Login with Google," and "Continue as Guest" buttons.
    *   [x] **0.4. Ensure Supabase JS Client is available on `login.html`:** Client initialization script added.

**1. Configure Supabase Auth (User Task)**
    *   [x] **1.1. Enable Google Provider:** Completed by user (Google Cloud Console OAuth setup).
    *   [x] **1.2. Enable Anonymous Sign-ins:** Completed by user in Supabase dashboard.
    *   [x] **1.3. Obtain JWT Signing Secret:** Completed by user; `SUPABASE_JWT_SECRET` to be used for backend verification.

**2. Implement Frontend Logic**
    *   [x] **2.1. Authentication UI on `login.html`:** UI elements for login buttons are present.
    *   [x] **2.2. Supabase JS Client Auth Logic on `login.html`:** Core logic for `signInWithOAuth`, `signInAnonymously`, and `onAuthStateChange` (for redirects) implemented and functional. Guest warning display present. (Client initialization issues resolved 2025-05-22).
    *   [x] **2.3. Auth Handling on Carousel Page (`/select` - `app/templates/pages/index.html` & `app/templates/components/scripts.html`):** (Verified existing implementation covers requirements as of 2025-05-22)
        *   On page load, `authManager` uses `supabase.auth.getSession()` to retrieve the current session.
        *   If no active session (or token is invalid/expired), user is redirected to `/` (login page).
        *   If a session exists, `authManager.accessToken` stores the JWT.
        *   `WebSocketManager` uses `authManager.accessToken` to pass the JWT when establishing the WebSocket connection.
        *   Logout button on `/select` calls `authManager.handleLogout()`, which uses `supabase.auth.signOut()` and results in a redirect to `/` via `onAuthStateChange`.
        *   UI on `/select` (`user-status` element) is updated by `authManager.updateUserStatusUI()` to display user status.
    *   **Summary of Frontend Debugging (Steps 2.1-2.3):** Initial client-side Supabase client initialization issues on both `login.html` and `base.html` (affecting `/select`) were resolved on 2025-05-22. This confirmed that the foundational frontend logic for authentication flows, session handling on the carousel page, and UI updates were correctly in place.

**Next Steps for Phase 4:**

**3. Implement Backend Logic (Cline - Act Mode)**
    *   [x] **3.1. Add `PyJWT` to `requirements.txt`:** (Completed 2025-05-23)
        *   `PyJWT[crypto]==2.10.1` added to `requirements.txt`.
        *   User confirmed `pip install -r requirements.txt` run successfully.
    *   [x] **3.2. Create JWT Verification Dependency:** (Completed 2025-05-23)
        *   Created `app/auth/dependencies.py`.
        *   Implemented `get_current_user_id_optional` FastAPI dependency with helper for JWT secret.
            *   Verifies JWT using `PyJWT`, extracts `user_id` from `sub` claim.
            *   Handles missing token, missing secret, expired token, invalid token, and missing `sub` claim.
    *   [x] **3.3. Integrate Auth into WebSocket Router (`app/routers/websocket_router.py`):** (Completed 2025-05-23)
        *   Updated WebSocket endpoint (`@router.websocket("/ws/story/{story_category}/{lesson_topic}")`) to accept `token: Optional[str] = Query(None)`.
        *   Added logic within the WebSocket connection handler to decode the JWT (if present) using `PyJWT` and `SUPABASE_JWT_SECRET` to get `user_id`.
        *   Stored this `user_id` (which can be `None`) in the `connection_data` dictionary.
    *   [x] **3.4. Pass `user_id` to Services:** (Completed 2025-05-23)
        *   **`StateStorageService` (`app/services/state_storage_service.py`):**
            *   Ensured `store_state` method correctly uses the `user_id` (changed param type to `Optional[UUID]`, added `user_id` to `update_record`).
            *   Modified `get_active_adventure_id` signature to `(client_uuid: Optional[str] = None, user_id: Optional[UUID] = None)`.
                *   Updated logic to prioritize querying by `user_id` if provided, falling back to `client_uuid`.
        *   **`TelemetryService` (`app/services/telemetry_service.py`):**
            *   Verified `log_event` method already correctly accepts `user_id: Optional[UUID]` and uses it.
        *   **Update Callers:** Modified `websocket_router.py` to pass `connection_data.get("user_id")` to `store_state`, `get_active_adventure_id`, and `log_event` calls.
    *   [x] **3.5. Update Database Interactions in Services:** (Completed 2025-05-23)
        *   `StateStorageService.store_state`: Verified that `user_id` (as `Optional[UUID]`) is included in the record for both insert and update operations if not `None`.
        *   `TelemetryService.log_event`: Verified that `user_id` (as `Optional[UUID]`) is included in the record if not `None`.
        *   (These were largely covered by changes and verifications in step 3.4)

**4. Update Database Schema/RLS (Cline - Act Mode)** (Completed 2025-05-23)
    *   [x] **4.1. Create Supabase Migration:** (Completed 2025-05-23)
        *   User ran `npx supabase migration new add_auth_fks_and_rls` creating `supabase/migrations/20250523114023_add_auth_fks_and_rls.sql`.
        *   Populated the migration file with SQL to:
            *   Add foreign key constraints from `adventures.user_id` and `telemetry_events.user_id` to `auth.users(id)` with `ON DELETE SET NULL`.
            *   Enable RLS on `telemetry_events`.
            *   Define RLS policies for `adventures` (select, insert, update for own/guest) and `telemetry_events` (insert for own/guest).
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

            -- Allow service_role full access (bypasses other RLS for backend operations)
            -- Note: Supabase automatically grants service_role bypass. Explicit policy can be for clarity or if specific service_role grants are needed.
            -- CREATE POLICY "Adventures service_role full access" ON public.adventures FOR ALL USING (true) WITH CHECK (true); -- This is often redundant.

            -- Policies for users interacting via frontend (anon key)
            CREATE POLICY "Users can select their own or guest adventures" ON public.adventures
            FOR SELECT USING (auth.uid() = user_id OR user_id IS NULL); -- Allow selection if user matches or if adventure is a guest adventure

            CREATE POLICY "Users can insert adventures for themselves or as guest" ON public.adventures
            FOR INSERT WITH CHECK (auth.uid() = user_id OR user_id IS NULL); -- Allow insert if user matches or if inserting as guest

            CREATE POLICY "Users can update their own adventures" ON public.adventures
            FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
            
            -- Deletion might be restricted. Consider if users should delete their own adventures.
            -- CREATE POLICY "Users can delete their own adventures" ON public.adventures
            -- FOR DELETE USING (auth.uid() = user_id);

            -- RLS Policies for 'telemetry_events' table
            -- CREATE POLICY "Telemetry service_role full access" ON public.telemetry_events FOR ALL USING (true) WITH CHECK (true); -- Redundant if service_role bypasses.

            CREATE POLICY "Users can insert their own telemetry" ON public.telemetry_events
            FOR INSERT WITH CHECK (auth.uid() = user_id OR user_id IS NULL);
            
            -- Select/update/delete on telemetry might be admin-only or restricted.
            -- CREATE POLICY "Users can select their own telemetry" ON public.telemetry_events
            -- FOR SELECT USING (auth.uid() = user_id OR user_id IS NULL);
            ```
    *   [x] **4.2. Apply Migration:** (Completed 2025-05-23)
        *   Ran `npx supabase db push` to apply the migration.

**5. Testing (User & Cline - Collaborative)**
    *   **Debugging Log & Resolution Status (As of 2025-05-24):**
        *   **Initial Problems & Debugging:**
            *   Initial tests revealed issues with JWT not being passed/processed correctly by the backend, leading to missing `user_id` in `connection_data`. This was traced to frontend WebSocket URL construction and backend parsing/logging.
            *   Subsequent fixes to frontend (`scripts.html`) and backend (`websocket_router.py` including adding temporary `print` statements) ensured the JWT was correctly sent, received, and parsed, and the `user_id` (as a UUID object) was extracted.
        *   **Resolved: `TypeError: Object of type UUID is not JSON serializable`**
            *   This error occurred in `state_storage_service.store_state` when attempting to save `user_id` (a UUID object) to Supabase.
            *   **Solution:** Modified `app/services/state_storage_service.py` to explicitly convert the `user_id` to a string (`str(user_id)`) before including it in the data payload for Supabase database operations.
            *   **Verification:** Google Login testing confirmed this resolved the `TypeError`, and `user_id` is correctly stored as a string in the `adventures` table.
        *   **Resolved: `NULL` `user_id` in `telemetry_events` Table**
            *   After the initial `adventure_started` event, subsequent telemetry events (e.g., `choice_made`, `chapter_viewed`) were logging `NULL` for `user_id`.
            *   **Solution:**
                *   Updated `app/services/websocket/choice_processor.py` (for `choice_made` events) to correctly pass the `user_id` (obtained from `connection_data`) to `telemetry_service.log_event`.
                *   Updated `app/services/websocket/stream_handler.py` (for `chapter_viewed` events) to correctly pass the `user_id` (obtained from `connection_data`) to `telemetry_service.log_event`.
            *   **Verification:** Google Login testing confirmed that `user_id` is now correctly populated for all relevant telemetry events in the `telemetry_events` table.
        *   **Resolved: Temporary Debug Logs Removed**
            *   Verbose `print()` statements added to `app/routers/websocket_router.py` for debugging JWT and query parameter parsing have been removed, and standard logging practices are now used.
        *   **Verified: Google Login Flow and `user_id` Propagation**
            *   The Google Login flow is functional.
            *   `user_id` is correctly extracted from the JWT.
            *   `user_id` is correctly stored as a string in the `adventures` table.
            *   `user_id` is correctly stored as a string in the `telemetry_events` table for all relevant events.
    *   [x] Test Google Login flow.
    *   [ ] Test "Continue as Guest" (Supabase anonymous sign-in) flow.
    *   [ ] Verify `user_id` is populated correctly in `adventures` and `telemetry_events` for authenticated users and Supabase anonymous users.
    *   [ ] Verify `user_id` is `NULL` for any adventures/telemetry created by truly unauthenticated flows (if any remain, or for legacy data).
    *   [ ] Test adventure resumption for Google users (ensure `get_active_adventure_id` works with `user_id`).
    *   [ ] Test adventure resumption for Supabase anonymous users (ensure `get_active_adventure_id` works, potentially using their anonymous `auth.uid()` as the `user_id`).
    *   [ ] Test RLS policies from client-side perspective (e.g., using Supabase JS client with user's token, try to access/modify data not permitted by policies).
    *   [ ] Test logout functionality (redirects to `/`, session cleared, subsequent attempts to access protected routes fail or redirect).
    *   [ ] Test behavior if user tries to access `/select` without being logged in (should redirect to `/`).

---

## General Considerations & Next Steps (Post Phase 4)

*   **User Identification for Resumption:** With `user_id` available from Supabase Auth (for both Google and anonymous users), `StateStorageService.get_active_adventure_id` should prioritize `user_id` for finding active adventures. The `client_uuid` can serve as a fallback for older data or truly unauthenticated scenarios if any.
*   **Error Handling:** Implement robust error handling for all new Supabase Auth interactions (backend JWT verification, RLS permission errors).
*   **Data Migration:** Not applicable for current transient data, but consider for future if schema changes affect existing user data.
*   **Testing:** Expand test suite to cover all authentication flows, RLS policies, and user-specific data interactions.
*   **Scalability & Security:** Monitor Supabase usage. Continuously review and refine RLS policies as per Supabase security best practices.
*   **Client-side State:** Re-evaluate client-side state management (`localStorage`) in light of server-side persistence and auth. For guest users, `localStorage` might still be primary for state before first save, but authenticated users' state should primarily be driven by Supabase.

---

## Future Enhancements & Observations (Post-Phase 2)

### Image Handling on Chapter Resume

#### Current Behaviors
- **Chapter 10 (CONCLUSION):** Image is re-generated on each refresh/resume. (Acceptable)
- **Chapters 1-9:** New image generation is bypassed on resume; original image is not re-displayed.

#### To-Do / Known Issue
- **Resuming Chapter Image Display (Chapters 1-9):**
    - **Goal:** When resuming an adventure at chapters 1-9, display the original image associated with that chapter.
    - **Current Limitation:** Image is not re-displayed.

#### Potential Solutions (for Chapters 1-9 Image Display)
1.  **Store Image Base64 in `ChapterData` (Medium Complexity)**
    *   Add `image_base64: Optional[str]` to `ChapterData` model.
    *   Store generated image base64 in `AdventureState`.
    *   Retrieve and send on resumption.
    *   *Considerations:* Increases `state_data` size.

2.  **Use Supabase Storage for Images (Higher Complexity, More Scalable)**
    *   Add `image_url: Optional[str]` to `ChapterData` model.
    *   Upload generated images to Supabase Storage.
    *   Store public/signed URL in `AdventureState`.
    *   Send URL on resumption for client to load.
    *   *Considerations:* More scalable, smaller `state_data`, but requires Supabase Storage setup.

---
