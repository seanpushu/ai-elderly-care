"""Standard-library ASGI tests for the minimal PausePal API."""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from app.main import INDEX_FILE, app


async def asgi_request(method: str, path: str, payload: object = None) -> tuple[int, object]:
    body = b"" if payload is None else json.dumps(payload).encode("utf-8")
    headers = [(b"host", b"testserver")]
    if payload is not None:
        headers.extend(
            [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("ascii")),
            ]
        )

    sent: list[dict[str, object]] = []
    already_received = False

    async def receive() -> dict[str, object]:
        nonlocal already_received
        if not already_received:
            already_received = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message: dict[str, object]) -> None:
        sent.append(message)

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": b"",
        "root_path": "",
        "headers": headers,
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
    }
    await app(scope, receive, send)

    response_start = next(message for message in sent if message["type"] == "http.response.start")
    response_body = b"".join(
        message.get("body", b"")
        for message in sent
        if message["type"] == "http.response.body"
    )
    return int(response_start["status"]), json.loads(response_body.decode("utf-8"))


class PausePalApiTests(unittest.IsolatedAsyncioTestCase):
    async def test_health_reports_demo_mode(self) -> None:
        status, body = await asgi_request("GET", "/health")
        self.assertEqual(status, 200)
        self.assertEqual(body, {"status": "ok", "analysis_mode": "demo"})

    async def test_demo_warning_quotes_original_case(self) -> None:
        status, body = await asgi_request(
            "POST",
            "/api/analyze",
            {"text": "Please Do Not Tell your family about this request."},
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["assessment"], "warning")
        self.assertEqual(body["signals"][0]["quote"], "Do Not Tell")
        self.assertEqual(body["mode"], "demo")

    async def test_short_and_unmatched_messages_are_distinguished(self) -> None:
        short_status, short_body = await asgi_request(
            "POST", "/api/analyze", {"text": "Hi!"}
        )
        plain_status, plain_body = await asgi_request(
            "POST", "/api/analyze", {"text": "I got your note this morning."}
        )
        self.assertEqual(short_status, 200)
        self.assertEqual(short_body["assessment"], "insufficient_information")
        self.assertEqual(plain_status, 200)
        self.assertEqual(plain_body["assessment"], "no_clear_signals")

    async def test_input_is_trimmed_and_length_limited(self) -> None:
        status, body = await asgi_request(
            "POST", "/api/analyze", {"text": "   Please send me a message.   "}
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["assessment"], "warning")

        blank_status, blank_body = await asgi_request(
            "POST", "/api/analyze", {"text": "   "}
        )
        self.assertEqual(blank_status, 422)
        self.assertIn("empty", blank_body["detail"].lower())

        long_status, long_body = await asgi_request(
            "POST", "/api/analyze", {"text": "x" * 4001}
        )
        self.assertEqual(long_status, 422)
        self.assertIn("4000", long_body["detail"])

    async def test_live_mode_does_not_fall_back_to_demo(self) -> None:
        with patch.dict(os.environ, {"PAUSEPAL_MODE": "live"}):
            status, body = await asgi_request(
                "POST", "/api/analyze", {"text": "Please send me the code."}
            )
        self.assertEqual(status, 503)
        self.assertIn("no AI integration", body["detail"])

    async def test_home_path_is_absolute_and_resolves_static_index(self) -> None:
        self.assertTrue(INDEX_FILE.is_absolute())
        self.assertEqual(INDEX_FILE, (Path(__file__).resolve().parents[1] / "static" / "index.html"))


if __name__ == "__main__":
    unittest.main()
