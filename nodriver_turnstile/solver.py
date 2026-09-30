"""Solve Cloudflare Turnstile inside a nodriver tab.

The flow is the same one you'd do by hand: read the sitekey off the page, hand
the (url, sitekey) pair to a solver, then drop the returned token back into the
widget's hidden input and fire the callback the page registered. nodriver drives
a real Chrome, so the page state, cookies, and TLS all belong to the browser you
are already using — the solver only supplies the token.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

import httpx

PEAK_ENDPOINT = "https://api.peak.fo/solve"


class TurnstileError(RuntimeError):
    """Raised when the sitekey can't be found or the solve fails."""


@dataclass
class SolveResult:
    token: str
    cost: float
    elapsed: float


# JS that pulls the sitekey out of a rendered Turnstile widget. Covers the three
# shapes you actually see in the wild: the explicit-render div, the implicit
# div, and the managed iframe whose src carries the key as a query param.
_FIND_SITEKEY = r"""
(() => {
  const el = document.querySelector('[data-sitekey]');
  if (el) return el.getAttribute('data-sitekey');
  const f = document.querySelector('iframe[src*="challenges.cloudflare.com"]');
  if (f) {
    const m = f.getAttribute('src').match(/[?&]sitekey=([^&]+)/);
    if (m) return decodeURIComponent(m[1]);
  }
  if (window.turnstile && window.__cfChlOpt && window.__cfChlOpt.sitekey)
    return window.__cfChlOpt.sitekey;
  return null;
})()
"""

# JS that installs the token: fills every cf-turnstile-response field, then calls
# the widget callback if the page wired one up (most forms read the input on
# submit, but SPAs lean on the callback).
_INJECT = r"""
(token) => {
  let n = 0;
  document.querySelectorAll(
    'input[name="cf-turnstile-response"], textarea[name="cf-turnstile-response"]'
  ).forEach((i) => { i.value = token; n++; });
  document.querySelectorAll('[name="g-recaptcha-response"]').forEach((i) => { i.value = token; });
  try {
    const el = document.querySelector('[data-callback]');
    if (el) {
      const cb = el.getAttribute('data-callback');
      if (cb && typeof window[cb] === 'function') { window[cb](token); n++; }
    }
  } catch (e) {}
  return n;
}
"""


async def read_sitekey(tab, timeout: float = 15.0, poll: float = 0.5) -> str:
    """Wait for the widget to render and return its sitekey."""
    deadline = asyncio.get_event_loop().time() + timeout
    while True:
        key = await tab.evaluate(_FIND_SITEKEY, await_promise=False)
        if key:
            return str(key)
        if asyncio.get_event_loop().time() >= deadline:
            raise TurnstileError(
                "no Turnstile sitekey on the page after "
                f"{timeout:.0f}s — is the widget actually present?"
            )
        await asyncio.sleep(poll)


async def request_token(
    api_key: str,
    url: str,
    sitekey: str,
    proxy: Optional[str] = None,
    timeout: float = 120.0,
) -> SolveResult:
    """Ask Peak for a token. Pass a proxy to match the browser's exit IP, or
    leave it out to use Peak's proxyless pool."""
    task = "turnstiletask" if proxy else "turnstiletaskproxyless"
    body = {"task_type": task, "url": url, "sitekey": sitekey}
    if proxy:
        body["proxy"] = proxy

    loop = asyncio.get_event_loop()
    t0 = loop.time()
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(
            PEAK_ENDPOINT,
            headers={"X-API-Key": api_key, "Content-Type": "application/json"},
            json=body,
        )
    elapsed = loop.time() - t0
    data = r.json()
    if not data.get("success"):
        raise TurnstileError(f"solve failed: {data.get('error') or r.text[:200]}")
    return SolveResult(
        token=data["data"]["token"],
        cost=float(data.get("cost", 0.0)),
        elapsed=elapsed,
    )


async def solve_turnstile(
    tab,
    api_key: str,
    proxy: Optional[str] = None,
    url: Optional[str] = None,
    timeout: float = 120.0,
) -> SolveResult:
    """End to end: read the sitekey off ``tab``, solve it, inject the token.

    ``tab`` is a nodriver tab/page. ``url`` defaults to the tab's current URL.
    Returns the :class:`SolveResult`; the token is already in the page.
    """
    page_url = url or await tab.evaluate("location.href", await_promise=False)
    sitekey = await read_sitekey(tab)
    result = await request_token(api_key, str(page_url), sitekey, proxy, timeout)
    injected = await tab.evaluate(
        f"({_INJECT})({result.token!r})", await_promise=False
    )
    if not injected:
        raise TurnstileError(
            "got a token but found nowhere to put it — the widget's response "
            "field wasn't on the page. Inject result.token yourself."
        )
    return result
