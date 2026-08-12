# AGENTS.md

## Start Here

- Read `README.md` for current architecture, setup, repository layout, and commands.
- Read `docs/security/deployment-model.md` before making deployment or secret-exposure claims.
- This repository uses Beads for durable task tracking. Run `bd prime` when Beads context is missing or stale; do not create markdown task lists.

## Git and Scope

- Do not use Git worktrees. Work in the main working directory and stay on the current branch unless the user explicitly asks for another branch.
- Do not commit, push, deploy, or sync Beads unless the user explicitly requests it.
- Preserve existing user changes and keep edits scoped to the request.

## Working Agreements

- Inspect existing definitions and nearby call sites before changing or using repository symbols.
- Match the conventions of the module being edited; avoid unrelated refactors and new dependencies.
- Use `.venv/bin/python` for Python commands, or activate `.venv` first.
- Run the smallest relevant validation first, then broader checks in proportion to the change.

## Project Invariants

- `AdventureState` is the source of truth for adventure flow and persistence.
- Chapter sequencing policy belongs in `ChapterManager`; consumers must derive behavior from `state.story_length`, `planned_chapter_types`, and `ChapterType`.
- Store chapter types as lowercase enum values at persistence boundaries.
- Store agency under `state.metadata["agency"]`; preserve its continuity and track references through `AdventureStateManager.update_agency_references()`.
- Do not repeat lesson questions within an adventure.
- Narrative prose, characters, and plot details are AI-generated. Application logic and tests must assert structure and state transitions, not exact prose.
- Persistent fields must round-trip through serialization and reconstruction; runtime-only tasks, callables, and locks remain excluded.
- In the WebSocket flow, send `chapter_update` before chapter content and stream story chapters only after validating that they contain exactly three choices.
- Preserve user isolation: authenticated adventure access is owned by `user_id`; do not fall back to `client_uuid` for authenticated users.

## Frontend and Deployment

- When changing served JavaScript or CSS, update the relevant `?v=` cache-busting references in templates and module imports.
- Production deploys only through GitHub to Railway auto-deploy. Never use `railway up` for production.
- Keep `.env` and `.env.*` untracked and excluded from Docker build context.

## Validation

- Python tests: `.venv/bin/python -m pytest -q`
- Deployment guardrails: `bash tools/check_deployment_security.sh`
- Carousel visual changes: `npm run test:visual:carousel`
