# AGENTS.md

## One-Word Commands
Quick shortcuts for common tasks:

- `$update`: Update memory-bank to reflect session changes. No opinionated remarks - ask for clarification when unsure.
- `$craft`: Generate high-quality conventional commit messages for this session’s changes (do not commit; user reviews first).
  - Behavior:
    - Inspect staged/unstaged changes and summarize what changed and why.
    - Propose a single commit or multiple commits if the work is logically separable.
  - Output format (no extra prose; emit only commit message text in code fences):
    - Single commit:
      ```
      <type>(<scope>): <summary>
      
      <body>
      
      - <bullet describing change>
      - <bullet describing change>
      
      Affected: <file1>, <file2>, ...
      Test Plan:
      - <how you verified>
      Revert plan:
      - <how to undo safely>
      ```
    - Multiple commits: output multiple blocks separated by a line with three dashes `---`.
  - Allowed types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert.
  - Conventions:
    - Subject ≤ 50 chars, imperative mood; wrap body at ~72 chars.
    - Use BREAKING CHANGE: in body when applicable.
    - Add Refs:/Closes: lines for issues/PRs when available.
  - If context is missing, ask one concise question; otherwise proceed with best assumption and note it in the body.
- `$review`: Use Oracle and remind it of the original objective, then review all changes made using all tools available. Check for opinionated changes, over-engineering, and opportunities for simplification or efficiency improvements. Present findings to user for decision.
- `$parallel-x`: Run x sub-agents in parallel (not sequentially) where x is the number specified.

## Commands
- **Virtual Environment**: ALWAYS activate `.venv` before running Python commands

## Code Style & Patterns
- **Imports**: Use absolute imports (`from app.services.summary import SummaryService`)
- **Type hints**: Required for all functions, use Pydantic models extensively
- **Error handling**: Use custom exceptions (`StateNotFoundError`, `SummaryError`)
- **Async**: Use `async`/`await` for all I/O operations, services are async
- **Naming**: snake_case for functions/variables, PascalCase for classes
- **State management**: `AdventureState` is single source of truth, never hardcode chapter data
- **Logging**: Use structured logging with context (`logger.info("message", extra={"state_id": id})`)
- **Code reuse**: Review existing codebase before creating new functions, prioritize modular design

## Critical Implementation Rules

### State Management
- `AdventureState` MUST be single source of truth
- NEVER hardcode chapter numbers (use `state.story_length` and `planned_chapter_types`)
- Agency choice MUST be stored in `state.metadata["agency"]`
- Always convert chapter types to lowercase when storing/retrieving
- Complete state serialization required with proper type hints
- State changes must be logged with context

### Chapter Requirements
- First chapter MUST be STORY type with agency choice
- Last chapter MUST be CONCLUSION type
- 3 LESSON chapters required (1 in a LESSON-REFLECT-STORY sequence, 2 additional non-consecutive)
- REFLECT chapters MUST only follow LESSON chapters
- No consecutive LESSON chapters allowed
- No question repetition in session

### Agency Implementation
- Agency MUST be referenced in all subsequent chapters
- Agency MUST evolve in REFLECT chapters
- Agency MUST have meaningful resolution in conclusion
- Use `update_agency_references()` for tracking

### Dynamic Content Handling (CRITICAL)
- **NEVER hardcode narrative strings, character names, or plot points** - content is AI-generated
- **Rely on state structure**: Base logic on `AdventureState` fields, `ChapterType`, metadata
- **Abstract testing**: Focus on state transitions, not specific LLM-generated text
- **Use metadata**: Store extracted information in structured fields, avoid parsing free-form text

## Code Implementation Guidelines (CRITICAL)

### NEVER Make Assumptions - Always Verify First
**Before writing ANY code that calls functions, imports, or references existing code:**

1. **ALWAYS use search tools to verify function names and signatures BEFORE using them**
   - Use `Grep` to find exact function definitions: `def function_name`
   - Use `codebase_search_agent` to understand how functions are used elsewhere
   - Use `Read` to examine the actual implementation and parameters

2. **NEVER assume function names, even if they seem logical**
   - Wrong: Assuming `get_previous_lessons()` exists 
   - Right: Search for "previous_lessons" or "lesson" functions first
   - Always verify import paths and module structure

3. **ALWAYS check existing import patterns before adding new imports**
   - Look at other files in the same directory for import examples
   - Verify module structure with `list_directory` if needed
   - Check that the function/class you're importing actually exists

4. **ALWAYS verify parameter types and return values**
   - Read function signatures and docstrings
   - Check how the function is called elsewhere in the codebase
   - Understand the expected data structures

### Implementation Order (MANDATORY)
1. **Search** → Find existing implementations
2. **Read** → Understand the actual code structure  
3. **Verify** → Check function signatures and usage patterns
4. **Implement** → Write code based on verified information
5. **Test** → Run diagnostics to catch errors early

### Red Flags That Require Verification
- Using any function name that "makes sense" but you haven't verified
- Importing from modules without checking they exist
- Assuming parameter types or return values
- Copy-pasting patterns without understanding the context
- Making changes that "should work" without verification

### Common Debugging Patterns
- **Method Missing at Runtime**: Check indentation - methods inside functions won't be accessible on class instances
- **AttributeError on Service Methods**: Verify method is properly indented within the class definition
- **Telemetry/Duration Issues**: Connection restarts cause chapter start times to be lost, resulting in null duration values. Check metadata keys and consider timestamp-based backfilling for historical data
- **Data Flow Tracing**: When debugging UI display issues, trace the complete data flow from storage → calculation → display rather than assuming the problem is at the UI layer

**Remember: Assumptions lead to bugs. Verification prevents them.**

## Security Audit Context

### Production Deployment Model (Railway)
- Production deploy path is **GitHub -> Railway auto-deploy only**.
- Local CLI deploys (for example `railway up`) are **not** part of the production release process.
- Local `.env` is developer-only, must remain gitignored, and must be excluded from Docker build context.

### Severity Rules for Local Secret Findings
- Presence of a local `.env` file alone is **not** automatically a production exposure.
- Escalate to `high`/`critical` only when at least one is true:
  - Secret is committed to git history.
  - Deployment source included local filesystem context.
  - Secret appears in shared logs/artifacts/images/backups.

### Required Verification for Secret-Exposure Claims
- Check deployment source in Railway deploy history (`via GitHub` vs local CLI source).
- Confirm `.env` is not tracked (`git ls-files .env` should be empty).
- Confirm `.dockerignore` excludes `.env` and `.env.*`.
- Refer to `docs/security/deployment-model.md` as the source of truth before assigning severity.

<!-- BEGIN BEADS INTEGRATION v:1 profile:minimal hash:970c3bf2 -->
## Beads Issue Tracker

This project uses **bd (beads)** for issue tracking. Run `bd prime` to see full workflow context and commands.

### Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --claim  # Claim work
bd close <id>         # Complete work
```

### Rules

- Use `bd` for ALL task tracking — do NOT use TodoWrite, TaskCreate, or markdown TODO lists
- Run `bd prime` for detailed command reference and session close protocol
- Use `bd remember` for persistent knowledge — do NOT use MEMORY.md files

**Architecture in one line:** issues live in a local Dolt DB; sync uses `refs/dolt/data` on your git remote; `.beads/issues.jsonl` is a passive export. See https://github.com/gastownhall/beads/blob/main/docs/SYNC_CONCEPTS.md for details and anti-patterns.

## Agent Context Profiles

The managed Beads block is task-tracking guidance, not permission to override repository, user, or orchestrator instructions.

- **Conservative (default)**: Use `bd` for task tracking. Do not run git commits, git pushes, or Dolt remote sync unless explicitly asked. At handoff, report changed files, validation, and suggested next commands.
- **Minimal**: Keep tool instruction files as pointers to `bd prime`; use the same conservative git policy unless active instructions say otherwise.
- **Team-maintainer**: Only when the repository explicitly opts in, agents may close beads, run quality gates, commit, and push as part of session close. A current "do not commit" or "do not push" instruction still wins.

## Session Completion

This protocol applies when ending a Beads implementation workflow. It is subordinate to explicit user, repository, and orchestrator instructions.

1. **File issues for remaining work** - Create beads for anything that needs follow-up
2. **Run quality gates** (if code changed) - Tests, linters, builds
3. **Update issue status** - Close finished work, update in-progress items
4. **Handle git/sync by active profile**:
   ```bash
   # Conservative/minimal/default: report status and proposed commands; wait for approval.
   git status

   # Team-maintainer opt-in only, unless current instructions forbid it:
   git pull --rebase
   bd dolt push
   git push
   git status
   ```
5. **Hand off** - Summarize changes, validation, issue status, and any blocked sync/commit/push step

**Critical rules:**
- Explicit user or orchestrator instructions override this Beads block.
- Do not commit or push without clear authority from the active profile or the current user request.
- If a required sync or push is blocked, stop and report the exact command and error.
<!-- END BEADS INTEGRATION -->

<!-- BEGIN BEADS CODEX SETUP: generated by bd setup codex -->
## Beads Issue Tracker

Use Beads (`bd`) for durable task tracking in repositories that include it. Use the `beads` skill at `.agents/skills/beads/SKILL.md` (project install) or `~/.agents/skills/beads/SKILL.md` (global install) for Beads workflow guidance, then use the `bd` CLI for issue operations.

### Quick Reference

```bash
bd ready                # Find available work
bd show <id>            # View issue details
bd update <id> --claim  # Claim work
bd close <id>           # Complete work
bd prime                # Refresh Beads context
```

### Rules

- Use `bd` for all task tracking; do not create markdown TODO lists.
- Run `bd prime` when Beads context is missing or stale. Codex 0.129.0+ can load Beads context automatically through native hooks; use `/hooks` to inspect or toggle them.
- Keep persistent project memory in Beads via `bd remember`; do not create ad hoc memory files.

**Architecture in one line:** issues live in a local Dolt DB; sync uses `refs/dolt/data` on your git remote; `.beads/issues.jsonl` is a passive export. See https://github.com/gastownhall/beads/blob/main/docs/SYNC_CONCEPTS.md for details and anti-patterns.
<!-- END BEADS CODEX SETUP -->
