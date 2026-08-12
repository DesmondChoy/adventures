# Architecture Cleanup Items

**Review date:** 2025-12-29

**Implementation verified:** 2026-08-12

**Status:** IMPLEMENTED

All five items identified during the architecture review are resolved.

| Item | Implemented resolution |
| --- | --- |
| Unused `state_manager` parameter | `handle_reveal_summary()` uses it to append the generated summary chapter through `AdventureStateManager`. |
| Dead `diagnose_character_visuals()` function | Character-visual generation and repair flows call the function. |
| Unclear deferred task execution | Runtime collections have explicit names, and deferred factories run after chapter streaming. |
| Insecure guest UUID fallback | UUIDs use `crypto.randomUUID()` or a `crypto.getRandomValues()` UUID v4 fallback. |
| Silent persistence failures | State saves retry with exponential backoff and notify the client after terminal failure. |

## 1. Summary state management

### Original finding

`handle_reveal_summary()` accepted `state_manager` without using it, leaving
unclear whether the summary chapter should be appended directly to state or
through the state manager.

### Implemented resolution

The function now calls `state_manager.append_new_chapter(summary_chapter)`.
This preserves `AdventureStateManager` as the mutation boundary while keeping
`AdventureState` as the source of truth.

## 2. Character-visual diagnostics

### Original finding

`diagnose_character_visuals()` appeared to be dead diagnostic code.

### Implemented resolution

The function is part of active character-visual handling. It is called by the
choice-processing flow when character visuals need extraction and by the image
generation flow when existing visuals need repair.

## 3. Deferred background work

### Original finding

The distinction between deferred task factories and running tasks was unclear,
and the review could not confirm that factories executed.

### Implemented resolution

The runtime-only state fields are named for their roles:

- `deferred_task_factories` stores callables that create background tasks.
- `pending_background_tasks` stores running tasks that must be awaited.

`execute_deferred_task_factories()` runs the factories after chapter content
finishes streaming, adds returned tasks to the pending collection, and clears
the deferred collection. Summary reveal waits for pending background work
before building the final summary.

## 4. Secure guest UUID generation

### Original finding

The browser fallback generated guest UUIDs with `Math.random()`.

### Implemented resolution

`AdventureStateManager` now prefers `crypto.randomUUID()`. Older supported
browsers use 16 bytes from `crypto.getRandomValues()`, with the UUID version
and variant bits set correctly. If the Web Crypto API is unavailable, the
client fails explicitly instead of generating a predictable identifier.

## 5. Visible and retryable persistence failures

### Original finding

WebSocket state-save failures were logged without retrying or telling the
client, so users could believe unsaved progress was durable.

### Implemented resolution

WebSocket persistence now goes through `store_state_with_retry()`:

- Saves receive three attempts with exponential backoff.
- New adventures use one preallocated ID and an upsert, making creation retries
  idempotent.
- Terminal failures emit a `save_failed` event when the socket remains usable.
- The frontend hides active loaders and displays the failure message.
- A failed final summary save can retry the existing in-memory summary without
  creating a duplicate chapter.

## Regression coverage

- `tests/test_adventure_state_manager_js.py` verifies the secure UUID fallback
  and guards against reintroducing `Math.random()`.
- `tests/test_websocket_persistence.py` covers transient success, stable IDs,
  idempotent upserts, terminal notification, and closed sockets.
- `tests/test_websocket_flow.py` verifies idempotent retry of an existing
  summary chapter.
