# PausePal — AI for Elderly Care

PausePal helps older adults pause, understand warning signs, and verify urgent requests through people they already trust.

## Status

Analysis is **live**: every `POST /api/analyze` makes one real model call. There is no demo or rule-based fallback. If the model is not configured, times out, or returns something that fails validation, the API answers HTTP 503 with a short English message instead of a made-up result. Do not present any output as verified scam detection; PausePal describes pressure patterns and suggests independent verification.

## Run

Use Python 3.11 or later:

```sh
python -m pip install -r requirements.txt
python start.py
```

The server binds `0.0.0.0` on `$PORT` (default 8000). Replit Run and Autoscale publishing settings are in `.replit`. Health check: `/health`. API: `POST /api/analyze` with JSON `{"text":"Your message"}`. The trusted-contact page is `/static/verify.html`.

## AI backend configuration

Confirmed provider: **OpenAI Chat Completions API** (`POST {base_url}/chat/completions`, Bearer-token auth, `json_schema` structured output) through the official `openai` Python package. Default model `gpt-4o-mini`; one request per analysis, `max_retries=0`, 25-second timeout.

Credentials are read from the environment (set them as Replit Secrets; never commit values). Either set works:

| Variable | Purpose |
| --- | --- |
| `AI_INTEGRATIONS_OPENAI_API_KEY` + `AI_INTEGRATIONS_OPENAI_BASE_URL` | Replit AI Integrations (Replit-managed OpenAI billing). Checked first. |
| `OPENAI_API_KEY` (+ optional `OPENAI_BASE_URL`) | Your own OpenAI key. |
| `PAUSEPAL_MODEL` (optional) | Override the model name. |
| `PAUSEPAL_MODEL_TIMEOUT_SECONDS` (optional) | Provider timeout, 1–60 seconds. |

`GET /health` reports `analysis_available: false` when neither credential set is present. Development and production credentials are configured separately in Replit; the published app needs its own secret values.

### Response contract

```json
{
  "assessment": "warning | no_clear_signals | insufficient_information",
  "summary": "English text",
  "signals": [{"quote": "exact substring of the submitted text", "reason": "English text"}],
  "next_steps": ["English text"],
  "mode": "live"
}
```

The server validates every model reply before returning it: assessment enum, field types and lengths, English text, every `quote` an exact substring of the submitted message, no signals for `insufficient_information`, at least one signal for `warning`, no percentages/probabilities, no authenticity, truth, or "your money is safe" claims, and no phone numbers, links, or e-mail addresses in `next_steps`. Anything that fails is a 503 (`reason: invalid_output`). Logs record the failure reason and message length only, never the message or any key.

### Tests

```sh
python -m unittest discover -s tests -v
```

`tests/test_api.py` mocks the provider call and covers HTTP-shaped requests, urgent/insufficient/prompt-injection messages, exact-quote preservation, request validation, provider timeout/transport/status failures, malformed model output, and the no-fallback rule. `tests/test_live_provider.py` performs a real round-trip and skips itself when no key is configured.

## Three-person development

- `frontend`: message input and analysis UI; own `static/index.html`, `static/analyze.js`, `static/analyze.css`.
- `backend-ai`: real model integration and API; own `app/`, Python dependencies, backend tests, and startup configuration.
- `integration`: trusted-contact and verification page; own `static/verify.html`, `static/verify.js`, `static/verify.css`; coordinate final deployment.
- `main`: shared, reviewed version for publishing.

Each teammate imports this repository into their own Replit account, fetches the latest code, and switches to their assigned branch before editing. Commit and push only your owned files. Merge changes through reviewed pull requests. Do not force-push or overwrite teammates' changes.

All product UI, AI explanations, errors, examples, and submission materials must be English. Source evidence quotes must remain verbatim. Do not commit secrets or real personal contact information. Contacts are stored only for the current browser session, not sent to the analysis endpoint.

## Hackathon

A three-person team project for the CMU build-with-AI hackathon.

## Our goal

Use AI to make everyday life for elderly people safer, easier, and more connected.

## Deployment and submission

We will collaborate through GitHub, deploy the project to Replit, and submit the Replit project link for the hackathon.

## Collaboration

- `main`: stable, integrated code ready for deployment.
- `frontend`: user interface and accessibility.
- `backend-ai`: backend APIs and AI features.
- `integration`: connect components, test the full project, and prepare Replit deployment.

Open pull requests to merge reviewed changes into `main`.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
