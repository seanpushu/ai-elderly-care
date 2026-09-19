"""One real round-trip against the configured provider.

Skipped automatically when no credentials are present, so the normal suite
stays offline. Run it deliberately after setting GROQ_API_KEY:

    python -m unittest tests.test_live_provider -v
"""

from __future__ import annotations

import unittest

from app.analyzer import is_configured
from tests.test_api import URGENT_TEXT, asgi_request


@unittest.skipUnless(is_configured(), "no Groq credentials configured")
class LiveProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_provider_round_trip(self) -> None:
        status, body, _ = await asgi_request("POST", "/api/analyze", {"text": URGENT_TEXT})
        self.assertEqual(status, 200, body)
        self.assertEqual(body["mode"], "live")
        self.assertIn(body["assessment"], ("warning", "no_clear_signals", "insufficient_information"))
        for signal in body["signals"]:
            self.assertIn(signal["quote"], URGENT_TEXT)

    async def test_real_provider_handles_routine_message(self) -> None:
        text = "Hi Mum, lunch still on for Sunday at ours? Tom is bringing the kids. Love, Sarah"
        status, body, _ = await asgi_request("POST", "/api/analyze", {"text": text})
        self.assertEqual(status, 200, body)
        self.assertEqual(body["mode"], "live")
        for signal in body["signals"]:
            self.assertIn(signal["quote"], text)


if __name__ == "__main__":
    unittest.main()
