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
- Supabase clients use `SUPABASE_URL` for the project URL,
  `SUPABASE_ANON_KEY` for the publishable API key used by browsers and Auth
  verification, and `SUPABASE_SERVICE_KEY` for the server-only secret API key.
  The existing variable names also accept legacy API keys during migration.
- HTTP and WebSocket authentication share `app/auth/supabase_auth.py`. It sends
  the user's token to the configured project's `/auth/v1/user` endpoint with a
  five-second HTTPX timeout and redirects disabled. Only Auth's returned user
  UUID supplies the application's authenticated identity. Token claims do not
  select the verification endpoint or supply that identity.
- The app does not read `SUPABASE_JWT_SECRET` or verify tokens against a local
  shared signing secret. Rejected tokens return HTTP 401 or WebSocket close
  code 1008. Verification failures return HTTP 503 or WebSocket close code
  1013. A missing token remains allowed only on paths that permit guests.
- `SECRET_KEY` signs the separate `story_app_session` cookie. Rotating it
  invalidates those cookies; it does not revoke Supabase Auth tokens.
- The optional feedback notification function in
  `supabase/functions/feedback-notify/` uses Supabase Edge Function secrets,
  including `RESEND_API_KEY` and `FEEDBACK_NOTIFICATION_EMAIL`.

The presence of these runtime secrets does not change the deployment-source
rules below. Severity depends on exposure, not on the fact that a local `.env`
exists.

## Supabase Credential and Signing Key Migration

Preserve service continuity by releasing compatible code before changing key
formats. The older Python SDK rejects publishable and secret API keys.

1. Confirm the Supabase project matches the production `SUPABASE_URL`. Create
   publishable and secret API keys alongside the legacy keys. Prepare an
   asymmetric signing key without rotating to it yet.
2. Deploy the updated SDK and shared Auth verifier through GitHub and Railway,
   retaining the current API key values for this first release.
3. Replace `SUPABASE_ANON_KEY` with the publishable key and
   `SUPABASE_SERVICE_KEY` with the secret key in Railway, then redeploy. Keep
   the secret key out of templates and browser configuration.
4. Verify Google login, anonymous login, HTTP ownership checks, and WebSocket
   resume and save behavior with the new API keys. Migrate other project
   consumers, including any enabled Edge Functions or webhooks, before
   disabling their legacy keys.
5. Rotate to the asymmetric signing key and verify newly issued tokens in
   both HTTP and WebSocket flows. Disable legacy `anon` and `service_role`
   API keys, then revoke the previous signing key. Creating new API keys
   alone does not revoke the old keys. Follow the
   [Supabase signing key guide](https://supabase.com/docs/guides/auth/signing-keys)
   for propagation and token-expiry considerations.
6. Remove `SUPABASE_JWT_SECRET` from runtime configuration and restart all app
   instances after revocation. WebSockets verify authentication at the
   handshake; restarting closes connections that retained an earlier identity.

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
