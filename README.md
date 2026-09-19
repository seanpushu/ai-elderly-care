# PausePal — AI for Elderly Care

PausePal helps older adults pause, understand warning signs, and verify urgent requests through people they already trust.

## Starter status

This is a runnable hackathon starter. Analysis currently uses **explicitly labeled demo rules**, not a live AI model. Do not present demo outputs as verified scam detection. The backend teammate will add the real model integration.

## Run

Use Python 3.11 or later:

```sh
python -m pip install -r requirements.txt
python start.py
```

Open port 8000. Replit Run and Autoscale publishing settings are in `.replit`. Health check: `/health`. API: `POST /api/analyze` with JSON `{"text":"Your message"}`. The trusted-contact page is `/static/verify.html`.

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
