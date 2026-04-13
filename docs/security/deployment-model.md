# Deployment Security Model

## Production Deployment Path

Production deploys follow this path:

- GitHub repository source
- Railway auto-deploy
- `Procfile` boot command:
  `uvicorn app.main:app --host 0.0.0.0 --port $PORT --proxy-headers`

Local CLI deployment such as `railway up` is not part of the production
release process.

## Repository Guardrails

This repository enforces deployment guardrails in two places:

- GitHub Actions workflow:
  `.github/workflows/deployment-security-guardrails.yml`
- Local shell check:
  `bash tools/check_deployment_security.sh`

The guardrail script fails if any of the following are true:

- `.env` is tracked by git
- `.dockerignore` is missing
- `.dockerignore` does not exclude `.env`
- `.dockerignore` does not exclude `.env.*`
- this policy file is missing

These checks run on pull requests and on pushes to `main` and `master`.

## Local `.env` Policy

- Local `.env` is for developer machines only.
- `.env` and `.env.*` must remain gitignored.
- `.env` and `.env.*` must be excluded from Docker build context via
  `.dockerignore`.
- `.env.example` may be committed as a template.

## Runtime Secret Surfaces

This project uses more than one secret-management surface:

- Application runtime secrets are loaded from local `.env` in development and
  from platform-managed environment variables in Railway.
- Supabase-backed services use the configured app secrets
  (`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`,
  `SUPABASE_JWT_SECRET`) at runtime.
- The optional feedback notification function in
  `supabase/functions/feedback-notify/` uses Supabase Edge Function secrets,
  including `RESEND_API_KEY` and `FEEDBACK_NOTIFICATION_EMAIL`.

The presence of these runtime secrets does not change the deployment-source
rules below. Severity depends on exposure, not on the fact that a local `.env`
exists.

## Severity Rules for Secret Exposure Findings

Do not automatically classify a local `.env` presence as production exposure.

Classify as `high` or `critical` only if at least one of the following is true:

1. A secret is committed in git history.
2. The deployment source included local filesystem context.
3. A secret appears in shared logs, artifacts, container images, or backups.

If none of the above are true, classify the finding at a lower severity and
state the assumptions clearly.

## Verification Checklist

Use this checklist before assigning final severity:

1. Confirm the Railway deployment source is `via GitHub`.
2. Run `git ls-files .env` and verify it returns no output.
3. Verify `.dockerignore` contains both:
   - `.env`
   - `.env.*`
4. Verify no known secret appears in git history or shared logs/artifacts.

## Change Control

If the deployment strategy changes, this policy must change in the same pull
request. Examples include:

- introducing local CLI deploys
- switching away from GitHub-sourced Railway deploys
- changing Docker build inputs
- moving sensitive workflows to new runtime environments

Reviewers should re-evaluate severity rules whenever one of those changes
lands.
