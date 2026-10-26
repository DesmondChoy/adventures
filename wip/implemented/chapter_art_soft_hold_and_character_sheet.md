# Chapter art: soft-hold + character sheet (PR #31)

## Status

**IMPLEMENTED** — merged via PR [#31](https://github.com/DesmondChoy/adventures/pull/31) (`feat/chapter-art-sync-and-sheet`).

Measured locally 2026-10-26 (Asia/Singapore) on two full 10-chapter guest runs before merge:
- Soft-hold: ch≥2 image releases in ~10–20ms when Gemini is ready; 0 timeouts on both full runs; timeout path proven once at 3501ms.
- Sheet: locks once after ch1 agency; reused ch2–10 (`skipping synthesis`). Heroes/companions mostly stable; agency props can still drift.

## Problem

1. **Latency / UX:** On the live path after PR #30, answer buttons could appear while `#chapterImage` was still empty (missing illustration — not a framed blank canvas). Kids saw text + choices with a hole where the picture should be.
2. **Consistency:** Chapter Gemini prompts were text-only (synthesis + `AGENCY_` keys). No locked reference JPEG across chapters.

## What changed (two domains)

### A. Client soft-hold + skeleton (ch ≥ 2)

- On `chapter_update` for chapter ≥ 2: show a grey shimmer placeholder (`#chapterImageSkeleton`) in `#chapterImageContainer`.
- Buffer incoming `choices` until an accepted `chapter_image_update` **or** **3500ms** after choices are received (`SOFT_HOLD_TIMEOUT_MS`).
- On timeout: release choices, keep skeleton until the image paints (or next chapter cancels).
- Chapter 1 unchanged (agency choice cards only; no main chapter hero image).
- `makeChoice` / adventure reset cancel the hold.
- Console: `[SOFT_HOLD] armed|choices_buffered|released`.

**Key files:** `app/static/js/uiManager.js`, `app/static/js/main.js`, `app/static/css/components.css`, `app/templates/components/story_container.html`, cache-bust in `base.html` / `scripts.html`.

### B. Server character sheet (multimodal Gemini refs)

- After ch1 agency lock: idempotently build a dedicated protagonist+agency portrait into `AdventureState.metadata["character_sheet"]` (JPEG base64; not object storage).
- For chapter ≥ 2: pass the sheet as a multimodal Gemini reference and **skip `synthesize_image_prompt`** when the sheet exists.
- Fail soft: if sheet generation fails, keep the previous text-only synthesis + `AGENCY_` path.
- Unit tests: `tests/test_character_sheet.py` (7 tests; no live Gemini key required for the suite).

**Key files:** `app/services/character_sheet.py` (new), `app/services/image_generation_service.py`, `app/services/websocket/choice_processor.py`, `app/services/websocket/image_generator.py`.

## Commits on the feature branch

| SHA (abbrev) | Message |
| --- | --- |
| `cd349ea` | `feat(ui): soft-hold choices + chapter image skeleton` |
| `b80719c` | `feat(images): character sheet ref for chapter Gemini` |

Parent of the branch (pre-change `main`): merge of PR #30 (`a974195`).

## How to revert

Prefer git over hand-editing — the two domains are separable.

### Revert both (full PR)

```bash
# After merge, find the merge commit on main, then:
git revert -m 1 <merge_commit_sha>
# Or, if the PR was squash-merged, revert that single squash commit.
```

Also use `git show <merge_commit_sha>` / the PR Files tab as the authoritative diff alongside this note.

### Revert only soft-hold (keep sheet)

```bash
git revert cd349ea
# If that SHA is not on main after squash, revert the soft-hold hunks in:
#   uiManager.js, main.js, components.css, story_container.html, base.html, scripts.html
```

After revert: hard-refresh clients (cache-bust versions in templates).

### Revert only character sheet (keep soft-hold)

```bash
git revert b80719c
# Or delete/stop calling character_sheet.py and restore image_generator /
# image_generation_service / choice_processor to pre-sheet behavior;
# remove tests/test_character_sheet.py.
```

Existing adventures may already have `metadata.character_sheet`; leaving the key in stored state is harmless if the code no longer reads it.

### Feature flags

None. Behavior is always on after deploy. Rollback = code revert + redeploy.

## Known leftovers (not blockers)

- Agency / prop drift can still happen; sheet does not freeze every late NPC.
- Chapter 10 soft-hold may arm twice and release as `image_waiting_choices` (finale often has no choice buttons).
- Resume still does not persist the last painted chapter JPEG (pre-existing).

## Related

- PR #30: live-path race (start image tasks before stream) — keep that; soft-hold sits on top.
- `wip/implemented/image_spillover_race_condition.md` — older spillover / `minExpectedImageChapter` work.
