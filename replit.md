# PausePal shared starter

Use FastAPI and plain HTML/CSS/JavaScript. Start with `python start.py` after installing `requirements.txt`. Keep the English product and the existing API contract. Analysis is live through the OpenAI Chat Completions API (`openai` package, default model `gpt-4o-mini`); credentials come from `AI_INTEGRATIONS_OPENAI_*` or `OPENAI_API_KEY` secrets. There is no demo fallback: any model/config failure is an English HTTP 503. Every model reply is validated in `app/schemas.py` (exact quotes, English, no probabilities/authenticity/safety claims, no contact details in next steps).

Before changes, check the current branch and git status. Preserve existing work. Never reset or force-push. Respect the file ownership described below.

## File ownership

- `frontend` branch → `static/index.html`, `static/analyze.js`, `static/analyze.css`
- `backend-ai` branch → `app/`, `requirements.txt`, tests, startup and deployment config
- `integration` branch → `static/verify.html`, `static/verify.js`, `static/verify.css`, release coordination
- `main` → published, integrated version only

## Running locally

```
pip install -r requirements.txt
PORT=5000 python start.py
```

App serves on port 5000. Homepage at `/`, verify page at `/static/verify.html`, health at `/health`.

## Deployment

- Target: Replit autoscale (Cloud Run)
- Build: `python -m venv .venv && .venv/bin/pip install -r requirements.txt`
- Run: `.venv/bin/python start.py`
- Public URL (when published): https://ai-elderly-care.replit.app
- Secrets required for live AI: `OPENAI_API_KEY` (own key) or `AI_INTEGRATIONS_OPENAI_API_KEY` + `AI_INTEGRATIONS_OPENAI_BASE_URL` (Replit AI Integrations); optional `PAUSEPAL_MODEL`, `PAUSEPAL_MODEL_TIMEOUT_SECONDS`. See README "AI backend configuration".

## API contract

`POST /api/analyze` — accepts `{"text": "..."}` (1–4000 chars), returns assessment (`warning` / `no_clear_signals` / `insufficient_information`), signals with original-text quotes, next steps, and `mode: "live"`. 503 (`{detail, reason}`) if the model is unconfigured, times out, errors, or returns output that fails validation; there is no demo mode.

## Rules

No database, account system, automatic messaging, or real-time call interception. No safety guarantees or invented test results. Source quotes are exact substrings; all generated explanations remain English. Contacts managed only in sessionStorage on the verify page — never sent to the API.
