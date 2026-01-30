---
description: Run end-to-end tests through a complete adventure using Playwright MCP. Tests selection screen, chapter progression, and summary.
allowed-tools: mcp__playwright__*, Bash(uvicorn:*), Bash(source:*), Bash(lsof:*), Bash(kill:*), Read
---

Run a complete end-to-end test of the Learning Odyssey application using Playwright MCP. This skill navigates through all 10 chapters of an adventure and validates each step.

## Prerequisites

Before starting, ensure the dev server is running.

### Check if Server is Running

```bash
lsof -i :8000
```

### Start Server if Needed

If no process is listening on port 8000:

```bash
source .venv/bin/activate && uvicorn app.main:app --reload &
```

Wait 3-5 seconds for the server to start, then verify it's running with `lsof -i :8000`.

## Phase 1: Selection Screen

### Actions

1. Navigate to `http://localhost:8000/select`
2. Take a snapshot to verify the page loaded
3. Verify both carousels are visible (story category and lesson topic)
4. Test carousel rotation by clicking arrow buttons
5. Test card selection by clicking a carousel card
6. Check console for JavaScript errors with `browser_console_messages`

### Validation

- Both carousels render with visible cards
- Arrow buttons rotate the carousel horizontally
- Clicking a card provides visual feedback (selection state)
- No JavaScript errors in console (especially ES6 module issues)

### Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Cards visible but not clickable | ES6 modules loaded twice | Check `scripts.html` for duplicate module loads |
| Carousel not showing | Stale cached JavaScript | Update version strings in `base.html` and `scripts.html` |
| Rotation not working | Carousel class not initialized | Check `carousel-manager.js` exports |

**STOP immediately if any validation fails. Do not proceed to start an adventure.**

## Phase 2: Start Adventure

### Actions

1. Select a story category (click a card in the first carousel)
2. Select a lesson topic (click a card in the second carousel)
3. Click the "Begin Adventure" button
4. Wait for WebSocket connection and initial content to load

### Validation

- "Begin Adventure" button becomes enabled after selections
- Page transitions to adventure view
- Chapter 1 content begins streaming

## Phase 3: Chapter Progression (Chapters 1-10)

Loop through each chapter with these validations.

### Per-Chapter Actions

1. Verify chapter counter shows correct "Chapter X of 10"
2. Verify background is blank (no image from previous chapter)
3. Wait for text to stream (allow up to 30 seconds)
4. Verify choice buttons appear after streaming completes
   - Chapters 1-9: exactly 3 choice buttons
   - Chapter 10 (CONCLUSION): 0 choice buttons
5. Wait for image to load (5-10 seconds after content finishes)
6. Check console for errors with `browser_console_messages`
7. Click a choice button to proceed to next chapter

### Validation Checklist

- [ ] Chapter counter updated immediately
- [ ] Background is white/blank (no image spillover)
- [ ] Loader appears while waiting for content
- [ ] Text streams progressively (word-by-word or chunk-by-chunk)
- [ ] Loader hides when streaming starts
- [ ] Correct number of choice buttons appear
- [ ] Image loads with alt text "Illustration for Chapter X"
- [ ] No console errors

### Image Spillover Bug

**Critical to check:** When the loader appears between chapters, the background must be completely white/blank. If the previous chapter's image remains visible during loading or while new content streams, this is a bug that must be flagged immediately.

### Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Previous image showing | `chapter_update` not hiding image | Check `uiManager.js` hides image on `chapter_update` |
| Buttons unresponsive | WebSocket disconnected | Check `webSocketManager.js` reconnection logic |
| Image never appears | Image generation failed | Check backend logs for Imagen API errors |
| Content doesn't stream | LLM generation failed | Check backend logs for API errors |

**STOP immediately if any anomaly is detected. Do not continue hoping it resolves.**

## Phase 4: Summary Screen

### Actions

1. After Chapter 10 completes, click the "Memory Lane" button
2. Wait for summary page to load (first load may take up to 30 seconds)
3. Verify all summary statistics

### Validation

- [ ] Summary page loads within 3-5 seconds (up to 30s for first time)
- [ ] **Chapters Completed** shows `10`
- [ ] **Questions Answered** shows `3`
- [ ] All 10 chapter summaries have meaningful titles (not placeholders like "Chapter 1: The Beginning")
- [ ] All 3 lesson questions display actual content from the adventure
- [ ] Each question shows user's selected answer and explanation

### Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Shows placeholder data | Race condition in fetch patch | Refresh page; verify `patchReactFetch()` runs immediately |
| Missing summaries | Background task didn't complete | Check backend logs for summary generation |

## Anomaly Handling Protocol

When ANY anomaly occurs:

1. **Stop testing immediately** - Do not continue through remaining chapters
2. **Close browser** with `browser_close`
3. **Check console** with `browser_console_messages` for JavaScript errors
4. **Review backend logs** for API or WebSocket errors
5. **Consult documentation:**
   - `memory-bank/` - Architectural decisions, system patterns
   - `wip/implemented/` - Implementation history for past bug fixes

## Test Report

After completing (or stopping due to failure), generate this report:

```
## E2E Test Results

**Status:** PASS / FAIL
**Chapters Completed:** X/10

### Selection Screen
- Carousels visible: ✓/✗
- Carousel rotation: ✓/✗
- Card selection: ✓/✗

### Chapter Progression
- Chapter 1: ✓/✗
- Chapter 2: ✓/✗
- ... (continue for all completed chapters)

### Summary Screen
- Page loaded: ✓/✗
- Chapters Completed = 10: ✓/✗
- Questions Answered = 3: ✓/✗
- Meaningful titles: ✓/✗

### Issues Found
- <description of any issues>

### Console Errors
- <any JavaScript errors captured>
```

## Wait Times Reference

- Chapter content streaming: 10-20 seconds
- Image generation: 5-10 seconds after content
- Summary page load: 3-5 seconds
- Summary generation (first time): up to 30 seconds
