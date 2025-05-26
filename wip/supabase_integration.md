# Supabase Integration Plan for Learning Odyssey

This document outlines the plan and progress for integrating Supabase into the Learning Odyssey application.

## Current Project Status & Immediate Focus (As of 2025-05-26 PM)

*   **Overall Progress:** Supabase integration is divided into multiple phases.
*   **Completed Phases:**
    *   **Phase 1: Prerequisites & Setup:** Fully complete.
    *   **Phase 2: Persistent Adventure State (Supabase Database):** Fully complete and validated.
    *   **Phase 3: Telemetry (Supabase Database):** Fully complete and validated.
    *   **Phase 4: Optional User Authentication (Supabase Auth):** Backend logic, database schema/RLS, and initial frontend flows completed.
*   **Phase 4.1: Adventure Resumption Bug Fix & Enhanced UX - IN PROGRESS**
    *   **Implementation Status:**
        *   Core fixes for adventure matching implemented.
        *   Resume modal flow partially implemented; CSS and basic JS for modal display fixed.
        *   Backend API (`/api/user/current-adventure`) updated to return `story_category` and `lesson_topic`.
        *   `StateStorageService` updated with `get_user_current_adventure_for_resume` method.
        *   `login.html` updated to store `story_category` and `lesson_topic` in `sessionStorage`.
        *   `scripts.html` updated to retrieve these values from `sessionStorage` for WebSocket URL construction.
    *   **Current Outcome:** Despite these changes, the primary issue of the resume modal not appearing consistently after login persists. Additionally, a new issue regarding multiple incomplete adventures for a single user has been identified, and the chapter display inconsistency remains.

*   **Current Issues & Next Steps:**
    *   **✅ FIXED (Previously):** Wrong adventure resumption (adventures now match story/lesson selection - *needs re-verification due to new issues*).
    *   **✅ FIXED (Previously):** Login flow now properly checks for existing adventures via `handleSignIn()` - *needs re-verification*.
    *   **✅ FIXED:** Resume modal CSS and basic JS display logic in `login.html`.
    *   **✅ FIXED:** Backend API and services updated to provide necessary data for resume.
    *   **✅ FIXED:** WebSocket URL construction in `scripts.html` now attempts to use `story_category` and `lesson_topic` from `sessionStorage`.
    *   **❌ ISSUE (HIGH PRIORITY):** Resume modal still not appearing consistently after logout/login, even with an incomplete adventure in the database.
        *   **Symptom:** User logs in, has an incomplete adventure, but no modal is shown.
        *   **Suspected Causes (Re-evaluation):**
            *   Timing issue with token availability or `handleSignIn` execution in `login.html`.
            *   `/api/user/current-adventure` not being called reliably or returning unexpected data despite backend changes.
            *   Logic in `login.html` that decides to show the modal might be flawed.
    *   **❌ ISSUE (HIGH PRIORITY):** Multiple incomplete adventures per user.
        *   **Symptom:** Starting a new adventure does not mark the previous incomplete adventure as "abandoned" or "complete". Database shows multiple rows with `is_complete = FALSE` for the same `user_id`.
        *   **Suspected Causes:** The `_abandon_existing_incomplete_adventure` method in `StateStorageService` (called by `store_state` for new adventures) is not functioning as intended.
    *   **❌ ISSUE (MEDIUM PRIORITY):** Chapter display inconsistency.
        *   **Symptom:** When an adventure *is* manually resumed (by selecting the same story/lesson), UI shows "Chapter 1 out of 10" but should display the actual current chapter (e.g., Chapter 3).
        *   **Suspected Causes:** Frontend state interpretation in `scripts.html` upon adventure load/resume, or the `state_data` itself might not be correctly reflecting `completed_chapter_count` in its `chapters` array length or `current_chapter_id`.

---

## Phase 1: Prerequisites & Setup ✅ COMPLETE
*Brief: All prerequisite steps for Supabase project creation, API key retrieval, library installation, and environment variable configuration are complete.*

- [x] Create Supabase Project & Find API Keys
- [x] Install Supabase Libraries (Backend: `supabase-py`, Frontend: `@supabase/supabase-js`)
- [x] Configure Environment Variables (Local and production via `.env` and Railway)

---

## Phase 2: Persistent Adventure State ✅ COMPLETE
*Brief: Successfully implemented persistent storage for adventure states using Supabase database, enabling adventure resumption.*

- [x] **Database Schema:** Created `adventures` table with columns for `id`, `user_id`, `state_data` (JSONB), `story_category`, `lesson_topic`, `is_complete`, `completed_chapter_count`, `created_at`, `updated_at`, `environment`
- [x] **Backend Service:** Refactored `StateStorageService` to use Supabase with methods: `store_state`, `get_state`, `get_active_adventure_id`
- [x] **Integration:** WebSocket/API flow integration for state saving and resumption
- [x] **Environment Support:** Added environment column for dev/prod data separation

**Key Learnings:** JSONB storage works well for complex state data. Environment separation critical for development.

---

## Phase 3: Telemetry ✅ COMPLETE
*Brief: Successfully implemented telemetry logging to Supabase for key user and system events.*

- [x] **Database Schema:** Created `telemetry_events` table with dedicated columns for `chapter_type`, `chapter_number`, `event_duration_seconds`
- [x] **Backend Service:** Implemented `TelemetryService` with event logging for 'adventure_started', 'chapter_viewed', 'choice_made', 'summary_viewed'
- [x] **Duration Tracking:** Added time-based analytics for user engagement

**Key Learnings:** Dedicated columns for analytics are better than generic metadata for common queries.

---

## Phase 4: User Authentication ✅ COMPLETE
*Brief: Implemented optional user authentication using Supabase Auth with Google OAuth and anonymous sessions.*

### Implementation Summary:
- [x] **Login System:** Created `/` (login) and `/select` (carousel) page separation
- [x] **Frontend Auth:** Google OAuth and anonymous sign-in with session management
- [x] **Backend JWT:** JWT verification, user ID extraction, and service integration  
- [x] **Database Integration:** Foreign keys, RLS policies for user-scoped data access
- [x] **User ID Propagation:** All services (StateStorage, Telemetry) now user-aware

### Key Issues Resolved:
- **UUID Serialization:** Fixed `TypeError: Object of type UUID is not JSON serializable` by converting UUID to string
- **Missing User ID in Telemetry:** Updated all telemetry logging points to pass user_id correctly
- **RLS Policies:** Implemented proper row-level security for user data isolation

**Key Learnings:** JWT handling requires careful error handling. RLS policies essential for multi-user security.

---

## Phase 4.1: Adventure Resumption Bug Fix & Enhanced UX 🟡 IN PROGRESS
*Brief: Addressed critical bug where users couldn't start new adventures with different story/lesson combinations, and implemented resume modal for better UX. Currently debugging issues with modal appearance and data integrity.*

### Root Problems Identified (Original & New):
1.  **Adventure Matching Bug (Addressed, needs re-verification):** `get_active_adventure_id` found ANY incomplete adventure, not story/lesson-specific ones.
2.  **Poor UX (Partially Addressed):** No clear resumption flow. Modal implemented but not appearing reliably.
3.  **Multiple Adventures (New/Persistent):** Users can accumulate multiple incomplete adventures. The "one adventure per user" rule is not being enforced.
4.  **Chapter Display Inconsistency (Persistent):** Resumed adventures show incorrect chapter progress.

### Solution Approach (Ongoing): Enhanced Resume Flow + Story/Lesson Filtering + Data Integrity Fixes
- **One Adventure Per User (NEEDS FIX):** Automatic abandonment of old adventures when starting new ones.
- **Resume Modal (NEEDS FIX):** Clean, professional modal showing adventure details with Continue/Start Fresh options.
- **Story/Lesson Matching (Implemented, needs re-verification):** Only resume adventures that match current selection.
- **30-Day Auto-Expiry (Implemented):** Cleanup system for old adventures.

### Implementation Status (Updated 2025-05-26 PM):

#### ✅ COMPLETED/ATTEMPTED FIXES:
**1. Adventure Matching Logic (`app/services/state_storage_service.py`)**
- Enhanced `get_active_adventure_id()` with `story_category` and `lesson_topic` parameters.
- Updated WebSocket router to pass story/lesson context when searching for adventures.
- Added `get_user_current_adventure_for_resume` to provide detailed data for modal and WebSocket URL.
- **Result (Initial):** Adventures matched selection. *Current status needs re-verification due to modal issues.*

**2. Resume Modal System**
- Created modal component (`app/templates/components/resume_modal.html`).
- Added API endpoints: `GET /api/user/current-adventure`, `POST /api/adventure/{id}/abandon`.
- Updated `/api/user/current-adventure` to return `story_category` and `lesson_topic`.
- Implemented frontend logic in `login.html` for modal interaction, including storing resume details in `sessionStorage`.
- Implemented frontend logic in `scripts.html` to use `sessionStorage` for WebSocket URL construction.
- Fixed missing CSS link for `resume-modal.css` in `login.html`.
- Restored truncated JavaScript in `login.html`.
- **Result:** Modal appeared briefly but issues persist. WebSocket URL construction for resume was improved.

**3. One Adventure Enforcement (`app/services/state_storage_service.py`)**
- Added `_abandon_existing_incomplete_adventure()` helper.
- Modified `store_state()` to call this helper.
- **Result:** This logic is currently NOT working as intended, as multiple incomplete adventures are observed.

**4. Session Bypass Fix (`app/templates/pages/login.html`)**
- Updated `checkLoginPageSession()` to call `handleSignIn()`.
- **Result (Initial):** Login flow properly checked for existing adventures. *Current status needs re-verification.*

#### ❌ REMAINING ISSUES (Updated 2025-05-26 PM):

**Issue 1: Resume Modal Not Appearing Consistently (HIGH PRIORITY)**
- **Symptom:** After logout/login, modal doesn't appear despite an incomplete adventure in the database.
- **Suspected Causes:**
    - Timing of `handleSignIn()` or token availability in `login.html`.
    - `/api/user/current-adventure` not being called or returning `null` unexpectedly.
    - Flaw in the logic within `login.html` that decides whether to show the modal based on API response.
- **Investigation Needed:**
    - Add detailed console logs in `login.html` around `handleSignIn`, `attemptResumeApiCall`, and the conditions for showing the modal.
    - Verify the exact data returned by `/api/user/current-adventure` in the browser network tab.
    - Step-through debugging of `login.html` JavaScript.

**Issue 2: Multiple Incomplete Adventures Per User (HIGH PRIORITY)**
- **Symptom:** Starting a new adventure does not result in the abandonment of the user's previous incomplete adventure.
- **Suspected Causes:**
    - `_abandon_existing_incomplete_adventure` in `StateStorageService` is not correctly identifying or updating the previous adventure.
    - The call to `_abandon_existing_incomplete_adventure` from `store_state` might not be happening under the correct conditions or is failing silently.
- **Investigation Needed:**
    - Add extensive logging within `store_state` (when `adventure_id` is `None`) and `_abandon_existing_incomplete_adventure` to trace its execution path and the data it's operating on.
    - Verify the Supabase query logic within `_abandon_existing_incomplete_adventure` and `abandon_adventure`.

**Issue 3: Chapter Display Inconsistency (MEDIUM PRIORITY)**
- **Symptom:** UI shows "Chapter 1 out of 10" but should display the actual current chapter (e.g., Chapter 3) when an adventure is resumed (even manually).
- **Suspected Causes:**
    - Frontend (`scripts.html`) incorrectly initializing or updating chapter progress display from the resumed state.
    - The `state_data.chapters` array length or `state_data.current_chapter_id` might be inconsistent with `completed_chapter_count` in the database for the specific adventure.
    - The `adventure_loaded` event in `scripts.html` might not be correctly populating `selectedCategory` and `selectedLessonTopic` from the server's state, leading to issues if `initWebSocket` is called again.
- **Investigation Needed:**
    - Log the full `data.state` received in `handleMessage` for `adventure_loaded` type in `scripts.html`.
    - Trace how `updateProgress` is called and what values it uses upon resuming.
    - Inspect the `state_data` JSON in Supabase for an affected adventure.

### Testing Progress (Updated 2025-05-26 PM):
✅ **Working (Partially/Intermittently):**
*   In-session resumption (browser refresh) - *needs re-verification*.
*   Adventure story/lesson matching when *manually* re-selecting - *needs re-verification*.
*   Content loading once an adventure starts.
*   Resume modal styling (when it rarely appeared).
*   Backend API providing `story_category` and `lesson_topic`.
*   `sessionStorage` being used for resume parameters.

❌ **Failing/Inconsistent:**
*   **Resume modal not appearing reliably after login.**
*   **Cross-session adventure resumption via modal.**
*   **One adventure limit enforcement (multiple incomplete adventures exist).**
*   Chapter number display accuracy on resume.

---

## Immediate Next Steps (Priority Order - Revised 2025-05-26 PM)

### 1. Debug Resume Modal Non-Appearance (CRITICAL)
**Investigation Tasks:**
-   **Frontend (`login.html`):**
    *   Add aggressive console logging in `handleSignIn()` and `attemptResumeApiCall()`:
        *   Confirm functions are called.
        *   Log `session` and `token` status immediately before `fetch`.
        *   Log the exact response (success or error, and data) from `/api/user/current-adventure`.
        *   Log the `adventureData` used in `showResumeModal`.
    *   Verify the conditions under which `showResumeModal` is called.
-   **Backend (`StateStorageService.get_user_current_adventure_for_resume`):**
    *   Log the `user_id` received.
    *   Log the raw SQL query being generated (if possible with Supabase client, or log parameters).
    *   Log the exact data returned from Supabase *before* any processing.
    *   Ensure it's correctly selecting only one, most recent, incomplete adventure.

**Potential Fixes:**
-   Adjust timing or conditions for API call in `login.html`.
-   Refine database query in `get_user_current_adventure_for_resume` if it's not selecting the correct single adventure.

### 2. Fix Multiple Incomplete Adventures (HIGH)
**Investigation Tasks:**
-   **Backend (`StateStorageService.store_state` and `_abandon_existing_incomplete_adventure`):**
    *   Add detailed logging to trace the execution flow when a new adventure is created (`adventure_id` is None).
    *   Log `user_id` being passed to `_abandon_existing_incomplete_adventure`.
    *   Inside `_abandon_existing_incomplete_adventure`, log the result of `get_user_current_adventure_for_resume`.
    *   Log the `adventure_to_abandon_id` and the result of the `abandon_adventure` call.
    *   Verify the Supabase `update` call in `abandon_adventure` (conditions, payload).

**Potential Fixes:**
-   Correct the logic or query in `_abandon_existing_incomplete_adventure` or `abandon_adventure`.
-   Ensure `store_state` correctly triggers this for authenticated users starting a new adventure.

### 3. Fix Chapter Display Bug (MEDIUM)
**Investigation Tasks:**
-   **Frontend (`scripts.html`):**
    *   When `wsManager.adventureIdToResume` is true, ensure `initWebSocket` uses the server-provided state (via `adventure_loaded` message) and not stale `localStorage` state.
    *   Log `data.state` in `handleMessage` for `adventure_loaded`.
    *   Trace how `selectedCategory`, `selectedLessonTopic`, and chapter progress UI elements are updated.
-   **Backend (`websocket_router.py`):**
    *   When resuming, log the state loaded by `adventure_state_manager.load_adventure` before sending to client.
-   **Database:**
    *   Inspect `state_data` JSON for an adventure that shows incorrect chapter count (e.g., the one with `completed_chapter_count: 3`). Verify its `chapters` array length and `current_chapter_id`.

**Potential Fixes:**
-   Adjust frontend logic in `scripts.html` to correctly use resumed state from server.
-   Ensure `updateProgress` uses the correct chapter count from the server-authoritative state.

### 4. Comprehensive Testing (MEDIUM)
**Test Scenarios (Re-evaluate after fixes):**
-   Resume modal appearance and functionality (Google, Anonymous).
-   One adventure limit enforcement.
-   Cross-session adventure persistence.
-   Chapter display accuracy on resume.
-   Starting fresh from modal correctly abandons old adventure.

---

## Architecture Decisions & Learnings
*(No changes in this section for this update)*

---

## Future Enhancements
*(No changes in this section for this update)*

---

## Key Files Modified (Recent)

### Backend
-   `app/routers/web.py` - Updated `/api/user/current-adventure` response model and logic.
-   `app/services/state_storage_service.py` - Added `get_user_current_adventure_for_resume` method.

### Frontend  
-   `app/templates/pages/login.html` - Added `sessionStorage` for resume details, fixed JS truncation, added CSS link.
-   `app/templates/components/scripts.html` - Updated WebSocket URL construction to use `sessionStorage` for resume.

*(Older file modifications remain as previously documented)*
---

This integration provides a solid foundation for user authentication and adventure persistence while maintaining the flexibility to support both authenticated and anonymous users. The remaining issues are primarily frontend UX polish that don't affect core functionality.
