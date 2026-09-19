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

Confirmed provider: **Groq Chat Completions API** through the official `groq` Python package. Default model `openai/gpt-oss-20b`; one request per analysis, `max_retries=0`, 25-second timeout, and strict JSON-schema output.

Credentials are read from the environment (set them as Replit Secrets; never commit values):

| Variable | Purpose |
| --- | --- |
| `GROQ_API_KEY` | Required Groq API credential for live analysis. |
| `GROQ_MODEL` (optional) | Override the Groq model; defaults to `openai/gpt-oss-20b`. |
| `PAUSEPAL_MODEL_TIMEOUT_SECONDS` (optional) | Provider timeout, 1–60 seconds. |

`GET /health` reports `analysis_available: false` when `GROQ_API_KEY` is absent. Development and production credentials are configured separately in Replit; the published app needs its own secret value.

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

The server validates every model reply before returning it (`app/schemas.py`):
- Assessment enum, field types, and lengths.
- Every `signals[].quote` is an exact verbatim substring of the submitted text.
- `insufficient_information` → no signals; `warning` → at least one signal.
- All generated text must be in English (≥ 90 % Latin script, minimum English function words).
- Verdict vocabulary is banned entirely: scam, fraud, phishing, legitimate, genuine, authentic, fake, impostor, cloned, AI-generated, and equivalents.
- Probabilistic or soft estimates are banned: likely, probably, looks like, 85 %, percent, odds, and equivalents.
- Authenticity/truth/"money is safe" verdicts are banned unless the same sentence first hedges with a word like *cannot tell*, *whether*, *verify*, etc.
- `next_steps` may not contain phone numbers, URLs, or e-mail addresses; may not tell the user to reply, click, tap, scan, download, log in, or share a code; may not refer to any contact channel supplied by the message (even as a warning — move those observations to a signal reason instead); and may only name a channel noun (number, link, …) when also naming an independent source (already saved, on the back of your card, official, in person, …).

Anything that fails is a 503 (`reason: invalid_output`). Logs record the failure reason and text length only — never the message or any key.

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
