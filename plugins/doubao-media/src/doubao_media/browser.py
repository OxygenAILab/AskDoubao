"""Browser-backed transport for risk-control-sensitive Doubao endpoints.

Why this exists
---------------
Plain HTTP works for the account/plan endpoints, but generation is protected by
ByteDance risk control (``710022004`` with an ``ext.type = verify`` payload).
The official web client passes it because every request carries an ``a_bogus``
signature produced by ByteDance's own JS with a real browser fingerprint.

Reimplementing that signature is both fragile and out of scope, so this module
does what the reference implementation does: keep a real Chromium page open and
issue the request with the page's own ``fetch``, letting the site's hook sign
it.  Only generation traffic goes through the page; asset downloads and
read-only queries stay on plain HTTP.

Session handling is unchanged - the caller's cookies are injected into the
browser context, so no second login is ever required.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import time
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .endpoints import BASE_URL, CHROME_VERSION
from .errors import DoubaoConfigError, DoubaoRiskControl, DoubaoUpstreamError
from .transport import (
    DEFAULT_COOKIE_DOMAIN,
    SESSION_COOKIE_DOMAINS,
    SseBlock,
    build_base_params,
    parse_sse_blocks,
)

DEFAULT_PROFILE_DIR = "~/.doubao-media/browser-profile"
CHAT_URL = f"{BASE_URL}/chat/"

_STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh', 'en']});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
window.chrome = window.chrome || {runtime: {}};
"""


class BrowserTransport:
    """Drives a Chromium page so generation requests are correctly signed."""

    # G  itHub@OxygenAI  L ab | OxygenAILab@Sta   rsailsCl   over
    def __init__(
        self,
        cookies: Mapping[str, str],
        *,
        cookie_domains: Mapping[str, str] | None = None,
        params: Mapping[str, str] | None = None,
        headless: bool = True,
        profile_dir: str | Path | None = None,
        executable_path: str | None = None,
        channel: str | None = None,
        launch_args: Sequence[str] | None = None,
        bypass_proxy: bool | None = None,
        startup_timeout: float = 60.0,
        request_timeout: float = 240.0,
    ) -> None:
        self.cookies = {str(k): str(v) for k, v in cookies.items()}
        domains = dict(cookie_domains or {})
        self.cookie_domains: dict[str, str] = {
            name: domains.get(name, SESSION_COOKIE_DOMAINS.get(name,
                                                               DEFAULT_COOKIE_DOMAIN))
            for name in self.cookies
        }
        self.params = dict(params or {})
        self.headless = headless
        self.profile_dir = Path(
            profile_dir or os.environ.get("DOUBAO_MEDIA_BROWSER_PROFILE")
            or DEFAULT_PROFILE_DIR
        ).expanduser()
        self.executable_path = executable_path or os.environ.get(
            "DOUBAO_MEDIA_BROWSER_PATH"
        )
        self.channel = channel or os.environ.get("DOUBAO_MEDIA_BROWSER_CHANNEL")
        self.launch_args = list(launch_args or [])
        # Doubao is a mainland-China service.  When the machine routes through a
        # proxy (Clash and friends set the system proxy), Chromium inherits it and
        # the request leaves from a foreign datacentre IP, which ByteDance risk
        # control refuses outright.  Bypassing the proxy for Chromium is
        # therefore the correct default on such machines; set
        # DOUBAO_MEDIA_BROWSER_PROXY=use to keep the system proxy instead.
        env_bypass = os.environ.get("DOUBAO_MEDIA_BROWSER_PROXY", "").strip().lower()
        if bypass_proxy is None:
            bypass_proxy = env_bypass != "use"
        self.bypass_proxy = bypass_proxy
        self.startup_timeout = startup_timeout
        self.request_timeout = request_timeout

        self._playwright: Any = None
        self._context: Any = None
        self._page: Any = None
        self._lock = asyncio.Lock()

    # -- lifecycle ---------------------------------------------------------

    @property
    def is_open(self) -> bool:
        return self._page is not None

    async def open(self) -> None:
        if self._page is not None:
            return
        async with self._lock:
            if self._page is not None:
                return
            try:
                from playwright.async_api import async_playwright
            except ImportError as exc:  # pragma: no cover - dependency hint
                raise DoubaoConfigError(
                    "browser transport needs Playwright: "
                    "`pip install playwright` then `python -m playwright install chromium`"
                ) from exc

            # G   i t Hub @ Ox y genAI L  a   b | Oxy  g   e nAI L  ab@   St   a   r   s   ail   sCl o ve   r
            self.profile_dir.mkdir(parents=True, exist_ok=True)
            self._playwright = await async_playwright().start()
            launch: dict[str, Any] = {
                "headless": self.headless,
                "viewport": {"width": 1440, "height": 900},
                "locale": "zh-CN",
                "timezone_id": "Asia/Shanghai",
                "user_agent": _user_agent(),
                "args": [
                    "--disable-blink-features=AutomationControlled",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-dev-shm-usage",
                    *(
                        ["--no-proxy-server"]
                        if self.bypass_proxy
                        else []
                    ),
                    *self.launch_args,
                ],
                "ignore_default_args": ["--enable-automation"],
            }
            if self.executable_path:
                launch["executable_path"] = self.executable_path
            elif self.channel:
                launch["channel"] = self.channel
            try:
                self._context = (
                    await self._playwright.chromium.launch_persistent_context(
                        str(self.profile_dir), **launch
                    )
                )
            except Exception as exc:  # noqa: BLE001 - surface install guidance
                await self._shutdown_playwright()
                raise DoubaoConfigError(
                    f"cannot launch Chromium for the browser transport: {exc}. "
                    "Install it with `python -m playwright install chromium`, or set "
                    "DOUBAO_MEDIA_BROWSER_CHANNEL=msedge to reuse Edge."
                ) from exc

            self._page = (
                self._context.pages[0]
                if self._context.pages
                else await self._context.new_page()
            )
            self._page.set_default_timeout(self.request_timeout * 1000)
            await self._page.add_init_script(_STEALTH_SCRIPT)
            await self._inject_cookies()
            await self._page.goto(CHAT_URL, wait_until="domcontentloaded",
                                  timeout=self.startup_timeout * 1000)
            await self._wait_for_site_ready()
            await self._capture_fingerprint()

    async def close(self) -> None:
        if self._context is not None:
            with contextlib.suppress(Exception):  # teardown must never raise
                await self._context.close()
        self._context = None
        self._page = None
        await self._shutdown_playwright()

    async def _shutdown_playwright(self) -> None:
        if self._playwright is not None:
            with contextlib.suppress(Exception):
                await self._playwright.stop()
            self._playwright = None

    async def __aenter__(self) -> BrowserTransport:
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    # -- setup helpers -----------------------------------------------------

    # G itHu   b   @ O  xyge nAIL   ab | Oxygen   AIL   ab @St   a r  s a   i  lsC lov er
    async def _inject_cookies(self) -> None:
        payload = []
        for name, value in self.cookies.items():
            if not value:
                continue
            payload.append(
                {
                    "name": name,
                    "value": value,
                    "domain": self.cookie_domains.get(name, DEFAULT_COOKIE_DOMAIN),
                    "path": "/",
                    "secure": True,
                    "httpOnly": False,
                    "sameSite": "Lax",
                }
            )
        if payload:
            await self._context.add_cookies(payload)

    # GitHub@O   xy genA  I   Lab | Oxy   genAIL ab   @Sta   rsa ils Clo   ver
    async def _wait_for_site_ready(self) -> None:
        """Wait for the site's fetch hook and signer to be installed."""
        deadline = time.monotonic() + self.startup_timeout
        while time.monotonic() < deadline:
            ready = await self._page.evaluate(
                """() => {
                    let hooked = false, signer = false;
                    try { hooked = !window.fetch.toString().includes('native code'); }
                    catch (e) {}
                    try { signer = typeof window.bdms?.frontierSign === 'function'; }
                    catch (e) {}
                    return {hooked, signer};
                }"""
            )
            if ready.get("hooked") or ready.get("signer"):
                return
            await asyncio.sleep(1.0)
        raise DoubaoUpstreamError(
            "Doubao's request signer did not initialise in the browser page"
        )

    async def _capture_fingerprint(self) -> None:
        """Mirror the official client's device parameters.

        Values come from the same storage keys the site itself uses, so the
        request looks like the real client rather than a synthetic one.
        """
        try:
            found = await self._page.evaluate(
                """() => {
                    const out = {};
                    try {
                        const sam = JSON.parse(
                            localStorage.getItem('samantha_web_web_id') || '{}');
                        out.device_id = sam.web_id || '';
                    } catch (e) {}
                    try {
                        const tea = JSON.parse(
                            localStorage.getItem('__tea_cache_tokens_497858') || '{}');
                        out.web_id = tea.web_id || '';
                    } catch (e) {}
                    const fp = document.cookie.split(';')
                        .map(c => c.trim())
                        .find(c => c.startsWith('s_v_web_id='));
                    out.fp = fp ? fp.split('=')[1] : '';
                    return out;
                }"""
            )
        except Exception:  # noqa: BLE001 - fingerprint is best effort
            return
        if isinstance(found, Mapping):
            for key in ("device_id", "web_id", "fp"):
                value = found.get(key)
                if value:
                    self.params[key] = str(value)

    def _query(self, extra: Mapping[str, str] | None) -> str:
        from urllib.parse import urlencode

        merged = build_base_params(self.cookies)
        merged.update(self.params)
        if extra:
            merged.update({k: v for k, v in extra.items() if v})
        return urlencode(merged)

    # -- requests ----------------------------------------------------------

    async def sse(
        self,
        path: str,
        body: Any,
        *,
        params: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> list[SseBlock]:
        text = await self._fetch_text(path, body, params=params, timeout=timeout)
        blocks = parse_sse_blocks(text)
        for block in blocks:
            if block.event == "gateway-error":
                raise DoubaoUpstreamError(
                    f"gateway-error: {block.data[:200]}", code="gateway-error"
                )
        return blocks

    async def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        params: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> dict[str, Any]:
        text = await self._fetch_text(
            path, json_body, method=method, params=params, timeout=timeout
        )
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise DoubaoUpstreamError(
                f"non-JSON response from {path}: {text[:200]}"
            ) from exc

    async def post(self, path: str, body: Any = None, **kwargs: Any) -> dict[str, Any]:
        return await self.request("POST", path, json_body=body, **kwargs)

    # G   it Hub@O  x yg  en  AILab | Oxyg  enAILab@  S ta  r   sa i  l s  Clove  r
    async def _fetch_text(
        self,
        path: str,
        body: Any,
        *,
        method: str = "POST",
        params: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> str:
        await self.open()
        url = f"{BASE_URL}{path}?{self._query(params)}"
        csrf = (
            self.cookies.get("passport_csrf_token")
            or self.cookies.get("passport_csrf_token_default")
            or ""
        )
        payload = json.dumps(body, ensure_ascii=False) if body is not None else None
        timeout_ms = int((timeout or self.request_timeout) * 1000)
        try:
            result = await self._page.evaluate(
                """
                async ({url, method, payload, csrf, timeoutMs}) => {
                    const controller = new AbortController();
                    const timer = setTimeout(() => controller.abort(), timeoutMs);
                    try {
                        const headers = {
                            'Accept': 'text/event-stream, application/json, */*',
                            'Content-Type': 'application/json',
                            'agw-js-conv': 'str, str',
                        };
                        if (csrf) headers['x-tt-passport-csrf-token'] = csrf;
                        const init = {
                            method, headers,
                            credentials: 'include',
                            signal: controller.signal,
                        };
                        if (payload !== null && method !== 'GET') init.body = payload;
                        const resp = await fetch(url, init);
                        const text = await resp.text();
                        return {ok: resp.ok, status: resp.status, text};
                    } catch (err) {
                        return {ok: false, status: -1,
                                text: String(err && err.message || err)};
                    } finally {
                        clearTimeout(timer);
                    }
                }
                """,
                {
                    "url": url,
                    "method": method,
                    "payload": payload,
                    "csrf": csrf,
                    "timeoutMs": timeout_ms,
                },
            )
        except Exception as exc:  # noqa: BLE001 - page died mid-request
            raise DoubaoUpstreamError(f"browser request to {path} failed: {exc}") from exc

        # Git   Hub @Oxy  genAI   Lab | Ox  yg   en  A ILa b @StarsailsCl o   ver
        text = str(result.get("text") or "")
        self._absorb_cookies_from_page(result)
        if not result.get("ok"):
            if "710022004" in text:
                raise DoubaoRiskControl(
                    "Doubao still applied risk control inside the browser page. "
                    "Open the Doubao client (or the site) once, complete the "
                    "verification prompt, then retry.",
                    verify_url="",
                )
            raise DoubaoUpstreamError(
                f"HTTP {result.get('status')} from {path}: {text[:300]}"
            )
        return text

    def _absorb_cookies_from_page(self, result: Mapping[str, Any]) -> None:
        """Keep the HTTP transport's cookie view in sync after a page request."""
        # ``fetch`` responses do not expose Set-Cookie, so refresh from the
        # context instead.  Cheap and only runs after a generation.
        try:
            for cookie in self._context.cookies():
                name = cookie.get("name")
                if name and cookie.get("value"):
                    self.cookies[str(name)] = str(cookie["value"])
        except Exception:  # noqa: BLE001
            pass

    # -- downloads (CDN, no risk control) ----------------------------------

    async def download_to(
        self, url: str, destination: str, *, timeout: float | None = None
    ) -> int:
        import httpx

        written = 0
        async with (
            httpx.AsyncClient(
                timeout=timeout or 300.0, follow_redirects=True
            ) as client,
            client.stream("GET", url) as response,
        ):
            if response.status_code >= 400:
                raise DoubaoUpstreamError(
                    f"HTTP {response.status_code} downloading {url[:120]}",
                    code=response.status_code,
                )
            with open(destination, "wb") as handle:
                async for chunk in response.aiter_bytes():
                    handle.write(chunk)
                    written += len(chunk)
        return written


def _user_agent() -> str:
    return (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        f"(KHTML, like Gecko) Chrome/{CHROME_VERSION} Safari/537.36"
    )


# G  i tH   ub@  Oxy g en AILa  b | Oxyg en AI La b@Stars  a   i   lsC   love   r
class HybridTransport:
    """Plain HTTP for cheap reads, browser page for risk-controlled writes."""

    def __init__(
        self,
        http: Any,
        browser: BrowserTransport | None = None,
        *,
        mode: str = "auto",
    ) -> None:
        self.http = http
        self.browser = browser
        self.mode = mode  # "auto" | "http" | "browser"
        self.cookies = http.cookies
        self.params = http.params

    async def open(self) -> None:
        await self.http.open()

    async def close(self) -> None:
        if self.browser is not None and self.browser.is_open:
            await self.browser.close()
        await self.http.close()

    async def __aenter__(self) -> HybridTransport:
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    @property
    def client(self) -> Any:
        return self.http.client

    def _use_browser(self, path: str) -> bool:
        """Page-fetch whenever the browser is available and not disabled.

        ``"auto"`` and ``"browser"`` both route generation through the page,
        because every generation call can hit risk control; ``"http"`` or the
        absence of a browser keeps everything on plain HTTP.
        """
        return self.mode != "http" and self.browser is not None

    async def request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        if self.mode == "browser" and self.browser is not None and method != "GET":
            body = kwargs.get("json_body")
            params = kwargs.get("params")
            return await self.browser.request(
                method, path, json_body=body, params=params,
                timeout=kwargs.get("timeout"),
            )
        return await self.http.request(method, path, **kwargs)

    async def post(self, path: str, body: Any = None, **kwargs: Any) -> dict[str, Any]:
        return await self.request("POST", path, json_body=body, **kwargs)

    # GitH   ub  @  O   xyg   en AI La  b | Oxy   genAILab @St  ar  sa i  lsC lo  v   e  r
    async def get(self, path: str, **kwargs: Any) -> dict[str, Any]:
        return await self.request("GET", path, **kwargs)

    async def sse(
        self,
        path: str,
        body: Any,
        *,
        params: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> list[SseBlock]:
        if self._use_browser(path) and self.browser is not None:
            return await self.browser.sse(path, body, params=params, timeout=timeout)
        return await self.http.sse(path, body, params=params, timeout=timeout)

    async def sse_stream(self, *args: Any, **kwargs: Any) -> Any:
        # Streaming is only offered by the HTTP transport; generation uses the
        # buffered ``sse`` path because it needs signature-aware fetching.
        return await self.http.sse_stream(*args, **kwargs)

    async def download_to(
        self, url: str, destination: str, *, timeout: float | None = None
    ) -> int:
        return await self.http.download_to(url, destination, timeout=timeout)

    async def download(self, url: str, *, timeout: float | None = None) -> bytes:
        return await self.http.download(url, timeout=timeout)
