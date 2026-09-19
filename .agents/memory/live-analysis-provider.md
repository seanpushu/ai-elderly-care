---
name: Live analysis provider decision
description: Which AI provider/credentials PausePal's backend uses and why.
---
Rule: the analysis backend uses Groq through the official `groq` Python package. Live credentials come only from
`GROQ_API_KEY`; the default model is `openai/gpt-oss-20b`, optionally overridden with `GROQ_MODEL`.

The backend performs one Chat Completions request with structured JSON output, `max_retries=0`, and a bounded timeout.
It validates the returned object before exposing `mode: "live"`. If credentials are absent, the provider fails, or
the result violates the PausePal contract, the API returns HTTP 503 and never falls back to demo output.

Never commit a Groq key. Configure the key separately in Replit workspace/deployment Secrets.
