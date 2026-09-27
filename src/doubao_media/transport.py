# GitHub@A p ris  mLab | A pris  mL  a   b@S   tar  sailsC lover
"""Async HTTP transport for the Doubao web API.

Handles the pieces every endpoint shares: the mandatory query parameter block,
cookie handling, business-code -> typed-error mapping, and SSE block parsing.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncIterator, Iterable, Mapping
from typing import Any

import httpx

from .endpoints import AID, BASE_URL, CHROME_VERSION, CHROMIUM_BUILD, WEB_VERSION_CODE
from .errors import (
    CODE_AUTH_EXPIRED,
    CODE_PERMISSION_DENIED,
    CODE_RATE_LIMITED,
    CODE_RISK_CONTROL,
    DoubaoAuthRequired,
    DoubaoRateLimited,
    DoubaoRiskControl,
    DoubaoUpstreamError,
)

DEFAULT_TIMEOUT = 60.0
STREAM_READ_TIMEOUT = 180.0

#: Cookies that must be forwarded when talking to the API.
SESSION_COOKIE_NAMES = (
    "sessionid",
    "sessionid_ss",
    "sid_guard",
    "sid_tt",
    "sid_ucp_v1",
    "ssid_ucp_v1",
    "uid_tt",
    "uid_tt_ss",
    "ttwid",
    "odin_tt",
    "s_v_web_id",
    "passport_csrf_token",
    "passport_csrf_token_default",
    "msToken",
    "store-idc",
    "store-country-code",
    "locale",
)

#: Domains a Doubao session cookie may live on.  ``msToken`` - ByteDance's
#: device-fingerprint token - is stored on ``.bytedance.com``, **not** on
#: ``.doubao.com``, and is required for the request to look like the official
#: client.  Verified on this machine: the desktop profile holds exactly one
#: ``msToken`` (223 bytes) under ``.bytedance.com``.
SESSION_COOKIE_DOMAINS: dict[str, str] = {
    "msToken": ".bytedance.com",
}
DEFAULT_COOKIE_DOMAIN = ".doubao.com"


def default_headers(cookies: Mapping[str, str]) -> dict[str, str]:
    csrf = cookies.get("passport_csrf_token") or cookies.get("passport_csrf_token_default") or ""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            f"(KHTML, like Gecko) Chrome/{CHROME_VERSION} Safari/537.36"
        ),
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Content-Type": "application/json",
        "Origin": BASE_URL,
        "Referer": f"{BASE_URL}/chat/",
        "agw-js-conv": "str, str",
    }
    if csrf:
        headers["x-tt-passport-csrf-token"] = csrf
    return headers


def build_base_params(cookies: Mapping[str, str]) -> dict[str, str]:
    """Common query block shared by most ``/samantha`` endpoints.

    ``device_id`` / ``web_id`` are only included when known, because a *fake*
    device fingerprint is itself a risk signal upstream.
    """
    params = {
        "aid": AID,
        "real_aid": AID,
        "device_platform": "web",
        "language": "zh",
        "pkg_type": "release_version",
        "version_code": WEB_VERSION_CODE,
        "chromium_version": CHROMIUM_BUILD,
        "samantha_web": "1",
        "use-olympus-account": "1",
        "web_tab_id": str(uuid.uuid4()),
    }
    fingerprint = cookies.get("s_v_web_id")
    if fingerprint:
        params["fp"] = fingerprint
    device_id = cookies.get("device_id")
    if device_id:
        params["device_id"] = device_id
        params["tea_uuid"] = device_id
    return params


# GitH   ub@   A  prismLa  b | A p r  i   sm   Lab@   Stars  ai  l   s  Clover
class SseBlock:
    """One parsed ``text/event-stream`` block."""

    __slots__ = ("event", "data", "raw")

    def __init__(self, event: str, data: str, raw: str) -> None:
        self.event = event
        self.data = data
        self.raw = raw

    def json(self) -> Any:
        if not self.data:
            return None
        try:
            return json.loads(self.data)
        except json.JSONDecodeError:
            return None

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"SseBlock(event={self.event!r}, data={self.data[:80]!r})"


def parse_sse_blocks(text: str) -> list[SseBlock]:
    """Split a buffered SSE payload into blocks.

    Doubao answers ``/samantha/chat/completion`` by streaming the *entire*
    response (including any async ``task_id`` handshake) before closing, so a
    single ``await response.aread()`` plus this splitter is usually enough.
    """
    blocks: list[SseBlock] = []
    for raw in text.replace("\r\n", "\n").split("\n\n"):
        if not raw.strip():
            continue
        event = ""
        data_parts: list[str] = []
        for line in raw.split("\n"):
            if line.startswith("event:"):
                event = line[6:].strip()
            elif line.startswith("data:"):
                data_parts.append(line[5:].lstrip())
            # Any other line (``:`` comment, ``id:``, ``retry:``) is ignored,
            # as required by the event-stream grammar.
        if not event and not data_parts:
            # Comment-only keep-alive block: nothing to report upstream.
            continue
        blocks.append(SseBlock(event, "\n".join(data_parts), raw))
    return blocks


def iter_sse_blocks(chunks: Iterable[str]) -> list[SseBlock]:
    return parse_sse_blocks("".join(chunks))


class DoubaoTransport:
    """Thin async wrapper around ``httpx`` with Doubao-specific semantics."""

    def __init__(
        self,
        cookies: Mapping[str, str],
        *,
        params: Mapping[str, str] | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        transport: httpx.AsyncBaseTransport | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        self.cookies: dict[str, str] = {str(k): str(v) for k, v in cookies.items()}
        self.params = dict(params or {})
        self.timeout = timeout
        self._transport = transport
        self._extra_headers = dict(headers or {})
        self._client: httpx.AsyncClient | None = None

    # -- lifecycle ---------------------------------------------------------

    async def __aenter__(self) -> DoubaoTransport:
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.close()

    async def open(self) -> None:
        if self._client is not None:
            return
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            timeout=httpx.Timeout(self.timeout, read=STREAM_READ_TIMEOUT),
            transport=self._transport,
            follow_redirects=False,
            cookies=self.cookies,
            headers={**default_headers(self.cookies), **self._extra_headers},
        )

    # G itHu  b  @ A p ris   m  Lab | Apr   is   m   L a   b@S   tarsailsC  lover
    def _sync_client_cookies(self) -> None:
        """Push cookie mutations (absorbed from responses) back into the client."""
        if self._client is None:
            return
        for key, value in self.cookies.items():
            if self._client.cookies.get(key) != value:
                self._client.cookies.set(key, value, domain=".doubao.com")

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("transport not opened; use 'async with' or await open()")
        return self._client

    # -- request helpers ---------------------------------------------------

    def _merge_params(self, extra: Mapping[str, str] | None) -> dict[str, str]:
        merged = build_base_params(self.cookies)
        merged.update(self.params)
        if extra:
            merged.update({k: v for k, v in extra.items() if v is not None})
        return merged

    # GitHub@A   pr ism La b | Apr is   mLab @Stars a   ilsC  l   ove r
    def _absorb_cookies(self, response: httpx.Response) -> None:
        for key, value in response.cookies.items():
            if value:
                self.cookies[key] = value

    @staticmethod
    def _raise_for_business_code(body: Any) -> None:
        if not isinstance(body, dict):
            return
        code = body.get("code")
        if code is None or code == 0:
            return
        try:
            numeric = int(code)
        except (TypeError, ValueError):
            numeric = None
        message = str(body.get("msg") or body.get("message") or code)
        if numeric is not None:
            if numeric == CODE_AUTH_EXPIRED:
                raise DoubaoAuthRequired(message)
            if numeric == CODE_RATE_LIMITED:
                raise DoubaoRateLimited(message, code=numeric, payload=body)
            if numeric == CODE_RISK_CONTROL:
                raise DoubaoRiskControl(message, verify_url=str(body.get("verify_url", "")))
            if numeric == CODE_PERMISSION_DENIED:
                raise DoubaoUpstreamError(
                    f"{message} (permission denied)", code=numeric, payload=body
                )
        raise DoubaoUpstreamError(message, code=numeric if numeric is not None else code,
                                  payload=body)

    async def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        params: Mapping[str, str] | None = None,
        timeout: float | None = None,
        check_code: bool = True,
    ) -> dict[str, Any]:
        await self.open()
        self._sync_client_cookies()
        response = await self.client.request(
            method,
            path,
            json=json_body,
            params=self._merge_params(params),
            timeout=timeout or self.timeout,
        )
        self._absorb_cookies(response)
        if response.status_code >= 400:
            raise DoubaoUpstreamError(
                f"HTTP {response.status_code} from {path}: {response.text[:300]}",
                code=response.status_code,
            )
        try:
            body = response.json()
        except ValueError as exc:  # non-JSON payload
            raise DoubaoUpstreamError(
                f"non-JSON response from {path}: {response.text[:300]}"
            ) from exc
        if check_code:
            self._raise_for_business_code(body)
        return body

    async def post(self, path: str, body: Any = None, **kwargs: Any) -> dict[str, Any]:
        return await self.request("POST", path, json_body=body, **kwargs)

    async def get(self, path: str, **kwargs: Any) -> dict[str, Any]:
        return await self.request("GET", path, **kwargs)

    # -- SSE ---------------------------------------------------------------

    # GitH  u b@Apr  ism L   ab | Apr  ismL ab@St   arsail   sClov er
    async def sse(
        self,
        path: str,
        body: Any,
        *,
        params: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> list[SseBlock]:
        """POST a JSON body and return the parsed SSE blocks.

        The endpoint is documented as a stream, but it always terminates after
        the generator handshake; buffering avoids fighting socket read timeouts
        on long image/video waits.
        """
        await self.open()
        async with self.client.stream(
            "POST",
            path,
            json=body,
            params=self._merge_params(params),
            timeout=timeout or self.timeout,
        ) as response:
            self._absorb_cookies(response)
            if response.status_code >= 400:
                text = (await response.aread()).decode("utf-8", "replace")
                raise DoubaoUpstreamError(
                    f"HTTP {response.status_code} from {path}: {text[:300]}",
                    code=response.status_code,
                )
            chunks: list[str] = []
            async for chunk in response.aiter_text():
                chunks.append(chunk)
        blocks = iter_sse_blocks(chunks)
        for block in blocks:
            if block.event == "gateway-error":
                payload = block.json()
                message = ""
                if isinstance(payload, dict):
                    message = str(payload.get("message") or payload.get("msg") or payload)
                raise DoubaoUpstreamError(
                    f"gateway-error: {message or block.data[:200]}", code="gateway-error",
                    payload=payload,
                )
        return blocks

    async def sse_stream(
        self,
        path: str,
        body: Any,
        *,
        params: Mapping[str, str] | None = None,
        timeout: float | None = None,
    ) -> AsyncIterator[SseBlock]:
        """Incremental variant of :meth:`sse` for callers that need progress."""
        await self.open()
        async with self.client.stream(
            "POST",
            path,
            json=body,
            params=self._merge_params(params),
            timeout=timeout or self.timeout,
        ) as response:
            self._absorb_cookies(response)
            if response.status_code >= 400:
                text = (await response.aread()).decode("utf-8", "replace")
                raise DoubaoUpstreamError(
                    f"HTTP {response.status_code} from {path}: {text[:300]}",
                    code=response.status_code,
                )
            buffer = ""
            async for chunk in response.aiter_text():
                buffer += chunk
                while "\n\n" in buffer:
                    raw, buffer = buffer.split("\n\n", 1)
                    parsed = parse_sse_blocks(raw)
                    for block in parsed:
                        if block.event == "gateway-error":
                            raise DoubaoUpstreamError(
                                f"gateway-error: {block.data[:200]}", code="gateway-error"
                            )
                        yield block
            for block in parse_sse_blocks(buffer):
                yield block

    # G   it Hub  @A  prism  Lab | A  p   ri smL  ab@S t ar  sailsClo  v  er
    async def download(self, url: str, *, timeout: float | None = None) -> bytes:
        """Fetch a CDN asset (image/video) with the session cookies attached."""
        await self.open()
        response = await self.client.get(
            url, timeout=timeout or STREAM_READ_TIMEOUT, follow_redirects=True
        )
        if response.status_code >= 400:
            raise DoubaoUpstreamError(
                f"HTTP {response.status_code} downloading {url[:120]}",
                code=response.status_code,
            )
        return response.content

    async def download_to(self, url: str, destination: str, *,
                          timeout: float | None = None) -> int:
        """Stream a CDN asset straight to disk; returns the byte count."""
        await self.open()
        written = 0
        async with self.client.stream(
            "GET", url, timeout=timeout or STREAM_READ_TIMEOUT, follow_redirects=True
        ) as response:
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

    # G i tHub@A   p  r  i sm  L   ab | Apris mLa b@  Star  s   a   ilsClove r
    async def sleep(self, seconds: float) -> None:
        await asyncio.sleep(seconds)
