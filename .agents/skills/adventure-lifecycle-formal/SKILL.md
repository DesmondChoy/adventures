---
name: adventure-lifecycle-formal
description: "Formally verify the WebSocket adventure lifecycle, persistence retries, background summary locking, and summary reveal state machine with TLA+ and TLC. Use whenever editing app/routers/websocket_router.py, app/services/websocket/persistence.py, app/services/websocket/choice_processor.py, or app/services/websocket/summary_generator.py."
---

# Adventure Lifecycle Formal Verification

## When to run

Run this check before finishing any change that touches:

- `app/routers/websocket_router.py` (`story_websocket`, initial save retry handling, server-authoritative state handling)
- `app/services/websocket/persistence.py` (`store_state_with_retry`, preallocated `new_adventure_id` upsert)
- `app/services/websocket/choice_processor.py` (`handle_reveal_summary`, `_store_summary_safe`, `generate_chapter_summary_background`)
- `app/services/websocket/summary_generator.py` (`ensure_all_summaries_exist`)

Last confirmed in sync with code at base commit: `82e0de2` (plus the fix resetting `state_manager.state = None` when initial save exhausts retries).

## What is verified

Model: `formal/AdventureLifecycle.tla`
Clean config: `formal/AdventureLifecycle.cfg`
Bug replays: `formal/replays/*.cfg`
Reader view: `formal/adventure_lifecycle.view.mjs`

Tool: TLA+ checked with TLC (`tla2tools-1.7.4.jar`, pinned SHA-256 `936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88`).

Properties checked across every interleaving of messages, transient DB failures, ambiguous write timeouts, background summary tasks, and reveal retries:

1. `SingleRecordPerAdventure`: Retrying an initial save after an ambiguous commit never creates a second database row (replays commit `88e1ab5`).
2. `ServerStateAuthoritative`: A stale client payload arriving on `reveal_summary` never overwrites server chapters (replays commit `3dfb9bd`).
3. `SummaryOnlyAfterConclusion`: `reveal_summary` before `CONCLUSION` never crashes, and `summary_ready` is only sent once the `SUMMARY` chapter is appended and persisted with `is_complete=True` (replays commit `f4b9b11`).
4. `ValidSummaryNeverClobbered`: A failing background or duplicate summary task never overwrites an already-valid chapter summary (replays commit `bf68786`).
5. `NoUnsavedChapterProgress`: If the initial adventure save exhausts retries, subsequent chapter generation cannot proceed with `adventure_id = None` (caught live bug in `app/routers/websocket_router.py:649`).

## Bounds and what is NOT covered

- Bounded to `StoryLength = 2` (Chapter 1 story, Chapter 2 conclusion, Chapter 3 summary) and one concurrent background chapter-summary task.
- Does not model Supabase JWT authentication, HTTP summary routes, LLM prompt content, or frontend DOM/image-loading races.

## Run the check

```bash
bash tools/run_formal_verification.sh
```

This runs TLC on `formal/AdventureLifecycle.cfg` (must pass) and on all five `formal/replays/*.cfg` configs (each must fail with its expected invariant violation).

To inspect counterexamples or render the Mermaid statechart in plain words, run the pstack `/statechart` skill against `formal/AdventureLifecycle.tla` with `--view formal/adventure_lifecycle.view.mjs`.

## Interpreting failures

1. **Clean config fails:** Read the shortest path with `/statechart`. Replay each action step-by-step against the real Python code in a pytest test. If the real code reproduces the failure, fix the bug in code; never weaken an invariant to make TLC pass.
2. **A bug-replay config unexpectedly passes:** The model no longer exercises the historical failure mode. Fix the spec or replay config before merging.
3. **Intentional lifecycle change:** Update `formal/AdventureLifecycle.tla` and `formal/adventure_lifecycle.view.mjs` to match the new code, confirm every action maps to real code lines, rerun `bash tools/run_formal_verification.sh`, and move the sync commit SHA above forward once committed.
