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
- Complete authorized work through implementation and verification. Infer routine details from context; ask for input when an unresolved decision materially affects scope, correctness, or an external commitment. Continue independent work while awaiting that input, and carry forward authorization already given.
- Within the requested scope, choose implementation and debugging methods autonomously. Treat established patterns as defaults. When a better design requires changing a project contract, explain the tradeoff and update the implementation, tests, and documentation together.
- Match the conventions of the module being edited and avoid unrelated refactors. Prefer existing dependencies; add a dependency within scope when its benefit justifies the maintenance cost, and explain that tradeoff.
- Use `.venv/bin/python` for Python commands, or activate `.venv` first.
- Run the smallest relevant validation first, then broader checks in proportion to the change. Once relevant checks pass, repeat or broaden them only for new changes, failures, or unresolved risks.

## Skills and Collaboration

- Explicit user instructions take precedence over skill guidelines. A skill does not expand the authorized scope.
- If a skill causes a pause, approval request, or departure from the user's intent, link its exact `SKILL.md`, quote the instruction, and explain whether it is a requirement or your interpretation. First complete independent work already authorized.
- Delegate independent, bounded work to available subagents when it saves time or improves review quality. Assign non-overlapping edits in the shared checkout, retain ownership of integration and verification, and handle small or tightly coupled tasks locally.

## Project Invariants & Enforcement Table

Every invariant below is paired with its structural enforcement. When a rule is violated twice, raise it to architecture, types, lint, or a formal model instead of adding prose.

| Invariant | Enforced By |
| --- | --- |
| `AdventureState` is the single source of truth; client payloads never overwrite server state. | Formal model `formal/AdventureLifecycle.tla` (`ServerStateAuthoritative`, replay `Bug3dfb9bdStaleClientOverwrite.cfg`), `app/routers/websocket_router.py`, `tests/test_websocket_flow.py`. |
| Initial save failures reset in-memory state so retries persist; initial retries never create duplicate DB rows. | Formal model `formal/AdventureLifecycle.tla` (`NoUnsavedChapterProgress`, `SingleRecordPerAdventure`), `app/services/websocket/persistence.py`, `tests/test_repo_invariants.py`, `tests/test_websocket_persistence.py`. |
| `reveal_summary` and `send_story_complete` require `CONCLUSION` as the final chapter; `summary_ready` waits for confirmed `is_complete=True` persistence. | Formal model `formal/AdventureLifecycle.tla` (`SummaryOnlyAfterConclusion`), runtime check in `app/services/websocket/core.py`, `tests/test_websocket_flow.py`. |
| Background chapter-summary writes serialize under `state.summary_lock` and failed tasks never clobber valid summaries. | AST lint `[summary-list-lock-discipline]` in `tools/check_repo_invariants.py`, formal model `formal/AdventureLifecycle.tla` (`ValidSummaryNeverClobbered`), `_store_summary_safe`. |
| Chapter sequencing policy belongs in `ChapterManager`; `AdventureState` enforces `len(chapters) <= story_length + 1` (with `+1` only for `SUMMARY`). | Pydantic `@model_validator` in `app/models/story.py`, `tests/data/test_chapter_manager.py`, `tests/test_repo_invariants.py`. |
| Store chapter types as lowercase enum values at persistence boundaries and round-trip every persistent `AdventureState` field while excluding runtime tasks, callables, and locks. | `ChapterType` enum + `PrivateAttr` locks + `exclude=True` in `app/models/story.py`, automated field-coverage test in `tests/test_repo_invariants.py`. |
| Route all LLM calls through `LLMServiceFactory.create_for_use_case(...)` with typed `LLMUseCase`; never instantiate external clients at module import time. | `LLMUseCase` Literal in `app/services/llm/factory.py`, removed legacy exports in `app/services/llm/__init__.py`, AST lints `[llm-provider-bypass]` and `[eager-external-client-import]` in `tools/check_repo_invariants.py`, clean-env import test `tests/test_service_imports.py`. |
| Guard optional single-row Supabase lookups against `None` responses from `.maybe_single().execute()`. | AST lint `[supabase-maybe-single-null-guard]` in `tools/check_repo_invariants.py`, `tests/test_supabase_credentials.py`. |
| Static assets and ES modules use content-hashed URLs and one import map so browsers never load duplicate module instances. | `app/utils/static_assets.py`, `<script type="importmap">` in `app/templates/base.html`, lints `[js-manual-version-query]`, `[template-manual-version-query]`, `[static-asset-exists]` in `tools/check_repo_invariants.py`, Playwright check in `tests/playwright/adventure-flow.spec.ts`. |
| In the WebSocket flow, send `chapter_update` before chapter prose and stream story chapters only after validating three choices. | Pydantic `StoryChapterOutput` + `ChapterData` validator, behavioral protocol test `tests/test_stream_handler_previous_lessons.py`. |
| Preserve user isolation: authenticated adventure access is owned by `user_id`; never fall back to `client_uuid` for authenticated users. | `app/auth/supabase_auth.py`, `app/routers/websocket_router.py`, `app/routers/summary_router.py`, `tests/test_supabase_auth.py`, `tests/test_websocket_flow.py`, `tests/test_conclusion_chapter_fix.py`. |
| Keep `.env` and `.env.*` untracked and excluded from Docker build context. | `tools/check_deployment_security.sh` (CI workflow `.github/workflows/deployment-security-guardrails.yml`). |
| Store agency under `state.metadata["agency"]`, do not repeat lesson questions, and assert structure/state rather than exact AI prose. | `tests/test_state_management_regressions.py`, `tests/data/test_lesson_loader.py` (judgment call for prompt/prose assertions). |

## Deployment

- Production deploys only through GitHub to Railway auto-deploy. Never use `railway up` for production.

## Validation

- Repo invariants: `.venv/bin/python tools/check_repo_invariants.py`
- Formal model (TLA+ / TLC): `bash tools/run_formal_verification.sh`
- Python tests: `.venv/bin/python -m pytest -q`
- Deployment guardrails: `bash tools/check_deployment_security.sh`
- Deterministic browser tests: `npm run test:browser:ci`
- Carousel visual changes: `npm run test:visual:carousel`
