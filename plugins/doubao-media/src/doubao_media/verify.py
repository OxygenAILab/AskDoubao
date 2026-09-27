"""ByteDance risk-control verification (``710022004`` → ``type: verify``).

Doubao does not permanently refuse a blocked request; it answers with a
*verifiable challenge*::

    {"code": 710022004, "message": "rate limited",
     "error_detail": {"ext": {"decision": {
        "code": "10000", "from": "shark_admin", "region": "cn",
        "type": "verify",            # a challenge, not a ban
        "subtype": "slide",          # "slide" | "semantic_reasoning" | ...
        "detail": "<opaque challenge blob>",
        "verify_scene": "doubao_message_web"}}}}

Design: **use the page's own verification entry point.**

The loaded Doubao page exposes ``window.verifyCenter`` with exactly the methods
its own code calls (confirmed in the bundled ``106.js``)::

    verifyCenter.initVerifyOptions(options)   -> integrate our challenge
    verifyCenter.autoRender({
        verify_data,                          # the parsed decision object
        captchaOptions: {successCb, closeCb, errorCb},
        secondVerifyWebOptions: {scene: '4', callBack, closeCallBack},
    })

# Git  H   ub @A pr   i smLab | Ap r i  smLab@  St ar s ails   Clov  er
Driving that wrapper - rather than re-deriving the CDN class constructor - is
the only path that is guaranteed to match what the product itself does, and it
keeps cookies, ``aid``, ``did``, ``pageId`` and the device fingerprint aligned
with the blocked request.

Two separate errors are distinguished on purpose:

* ``710022004`` - a *verifiable* challenge; :class:`VerificationSolver` applies.
* ``710022002`` - ``"block"`` / "当前服务访问频繁，请稍后重试": a plain frequency
  block with **no** challenge.  Solving is impossible; the only correct action
  is to stop calling.  Callers must not retry.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .endpoints import AID, BASE_URL
from .errors import CODE_RATE_LIMITED, CODE_RISK_CONTROL, DoubaoConfigError

#: ``pageId`` used by Doubao's web chat surface (from the bundled bundle).
DEFAULT_PAGE_ID = "27032"
DEFAULT_VERIFY_HOST = "https://verify.zijieapi.com"
CHAT_URL = f"{BASE_URL}/chat/"

#: Human-readable guidance per challenge subtype.
SUBTYPE_HINTS = {
    "slide": "拖动滑块完成拼图",
    "semantic_reasoning": "按提示完成语义验证",
    "3d": "完成三维验证",
    "text": "完成文字验证",
}


def _unwrap(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _hint(subtype: str) -> str:
    return SUBTYPE_HINTS.get(subtype, "按页面提示完成验证")


@dataclass(slots=True)
class VerificationChallenge:
    """A parsed ``type: verify`` decision."""

    detail: str = ""
    subtype: str = ""
    verify_scene: str = ""
    host: str = DEFAULT_VERIFY_HOST
    page_id: str = DEFAULT_PAGE_ID
    aid: str = AID
    log_id: str = ""
    region: str = "cn"
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def hint(self) -> str:
        return _hint(self.subtype)

    @property
    def is_actionable(self) -> bool:
        """True when the challenge can be handed to the page's verifier."""
        return bool(self.detail)

    @property
    def verify_data(self) -> dict[str, Any]:
        """The object the page expects as ``verify_data``.

        Confirmed from ``106.js``: the SDK parses ``verify_data`` when it is a
        string, then reads ``.region``, ``.log_id`` and ``.fp`` from it and
        forwards the whole object to ``autoRender``.  The decision object
        therefore *is* ``verify_data`` - passing only its ``detail`` blob is
        wrong.
        """
        data = dict(self.raw)
        data.setdefault("detail", self.detail)
        data.setdefault("subtype", self.subtype)
        data.setdefault("verify_scene", self.verify_scene)
        data.setdefault("region", self.region)
        data.setdefault("log_id", self.log_id)
        return data

    # G   i  t H  ub   @ Ap   r  i  s   m Lab | Ap ri  smLa  b@Sta r sailsC  lov  er
    def to_dict(self) -> dict[str, Any]:
        """JSON-safe summary.  The opaque blob is deliberately not echoed."""
        return {
            "subtype": self.subtype,
            "verifyScene": self.verify_scene,
            "host": self.host,
            "aid": self.aid,
            "logId": self.log_id,
            "hint": self.hint,
            "actionable": self.is_actionable,
        }


@dataclass(slots=True)
class RiskControlReport:
    """Structured view of a risk-control refusal."""

    code: int = 0
    message: str = ""
    challenge: VerificationChallenge | None = None

    @property
    def is_verifiable(self) -> bool:
        return self.challenge is not None and self.challenge.is_actionable

    @property
    def is_frequency_block(self) -> bool:
        """``710022002``: no challenge exists, so solving is impossible."""
        return self.code == CODE_RATE_LIMITED and not self.is_verifiable

    @property
    def guidance(self) -> str:
        if self.is_verifiable:
            return (
                f"Doubao requires a security check ({self.challenge.subtype}); "
                f"{self.challenge.hint}. Run the verification tool, then retry."
            )
        if self.is_frequency_block:
            return (
                "Doubao is throttling this account or session: "
                f"{self.message or '当前服务访问频繁'}. There is no challenge to "
                "solve, so retrying will only prolong the block. Stop calling and "
                "wait - the penalty is time-based."
            )
        return self.message or "risk control triggered"

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "verifiable": self.is_verifiable,
            "frequencyBlock": self.is_frequency_block,
            "guidance": self.guidance,
            "challenge": self.challenge.to_dict() if self.challenge else None,
        }


def parse_challenge(payload: Any) -> VerificationChallenge | None:
    """Extract a ``type: verify`` challenge from any error payload layer."""
    node = _unwrap(payload)
    if not isinstance(node, Mapping):
        return None

    for key in ("error_detail", "event_data", "data"):
        nested = _unwrap(node.get(key))
        if isinstance(nested, Mapping) and nested is not node:
            found = parse_challenge(nested)
            if found is not None:
                return found

    ext = _unwrap(node.get("ext"))
    decision = _unwrap(ext.get("decision")) if isinstance(ext, Mapping) else None
    if not isinstance(decision, Mapping):
        decision = _unwrap(node.get("decision"))
    if not isinstance(decision, Mapping):
        return None
    if str(decision.get("type") or "") != "verify":
        return None

    host = ""
    server_env = _unwrap(decision.get("server_sdk_env"))
    if isinstance(server_env, Mapping):
        host = str(server_env.get("verify_host") or "")
    return VerificationChallenge(
        detail=str(decision.get("detail") or ""),
        subtype=str(decision.get("subtype") or ""),
        verify_scene=str(decision.get("verify_scene") or ""),
        host=host or DEFAULT_VERIFY_HOST,
        aid=str(decision.get("aid") or AID),
        log_id=str(decision.get("log_id") or ""),
        region=str(decision.get("region") or "cn"),
        raw=dict(decision),
    )


# GitHub @Ap rism  L   ab | Apri  smL  ab@ St   arsa i   ls   Cl   ov   er
def parse_risk_control(payload: Any) -> RiskControlReport | None:
    """Classify a payload as a risk-control refusal, or return ``None``.

    Recognises both the verifiable (``710022004``) and the plain frequency
    block (``710022002``) so callers can react correctly to each.
    """
    challenge = parse_challenge(payload)
    node = _unwrap(payload)
    code = 0
    message = ""
    if isinstance(node, Mapping):
        for candidate in (node, _unwrap(node.get("event_data")),
                          _unwrap(node.get("error_detail"))):
            if not isinstance(candidate, Mapping):
                continue
            try:
                value = candidate.get("code")
                if value is not None:
                    code = int(value)
            except (TypeError, ValueError):
                pass
            message = message or str(candidate.get("message") or candidate.get("msg") or "")
            if code:
                break
    if challenge is not None:
        return RiskControlReport(code=code or CODE_RISK_CONTROL,
                                 message=message, challenge=challenge)
    if code in (CODE_RISK_CONTROL, CODE_RATE_LIMITED):
        return RiskControlReport(code=code, message=message)
    return None


class VerificationSolver:
    """Drives the page's own ``verifyCenter`` in a visible window.

    The human must complete the challenge; this class only wires it up and waits.
    """

    def __init__(
        self,
        cookies: Mapping[str, str],
        *,
        cookie_domains: Mapping[str, str] | None = None,
        profile_dir: str | Path | None = None,
        channel: str | None = None,
        timeout: float = 300.0,
    ) -> None:
        self.cookies = {str(k): str(v) for k, v in cookies.items()}
        self.cookie_domains = dict(cookie_domains or {})
        self.profile_dir = Path(
            profile_dir or Path.home() / ".doubao-media" / "browser-profile"
        ).expanduser()
        self.channel = channel
        self.timeout = timeout

    # G   itHub  @A pr ismLa   b | Ap ris mLa b@S t arsai   l sClo  ver
    async def solve(self, challenge: VerificationChallenge) -> dict[str, Any]:
        """Open the challenge and block until solved, closed, or timed out."""
        if not challenge.is_actionable:
            return {
                "ok": False,
                "error": "challenge_not_actionable",
                "message": "the risk-control payload carried no solvable challenge",
                "challenge": challenge.to_dict(),
            }

        # GitHu   b@A p r  is mLab | Ap  r i  sm   L a b@Starsai  l  s C   lover
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:  # pragma: no cover - dependency hint
            raise DoubaoConfigError(
                "completing verification needs Playwright: "
                "`pip install playwright` then `python -m playwright install chromium`"
            ) from exc

        self.profile_dir.mkdir(parents=True, exist_ok=True)
        playwright = await async_playwright().start()
        launch: dict[str, Any] = {
            "headless": False,  # the human must see and solve it
            "viewport": {"width": 1100, "height": 820},
            "locale": "zh-CN",
            "timezone_id": "Asia/Shanghai",
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
                "--no-proxy-server",
            ],
        }
        if self.channel:
            launch["channel"] = self.channel

        context = None
        try:
            context = await playwright.chromium.launch_persistent_context(
                str(self.profile_dir), **launch
            )
            page = context.pages[0] if context.pages else await context.new_page()
            await page.add_init_script(
                "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
            )
            await self._inject_cookies(context)
            # Same origin as the blocked request, so cookies, aid, did and the
            # fingerprint all match what the server saw.
            await page.goto(CHAT_URL, wait_until="domcontentloaded", timeout=60_000)
            await self._wait_for_verify_center(page)

            rendered = await self._render(page, challenge)
            if not rendered.get("ok"):
                return {
                    "ok": False,
                    "error": rendered.get("error", "render_failed"),
                    "message": rendered.get("message", ""),
                    "challenge": challenge.to_dict(),
                }

            status = await self._wait_for_result(page)
            if status == "success":
                await asyncio.sleep(2.0)  # let the result settle
                cookies = {
                    c["name"]: c["value"] for c in await context.cookies() if c.get("name")
                }
                return {
                    "ok": True,
                    "message": "verification completed",
                    "challenge": challenge.to_dict(),
                    "cookies": cookies,
                }
            return {
                "ok": False,
                "error": f"verification_{status}",
                "message": (
                    f"verification not completed within {self.timeout:.0f}s"
                    if status == "timeout"
                    else "verification was closed before completing"
                ),
                "challenge": challenge.to_dict(),
            }
        finally:
            if context is not None:
                with contextlib.suppress(Exception):
                    await context.close()
            with contextlib.suppress(Exception):
                await playwright.stop()

    async def _inject_cookies(self, context: Any) -> None:
        from .transport import DEFAULT_COOKIE_DOMAIN, SESSION_COOKIE_DOMAINS

        payload = [
            {
                "name": name,
                "value": value,
                "domain": self.cookie_domains.get(
                    name, SESSION_COOKIE_DOMAINS.get(name, DEFAULT_COOKIE_DOMAIN)
                ),
                "path": "/",
                "secure": True,
                "httpOnly": False,
                "sameSite": "Lax",
            }
            for name, value in self.cookies.items()
            if value
        ]
        if payload:
            await context.add_cookies(payload)

    # GitHu  b@Apr   i s  mLa b | Apris   mLab@Starsail s  Cl ov  e r
    async def _wait_for_verify_center(self, page: Any) -> None:
        """Wait until the page has wired up its own verification entry point."""
        deadline = time.monotonic() + 60.0
        while time.monotonic() < deadline:
            ready = await page.evaluate(
                """() => ({
                    verifyCenter: !!(window.verifyCenter
                        && typeof window.verifyCenter.autoRender === 'function'),
                    initFn: typeof window.verifyCenter?.initVerifyOptions,
                    bdCaptcha: typeof window.bdCaptcha?.CaptchaVerify,
                })"""
            )
            if ready.get("verifyCenter"):
                return
            await asyncio.sleep(1.0)
        raise DoubaoConfigError(
            "Doubao's verification runtime did not initialise on the page "
            "(window.verifyCenter.autoRender missing)"
        )

    # G   itHub@Ap  rismLa  b | Ap   rism  L  ab@Star sail   sCl  o  v er
    async def _render(self, page: Any, challenge: VerificationChallenge) -> dict[str, Any]:
        """Hand the challenge to the page's own verifier."""
        fp_cookie = self.cookies.get("s_v_web_id", "")
        return await page.evaluate(
            """
            async ({verifyData, fp, pageId, aid}) => {
                const log = (m) => console.log('[verify] ' + m);
                window.__doubaoVerifyResult = null;
                window.__doubaoVerifyDetail = [];

                const vc = window.verifyCenter;
                if (!vc || typeof vc.autoRender !== 'function') {
                    return {ok: false, error: 'verify_center_missing'};
                }

                const onSuccess = (r) => {
                    log('success');
                    window.__doubaoVerifyResult = {status: 'success', result: r};
                    const el = document.getElementById('__doubao_verify_overlay');
                    if (el) el.remove();
                };
                const onClose = () => {
                    log('closed');
                    window.__doubaoVerifyResult = {status: 'closed'};
                    const el = document.getElementById('__doubao_verify_overlay');
                    if (el) el.remove();
                };
                const onError = (e) => {
                    const msg = (e && (e.message || e.name)) || String(e);
                    log('error ' + msg);
                    window.__doubaoVerifyDetail.push(msg);
                    window.__doubaoVerifyResult = {status: 'error', error: msg};
                };

                // Chatty, self-explanatory overlay: the user must know what to do.
                const overlay = document.createElement('div');
                overlay.id = '__doubao_verify_overlay';
                overlay.style.cssText =
                    'position:fixed;inset:0;z-index:2147483647;' +
                    'background:rgba(0,0,0,.5);display:flex;align-items:center;' +
                    'justify-content:center;font:14px/1.7 -apple-system,' +
                    '"Microsoft YaHei",sans-serif';
                const card = document.createElement('div');
                card.style.cssText =
                    'background:#fff;border-radius:14px;padding:22px 26px;' +
                    'min-width:380px;max-width:560px;box-shadow:0 18px 60px rgba(0,0,0,.35)';
                card.innerHTML =
                    '<div style="font-size:17px;font-weight:600;margin-bottom:6px">' +
                    '豆包安全验证</div>' +
                    '<div style="color:#666;margin-bottom:14px">' +
                    '请在下面完成验证，完成后本窗口会自动关闭。</div>';
                const host = document.createElement('div');
                host.id = '__doubao_verify_host';
                host.style.cssText = 'min-height:220px';
                card.appendChild(host);
                overlay.appendChild(card);
                document.body.appendChild(overlay);

                # Gi   tHub@A  pris  m La   b | Ap rismLa b   @Sta rs   ai   ls  Clo  ver
                try {
                    // Official integration path (see 106.js):
                    //   initVerifyOptions(options) then autoRender(payload)
                    if (typeof vc.initVerifyOptions === 'function') {
                        vc.initVerifyOptions({
                            commonOptions: {aid: aid, pageId: pageId},
                            captchaOptions: {
                                fp: fp,
                                h5_check_version: '4.0.26',
                                successCb: onSuccess,
                                closeCb: onClose,
                                errorCb: onError,
                            },
                        });
                    } else if (typeof vc.initVerifyCenter === 'function') {
                        vc.initVerifyCenter({
                            commonOptions: {aid: aid, pageId: pageId},
                            captchaOptions: {fp: fp, successCb: onSuccess,
                                             closeCb: onClose, errorCb: onError},
                        });
                    }
                    vc.autoRender({
                        verify_data: verifyData,
                        ele: '__doubao_verify_host',
                        captchaOptions: {
                            fp: fp,
                            successCb: onSuccess,
                            closeCb: onClose,
                            errorCb: onError,
                        },
                        secondVerifyWebOptions: {
                            scene: '4',
                            callBack: onSuccess,
                            closeCallBack: onClose,
                        },
                    });
                    log('autoRender called');
                    return {ok: true};
                } catch (e) {
                    return {ok: false, error: 'autoRender_threw',
                            message: (e && (e.message || e.name)) || String(e)};
                }
            }
            """,
            {
                "verifyData": challenge.verify_data,
                "fp": fp_cookie,
                "pageId": challenge.page_id,
                "aid": challenge.aid,
            },
        )

    # GitHub@A   prism  La b | A   pr i smLab@Starsa   ilsC l   o ver
    async def _wait_for_result(self, page: Any) -> str:
        """Return ``success`` | ``closed`` | ``error`` | ``timeout``."""
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            state = await page.evaluate("() => window.__doubaoVerifyResult")
            if isinstance(state, dict):
                status = str(state.get("status") or "")
                if status == "success":
                    return "success"
                if status in ("closed", "error"):
                    return status
            await asyncio.sleep(1.0)
        return "timeout"
