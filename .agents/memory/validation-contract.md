---
name: Validation contract
description: Rules validate_analysis enforces in app/schemas.py; durable design decisions about what the backend rejects.
---
Rule: every model reply must pass app/schemas.validate_analysis before it is returned.
Failures raise InvalidAnalysis → HTTP 503 reason=invalid_output; no demo fallback.

**What is rejected:**
- Verdict vocabulary anywhere (scam, fraud, phishing, legitimate, genuine, authentic, fake, impostor, cloned, AI-generated, …) — not hedgeable.
- Probabilistic/soft claims (likely, probably, looks/seems like, 85 %, percent, …) — not hedgeable.
- Authenticity/truth/"money is safe" verdicts unless the same sentence contains a hedge word (mean, whether, know, tell, verify, …).
- Non-English generated text: latin-script ratio < 0.9, or < 2 English function words among ≥ 8 total words, or < 1 among 3–7, or < 3 words at all.
- Signal quote that is not a verbatim substring of the submitted text.
- insufficient_information with any signals; warning with no signals.
- Next steps that contain a literal phone number, URL, or e-mail address.
- Next steps that tell the user to reply, text back, click, tap, scan, download, log in, or read out a code.
- Next steps that refer to a channel attributed to the message (the number in the message, the link they sent, call them back, …) — even as a warning.
- Next steps that mention a channel noun (number, link, …) without also mentioning an independent source (already saved, on the back of your card, official, in person, …).

**What is allowed:**
- Hedged disclaimers: "PausePal cannot tell whether the caller is really your grandson" — hedge word (tell, whether) present before the verdict phrase.
- Independent verification steps: pause, call on a number already saved, use number on back of card, visit branch in person, ask a trusted person, "do not reply until you have spoken to someone you trust".

**Why:** The app's audience is older adults; any wording that endorses an attacker-supplied channel or makes a definitive scam verdict is a direct harm risk. The hedge allowance lets the model write natural disclaimers ("does not mean it is safe") without triggering false positives.

**How to apply:** Change _check_generated_text or _check_next_step in app/schemas.py when adding or relaxing a rule. Add a test for every new case in test_next_steps_may_not_endorse_message_supplied_contacts and test_independent_verification_steps_are_accepted.
