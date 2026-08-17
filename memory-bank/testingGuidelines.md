# Testing Guidelines for Learning Odyssey

## Core Rules

- Use `.venv/bin/python -m pytest`, not direct execution of `tests/test_*.py`.
- Assert structure, state transitions, ownership, and message order. Narrative
  prose, character details, and plots are model-generated and must not be
  hardcoded in application tests.
- `AdventureState` is authoritative. Chapter-flow assertions must use
  `state.story_length`, `planned_chapter_types`, and `ChapterType`.
- Start with the smallest relevant test, then widen validation in proportion to
  the change.

## Python Tests

Run the full suite:

```bash
.venv/bin/python -m pytest -q
```

Useful focused groups:

| Area | Command |
| --- | --- |
| LLM routing and structured chapter output | `.venv/bin/python -m pytest tests/test_llm_factory.py tests/test_llm_providers.py tests/test_chapter_output.py -q` |
| State reconstruction and persistence | `.venv/bin/python -m pytest tests/test_state_management_regressions.py tests/test_state_storage_reconstruction.py tests/test_websocket_persistence.py -q` |
| WebSocket flow and message ordering | `.venv/bin/python -m pytest tests/test_websocket_flow.py tests/test_stream_handler_previous_lessons.py -q` |
| Memory Lane summary | `.venv/bin/python -m pytest tests/test_summary_button_flow.py tests/test_summary_service.py tests/test_summary_questions.py tests/test_summary_generator_backfill.py -q` |
| Data loaders and chapter sequencing | `.venv/bin/python -m pytest tests/data tests/simulations/test_chapter_sequence_validation.py tests/simulations/test_chapter_type_assignment.py -q` |
| LLM logging privacy | `.venv/bin/python -m pytest tests/test_logging_config.py -q` |

### Chapter sequence contract

Every adventure has 10 planned chapters:

- Chapter 1 is STORY.
- Chapter 9 is STORY.
- Chapter 10 is CONCLUSION.
- Exactly three chapters are LESSON.
- Exactly one REFLECT follows a LESSON and is followed by STORY.
- LESSON chapters are never consecutive.
- At least three lesson questions must be available.

The SUMMARY chapter is created only after the conclusion and is not part of
`planned_chapter_types`.

### Structured chapter contract

- STORY and REFLECT output contains narrative plus exactly three distinct,
  complete choices.
- LESSON choices come from the sampled lesson question.
- CONCLUSION output contains narrative and no choices.
- Reject choice labels, numbering, bracketed placeholders, legacy `<CHOICES>`
  markup, duplicate choices, and choices embedded in narrative prose.
- `chapter_update` must precede chapter content on the WebSocket.

## Browser Regression

Install Node dependencies once with `npm install`, then use:

| Scope | Command |
| --- | --- |
| All local Playwright tests | `npm run test:browser` |
| Deterministic Chromium CI suite | `npm run test:browser:ci` |
| Carousel visual regression | `npm run test:visual:carousel` |
| Refresh carousel snapshots | `npm run test:visual:carousel:update` |

The deterministic suite covers the selection flow, ten mocked chapters,
Memory Lane handoff, transition clearing, sticky reader progress, context
ticker behavior, and focused carousel regressions. Pull requests run Chromium;
scheduled and manual workflows add WebKit/mobile and macOS visual snapshots.

## Live Release Journey

Use `.agents/skills/playwright-test/SKILL.md` for release validation:

1. Run the deterministic preflight.
2. Complete a real model-driven 10-chapter journey in Codex Browser.
3. Open Memory Lane and capture its `state_id`.
4. Run the read-only persistence and telemetry audit:

   ```bash
   .venv/bin/python tools/audit_e2e_supabase.py --state-id <uuid>
   ```

Do not call a release journey complete from Playwright alone; the live path must
also prove model generation, final persistence, summary retrieval, and expected
telemetry.

## Simulations and Summary Preview

| Task | Command |
| --- | --- |
| Automated simulation with server management | `.venv/bin/python tests/simulations/run_test_analysis.py --runs 3` |
| Analyze the newest simulation log | `.venv/bin/python tests/simulations/run_test_analysis.py --analyze-only` |
| Raw WebSocket simulations against a running server | `.venv/bin/python tests/simulations/adventure_test_runner.py --runs 5 --host localhost --port 8000` |
| Generate a reusable full-adventure state | `.venv/bin/python tests/simulations/generate_all_chapters.py --category enchanted_forest_tales --topic "Singapore History"` |
| Generate summaries from the latest saved state | `.venv/bin/python tests/simulations/generate_chapter_summaries.py --compact` |
| Preview Memory Lane from saved state | `.venv/bin/python tests/summary_chapter_preview.py --state-file <simulation-state.json> --port 8001` |

Detailed simulation options live in `tests/simulations/README.md`.

## Security and Persistence Checks

- Authenticated adventure lookup and resume must use `user_id`; never fall back
  to `client_uuid` for an authenticated user.
- Guest access may use `client_uuid` only when no authenticated `user_id` is
  present.
- Persistence tests must cover bounded retries, one stable ID for creation
  retries, ownership-aware updates, and the terminal `save_failed` event.
- Runtime tasks, task factories, callables, and locks must remain excluded from
  serialized state; durable fields such as `protagonist_name`, agency metadata,
  chapter types, and character visuals must round-trip.
- Run deployment guardrails when deployment, secrets, Docker inputs, or CI
  configuration changes:

  ```bash
  bash tools/check_deployment_security.sh
  ```

## Debugging Checklist

### WebSocket flow

1. Verify `/ws/story/{story_category}/{lesson_topic}` and its query parameters.
2. Confirm `chapter_update` arrives before chapter text.
3. Confirm story/reflect choices appear only after all three pass validation.
4. Inspect reconnection and ownership logs before changing state recovery.
5. Distinguish harmless post-close disconnect noise from a user-visible error.

### LLM calls

1. Confirm the use case maps to the expected provider in
   `LLMServiceFactory.USE_CASE_CONFIG_MAP`.
2. Correlate request, response, cancellation, or failure records with
   `llm_call_id`.
3. In production, verify prompt and response bodies are absent while bounded
   metadata remains.
4. Treat authentication and permission failures as non-retryable for story
   generation.

### Image generation

1. Verify `GOOGLE_API_KEY` and the Gemini 3.1 Flash Image request settings.
2. Trace image-scene text, Flash Lite prompt synthesis, and final image request
   as separate calls.
3. Confirm the five-retry exponential-backoff path and no-image handling.
4. Check protagonist, agency, sensory, and evolved character visual inputs.

### Subprocesses

Use `sys.executable` in Python subprocess commands so child processes use the
same virtual environment as the test runner.
