---
name: quality
description: Review scoped changes for correctness and regressions before committing or when a quality review is requested. Fix findings within authorized implementation scope; keep read-only reviews read-only.
---

# Quality

Review the intended changes before committing and when a quality review is
requested. Use the tools available in the current environment.

## Establish Scope and Context

Inspect `git status --short` and the diff for the requested changes. Include
relevant staged, unstaged, and untracked files; preserve unrelated user work.

Start with the scoped diff, affected definitions, callers, and tests. Expand to
complete files or other modules when needed to understand behavior and risk.
For documentation and skill changes, check instruction consistency, references,
and examples against the maintained implementation.

## Assess the Change

- Check intended behavior, edge cases, error handling, and regressions.
- Trace changed types, signatures, API contracts, state transitions, and
  persistence through affected consumers.
- Apply the project invariants in `AGENTS.md` where relevant.
- Identify dead code and accidental debugging residue introduced by the change.
  Preserve intentional diagnostics; assess logging content, purpose, and
  exposure instead of treating debug-level logging as a defect.

## Act Within the Request

Fix findings within authorized implementation scope, including necessary
supporting changes. Report unrelated findings without expanding the task.
For read-only reviews, report findings without changing files or tracker state.

Choose routine implementation details autonomously. Explain tradeoffs when a
finding requires a change to requirements or a project contract; seek user input
only when a material decision cannot be resolved from the existing request.

After fixes, run the smallest relevant validation and broaden it in proportion
to the change. Use existing tests where they provide meaningful evidence;
report checks that could not run.

## Report

Summarize the scope reviewed, issues fixed or actionable findings with file
locations, validation results, and any remaining uncertainty. If no actionable
findings remain, say so without implying that unperformed checks passed.
