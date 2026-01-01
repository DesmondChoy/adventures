# Manual Testing with Playwright MCP

Use the Playwright MCP server for end-to-end testing. Launch the dev server first, then navigate through a complete adventure.

```bash
# Terminal 1: Start the dev server
source .venv/bin/activate
uvicorn app.main:app --reload

# Terminal 2: Use Playwright MCP via Claude Code to test
```

## Test Flow

1. Navigate to `http://localhost:8000/select`
2. Verify carousel is working (see Selection Screen Checklist below)
3. Select a story category and lesson topic
4. Progress through all 10 chapters by clicking choices
5. Click "Memory Lane" to view the summary
6. Verify summary shows actual adventure data

## Selection Screen Checklist

**Complete ALL items before selecting a story category.**

After page loads, verify each item:

- [ ] **Carousel is visible** - Both story category and lesson topic carousels render with cards
- [ ] **Carousel rotates** - Left/right arrow buttons rotate carousel horizontally (cycle through cards)
- [ ] **Cards are clickable** - Clicking a carousel card selects it (visual feedback: card highlights or changes state)
- [ ] **Selection registers** - Selected category/topic updates the UI (e.g., "Begin Adventure" button enables)
- [ ] **No console errors** - Check `browser_console_messages` for JavaScript errors (especially ES6 module issues)

**If any checkbox fails, STOP immediately and debug. Do not proceed to start an adventure.**

Common carousel issues:
- Cards visible but not clickable → Check for duplicate ES6 module instances (see `scripts.html` comments)
- Carousel not showing → Check for stale cached JavaScript (update version strings in `base.html`)
- Rotation not working → Check carousel-manager.js initialization and Carousel class exports

## Anomaly Handling

**IMPORTANT: Stop testing immediately if any anomaly is detected.** Do not continue through all 10 chapters hoping the issue resolves itself.

When an anomaly occurs:
1. Close the Playwright browser (`browser_close`)
2. Check console messages for errors (`browser_console_messages`)
3. Review backend logs for API or WebSocket errors
4. Consult documentation for context:
   - `memory-bank/` - Architectural decisions, system patterns, implementation plans
   - `wip/implemented/` - Detailed implementation history for past bug fixes and features
5. Debug the root cause before resuming testing

Examples of anomalies that require immediate investigation:
- Image loads before text content finishes streaming
- Previous chapter's image remains visible when new chapter starts
- Choice buttons don't appear after content streams
- Chapter counter doesn't update
- Content doesn't stream at all (stuck on loader)
- JavaScript errors in console

### Image Spillover Bug

Watch for this specific issue: when the loader appears and placeholder text shows, the background should be completely white/blank. However, the previous chapter's image may "spill over" and appear in the background during loading. The image persists even as the new chapter's text streams in, only disappearing when the current chapter's image finally loads.

This is a poor user experience and should be flagged immediately. The previous chapter's image must be fully hidden the moment a new chapter transition begins (when the choice button is clicked).

## Per-Chapter Checklist

**Complete ALL items before clicking a choice button to proceed.**

After clicking a choice button, verify each item in order:

- [ ] **Chapter counter updated** - Shows correct "Chapter X of 10" immediately
- [ ] **Background is blank** - No image spillover from previous chapter; background is white/clean
- [ ] **Loader appears** - Loading indicator visible while waiting for LLM response
- [ ] **Text streams progressively** - Content appears word-by-word or chunk-by-chunk (allow up to 30 seconds)
- [ ] **Loader hides** - Loading indicator disappears when streaming starts
- [ ] **Choice buttons appear** - 3 clickable buttons visible after streaming completes (0 buttons for Chapter 10/CONCLUSION only)
- [ ] **Image loads** - Appears 5-10 seconds after content finishes; alt text matches `"Illustration for Chapter X"`
- [ ] **No console errors** - Check `browser_console_messages` for JavaScript errors

**If any checkbox fails, STOP immediately and debug. Do not proceed to the next chapter.**

## Adventure Resumption Checklist

Test that resuming a saved adventure works correctly:

- [ ] **No errors on resume** - Adventure loads without JavaScript or console errors
- [ ] **Works for guest users** - Guest sessions can resume from localStorage
- [ ] **Works for authenticated users** - Google OAuth sessions can resume from Supabase
- [ ] **State reconstructed** - Chapter counter shows correct position, story content displays
- [ ] **Choice buttons functional** - All 3 choice buttons appear and are clickable
- [ ] **Images do not load** - This is expected (known trade-off to avoid image storage)
- [ ] **Adventure continues** - Clicking a choice progresses the story normally

## Summary Screen Checklist

After completing all 10 chapters and clicking "Memory Lane":

- [ ] **Page loads** - Summary screen appears within 3-5 seconds (first load may take up to 30 seconds)
- [ ] **Chapters Completed** - Shows `10`
- [ ] **Questions Answered** - Shows `3`
- [ ] **Chapter summaries** - All 10 have meaningful titles (not placeholder text like "Chapter 1: The Beginning")
- [ ] **Lesson questions** - All 3 questions display actual content from the adventure
- [ ] **Answers and explanations** - Each question shows user's selected answer and explanation

If placeholder data appears, refresh the page - this indicates a race condition in `react-app-patch.js`.

## WebSocket Stability

Monitor throughout the test:

- Watch for timeout errors in console (especially after idle periods)
- If connection drops, the app should attempt reconnection
- After reconnection, state should be preserved

## Common Issues and Debugging

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Carousel cards not clickable | ES6 modules loaded twice (duplicate Carousel classes) | Ensure only `main.js` loads modules in `scripts.html`; don't load modules directly |
| Carousel not showing | Stale cached JavaScript | Update version strings in `base.html` and `scripts.html` |
| Carousel rotation not working | Carousel class not initialized | Check `carousel-manager.js` exports and `main.js` imports |
| Previous chapter's image showing | `chapter_update` not hiding image container | Check `uiManager.js` hides image on `chapter_update` |
| Summary shows placeholder data | Race condition - fetch not patched in time | Refresh page; verify `patchReactFetch()` is called immediately on script load |
| Buttons unresponsive after idle | WebSocket disconnected silently | Check reconnection logic in `webSocketManager.js` |
| Image never appears | Image generation failed or timed out | Check backend logs for Imagen API errors |
| Content doesn't stream | LLM generation failed | Check backend logs for API errors |

## Wait Times Reference

- Chapter content streaming: 10-20 seconds
- Image generation: 5-10 seconds after content
- Summary page load: 3-5 seconds
- Summary generation (first time): up to 30 seconds
