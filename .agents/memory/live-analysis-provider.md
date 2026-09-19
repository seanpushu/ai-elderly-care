---
name: Live analysis provider decision
description: Which AI provider/credentials PausePal's backend uses and why; what was checked before choosing.
---
Rule: the analysis backend targets the OpenAI Chat Completions contract via the official `openai` package and reads
credentials from `AI_INTEGRATIONS_OPENAI_*` (Replit AI Integrations) first, then `OPENAI_API_KEY`. No other provider.

**Why:** On 2026-09-19 the workspace integration catalog had no OpenAI/Anthropic/Gemini connector (only xAI/MiniMax/
Replicate as unconfigured catalog entries) and no `AI_INTEGRATIONS_*` env vars were injected, so the contract was
confirmed from OpenAI's public API docs instead. The openai package on PyPI here is 3.x (depends on `httpx2`), but the
`AsyncOpenAI(..., max_retries=0, timeout=...)` + `chat.completions.create(response_format=json_schema)` surface is unchanged.

**How to apply:** don't add a second provider or a demo fallback; if credentials are absent the API must 503.
The dev `.venv` inherits `.pythonlibs` via sitecustomize, so `pip install` into it reports "already satisfied" —
verify deploy installs through `requirements.txt`, not by inspecting `.venv`.
