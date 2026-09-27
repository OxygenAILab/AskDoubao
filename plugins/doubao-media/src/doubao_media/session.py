"""Session store, onboarding (QR login) and browser-cookie adoption.

Design notes
------------
* The session file is written **DPAPI-encrypted** (current-user scope), so the
  plaintext ``sessionid`` never lands on disk unprotected.  Plain JSON is still
  accepted on read for manual setup and for administrators who inject a cookie
  header themselves.
* Onboarding prefers reusing a browser the user already signed in with.  When
  that is impossible the module drives the *official* QR login flow over plain
  HTTPS - proven to work without launching a browser.
* This module never prints cookie values.
"""

from __future__ import annotations

import asyncio
import base64
import contextlib
import ctypes
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time
from collections.abc import Callable, Mapping
from ctypes import wintypes
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from .endpoints import AID, BASE_URL, EP_LOGIN_CHECK, EP_LOGIN_QRCODE, EP_SUBSCRIPTION_ENTRY_CONFIG
from .errors import DoubaoAuthRequired, DoubaoConfigError, DoubaoUpstreamError
from .transport import (
    DEFAULT_COOKIE_DOMAIN,
    SESSION_COOKIE_DOMAINS,
    SESSION_COOKIE_NAMES,
    default_headers,
)

#: Additional cookies that live outside ``.doubao.com`` but belong to the
#: session (ByteDance device fingerprint tokens).
EXTRA_SESSION_COOKIES = tuple(SESSION_COOKIE_DOMAINS)

DPAPI_MAGIC = b"DBMEDIA1\n"
DEFAULT_SESSION_PATH = "~/.doubao-media/session.json"

ProgressCallback = Callable[[str, str], None]


# ---------------------------------------------------------------------------
# Windows DPAPI helper
# ---------------------------------------------------------------------------

_IS_WINDOWS = sys.platform == "win32"


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_char)),
    ]


def dpapi_protect(data: bytes) -> bytes:
    """Encrypt ``data`` for the current Windows user."""
    if not _IS_WINDOWS:
        raise DoubaoConfigError("DPAPI is only available on Windows")
    buffer = ctypes.create_string_buffer(data, len(data))
    blob_in = _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
    blob_out = _DataBlob()
    ok = ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)
    )
    if not ok:
        raise DoubaoConfigError("CryptProtectData failed")
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)


def dpapi_unprotect(data: bytes) -> bytes:
    """Decrypt a blob previously produced by :func:`dpapi_protect`."""
    if not _IS_WINDOWS:
        raise DoubaoConfigError("DPAPI is only available on Windows")
    buffer = ctypes.create_string_buffer(data, len(data))
    blob_in = _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
    blob_out = _DataBlob()
    ok = ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(blob_in), None, None, None, None, 0, ctypes.byref(blob_out)
    )
    if not ok:
        raise DoubaoConfigError(
            "CryptUnprotectData failed (session file belongs to another user profile?)"
        )
    try:
        return ctypes.string_at(blob_out.pbData, blob_out.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(blob_out.pbData)


# ---------------------------------------------------------------------------
# Session value object
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Session:
    """A captured Doubao login."""

    cookies: dict[str, str] = field(default_factory=dict)
    cookie_domains: dict[str, str] = field(default_factory=dict)
    params: dict[str, str] = field(default_factory=dict)
    source: str = "unknown"
    created_at: float = 0.0
    nickname: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = time.time()
        for name in self.cookies:
            self.cookie_domains.setdefault(
                name, SESSION_COOKIE_DOMAINS.get(name, DEFAULT_COOKIE_DOMAIN)
            )

    @property
    def session_id(self) -> str:
        """A short non-reversible identifier, safe to print."""
        import hashlib

        raw = self.cookies.get("sessionid", "")
        if not raw:
            return ""
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]

    @property
    def has_login(self) -> bool:
        return bool(self.cookies.get("sessionid"))

    def slim_cookies(self) -> dict[str, str]:
        """Return the cookies the API needs.

        ``msToken`` and similar device-fingerprint cookies live on
        ``.bytedance.com`` rather than ``.doubao.com``; they are included here
        because their absence is exactly what makes Doubao answer ``710022004``
        (risk control) instead of generating.
        """
        wanted = set(SESSION_COOKIE_NAMES) | set(SESSION_COOKIE_DOMAINS)
        return {k: v for k, v in self.cookies.items() if k in wanted}

    def to_payload(self) -> dict[str, Any]:
        kept = self.slim_cookies()
        return {
            "cookies": kept,
            "cookie_domains": {
                k: v for k, v in self.cookie_domains.items() if k in kept
            },
            "params": self.params,
            "source": self.source,
            "created_at": self.created_at,
            "nickname": self.nickname,
        }

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> Session:
        session = cls(
            cookies={str(k): str(v) for k, v in (payload.get("cookies") or {}).items()},
            params={str(k): str(v) for k, v in (payload.get("params") or {}).items()},
            source=str(payload.get("source") or "unknown"),
            created_at=float(payload.get("created_at") or 0.0),
            nickname=str(payload.get("nickname") or ""),
        )
        stored = payload.get("cookie_domains") or {}
        if isinstance(stored, Mapping):
            session.cookie_domains.update({str(k): str(v) for k, v in stored.items()})
        return session

    @classmethod
    def from_cookie_header(cls, header: str, *, source: str = "cookie-header") -> Session:
        cookies: dict[str, str] = {}
        domains: dict[str, str] = {}
        for item in header.split(";"):
            item = item.strip()
            if not item or "=" not in item:
                continue
            name, value = item.split("=", 1)
            cookies[name.strip()] = value.strip()
        if not cookies.get("sessionid"):
            raise DoubaoConfigError("cookie header does not contain a sessionid")
        for name in cookies:
            domains[name] = SESSION_COOKIE_DOMAINS.get(name, DEFAULT_COOKIE_DOMAIN)
        return cls(cookies=cookies, cookie_domains=domains, source=source)


def default_session_path() -> Path:
    override = os.environ.get("DOUBAO_MEDIA_SESSION")
    if override:
        return Path(override).expanduser()
    return Path(DEFAULT_SESSION_PATH).expanduser()


def save_session(session: Session, path: Path | str | None = None,
                 *, plaintext: bool = False) -> Path:
    """Persist ``session`` (DPAPI-encrypted unless ``plaintext``)."""
    target = Path(path).expanduser() if path else default_session_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(session.to_payload(), ensure_ascii=False).encode("utf-8")
    if plaintext or not _IS_WINDOWS:
        target.write_bytes(raw)
    else:
        target.write_bytes(DPAPI_MAGIC + dpapi_protect(raw))
    with contextlib.suppress(OSError):  # best-effort hardening; never fatal
        os.chmod(target, 0o600)
    return target


def load_session(path: Path | str | None = None) -> Session:
    """Load a session from disk, the environment, or a cookie header env var."""
    header = os.environ.get("DOUBAO_MEDIA_COOKIE", "").strip()
    if header:
        return Session.from_cookie_header(header, source="env:DOUBAO_MEDIA_COOKIE")

    target = Path(path).expanduser() if path else default_session_path()
    if not target.exists():
        raise DoubaoAuthRequired(
            f"no session at {target}; run the doubao-media login flow "
            "(MCP tool `doubao_login_start`) or import browser cookies"
        )
    raw = target.read_bytes()
    if raw.startswith(DPAPI_MAGIC):
        raw = dpapi_unprotect(raw[len(DPAPI_MAGIC):])
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DoubaoConfigError(f"session file {target} is not valid JSON") from exc
    session = Session.from_payload(payload)
    if not session.has_login:
        raise DoubaoAuthRequired(f"session file {target} has no sessionid")
    return session


# ---------------------------------------------------------------------------
# Browser cookie adoption
# ---------------------------------------------------------------------------


def _chromium_master_key(user_data_dir: Path) -> bytes:
    state = json.loads((user_data_dir / "Local State").read_text(encoding="utf-8"))
    encrypted = base64.b64decode(state["os_crypt"]["encrypted_key"])
    if encrypted[:5] == b"DPAPI":
        return dpapi_unprotect(encrypted[5:])
    return encrypted


def _decrypt_chromium_cookie(blob: bytes, key: bytes, host_key: str = "") -> str:
    """Decrypt one Chromium cookie value.

    Current Chromium builds prepend a 32-byte ``SHA256(host_key)`` integrity
    prefix (Chrome 130+, Edge 130+) *after* decryption.  Verified on this
    machine: all 24 Doubao cookies carried that prefix and the digest matched
    the host key exactly.  The prefix is stripped when present so callers always
    receive the usable cookie value.
    """
    import hashlib

    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    if blob[:3] not in (b"v10", b"v11"):
        raise DoubaoConfigError("unsupported Chromium cookie encryption version")
    nonce, ciphertext = blob[3:15], blob[15:]
    raw = AESGCM(key).decrypt(nonce, ciphertext, None)
    if len(raw) > 32 and host_key:
        expected = hashlib.sha256(host_key.encode("utf-8")).digest()
        if raw[:32] == expected:
            raw = raw[32:]
    return raw.decode("utf-8", "replace")


def _is_usable_cookie_value(value: str) -> bool:
    """Cookie values must be header-safe; anything else is a decrypt failure."""
    return bool(value) and all(0x21 <= ord(ch) <= 0x7E for ch in value)


def _is_relevant_cookie_host(host: str, name: str) -> bool:
    """Decide whether a cookie from ``host`` belongs to the Doubao session.

    The Doubao/browser cookie jar also contains unrelated sites (bing, linkedin,
    ...), so the host has to be filtered.  Device-fingerprint cookies such as
    ``msToken`` are stored on ``.bytedance.com`` and must be kept.
    """
    if name in SESSION_COOKIE_DOMAINS:
        return _host_matches(host, SESSION_COOKIE_DOMAINS[name])
    return "doubao.com" in host


def _host_matches(host: str, domain: str) -> bool:
    bare = domain.lstrip(".")
    return host.lstrip(".").endswith(bare)


def _cookie_db_candidates(profile_dir: Path) -> list[Path]:
    return [
        profile_dir / "Default" / "Network" / "Cookies",
        profile_dir / "Default" / "Cookies",
        profile_dir / "Network" / "Cookies",
    ]


def browser_profiles() -> dict[str, Path]:
    """Well-known Chromium profile locations on this machine.

    The Doubao **desktop client** is listed first: when the user is signed in
    there, its profile gives us a session with no extra interaction.
    """
    local = os.environ.get("LOCALAPPDATA", "")
    roaming = os.environ.get("APPDATA", "")
    candidates = {
        "doubao-desktop": Path(local) / "Doubao" / "User Data",
        "edge": Path(local) / "Microsoft" / "Edge" / "User Data",
        "chrome": Path(local) / "Google" / "Chrome" / "User Data",
        "chromium": Path(local) / "Chromium" / "User Data",
        "brave": Path(local) / "BraveSoftware" / "Brave-Browser" / "User Data",
        "vivaldi": Path(local) / "Vivaldi" / "User Data",
        "360chrome": Path(roaming) / "360se6" / "User Data",
    }
    return {name: path for name, path in candidates.items() if path.exists()}


def adopt_browser_session(name: str, profile_dir: Path | str) -> Session:
    """Read a logged-in Doubao session out of a Chromium-based profile.

    Raises :class:`DoubaoConfigError` when the browser is running (its cookie
    database is locked) or no Doubao session is present.
    """
    profile = Path(profile_dir)
    master_key = _chromium_master_key(profile)

    source_db = next((p for p in _cookie_db_candidates(profile) if p.exists()), None)
    if source_db is None:
        raise DoubaoConfigError(f"no cookie database under {profile}")

    tmp = Path(tempfile.gettempdir()) / f"doubao-media-{os.getpid()}-{int(time.time())}.db"
    try:
        shutil.copy2(source_db, tmp)
    except (PermissionError, OSError):
        # A running Chromium holds the database open in share-write mode; a
        # plain byte copy still succeeds and SQLite takes a read lock itself.
        # Only complain when even that fails.
        try:
            tmp.write_bytes(source_db.read_bytes())
        except OSError as exc2:
            raise DoubaoConfigError(
                f"cannot read {source_db}; close {name} completely and retry "
                f"(a running browser may hold an exclusive lock): {exc2}"
            ) from exc2

    cookies: dict[str, str] = {}
    cookie_domains: dict[str, str] = {}
    try:
        connection = sqlite3.connect(tmp)
        try:
            rows = connection.execute(
                "select host_key, name, value, encrypted_value from cookies"
            )
            for host, cname, value, encrypted in rows:
                if not cname or not _is_relevant_cookie_host(host or "", cname):
                    continue
                cookie_domains[cname] = (
                    SESSION_COOKIE_DOMAINS.get(cname, DEFAULT_COOKIE_DOMAIN)
                )
                if value:
                    cookies[cname] = value
                elif encrypted:
                    try:
                        decrypted = _decrypt_chromium_cookie(
                            bytes(encrypted), master_key, host or ""
                        )
                    except Exception:  # noqa: BLE001 - skip undecryptable entries
                        continue
                    if _is_usable_cookie_value(decrypted):
                        cookies[cname] = decrypted
        finally:
            connection.close()
    finally:
        tmp.unlink(missing_ok=True)

    if not cookies.get("sessionid"):
        raise DoubaoConfigError(f"no Doubao login found in the {name} profile")

    cookies = {k: v for k, v in cookies.items() if _is_usable_cookie_value(v)}
    if not cookies.get("sessionid"):
        raise DoubaoConfigError(
            f"Doubao cookies in the {name} profile could not be decrypted "
            "(unsupported encryption scheme or a stale master key)"
        )
    return Session(
        cookies=cookies, cookie_domains=cookie_domains, source=f"browser:{name}"
    )


def discover_session(*, prefer: str | None = None) -> Session:
    """Try every local profile and return the first usable session."""
    profiles = browser_profiles()
    ordered = sorted(profiles.items(), key=lambda kv: 0 if kv[0] == prefer else 1)
    failures: list[str] = []
    for name, path in ordered:
        if prefer and name != prefer and len(ordered) > 1:
            pass  # keep natural order but honour explicit preference first
        try:
            return adopt_browser_session(name, path)
        except DoubaoConfigError as exc:
            failures.append(f"{name}: {exc}")
    raise DoubaoConfigError(
        "no usable Doubao session found locally. " + ("; ".join(failures) or "no profiles")
    )


# ---------------------------------------------------------------------------
# Live session validation
# ---------------------------------------------------------------------------


async def validate_session(cookies: Mapping[str, str], *,
                           transport: httpx.AsyncBaseTransport | None = None
                           ) -> dict[str, Any]:
    """Confirm the cookies still work; returns the subscription entry config."""
    from .transport import DoubaoTransport

    url = BASE_URL + EP_SUBSCRIPTION_ENTRY_CONFIG
    headers = default_headers(cookies)
    try:
        async with httpx.AsyncClient(
            timeout=20.0, transport=transport, headers=headers, follow_redirects=False
        ) as client:
            response = await client.post(
                url, json={"AgwCommonParam": {}}, cookies=dict(cookies)
            )
    except httpx.HTTPError as exc:
        raise DoubaoUpstreamError(f"cannot reach Doubao: {exc}") from exc
    if response.status_code >= 400:
        raise DoubaoUpstreamError(
            f"session validation failed with HTTP {response.status_code}"
        )
    body = response.json()
    DoubaoTransport._raise_for_business_code(body)  # reuse the code mapping
    return body


# ---------------------------------------------------------------------------
# QR login onboarding (pure HTTP, no browser)
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class QrLoginState:
    """Progress of an in-flight QR login."""

    status: str = "idle"          # idle|waiting_scan|scanned|confirmed|expired|error
    message: str = ""
    qr_png_base64: str = ""
    token: str = ""
    session: Session | None = None

    def public(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "message": self.message,
            "qrPngBase64": self.qr_png_base64,
            "sessionId": self.session.session_id if self.session else "",
        }


class QrLogin:
    """Drives ``/passport/web/get_qrcode`` + ``check_qrconnect`` polling."""

    POLL_INTERVAL = 1.5
    TIMEOUT_SECONDS = 180

    def __init__(self, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._transport = transport
        self.state = QrLoginState()
        self._cookies: dict[str, str] = {}
        self._csrf = ""

    async def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=20.0,
            transport=self._transport,
            headers={**default_headers(self._cookies), "Accept": "application/json, text/plain, */*"},
            follow_redirects=False,
        )

    def _absorb(self, response: httpx.Response) -> None:
        for key, value in response.cookies.items():
            if value:
                self._cookies[key] = value

    async def start(self, *, on_progress: ProgressCallback | None = None) -> QrLoginState:
        """Fetch the QR code and publish it; polling continues via :meth:`wait`."""

        def report(status: str, message: str) -> None:
            self.state.status = status
            self.state.message = message
            if on_progress:
                on_progress(status, message)

        try:
            async with await self._client() as client:
                home = await client.get(BASE_URL + "/")
                self._absorb(home)

                self._csrf = (
                    self._cookies.get("passport_csrf_token")
                    or self._cookies.get("passport_csrf_token_default")
                    or ""
                )
                if not self._csrf:
                    csrf_response = await client.get(
                        f"{BASE_URL}/passport/safe/csrf_token/?aid={AID}"
                    )
                    self._absorb(csrf_response)
                    payload = csrf_response.json()
                    self._csrf = (
                        (payload.get("data") or {}).get("passport_csrf_token", "")
                        or self._cookies.get("passport_csrf_token", "")
                    )
                if not self._csrf:
                    raise DoubaoUpstreamError("could not obtain passport_csrf_token")

                headers = {"x-tt-passport-csrf-token": self._csrf}
                qr_response = await client.get(
                    f"{BASE_URL}{EP_LOGIN_QRCODE}",
                    params={"next": BASE_URL, "aid": AID},
                    headers=headers,
                )
                self._absorb(qr_response)
                payload = qr_response.json()
                data = payload.get("data") or {}
                if data.get("error_code", payload.get("error_code", -1)) != 0:
                    raise DoubaoUpstreamError(
                        f"get_qrcode failed: error_code={data.get('error_code')}"
                    )
                self.state.token = str(data.get("token") or "")
                raw_qr = str(data.get("qrcode") or data.get("qrcode_url") or "")
                if not self.state.token:
                    raise DoubaoUpstreamError("QR response carried no token")
                if raw_qr.startswith("data:"):
                    self.state.qr_png_base64 = raw_qr.split(",", 1)[1]
                else:
                    self.state.qr_png_base64 = raw_qr
                report("waiting_scan", "请使用豆包 App 扫码登录")
                return self.state
        except Exception as exc:  # noqa: BLE001 - surfaced as state, not raised
            report("error", f"{type(exc).__name__}: {exc}")
            return self.state

    async def wait(self, *, on_progress: ProgressCallback | None = None,
                   timeout: float | None = None) -> QrLoginState:
        """Poll until the QR code is confirmed, expires, or times out."""
        if self.state.status in ("error", "expired"):
            return self.state
        if not self.state.token:
            return await self.start(on_progress=on_progress)

        deadline = time.monotonic() + (timeout or self.TIMEOUT_SECONDS)
        headers = {"x-tt-passport-csrf-token": self._csrf}
        last = ""
        async with await self._client() as client:
            while time.monotonic() < deadline:
                if self.state.status == "confirmed":
                    break
                try:
                    response = await client.get(
                        f"{BASE_URL}{EP_LOGIN_CHECK}",
                        params={"next": BASE_URL, "token": self.state.token, "aid": AID},
                        headers=headers,
                    )
                    self._absorb(response)
                    payload = response.json()
                except (httpx.HTTPError, ValueError):
                    await asyncio.sleep(2.0)
                    continue

                data = payload.get("data") or {}
                if data.get("error_code", payload.get("error_code", -1)) != 0:
                    description = str(data.get("description", "")).lower()
                    if "expired" in description or "过期" in description:
                        self.state.status = "expired"
                        self.state.message = "二维码已过期，请重新获取"
                        return self.state
                    await asyncio.sleep(2.0)
                    continue

                status = str(data.get("status") or "")
                if status != last:
                    last = status
                    if status == "new":
                        self.state.message = "等待扫码"
                    elif status == "scanned":
                        self.state.status = "scanned"
                        self.state.message = "已扫码，请在手机上确认"
                    if on_progress:
                        on_progress(self.state.status, self.state.message)

                if status == "confirmed":
                    redirect_url = str(data.get("redirect_url") or "")
                    if redirect_url:
                        try:
                            follow = await client.get(redirect_url, follow_redirects=True)
                            self._absorb(follow)
                        except httpx.HTTPError:
                            pass
                    if not self._cookies.get("sessionid"):
                        self.state.status = "error"
                        self.state.message = "登录已确认，但未取得 sessionid"
                        return self.state
                    self.state.session = Session(cookies=dict(self._cookies),
                                                 source="qr-login")
                    self.state.status = "confirmed"
                    self.state.message = "登录成功"
                    if on_progress:
                        on_progress("confirmed", "登录成功")
                    return self.state

                if status == "expired":
                    self.state.status = "expired"
                    self.state.message = "二维码已过期"
                    return self.state

                await asyncio.sleep(self.POLL_INTERVAL)

        if self.state.status != "confirmed":
            self.state.status = "expired"
            self.state.message = "登录超时，请重新获取二维码"
        return self.state
