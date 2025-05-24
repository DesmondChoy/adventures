# Active Context

## Current Focus: Supabase User Authentication & General Enhancements (As of 2025-05-24)

Following the successful completion of Supabase Phase 2 (Persistent Adventure State) and Phase 3 (Telemetry), and significant progress on Phase 4 (User Authentication), the project is now focused on completing Phase 4 testing and addressing other key enhancements.

### Recently Completed Milestones
*   **Supabase Integration - Phase 4 (User Authentication - Google Flow):**
    *   **Backend Logic:** Implemented JWT verification in `websocket_router.py` using `PyJWT`.
    *   **User ID Propagation:** Ensured `user_id` (extracted from JWT) is correctly passed to `StateStorageService` and `TelemetryService`.
    *   **Database Interaction Fixes:**
        *   Resolved `TypeError: Object of type UUID is not JSON serializable` in `StateStorageService` by converting `user_id` to a string before database operations.
        *   Fixed `NULL` `user_id` issue in `telemetry_events` table for `choice_made` and `chapter_viewed` events by ensuring correct `user_id` passing in `choice_processor.py` and `stream_handler.py`.
    *   **Database Schema & RLS:** Added foreign key constraints for `user_id` in `adventures` and `telemetry_events` tables, and defined initial RLS policies. Migration applied successfully.
    *   **Debug Log Cleanup:** Removed temporary `print()` statements from `websocket_router.py`, converting to standard logging.
    *   **Google Login Flow Testing:** Successfully tested the Google login flow, verifying `user_id` is correctly populated in `adventures` and `telemetry_events` tables.
*   **Supabase Integration - Phase 3 (Telemetry):** Fully completed and validated (as of 2025-05-21). This includes schema definition, backend logging integration, detailed telemetry columns, and analytics capabilities.
*   **Supabase Integration - Phase 2 (Persistent Adventure State):** Fully completed and validated (as of 2025-05-20). Adventures are persistent, and resumption is functional.
*   **Visual Consistency Epic (Core Implementation):**
    *   Implemented two-step image prompt synthesis for protagonist visual stability.
    *   Established a system for tracking and updating visual descriptions for all characters (protagonist and NPCs) across chapters (`state.character_visuals`).
    *   Fixed character visual extraction timing issues.
    *   Enhanced agency visual detail integration into prompts.
    *   Updated Chapter 1 prompt generation to include protagonist description.
    *   Added significant logging for visual tracking and image generation processes.

### Immediate Next Steps & Priorities

1.  **Complete Phase 4 Testing: User Authentication (Supabase Auth)**
    *   **Goal:** Finalize testing for all aspects of Supabase user authentication.
    *   **Tasks:**
        *   Test "Continue as Guest" (Supabase anonymous sign-in) flow.
        *   Verify `user_id` is populated correctly in `adventures` and `telemetry_events` for Supabase anonymous users.
        *   Verify `user_id` is `NULL` for any adventures/telemetry created by truly unauthenticated flows (if any remain, or for legacy data).
        *   Test adventure resumption for Google users (ensure `get_active_adventure_id` works with `user_id`).
        *   Test adventure resumption for Supabase anonymous users.
        *   Test RLS policies from client-side perspective (e.g., using Supabase JS client with user's token, try to access/modify data not permitted by policies).
        *   Test logout functionality (redirects to `/`, session cleared, subsequent attempts to access protected routes fail or redirect).
        *   Test behavior if user tries to access `/select` without being logged in (should redirect to `/`).

2.  **Implement Resuming Chapter Image Display (Chapters 1-9)**
    *   **Goal:** Address the known issue where the original image for chapters 1-9 is not re-displayed when an adventure is resumed.
    *   **Context:** This is a follow-up enhancement to the Supabase Phase 2 (Resumption) work. Potential solutions are outlined in `wip/supabase_integration.md`.

3.  **WebSocket Disconnection Fix**
    *   **Goal:** Resolve WebSocket `ConnectionClosedOK` errors and `RuntimeError` that occur when clients navigate away (e.g., to the summary page) by improving connection lifecycle management.
    *   **Context:** Noted as a known issue in `wip/implemented/summary_chapter_race_condition.md`.

4.  **Finalize "Visual Consistency Epic"**
    *   **Goal:** Ensure full completion of the visual consistency improvements.
    *   **Tasks:**
        *   Add comprehensive tests specifically for the new visual consistency features.
        *   Implement explicit protagonist gender consistency checks, if deemed necessary.
        *   Update core Memory Bank documentation (`projectbrief.md`, `systemPatterns.md`, `techContext.md`, `progress.md`, `llmBestPractices.md`, `implementationPlans.md`) to reflect all recent visual consistency implementations.

5.  **Ongoing Supabase Considerations & Enhancements**
    *   **Goal:** Continuously improve the Supabase integration.
    *   **Tasks:** Refine user identification for resumption, enhance error handling for Supabase interactions, add specific tests for Supabase features (especially if Auth is added), implement/verify RLS policies, and monitor scalability.

6.  **General Testing Enhancements & LLM Prompt Optimization**
    *   **Goal:** Broader, ongoing improvements to overall test coverage and LLM prompt efficiency.

---

## Previous Focus: Testing Supabase Persistence & Resume (2025-04-27)
*(This phase is now complete and validated as of 2025-05-20. See "Recently Completed Milestones" above.)*

## Previous Focus: Logging Configuration Fix (2025-04-07)
*(Details of this completed task are preserved below for historical context but are no longer the active focus.)*

We fixed a logging configuration issue in `app/utils/logging_config.py` that caused both a `TypeError` on startup and potential `UnicodeEncodeError` during runtime on Windows.

### Problem Addressed
1.  **`TypeError` on Startup:** The `logging.StreamHandler` was incorrectly initialized with an `encoding="utf-8"` argument, which it does not accept.
2.  **`UnicodeEncodeError` during Runtime:** The default Windows console encoding (`cp1252`) could not handle certain Unicode characters, causing errors when logging messages containing them.

### Implemented Solution
1.  **Removed Invalid Argument:** Removed the `encoding="utf-8"` argument from the `logging.StreamHandler` initialization.
2.  **Wrapped `sys.stdout`:** Wrapped the standard output stream (`sys.stdout.buffer`) using `io.TextIOWrapper` configured with `encoding='utf-8'` and `errors='replace'`.
3.  **Added Basic Console Formatter:** Added a simple `logging.Formatter('%(message)s')` to the console handler.
4.  **Ensured File Handler Encoding:** Explicitly set `encoding='utf-8'` for the `logging.FileHandler`.
5.  **Added JSON File Formatter:** Added a basic JSON formatter to the file handler.

### Result
The application now starts without the `TypeError`, and console logging correctly handles Unicode characters.

### Affected Files
1.  `app/utils/logging_config.py`: Updated `setup_logging` function.

*(Older "Previous Focus" sections for Image Scene Prompt Enhancement, Agency Choice Visual Details, Character Visual Extraction Timing Fix, Logging Improvements & Bug Fixes, Protagonist Inconsistencies Fix (initial work), and Character Visual Consistency & Evolution Debugging have been summarized into the "Visual Consistency Epic" under "Recently Completed Milestones" to keep this document focused on the most current active context.)*
