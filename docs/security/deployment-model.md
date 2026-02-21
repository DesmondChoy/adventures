# Deployment Security Model

## Production Deployment Path

This project deploys to production using:

- GitHub repository source
- Railway auto-deploy ("via GitHub" in Railway deployment history)

Local CLI deployment (`railway up`) is not part of the production release process.

## Local `.env` Policy

- Local `.env` is for developer machines only.
- `.env` and `.env.*` must remain gitignored.
- `.env` and `.env.*` must be excluded from Docker build context via `.dockerignore`.
- `.env.example` may be committed as a template.

## Severity Rules for Secret Exposure Findings

Do not automatically classify a local `.env` presence as production exposure.

Classify as `high`/`critical` only if at least one is true:

1. Secret is committed in git history.
2. Deployment source included local filesystem context.
3. Secret appears in shared logs/artifacts/container images/backups.

If none of the above are true, classify as lower severity and include assumptions.

## Verification Checklist

Use this checklist before final severity assignment:

1. Confirm deployment source in Railway Deployments is `via GitHub`.
2. Run `git ls-files .env` and verify no output.
3. Verify `.dockerignore` contains:
   - `.env`
   - `.env.*`
4. Verify no known secret appears in git history or shared logs.

## Change Control

If deployment strategy changes (for example, local CLI deploys or different CI pipeline),
this policy must be updated in the same PR and reviewers should re-evaluate severity rules.
