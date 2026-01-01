# WebSocket Reconnection Failure (Resumed Adventures)

## Current Status

**Status: ✅ FIXED (2026-01-01)**

The WebSocket reconnection failure that occurred when resuming saved adventures has been resolved. The issue was caused by dynamic ES6 module imports resetting the `window.appState` object.

### Key Finding (Resolved)

| Scenario | Chapter Transition | Result |
|----------|-------------------|--------|
| Fresh adventure | ✅ Works | All chapters stream normally |
| Resumed adventure | ✅ Works (FIXED) | Adventures resume and continue normally |

## Testing Note

**The bug can be reproduced at ANY chapter, not just Chapter 9→10.** To speed up testing:
1. Start a fresh adventure
2. Progress to Chapter 2 or 3
3. Refresh the page to trigger resumption
4. Click a choice button
5. Observe the "Reconnecting..." failure

There is no need to wait until Chapter 9 to reproduce this issue.

## Problem Statement

When attempting to advance to the next chapter in a **resumed adventure**, clicking a choice button triggers a WebSocket reconnection failure instead of progressing the story.

**User-observed behavior:**
1. User resumes an adventure (loaded from Supabase)
2. Current chapter content displays correctly with 3 choice buttons
3. User clicks a choice button to advance
4. Button shows `[active]` state, loader appears
5. **BUG:** "Reconnecting..." message appears
6. WebSocket fails to reconnect
7. Page remains stuck on current chapter content
8. Refreshing the page restores the chapter but clicking any choice repeats the failure

**Expected behavior:**
- Choice should be processed
- Next chapter should stream
- Adventure should continue normally

## Root Cause Analysis (Updated 2026-01-01)

### Identified Issue: Dual WebSocket Reference Desync

The frontend maintains TWO references to the WebSocket:
1. `window.appState.storyWebSocket` - checked by choice button click handler
2. `window.appState.wsManager.connection` - managed by WebSocketManager

**Critical Discovery:** When the choice button is clicked, both references are `null`:

```javascript
// Evaluated in browser after "Reconnecting..." appears
{
  "storyWebSocket": null,        // Should be WebSocket object
  "wsManagerConnection": null,   // Should be WebSocket object
  "areTheSameReference": false
}
```

This explains the "Reconnecting..." message - the code at `uiManager.js:896` checks:
```javascript
if (storyWebSocket?.readyState !== WebSocket.OPEN) {
    showLoader();
    showError('Reconnecting...');
    // ...
}
```

With `storyWebSocket` being `null`, the condition is always true.

### Why References Become Null

Investigation revealed:
1. Content IS displayed (WebSocket WAS connected at some point)
2. Backend logs show successful ping/pong activity
3. But by the time user clicks a choice, references are null

Possible causes being investigated:
1. **Async timing issue** - `initialize()` in main.js may not complete WebSocket setup before user interaction
2. **Silent WebSocket close** - Connection may close without triggering proper cleanup/reconnection
3. **State reset** - Some code path may be clearing `window.appState` properties

### Initial Setup Path (main.js)

```javascript
// Line 320 - wsManager is created
window.appState.wsManager = new WebSocketManager(authManager);

// Two paths call initWebSocket():
// 1. If URL has resume_adventure_id param (line 349)
// 2. If localStorage has saved state (line 369)

// initWebSocket() creates WebSocket and syncs references:
window.appState.storyWebSocket = new WebSocket(websocketUrl);
window.appState.wsManager.connection = window.appState.storyWebSocket;
```

## Partial Fix Implemented

### Fix 1: Sync References During Reconnection

Added synchronization of `window.appState.storyWebSocket` in `webSocketManager.js:reconnect()`:

```javascript
// webSocketManager.js lines 100-108
async reconnect() {
    // ...
    try {
        this.connection = new WebSocket(websocketUrl);
        // CRITICAL: Sync window.appState.storyWebSocket with the new connection
        // Without this, choice button clicks check the old (closed) WebSocket
        if (window.appState) {
            window.appState.storyWebSocket = this.connection;
        }
        this.setupConnectionHandlers();
        this.reconnectAttempts++;
    } catch (e) {
        // ...
    }
}
```

**Result:** This fix alone did NOT resolve the issue. The "Reconnecting..." message still appears, indicating the problem occurs BEFORE `reconnect()` is called.

## Unrelated Fix During Testing

### Gemini Model 404 Error

During testing, encountered:
```
models/gemini-2.5-flash-lite-preview-06-17 is not found for API version v1beta
```

**Fix applied to `app/services/llm/providers.py`:**
```python
# Before (deprecated):
GEMINI_FLASH_LITE_MODEL = "gemini-2.5-flash-lite-preview-06-17"

# After (current):
GEMINI_FLASH_LITE_MODEL = "gemini-2.5-flash-lite"
```

## Files Involved

### Frontend Files
| File | Purpose | Key Lines |
|------|---------|-----------|
| `app/static/js/main.js` | WebSocket initialization, `makeChoice()` | 48-81 (initWebSocket), 84-130 (makeChoice) |
| `app/static/js/webSocketManager.js` | Connection management, reconnection | 82-114 (reconnect), 116-163 (handlers) |
| `app/static/js/uiManager.js` | Choice button handlers, "Reconnecting..." | 891-930 (button onclick) |
| `app/static/js/stateManager.js` | Local state management | - |

### Backend Files
| File | Purpose |
|------|---------|
| `app/routers/websocket_router.py` | WebSocket connection handling, state reconstruction |
| `app/services/websocket/choice_processor.py` | Choice processing |
| `app/services/adventure_state_manager.py` | State reconstruction from Supabase |
| `app/services/state_storage_service.py` | Supabase state persistence |

## Observed Timeline (Detailed)

```
Timeline (Resumed Adventure):
─────────────────────────────────────────────────────────────────────────────────
T0: Page loads (via refresh or navigation)
    → DOMContentLoaded fires
    → initialize() called in main.js
    → wsManager created (line 320)
    → Auth initialized
    → Check for resume conditions:
      - URL param: resume_adventure_id? → initWebSocket()
      - OR localStorage has state? → initWebSocket()

T1: WebSocket connects (if initWebSocket was called)
    → window.appState.storyWebSocket = new WebSocket(...)
    → window.appState.wsManager.connection = storyWebSocket
    → Backend loads state from Supabase
    → Chapter content streams and displays
    → Choice buttons appear
    → Ping/pong keep-alive starts

T2: User clicks choice button
    → uiManager.js button.onclick fires (line 891)
    → Checks: storyWebSocket?.readyState !== WebSocket.OPEN

T3: *** FAILURE POINT ***
    → storyWebSocket is NULL (not just closed, but null)
    → wsManager is also NULL
    → Condition is true (null !== 1)
    → showError('Reconnecting...') displayed
    → Reconnection attempt: wsManager?.reconnect() → does nothing (wsManager is null)
    → Page stuck

T4: No recovery possible
    → User refreshes page
    → Same cycle repeats
─────────────────────────────────────────────────────────────────────────────────
```

## Next Investigation Steps

### 1. Determine When References Become Null

Add defensive logging to track when references change:
```javascript
// In main.js after initialize()
setInterval(() => {
    console.log('[WS Monitor]', {
        storyWebSocket: window.appState?.storyWebSocket?.readyState,
        wsManagerConnection: window.appState?.wsManager?.connection?.readyState,
        wsManagerExists: !!window.appState?.wsManager
    });
}, 5000);
```

### 2. Check If initWebSocket() Is Called for Resumed Adventures

Add logging at the start of initWebSocket():
```javascript
export function initWebSocket() {
    console.log('[initWebSocket] Called');
    console.log('[initWebSocket] wsManager before:', window.appState?.wsManager);
    // ...
}
```

### 3. Verify URL Parameters and localStorage State

Before the resume path decision:
```javascript
console.log('[initialize] URL params:', urlParams.toString());
console.log('[initialize] localStorage state:', stateManager.loadState());
```

### 4. Check for Code That Clears References

Known locations that set references to null:
- `uiManager.js:1180` - `resetApplicationState()` sets `storyWebSocket = null`
- Verify this function is not being called unexpectedly

## Potential Root Causes (Prioritized)

1. **HIGH: initWebSocket() never called for resumed adventures**
   - If neither URL param nor localStorage state exists, WebSocket is never created
   - Content may be cached/rendered from previous session

2. **MEDIUM: Race condition in async initialization**
   - `initialize()` is async, user may click before setup completes
   - wsManager created but initWebSocket() not yet called

3. **MEDIUM: WebSocket closes silently**
   - `onclose` handler may not properly trigger reconnection
   - References may be cleared without proper cleanup

4. **LOW: resetApplicationState() called unexpectedly**
   - This function explicitly sets `storyWebSocket = null`
   - May be triggered by some user action or error handling

## Testing Checklist (Updated)

To reproduce and verify the fix:

1. [ ] Start a fresh adventure (any story category/lesson topic)
2. [ ] Progress to Chapter 2 or 3 (not necessary to reach Chapter 9)
3. [ ] Add console logging to track WebSocket state
4. [ ] Refresh the page to trigger resume from Supabase
5. [ ] Immediately check browser console for WebSocket state
6. [ ] Wait for content to load
7. [ ] Check WebSocket state again
8. [ ] Click choice button
9. [ ] Observe if "Reconnecting..." appears
10. [ ] If failure occurs, check console for when references became null
11. [ ] Implement fix based on findings
12. [ ] Verify resumed adventure can continue normally

## Final Root Cause

The issue was caused by the dynamic import `await import('./main.js')` in the button onclick handler (uiManager.js). When this import executed, the browser was re-evaluating the main.js module due to caching issues, which reset `window.appState` to its initial values (with `wsManager: null` and `storyWebSocket: null`).

## Fix Applied

### 1. Exposed `makeChoice` globally (main.js)
```javascript
// Added at the end of main.js
window.makeChoice = makeChoice;
```

### 2. Removed dynamic import in onclick handler (uiManager.js)
```javascript
// Before (broken):
button.onclick = async (e) => {
    const { makeChoice } = await import('./main.js');  // This was resetting window.appState!
    // ...
}

// After (fixed):
button.onclick = async (e) => {
    // Use globally-exposed makeChoice to avoid dynamic import issues
    const storyWebSocket = window.appState?.storyWebSocket;
    // ...
    window.makeChoice(choice.id, choice.text);
}
```

### 3. Added module preloading with version strings (scripts.html)
All JavaScript modules now have explicit `<script type="module">` tags with version query strings to ensure proper cache busting:
```html
<script type="module" src="/static/js/uiManager.js?v=20260101a"></script>
<script type="module" src="/static/js/stateManager.js?v=20260101a"></script>
<!-- ... etc -->
```

### 4. Added localStorage persistence for resumed adventures (uiManager.js)
When `adventure_loaded` message is received, the state is saved to localStorage to enable proper resumption after page refresh.

## Related Issues

- Image spillover race condition fix: `wip/implemented/image_spillover_race_condition.md`
- Gemini model update: `app/services/llm/providers.py`

## Date Log

| Date | Event |
|------|-------|
| 2026-01-01 | Issue first observed during image spillover testing |
| 2026-01-01 | Confirmed fresh adventures work; issue specific to resumed adventures |
| 2026-01-01 | Identified dual WebSocket reference desync as root cause |
| 2026-01-01 | Implemented fix in webSocketManager.js (sync references during reconnect) |
| 2026-01-01 | Fix insufficient - both references are NULL, not just desync'd |
| 2026-01-01 | Updated documentation with detailed findings |
| 2026-01-01 | Noted testing can occur at any chapter, not just Chapter 9 |
| 2026-01-01 | **FIXED**: Identified dynamic import as true root cause; exposed makeChoice globally |
| 2026-01-01 | Added module preloading in scripts.html for proper cache busting |
| 2026-01-01 | Verified fix works - resumed adventure progresses to Chapter 10 successfully |
