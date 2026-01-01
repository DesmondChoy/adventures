# Image Spillover Race Condition

## Current Status

**Status: FIXED**

The race condition has been resolved by implementing Solutions 1 and 4 from the analysis below.

### Fix Applied
1. **Solution 1 (Remove DOM Dependency)**: The image filter no longer reads `currentChapter` from DOM, eliminating race conditions caused by unreliable DOM state during transitions.

2. **Solution 4 (Single Chapter Image Display Lock)**: Added `displayedImageChapter` tracking variable that prevents any older chapter's image from being displayed once a newer chapter's image has been shown.

### Changes Made
- Added `displayedImageChapter` variable in `uiManager.js:17`
- Modified `updateChapterImage()` to check and update `displayedImageChapter`
- Simplified filter in `handleMessage()` to use only `minExpectedImageChapter`
- Added `resetDisplayedImageChapter()` export function
- Reset `displayedImageChapter` in: `makeChoice()`, `startAdventure()`, `resetApplicationState()`

### Previous State (for reference)
- Image spillover prevented in most transitions (Chapters 2, 3, 4, 5 tested successfully)
- `minExpectedImageChapter` filtering prevents most stale images
- `hideChapterImage()` hides container immediately on choice click
- Fresh adventures start with clean image state

### Edge Case That Was Fixed
- Chapter 5 image appeared during Chapter 6 content display
- Occurred when user clicked choice button before previous chapter's image had loaded
- The late-arriving image from the previous chapter "slipped through" the filter

## Problem Statement

When a user makes a choice to advance to the next chapter, the previous chapter's image may "spill over" and appear in the background while the new chapter's content is streaming. This creates a poor user experience where the visual doesn't match the narrative.

**User-observed behavior:**
1. User is on Chapter 5, content has finished streaming
2. Chapter 5 image has NOT yet loaded (still generating on server)
3. User clicks a choice button to advance to Chapter 6
4. Chapter 6 content begins streaming
5. **BUG:** Chapter 5 image arrives and displays, appearing below Chapter 6 text
6. Chapter 5 image remains until Chapter 6 image eventually loads and replaces it

**Expected behavior:**
- When a choice is clicked, the background should immediately become blank/white
- No image should appear until the current chapter's image is ready

## Root Cause Analysis

### The Current Fix Mechanism (Commit 193926d)

The fix implements a two-layer defense:

**Layer 1: Immediate hiding on choice click** (`main.js:119-123`)
```javascript
// CRITICAL: Advance image chapter and hide container BEFORE sending message
const nextChapter = currentChapter.length + 2; // +1 for 0-based, +1 for next chapter
advanceExpectedImageChapter(nextChapter);
hideChapterImage();

// Send state and choice data to server
window.appState.wsManager.sendMessage({...});
```

**Layer 2: Filter incoming images** (`uiManager.js:1044-1056`)
```javascript
} else if (data.type === 'chapter_image_update') {
    const currentChapterEl = document.getElementById('current-chapter');
    const currentChapter = currentChapterEl ? parseInt(currentChapterEl.textContent, 10) : 0;

    // Two conditions must BOTH be true:
    // 1. Image chapter matches currently displayed chapter
    // 2. Image chapter >= minimum expected chapter
    if (data.chapter_number === currentChapter && data.chapter_number >= minExpectedImageChapter) {
        updateChapterImage(data.chapter_number, data.image_data);
    } else {
        console.log(`[IMAGE DEBUG] Ignoring image...`);
    }
}
```

### Why The Bug Still Occurs

The race condition occurs in this specific timing window:

```
Timeline:
─────────────────────────────────────────────────────────────────────────────────
T0: User on Chapter 5, content done streaming
    DOM: currentChapter = 5
    State: minExpectedImageChapter = 5
    Server: Chapter 5 image generation in progress (takes 5-10 seconds)

T1: User clicks choice button
    → advanceExpectedImageChapter(6) called → minExpectedImageChapter = 6
    → hideChapterImage() called → container hidden
    → WebSocket message sent to server

T2: Server processes choice, sends chapter_update for Chapter 6
    (This message is in-flight to client)

T3: *** RACE CONDITION WINDOW ***
    Server's Chapter 5 image generation completes
    Server sends chapter_image_update with chapter_number: 5

T4: Client receives chapter_image_update for Chapter 5
    Check: data.chapter_number (5) === currentChapter (???)

    IF currentChapter DOM still shows 5 (chapter_update not yet processed):
        → 5 === 5 is TRUE
        → But 5 >= 6 is FALSE
        → Image SHOULD be rejected ✓

    IF currentChapter DOM already updated to 6:
        → 5 === 6 is FALSE
        → Image rejected ✓

T5: Client receives chapter_update for Chapter 6
    DOM: currentChapter = 6
    Content streaming begins
─────────────────────────────────────────────────────────────────────────────────
```

**Theoretical analysis suggests the filter should work**, but empirical testing showed the Chapter 5 image DID appear. This suggests:

1. **Possible cause**: The `chapter_update` message arrived and updated DOM to "Chapter 6" BEFORE the Chapter 5 image arrived, but `minExpectedImageChapter` was somehow not yet 6, OR
2. **Possible cause**: There's a JavaScript event loop edge case where the image handler runs with stale variable values
3. **Possible cause**: Another code path is displaying the image that bypasses the filter

### Key Observation

When the spillover occurred during testing, the image container's class was:
```
"chapter-image-container mb-6"  ← NO "hidden" class!
```

This proves that `updateChapterImage()` was called (which does `imageContainer.classList.remove('hidden')`), meaning the filter check passed when it shouldn't have.

## Files Involved

### Primary Files
- **`/app/static/js/main.js`** - Choice handling, calls `advanceExpectedImageChapter()` and `hideChapterImage()`
- **`/app/static/js/uiManager.js`** - Image filtering logic, `handleMessage()`, `updateChapterImage()`

### Key Functions
| Function | File | Purpose |
|----------|------|---------|
| `makeChoice()` | main.js:102 | Handles user choice, initiates chapter transition |
| `advanceExpectedImageChapter()` | uiManager.js:1259 | Updates `minExpectedImageChapter` filter |
| `hideChapterImage()` | uiManager.js:1270 | Hides image container, removes 'show' class |
| `handleMessage()` | uiManager.js:990 | Processes WebSocket messages including images |
| `updateChapterImage()` | uiManager.js:783 | Displays image, removes 'hidden' class |

### State Variables
- `minExpectedImageChapter` (uiManager.js:16) - Module-level variable for filtering

## Potential Solutions

### Solution 1: Store Expected Chapter at Click Time (Recommended)

**Problem**: The filter checks `currentChapter` from DOM at message receipt time, which may have changed.

**Solution**: Store the expected chapter number when the choice is clicked, and use that stored value for filtering instead of reading from DOM.

```javascript
// In uiManager.js
let expectedImageChapterAtClick = null;  // New variable

export function setExpectedImageChapter(chapter) {
    expectedImageChapterAtClick = chapter;
    minExpectedImageChapter = chapter;
}

// In handleMessage(), change the filter:
if (data.type === 'chapter_image_update') {
    // Use the stored expected chapter, not DOM
    if (data.chapter_number >= minExpectedImageChapter) {
        updateChapterImage(data.chapter_number, data.image_data);
    }
}
```

**Pros**: Eliminates dependency on DOM timing
**Cons**: Simple change, minimal risk

### Solution 2: Track In-Flight Image Requests

**Problem**: Late-arriving images from previous chapters slip through.

**Solution**: Maintain a map of "pending" image requests and cancel/ignore them on chapter transition.

```javascript
let pendingImageChapter = null;

// When chapter starts
pendingImageChapter = currentChapter;

// When choice is clicked
pendingImageChapter = nextChapter;

// When image arrives
if (data.chapter_number !== pendingImageChapter) {
    // Reject - this image is stale
    return;
}
```

**Pros**: Clear semantic meaning
**Cons**: Requires tracking state across multiple places

### Solution 3: Timestamp-Based Rejection

**Problem**: Race conditions due to network timing.

**Solution**: Include timestamps in image requests and responses, reject images generated before the last choice click.

```javascript
let lastChoiceTimestamp = 0;

// When choice is clicked
lastChoiceTimestamp = Date.now();

// Send timestamp with choice
wsManager.sendMessage({
    ...
    choiceTimestamp: lastChoiceTimestamp
});

// Server includes timestamp in image response
// Client rejects if image.requestTimestamp < lastChoiceTimestamp
```

**Pros**: Robust against all timing issues
**Cons**: Requires backend changes

### Solution 4: Single Chapter Image Display Lock

**Problem**: Multiple image updates can race.

**Solution**: Implement a "lock" that only allows one chapter's image to be displayed at a time.

```javascript
let displayedImageChapter = null;

function updateChapterImage(chapterNumber, imageData) {
    // Only update if this is a newer chapter
    if (displayedImageChapter !== null && chapterNumber <= displayedImageChapter) {
        console.log(`Rejecting image for chapter ${chapterNumber}, already showing ${displayedImageChapter}`);
        return;
    }

    displayedImageChapter = chapterNumber;
    // ... rest of update logic
}
```

**Pros**: Simple, prevents regression
**Cons**: May not handle edge cases like resuming adventures

### Solution 5: Remove DOM Dependency Entirely

**Problem**: Reading `currentChapter` from DOM is unreliable.

**Solution**: Track chapter state purely in JavaScript, never read from DOM for logic.

```javascript
// In stateManager.js or dedicated module
let currentChapterState = {
    chapter: 1,
    expectingImageForChapter: 1
};

// All updates go through state manager
export function advanceToChapter(chapter) {
    currentChapterState.chapter = chapter;
    currentChapterState.expectingImageForChapter = chapter;
}

// Image filter uses state, not DOM
if (data.chapter_number === currentChapterState.expectingImageForChapter) {
    // Show image
}
```

**Pros**: Clean architecture, no race conditions
**Cons**: Larger refactor, more testing needed

## Recommended Approach

**Solution 1 (Remove DOM Dependency)** combined with **Solution 4 (Single Chapter Image Display Lock)** provides the best balance of:
- Minimal code changes
- Robust protection against race conditions
- No backend changes required
- Easy to test and verify

**This approach has been implemented.**

## Testing Checklist

To verify the fix:

1. [x] Start fresh adventure
2. [x] Click choice buttons IMMEDIATELY after content finishes streaming (before image loads)
3. [x] Verify background stays blank during transition
4. [x] Repeat for all 10 chapters
5. [ ] Test rapid clicking (multiple chapters in quick succession)
6. [ ] Test with slow network (simulate delayed image delivery)
7. [x] Verify image eventually appears for current chapter
8. [x] Check browser console for `[IMAGE DEBUG]` logs showing rejections

### Test Results (2026-01-01)

**Full 10-chapter adventure completed successfully with Playwright MCP.**

| Chapter | Transition | Image Container | Image Loaded | Notes |
|---------|------------|-----------------|--------------|-------|
| 1→2 | ✅ | Hidden | ✅ Ch.2 | Guardian choice |
| 2→3 | ✅ | Hidden | ✅ Ch.3 | LESSON (Venus rotation) |
| 3→4 | ✅ | Hidden | ✅ Ch.4 | REFLECT |
| 4→5 | ✅ | Hidden | ✅ Ch.5 | STORY |
| 5→6 | ✅ | Hidden | ✅ Ch.6 | LESSON (Galaxy spirals) |
| 6→7 | ✅ | Hidden | ✅ Ch.7 | REFLECT |
| 7→8 | ✅ | Hidden | ✅ Ch.8 | LESSON (Astronaut floating) |
| 8→9 | ✅ | Hidden | ✅ Ch.9 | STORY |
| 9→10 | ✅ | Hidden | ✅ Ch.10 | CONCLUSION - **No WebSocket issue!** |

**Summary screen**: Initially showed placeholder data due to WebSocket timeout (8 seconds). After page refresh, displayed correct data:
- Chapters Completed: 10
- Questions Answered: 3 (100% correct)
- All chapter summaries meaningful
- All lesson explanations present

## Debug Logging

The current implementation includes debug logging. To investigate spillover:

```javascript
// In browser console, look for:
[IMAGE DEBUG] chapter_image_update received: image for chapter X, min expected is Y, displayed is Z
[IMAGE DEBUG] Passing image for chapter X to updateChapterImage
[IMAGE DEBUG] Displaying image for chapter X, updated displayedImageChapter to X
[IMAGE DEBUG] Ignoring stale image for chapter X (min expected: Y)
[IMAGE DEBUG] Rejecting image for chapter X - already showed chapter Z
[IMAGE DEBUG] Advanced expected image chapter to X
[IMAGE DEBUG] Reset displayedImageChapter to 0
[UI FIX] Hiding visible image container
```

The two-layer defense now works as:
1. `minExpectedImageChapter` filter rejects stale images before they reach `updateChapterImage`
2. `displayedImageChapter` lock in `updateChapterImage` prevents regression (showing older chapter after newer)

---

## Related Issues

- **WebSocket Reconnection Failure (Resumed Adventures)**: See `wip/websocket_reconnection_resumed_adventures.md`
  - Observed during testing of this fix
  - Only affects resumed adventures, not fresh ones
  - Chapter 9→10 transition fails with "Reconnecting..." error
