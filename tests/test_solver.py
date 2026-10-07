"""Unit tests that stub out the browser and the network.

Run with: pytest -q
"""

import asyncio

import pytest

from nodriver_turnstile import TurnstileError, solve_turnstile
from nodriver_turnstile import solver


class FakeTab:
    """Just enough of a nodriver tab for the solver."""

    def __init__(self, sitekey=None, has_field=True):
        self.url = "https://protected.example/login"
        self._sitekey = sitekey
        self._has_field = has_field
        self.injected = None

    async def evaluate(self, js, await_promise=False):
        if "cf-turnstile-response" in js and self.injected is None and "document.querySelectorAll" in js:
            # this is the _INJECT call wrapped as an expression; handled below
            pass
        if js == "location.href":
            return self.url
        if "querySelectorAll" in js and "forEach" not in js:
            return self._sitekey
        # treat anything else containing a literal token as the inject call
        if "n = 0" in js or "document.querySelectorAll(" in js and "(" in js and js.strip().startswith("("):
            if not self._has_field:
                return 0
            self.injected = True
            return 1
        return self._sitekey


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


def test_solves_and_injects(monkeypatch):
    async def fake_request_token(api_key, url, sitekey, proxy=None, timeout=120.0):
        assert sitekey == "0x4AAAAAAABkMYinukE8nzKd"
        return solver.SolveResult(token="SOLVED-TOKEN", cost=0.0009, elapsed=0.8)

    monkeypatch.setattr(solver, "request_token", fake_request_token)

    tab = FakeTab(sitekey="0x4AAAAAAABkMYinukE8nzKd", has_field=True)
    result = run(solve_turnstile(tab, api_key="pk_test"))
    assert result.token == "SOLVED-TOKEN"
    assert tab.injected is True


def test_raises_when_no_response_field(monkeypatch):
    async def fake_request_token(api_key, url, sitekey, proxy=None, timeout=120.0):
        return solver.SolveResult(token="SOLVED-TOKEN", cost=0.0009, elapsed=0.8)

    monkeypatch.setattr(solver, "request_token", fake_request_token)

    tab = FakeTab(sitekey="0xSITEKEY", has_field=False)
    with pytest.raises(TurnstileError):
        run(solve_turnstile(tab, api_key="pk_test"))


def test_read_sitekey_times_out():
    tab = FakeTab(sitekey=None)

    async def fake_evaluate(js, await_promise=False):
        return None

    tab.evaluate = fake_evaluate
    with pytest.raises(TurnstileError):
        run(solver.read_sitekey(tab, timeout=0.2, poll=0.05))


def test_request_token_raises_on_failure(monkeypatch):
    class FakeResponse:
        text = '{"success": false, "error": "bad sitekey"}'

        def json(self):
            return {"success": False, "error": "bad sitekey"}

    class FakeAsyncClient:
        def __init__(self, timeout=120.0):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, headers=None, json=None):
            return FakeResponse()

    monkeypatch.setattr(solver.httpx, "AsyncClient", FakeAsyncClient)
    with pytest.raises(TurnstileError):
        run(solver.request_token("pk_test", "https://x.example/", "0xSITEKEY"))
