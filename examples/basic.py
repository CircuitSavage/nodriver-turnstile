"""Solve a Turnstile widget with nodriver + Peak, then submit the form.

    pip install nodriver nodriver-turnstile
    PEAK_API_KEY=pk_xxx python examples/basic.py
"""

import asyncio
import os

import nodriver as uc

from nodriver_turnstile import solve_turnstile

API_KEY = os.environ["PEAK_API_KEY"]
TARGET = "https://your-target.example/login"

# Optional: pass the same proxy the browser uses so the token's IP matches.
# PROXY = "http://user:pass@host:port"
PROXY = None


async def main():
    browser = await uc.start()
    tab = await browser.get(TARGET)

    result = await solve_turnstile(tab, API_KEY, proxy=PROXY)
    print(f"solved in {result.elapsed:.1f}s, cost ${result.cost}")

    # Token is already in the widget's hidden input. Submit however the page wants.
    submit = await tab.select("button[type=submit]")
    if submit:
        await submit.click()
        await tab.sleep(3)

    print("done:", tab.url)
    browser.stop()


if __name__ == "__main__":
    asyncio.run(main())
