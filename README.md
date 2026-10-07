<div align="center">

# nodriver-turnstile

**Solve Cloudflare Turnstile inside a [nodriver](https://github.com/ultrafunkamsterdam/nodriver) browser.** Read the sitekey off the page, get a token, drop it into the widget. Three lines, and it works with the real Chrome nodriver already drives.

<p>
  <img src="https://img.shields.io/badge/python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/nodriver-async-00A67E?style=for-the-badge" alt="nodriver">
  <img src="https://img.shields.io/badge/license-MIT-007EC7?style=for-the-badge" alt="MIT License">
</p>

</div>

---

nodriver gets you past most bot checks on its own. It's a genuine Chrome with no CDP fingerprints. What it can't do is *answer* a Turnstile challenge, because that's a token the widget mints server-side, not something a browser flag turns off. This library fills that one gap: it hands the `(url, sitekey)` to a solver and puts the returned token back where the page expects it. Everything else (cookies, TLS, the session) stays in your nodriver browser.

## Install

```bash
pip install nodriver-turnstile
```

## Use it

```python
import asyncio, os
import nodriver as uc
from nodriver_turnstile import solve_turnstile

async def main():
    browser = await uc.start()
    tab = await browser.get("https://site-with-turnstile.example/login")

    result = await solve_turnstile(tab, os.environ["PEAK_API_KEY"])
    print(result.elapsed, result.cost)   # token is already in the page

    await (await tab.select("button[type=submit]")).click()

asyncio.run(main())
```

That's the whole thing. `solve_turnstile` finds the sitekey (explicit-render div, implicit div, or the managed iframe), requests a token, fills every `cf-turnstile-response` field, and fires the widget's callback if the page registered one.

## Matching the exit IP

Turnstile scores the IP that submits the token. If your nodriver browser runs behind a proxy, give the solver the same one so the token and the request line up:

```python
result = await solve_turnstile(tab, api_key, proxy="http://user:pass@host:port")
```

Leave `proxy` off and the token is minted from a clean pool instead. That's fine for a lot of sites; test it against yours.

## Lower-level pieces

You don't have to hand it the tab. Pull the sitekey and token yourself when you want control over injection:

```python
from nodriver_turnstile import read_sitekey, request_token

sitekey = await read_sitekey(tab)
res = await request_token(api_key, url="https://target.example/", sitekey=sitekey)
await tab.evaluate(f'document.querySelector("[name=cf-turnstile-response]").value = {res.token!r}')
```

## Getting a key

`solve_turnstile` needs an API key for the solver it calls: [Peak](https://peak.fo/?utm_source=github&utm_medium=readme&utm_campaign=packages&utm_content=nodriver-turnstile). Turnstile solves come back in about a second, you pay only for the ones that land, and the free tier is enough to wire this up and test it end to end. Peak also solves the Cloudflare 5-second challenge (`task_type: "cloudflare5stask"`); this package focuses on Turnstile.

<div align="center">

<a href="https://peak.fo/?utm_source=github&utm_medium=readme&utm_campaign=packages&utm_content=nodriver-turnstile"><img src="https://img.shields.io/badge/Get_a_key-Peak-FF6B35?style=for-the-badge" alt="Peak"></a>
<br>
<sub><strong>$0.90 per 1,000 Turnstile solves</strong>, down to $0.35 at volume · pay only on success · 1,000 free solves · <a href="https://peak.fo/?utm_source=github&utm_medium=readme&utm_campaign=packages&utm_content=nodriver-turnstile">peak.fo</a></sub>

</div>

## Related

Same pattern for other stacks: [playwright-turnstile](https://github.com/CircuitSavage/playwright-turnstile) · [selenium-turnstile](https://github.com/CircuitSavage/selenium-turnstile) · [camoufox-turnstile](https://github.com/CircuitSavage/camoufox-turnstile) · [scrapling-turnstile](https://github.com/CircuitSavage/scrapling-turnstile) · [crawlee-turnstile](https://github.com/CircuitSavage/crawlee-turnstile) · [drissionpage-turnstile](https://github.com/CircuitSavage/drissionpage-turnstile) · [puppeteer-extra-plugin-turnstile](https://github.com/CircuitSavage/puppeteer-extra-plugin-turnstile) · [scrapy-turnstile](https://github.com/CircuitSavage/scrapy-turnstile) · [turnstile-curl](https://github.com/CircuitSavage/turnstile-curl) · [cloudscraper-turnstile](https://github.com/CircuitSavage/cloudscraper-turnstile) · [crawl4ai-turnstile](https://github.com/CircuitSavage/crawl4ai-turnstile). Full list in [awesome-turnstile-solvers](https://github.com/CircuitSavage/awesome-turnstile-solvers).

## Notes

Use this on sites and accounts you're allowed to automate. Respect each target's Terms of Service and `robots.txt`. This is tooling for legitimate automation, testing, and public-data scraping; nothing here helps with credential stuffing or abuse. Not affiliated with Cloudflare.

## License

MIT
