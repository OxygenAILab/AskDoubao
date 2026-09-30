"""ByteDance risk-control verification (``710022004`` -> ``type: verify``).

Doubao answers a blocked request with a *verifiable challenge*, not a ban::

    {"code": 710022004, "message": "rate limited",
     "error_detail": {"ext": {"decision": {
        "code": "10000", "from": "shark_admin", "region": "cn",
        "type": "verify",            # a challenge, not a ban
        "subtype": "slide",          # "slide" | "semantic_reasoning" | ...
        "detail": "<opaque challenge blob>",
        "verify_scene": "doubao_message_web",
        "log_id": "..."}}}}

The blob is consumed by ByteDance's own captcha SDK, which the page already
loads as ``window.verifySDK``.  Reproducing signatures would be the wrong layer;
rendering the official widget and letting the account holder solve it is the
right one, and it is also what clears the state for the session.

Getting the call right (each of these was found the hard way):

1. Target ``window.verifySDK``, not ``window.bdCaptcha.CaptchaVerify`` (the raw
   CDN class) and not ``window.verifyCenter`` (an inert wrapper whose
   ``myOptions.options`` stays ``{}`` - calling it is a silent no-op).
2. Call ``renderCaptcha(options)`` **with ``aid`` at the top level**.  Its source
   does ``if (e.aid) c = e; else c = merge(myOptions)``, so a top-level ``aid``
   makes the SDK adopt our options wholesale.  Going through
   ``initVerifyOptions`` + ``autoRender`` instead merges into the page's empty
   defaults and silently mounts nothing.
3. ``aid`` must be a **number**; a string throws
   ``"The parameter aid is required and of type int"``, which ``autoRender``
   catches and rethrows as the misleading ``"verify_data is required"``.
4. Supply ``did`` (device id).  The SDK otherwise queries
   ``/vc/setting?...&did=0&iid=0`` and never renders.
5. The container needs a **definite size**: the rendered card is ``h-full w-full``,
   so a container sized only with ``min-height`` collapses it to 0x0 - mounted
   but invisible.
6. ``renderCaptcha`` short-circuits while ``window.__vc_is_render__`` is truthy.

Two separate errors are distinguished on purpose:

* ``710022004`` - a *verifiable* challenge; :class:`VerificationSolver` applies.
* ``710022002`` - ``"block"`` / "当前服务访问频繁，请稍后重试": a plain frequency
  block with **no** challenge.  Nothing can be solved; the only correct action is
  to stop calling.
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

# Git H u b@  O   xyge  nA  IL  ab | Oxyge  nAIL   a  b   @ Stars  ailsC lov er
# GitH   ub@  Oxyg   enAI Lab | Ox y g enA   ILab@St arsailsClo   v e   r
DEFAULT_PAGE_ID = "27032"
DEFAULT_VERIFY_HOST = "https://verify.zijieapi.com"
CHAT_URL = f"{BASE_URL}/chat/"

#: Official captcha SDK bundles, in fallback order.  The product loads one of
#: these and then talks to the resulting ``window.verifySDK`` object (see the
#: bundled ``106.js`` and ``s2-security-verify.js``).
SDK_URLS = (
    "https://lf-rc1.yhgfb-cn-static.com/obj/rc-verifycenter/rmc-captcha/1.0.0.739/captcha.js",
    "https://lf-rc2.yhgfb-cn-static.com/obj/rc-verifycenter/rmc-captcha/1.0.0.739/captcha.js",
    "https://lf-cdn-tos.bytescm.com/obj/rc-verifycenter/rmc-captcha/1.0.0.739/captcha.js",
)

#: Human-readable guidance per challenge subtype.
SUBTYPE_HINTS = {
    "slide": "拖动滑块完成拼图",
    "semantic_reasoning": "按提示完成语义验证",
    "3d": "完成三维验证",
    "text": "完成文字验证",
}

#: Container size for the challenge.  ``verifySDK.setting`` reports 300x303 for
#: the CN region; a little headroom keeps the widget comfortably visible.
CONTAINER_WIDTH = 340
CONTAINER_HEIGHT = 340

#: Kept as a module-level constant so it can be syntax-checked with
#: ``node --check`` (see ``_scratch/extract_js.py``).  Inline JS inside a Python
#: triple-quoted string is otherwise impossible to lint, and a single bad
#: character only surfaces as a runtime ``SyntaxError`` from ``page.evaluate``.
VERIFY_DRIVE_JS = r"""
async ({verifyData, fp, pageId, aid, did, width, height, hint}) => {
    const log = (m) => console.log('[verify] ' + m);
    window.__doubaoVerifyResult = null;
    window.__doubaoVerifyDetail = [];
    window.__doubaoVerifyNodes = [];

    const observer = new MutationObserver((records) => {
        for (const rec of records) {
            for (const node of rec.addedNodes) {
                if (node.nodeType !== 1) continue;
                const rect = node.getBoundingClientRect();
                window.__doubaoVerifyNodes.push({
                    tag: node.tagName, id: node.id || null,
                    src: node.src ? String(node.src).slice(0, 120) : null,
                    w: Math.round(rect.width), h: Math.round(rect.height),
                });
            }
        }
    });
    observer.observe(document.body, {childList: true, subtree: true});

    const overlay = document.createElement('div');
    overlay.id = '__doubao_verify_overlay';
    overlay.style.cssText = [
        'position:fixed', 'inset:0', 'z-index:2147483647',
        'background:rgba(15,23,42,.55)', 'display:flex',
        'align-items:center', 'justify-content:center',
        "font:14px/1.7 -apple-system,'Microsoft YaHei',sans-serif",
    ].join(';');

    const card = document.createElement('div');
    card.style.cssText = [
        'background:#fff', 'border-radius:16px', 'padding:24px 28px',
        'box-shadow:0 20px 60px rgba(0,0,0,.35)', 'display:flex',
        'flex-direction:column', 'gap:12px', 'align-items:center',
    ].join(';');

    const title = document.createElement('div');
    title.style.cssText = 'font-size:17px;font-weight:600;color:#111';
    title.textContent = 'Doubao security check';

    const subtitle = document.createElement('div');
    subtitle.style.cssText =
        'font-size:13px;color:#666;max-width:440px;text-align:center';
    subtitle.textContent =
        'Complete the check below; this window closes by itself when done.'
        + (hint ? ' (' + hint + ')' : '');

    // Definite size: the rendered widget is h-full w-full, so a container with
    // only min-height mounts the challenge invisibly at 0x0.
    const host = document.createElement('div');
    host.id = '__doubao_verify_host';
    host.style.cssText =
        'width:' + width + 'px;height:' + height + 'px;flex:0 0 auto';

    card.appendChild(title);
    card.appendChild(subtitle);
    card.appendChild(host);
    overlay.appendChild(card);
    document.body.appendChild(overlay);

    const onSuccess = (r) => {
        log('success');
        window.__doubaoVerifyResult = {status: 'success', result: r};
        overlay.remove();
    };
    const onClose = () => {
        log('closed');
        window.__doubaoVerifyResult = {status: 'closed'};
        overlay.remove();
    };
    const onError = (e) => {
        const msg = (e && (e.message || e.name)) || String(e);
        log('error ' + msg);
        window.__doubaoVerifyDetail.push(msg);
        window.__doubaoVerifyResult = {status: 'error', error: msg};
    };

    const sdk = window.verifySDK;
    if (!sdk || typeof sdk.renderCaptcha !== 'function') {
        return {ok: false, error: 'verify_sdk_missing',
                sdk: !!sdk, verifyCenter: !!window.verifyCenter};
    }
    // renderCaptcha returns early while this flag is truthy.
    window.__vc_is_render__ = false;

    try {
        sdk.renderCaptcha({
            aid: aid,                 // top-level aid => SDK adopts these options
            did: did,
            pageId: pageId,
            verify_data: verifyData,
            ele: '__doubao_verify_host',
            captchaOptions: {
                fp: fp,
                did: did,
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
    } catch (e) {
        return {ok: false, error: 'renderCaptcha_threw',
                message: (e && (e.message || e.name)) || String(e)};
    }
    return {ok: true, strategy: 'renderCaptcha'};
}
"""


# GitHub  @  Ox  y   gen AILa  b | Oxy   ge   nAILa   b   @  Starsa   ilsClov   er
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
        """The object the SDK consumes as ``verify_data``.

        The SDK parses ``verify_data`` when it is a string, then reads
        ``.region``, ``.log_id`` and ``.fp`` from it, and ``autoRender`` routes
        on ``.code`` (``10000`` -> the slider branch).  The decision object
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

    # GitHu   b@ Ox   y   gen   AIL  ab | O x   ygenAILa  b@   Star s   ai   l   sCl   o  ve   r
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
            challenge = self.challenge
            assert challenge is not None
            return (
                f"Doubao requires a security check ({challenge.subtype}); "
                f"{challenge.hint}. Run the verification tool, then retry once."
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


# G  itHu  b@OxygenAI  L  a   b | OxygenAI La b  @   Stars   ail s C   lover
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
            message = message or str(
                candidate.get("message") or candidate.get("msg") or ""
            )
            if code:
                break
    if challenge is not None:
        return RiskControlReport(
            code=code or CODE_RISK_CONTROL, message=message, challenge=challenge
        )
    if code in (CODE_RISK_CONTROL, CODE_RATE_LIMITED):
        return RiskControlReport(code=code, message=message)
    return None


# G  i  tHu  b@O x   ygen   AI  La  b | O   xy  genAI Lab@S   ta   r sa  i   lsClove  r
class VerificationSolver:
    """Renders the official challenge in a visible window for the user to solve."""

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

    async def solve(self, challenge: VerificationChallenge) -> dict[str, Any]:
        """Open the challenge and block until solved, closed, or timed out."""
        if not challenge.is_actionable:
            return {
                "ok": False,
                "error": "challenge_not_actionable",
                "message": "the risk-control payload carried no solvable challenge",
                "challenge": challenge.to_dict(),
            }

        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:  # pragma: no cover - dependency hint
            raise DoubaoConfigError(
                "completing verification needs Playwright: "
                "`pip install playwright` then `python -m playwright install chromium`"
            ) from exc

        # G it   H  u  b@  OxygenA ILab | Oxygen AILa b@S   ta rs   a i   lsC  lov   er
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
            await self._wait_for_verify_sdk(page)

            rendered = await self._render(page, challenge)
            if not rendered.get("ok"):
                return {
                    "ok": False,
                    "error": str(rendered.get("error", "render_failed")),
                    "message": str(rendered.get("message", "")),
                    "challenge": challenge.to_dict(),
                }

            status = await self._wait_for_result(page)
            if status == "success":
                await asyncio.sleep(2.0)  # let the result settle
                cookies = {
                    c["name"]: c["value"]
                    for c in await context.cookies()
                    if c.get("name")
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

        # G itHub   @   Oxyge  n  A   ILa  b | O   x y ge   n A   I   L ab@   S   t a rs  a  i lsC lo   ver
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

    async def _wait_for_verify_sdk(self, page: Any) -> None:
        """Wait until the page exposes the captcha SDK it loads itself."""
        deadline = time.monotonic() + 60.0
        while time.monotonic() < deadline:
            ready = await page.evaluate(
                """() => ({
                    verifySDK: !!(window.verifySDK
                        && typeof window.verifySDK.renderCaptcha === 'function'),
                    bdCaptcha: typeof window.bdCaptcha?.CaptchaVerify,
                })"""
            )
            if ready.get("verifySDK"):
                return
            await asyncio.sleep(1.0)
        raise DoubaoConfigError(
            "the Doubao page did not expose window.verifySDK.renderCaptcha"
        )

    async def _device_id(self, page: Any) -> str:
        """Read the site's own device id, so ``vc/setting`` is not asked with 0."""
        try:
            found = await page.evaluate(
                """() => {
                    try {
                        const sam = JSON.parse(
                            localStorage.getItem('samantha_web_web_id') || '{}');
                        if (sam.web_id) return String(sam.web_id);
                    } catch (e) {}
                    try {
                        const tea = JSON.parse(
                            localStorage.getItem('__tea_cache_tokens_497858') || '{}');
                        if (tea.web_id) return String(tea.web_id);
                    } catch (e) {}
                    return '0';
                }"""
            )
        except Exception:  # noqa: BLE001 - best effort
            return "0"
        return str(found or "0")

    # Git Hub@Oxyg  enA IL   ab | OxygenAILab @ St  a rs   ailsC lover
    async def _render(self, page: Any, challenge: VerificationChallenge) -> dict[str, Any]:
        """Mount the challenge through the official ``window.verifySDK``."""
        return await page.evaluate(
            VERIFY_DRIVE_JS,
            {
                "verifyData": challenge.verify_data,
                "fp": self.cookies.get("s_v_web_id", ""),
                "pageId": challenge.page_id,
                # renderCaptcha validates ``typeof aid === 'number'``.
                "aid": int(challenge.aid or AID),
                "did": await self._device_id(page),
                "width": CONTAINER_WIDTH,
                "height": CONTAINER_HEIGHT,
                "hint": challenge.hint,
            },
        )

    # G  i   tHub   @OxygenAILab | O x  y g enA  ILab @St a  rs ail sClover
    async def _wait_for_result(self, page: Any) -> str:
        """Return ``success`` | ``closed`` | ``error`` | ``timeout``.

        Also treats "the widget vanished without reporting" as closed, so a user
        dismissing the challenge cannot leave the caller hanging.
        """
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            state = await page.evaluate(
                """() => ({
                    result: window.__doubaoVerifyResult,
                    overlay: !!document.getElementById('__doubao_verify_overlay'),
                })"""
            )
            result = state.get("result") if isinstance(state, dict) else None
            if isinstance(result, dict):
                status = str(result.get("status") or "")
                if status == "success":
                    return "success"
                if status in ("closed", "error"):
                    return status
            if isinstance(state, dict) and state.get("overlay") is False:
                return "closed"
            await asyncio.sleep(1.0)
        return "timeout"
