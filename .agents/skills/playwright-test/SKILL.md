---
description: Run the Learning Odyssey E2E suite with deterministic Playwright preflight coverage followed by a real 10-chapter Codex Browser journey, Memory Lane validation, and a read-only Supabase persistence and telemetry audit.
---

Run the Learning Odyssey end-to-end suite. The default mission is a real
browser journey through all 10 chapters, followed by Memory Lane and summary
screen validation. This catches more anomalies than deterministic assertions
alone, so do not treat the automated Playwright suite as a substitute.

Default run order:

1. Run the automated Playwright preflight.
2. If preflight fails, stop and report the exact failure.
3. If preflight passes, use Codex Browser to complete the full 10-chapter
   browser adventure. Use Playwright MCP only when the built-in browser is not
   available in the current Codex surface.
4. Click Memory Lane, wait for the summary screen, and validate it.
5. Audit the completed adventure and its telemetry directly in Supabase.

Only skip the full browser adventure when the user explicitly asks for
`fast-only`, `automated-only`, or targeted regression checks.

The recent regression history matters:

- `tests/playwright/carousel-visual.spec.ts` already covers desktop/mobile
  carousel layout, rotated states, and selection enabling.
- `tests/playwright/chapter-transition.spec.ts` already covers the stale stream
  bug where Chapter 1 text prefixed Chapter 2 after `chapter_update`.
- Recent summary fixes were about `summary_ready`, `summary_state_id`, and auth
  token handoff into `/adventure/summary`.

Do not grind through ten live chapters when preflight has already failed. Stop,
report the exact failure, and fix that first. If preflight passes, the full
browser run is mandatory.

## Automated Preflight

Run this before any long manual journey unless the user explicitly asked for
manual MCP only:

```bash
npx playwright test
```

The Playwright config starts the app on `127.0.0.1:8000` with the repo's
`.venv` Python. Do not start a second server for this path.

For targeted work:

```bash
npx playwright test tests/playwright/carousel-visual.spec.ts
npx playwright test tests/playwright/chapter-transition.spec.ts
```

Use snapshot updates only when the UI change is intentional:

```bash
npm run test:visual:carousel:update
```

If the preflight fails, stop. The full live adventure will mostly waste time.
If the preflight passes, continue to the full Codex Browser run.

## Full Codex Browser Path

This is the priority path. Use the in-app Codex Browser to exercise the real
browser app through:

- real WebSocket lifecycle
- real LLM/content streaming
- real image generation
- real Chapter 10 -> Memory Lane -> summary page handoff

Do not stop after the automated preflight unless the user asked for that. Keep
the live task phased and inspect rendered state after every chapter. Enable
Browser Developer mode when console, network, or DOM evidence is needed.

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
3. Continue as guest if the auth screen appears
4. Verify the story category carousel is visible
5. Click carousel arrows and a card
6. Verify the continue button enables
7. Continue to the lesson carousel
8. Verify the lesson carousel is visible, rotates, and selection enables start
9. Inspect the Browser console for JavaScript errors

### Validation

- Both carousels render with visible cards
- Arrow buttons rotate the carousel horizontally
- Clicking a card provides visual feedback (selection state)
- Selection enables `#category-continue-btn` and `#lesson-start-btn`
- No JavaScript errors in console, especially duplicate ES module instances
- If carousel screenshots already passed, do not over-inspect visual geometry
  manually. Smoke the UI and move on.

### Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Cards visible but not clickable | ES6 modules loaded twice | Check `scripts.html` for duplicate module loads |
| Carousel not showing | Stale cached JavaScript | Update version strings in `base.html` and `scripts.html` |
| Rotation not working | Carousel class not initialized | Check `carousel-manager.js` exports |
| Mobile cards overlap/clipped badly | Carousel radius or CSS regression | Run `npx playwright test tests/playwright/carousel-visual.spec.ts` |

**STOP immediately if any validation fails. Do not proceed to start an adventure.**

## Phase 2: Start Adventure

### Actions

1. If Phase 1 did not leave both selections active, select a story category and
   lesson topic now
2. Click the enabled `#lesson-start-btn`
3. Wait for WebSocket connection and initial content to load

### Validation

- The start button becomes enabled after selections
- Page transitions to adventure view
- Chapter 1 content begins streaming
- No console errors like `WebSocket open handler failed`, `WebSocket is not open`,
  or handler/import failures
- Loader does not hang forever before the first chapter

## Phase 3: Chapter Progression (Chapters 1-10)

Loop through each chapter with these validations.

### Per-Chapter Actions

1. Verify chapter counter shows correct "Chapter X of 10"
2. Verify background is blank (no image from previous chapter)
3. Verify `#storyContent` is empty before new chapter text arrives
4. Wait for text to stream (allow up to 30 seconds)
5. Verify new text does not start with or contain previous chapter text
6. Verify choice buttons appear after streaming completes
   - Chapters 1-9: exactly 3 choice buttons
   - Chapter 10 (CONCLUSION): 0 choice buttons, then Memory Lane controls
7. Wait for image to load (5-15 seconds after content finishes)
8. Inspect the Browser console for errors
9. Chapters 1-9: click a choice button to proceed. Chapter 10: stop after
   Memory Lane controls appear.

### Validation Checklist

- [ ] Chapter counter updated immediately
- [ ] Background is white/blank (no image spillover)
- [ ] Previous chapter text is cleared before the next stream
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
| Previous text prefixes new chapter | Stream buffer not cleared | Run `npx playwright test tests/playwright/chapter-transition.spec.ts`; check `clearChapterTransitionContent()` |
| Buttons unresponsive | WebSocket disconnected | Check `webSocketManager.js` reconnection logic |
| Image never appears | Image generation failed | Check backend logs for Imagen API errors |
| Content doesn't stream | LLM generation failed | Check backend logs for API errors |

**STOP immediately if any anomaly is detected. Do not continue hoping it resolves.**

## Phase 4: Summary Screen

### Actions

1. After Chapter 10 completes, click the Memory Lane button
2. Wait for navigation to `/adventure/summary?state_id=<id>`
3. Verify `localStorage.summary_state_id` matches the URL `state_id`
4. Verify auth handoff exists:
   - `localStorage.summary_access_token` is present, or
   - a Supabase `sb-*-auth-token` entry is present for fallback recovery
5. Wait for summary page to load (first load may take up to 30 seconds)
6. Verify all summary statistics

### Validation

- [ ] Summary page loads within 3-5 seconds (up to 30s for first time)
- [ ] URL contains one clean `state_id`
- [ ] Summary API is not blocked by `401`, `400`, `404`, or "No Adventure Found"
- [ ] **Chapters Completed** shows `10`
- [ ] **Questions Answered** shows `3`
- [ ] All 10 chapter summaries have meaningful titles
- [ ] All 3 lesson questions display actual content from the adventure
- [ ] Each question shows user's selected answer and explanation

Flag placeholder titles immediately: `Chapter X`, `Adventure Chapter`,
`Chapter Summary`, `Summary not available`, `A scene from the story`, or
anything clearly generic.

### Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Shows placeholder data | Race condition in fetch patch | Refresh page; verify `patchReactFetch()` runs immediately |
| Missing summaries | Background task didn't complete | Check backend logs for summary generation |
| Summary redirects without state | `summary_ready` handoff failed | Check `viewAdventureSummary()` and `uiManager.js` summary fallback |
| Summary API unauthorized | Auth token not carried to summary app | Check `summary_access_token` and `summary-state-handler.js` fallback |

## Phase 5: Supabase Audit

Use the exact `state_id` from the validated Memory Lane URL. Run the checked-in
read-only audit against the same Supabase project used by the live app:

```bash
.venv/bin/python tools/audit_e2e_supabase.py --state-id <state-id>
```

The command uses `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` from the local
environment. Never print either value. It must report `PASS` and validate:

- the completed adventure has its authenticated owner, client UUID, world,
  topic, and environment
- persisted state contains Chapters 1-10 plus the internal summary chapter
- Chapter 10 is `conclusion`, the final internal chapter is `summary`, and all
  chapter content is non-empty
- 10 meaningful, unique titles and summaries are stored
- all three lesson questions and answers are stored
- `adventure_started`, `chapter_viewed`, `choice_made`, and `summary_viewed`
  events are linked to the same adventure and owner
- `chapter_viewed` covers Chapters 1-10; resumption duplicates are allowed
- `choice_made` occurs exactly once for Chapters 1-10
- telemetry chapter types and environment match the persisted adventure

If the audit fails, the E2E run fails. Report the missing or inconsistent rows;
do not compensate by editing Supabase data.

## Anomaly Handling Protocol

When ANY anomaly occurs:

1. **Stop testing immediately** - Do not continue through remaining chapters
2. **Check the Browser console** for JavaScript errors
3. Take a snapshot if the visible state matters
4. **Close the Browser tab**
5. **Review backend logs** for API or WebSocket errors
6. **Consult documentation:**
   - `memory-bank/` - Architectural decisions, system patterns
   - `wip/implemented/` - Implementation history for past bug fixes

## Test Report

After completing (or stopping due to failure), generate this report:

```
## E2E Test Results

**Status:** PASS / FAIL
**Chapters Completed:** X/10

### Automated Playwright Preflight
- Full suite: ✓/✗/skipped
- Carousel visual regression: ✓/✗/skipped
- Chapter transition regression: ✓/✗/skipped

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
- Clean state_id URL: ✓/✗
- Auth handoff present: ✓/✗
- Chapters Completed = 10: ✓/✗
- Questions Answered = 3: ✓/✗
- Meaningful titles: ✓/✗

### Supabase Audit
- Adventure persistence: ✓/✗
- Chapter and summary state: ✓/✗
- Lesson answers: ✓/✗
- Telemetry event coverage: ✓/✗
- Ownership and environment linkage: ✓/✗

### Recent Regression Probes
- No duplicate module / carousel init failure: ✓/✗
- WebSocket handlers active before open: ✓/✗
- No image spillover on chapter_update: ✓/✗
- No stale story text after chapter_update: ✓/✗
- Summary_ready handoff works: ✓/✗

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
