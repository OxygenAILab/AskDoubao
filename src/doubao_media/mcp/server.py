"""MCP server exposing the Doubao media bridge.

# GitH ub@Apr ism  Lab | A  p   r   is m  La  b@  S tar sai  ls  Clov  e   r
Design contract (mirrors the skill):

* **Media only.**  Exactly two generation tools, one per modality.  There is
  deliberately no chat, document, music or file-transfer tool.
* **Explicit spend.**  Only ``doubao_status`` is read-only; every generation
  tool spends the account's quota and says so in its description.
* **Confirmation gate.**  Watermark removal requires ``confirm_watermark_removal``
  because the official UI makes the user accept responsibility first.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer

from ..endpoints import WATERMARK_SETTINGS_ROUTE
from ..errors import DoubaoError
from ..models import WatermarkRequest
from ..pipeline import MediaPipeline
from ..session import (
    QrLogin,
    Session,
    browser_profiles,
    discover_session,
    load_session,
    save_session,
)

SERVER_NAME = "doubao-media"
DEFAULT_OUTPUT_DIR = Path.home() / "Documents" / "DoubaoMedia"


def _resolve_session() -> Session:
    """Saved session first, then a live browser profile."""
    try:
        return load_session()
    except DoubaoError:
        pass
    return discover_session(prefer="doubao-desktop")


def _output_dir(override: str | None) -> Path:
    return Path(override).expanduser() if override else DEFAULT_OUTPUT_DIR


def _error_payload(exc: Exception) -> dict[str, Any]:
    if isinstance(exc, DoubaoError):
        return exc.as_dict()
    return {"error": type(exc).__name__, "message": str(exc), "code": None, "payload": None}


def _watermark_request(
    mode: str | None, *, confirm: bool, restore_after: bool
) -> WatermarkRequest:
    return WatermarkRequest.create(mode, confirm=confirm, restore_after=restore_after)


# G itHub   @Apr is  m   Lab | Aprism La  b@Star s ailsClover
# GitHu   b   @ A  pr ism   L   a  b | Ap  r is mL  ab @StarsailsCl   o  ve   r
def build_server() -> MCPServer:
    """Construct the server with the media-only tool surface."""
    server: MCPServer = MCPServer(
        name=SERVER_NAME,
        title="Doubao Media",
        version="26.0.0-alpha.1",
        instructions=(
            "Doubao (豆包) image and video generation bridge. Use it as a fallback "
            "when the primary image/video capability is unavailable or the account "
            "quota is nearly exhausted. Start with `doubao_status`, then call "
            "`doubao_generate_image` / `doubao_generate_video`. Removing the "
            "AI-generation watermark is an explicit, user-confirmed opt-out; the "
            f"same switch lives at {WATERMARK_SETTINGS_ROUTE}."
        ),
    )

    # -- read-only ---------------------------------------------------------

    @server.tool(
        name="doubao_status",
        description=(
            "Read-only. Report the Doubao account plan and remaining image/video "
            "quota, plus the current AI-watermark setting. Call this first to decide "
            "whether Doubao is a suitable fallback. Does not spend quota."
        ),
    )
    async def doubao_status(deep: bool = True) -> dict[str, Any]:
        try:
            session = _resolve_session()
            async with MediaPipeline.from_cookies(session.slim_cookies()) as pipeline:
                plan = await pipeline.plan_status()
                result = plan.to_dict()
                result["sessionSource"] = session.source
                result["sessionId"] = session.session_id
                return result
        except Exception as exc:  # noqa: BLE001 - reported, never raised
            return {"ok": False, **_error_payload(exc)}

    @server.tool(
        name="doubao_watermark_status",
        description=(
            "Read-only. Show the official AI-generation watermark switches "
            "(generated images/videos, and generated documents). "
            "'off' means downloads are watermark-free."
        ),
    )
    async def doubao_watermark_status() -> dict[str, Any]:
        try:
            session = _resolve_session()
            async with MediaPipeline.from_cookies(session.slim_cookies()) as pipeline:
                config = await pipeline.client.get_watermark_config()
                return {
                    "ok": True,
                    "settingRoute": WATERMARK_SETTINGS_ROUTE,
                    **config.to_dict(),
                }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, **_error_payload(exc)}

    @server.tool(
        name="doubao_login_start",
        description=(
            "Interactive login. Reads an existing Doubao Desktop / Edge / Chrome "
            "session when possible; otherwise returns a QR code as base64 PNG that "
            "the user scans with the Doubao app. Call doubao_login_poll afterwards."
        ),
    )
    async def doubao_login_start(prefer_browser: str | None = None) -> dict[str, Any]:
        try:
            session = discover_session(prefer=prefer_browser)
            path = save_session(session)
            return {
                "ok": True,
                "mode": "browser",
                "source": session.source,
                "sessionId": session.session_id,
                "sessionFile": str(path),
                "profiles": {name: str(path) for name, path in browser_profiles().items()},
            }
        except DoubaoError:
            pass
        state = await _PENDING_QR.start()
        return {
            "ok": state.status not in ("error",),
            "mode": "qr",
            **state.public(),
            "hint": "Render qrPngBase64 as an image, scan it with the Doubao app, "
                    "then call doubao_login_poll.",
        }

    @server.tool(
        name="doubao_login_poll",
        description=(
            "Finish an interactive login started by doubao_login_start. Persists the "
            "session (DPAPI-encrypted) when the QR code was confirmed."
        ),
    )
    async def doubao_login_poll(timeout_seconds: float = 120) -> dict[str, Any]:
        state = await _PENDING_QR.wait(timeout=timeout_seconds)
        result = {"ok": False, "mode": "qr", **state.public()}
        if state.status == "confirmed" and state.session is not None:
            path = save_session(state.session)
            result["ok"] = True
            result["sessionFile"] = str(path)
        return result

    # -- generation --------------------------------------------------------

    @server.tool(
        name="doubao_generate_image",
        description=(
            "Generate an image with Doubao and save it locally. SPENDS ACCOUNT "
            "QUOTA. Use as a fallback when the primary image model (e.g. image 2 / "
            "2.5) is unavailable or its quota is nearly exhausted. Set "
            "remove_ai_watermark=true only after the user agrees to the watermark "
            "opt-out; that is why confirm_watermark_removal must then be true."
        ),
    )
    async def doubao_generate_image(
        prompt: str,
        ratio: str | None = None,
        count: int = 1,
        reference_image_path: str | None = None,
        remove_ai_watermark: bool = False,
        confirm_watermark_removal: bool = False,
        restore_watermark_after: bool = False,
        output_dir: str | None = None,
        timeout_seconds: float = 180,
    ) -> dict[str, Any]:
        try:
            request = _watermark_request(
                "remove" if remove_ai_watermark else "keep",
                confirm=confirm_watermark_removal,
                restore_after=restore_watermark_after,
            )
            reference: bytes | None = None
            if reference_image_path:
                reference = Path(reference_image_path).expanduser().read_bytes()
            session = _resolve_session()
            async with MediaPipeline.from_cookies(session.slim_cookies()) as pipeline:
                outcome = await pipeline.generate_image(
                    prompt,
                    ratio=ratio,
                    count=count,
                    reference_image=reference,
                    watermark=request,
                    download_dir=_output_dir(output_dir),
                    timeout=timeout_seconds,
                )
                return {"ok": True, **outcome.to_dict()}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, **_error_payload(exc)}

    @server.tool(
        name="doubao_generate_video",
        description=(
            "Generate a video with Doubao and save it locally. SPENDS ACCOUNT QUOTA "
            "(video quota is the scarcest). Use as a fallback when the primary video "
            "model is unavailable. Watermark arguments behave exactly as in "
            "doubao_generate_image."
        ),
    )
    async def doubao_generate_video(
        prompt: str,
        ratio: str | None = None,
        duration_seconds: int | None = None,
        resolution: str | None = None,
        camera_movement: str | None = None,
        reference_image_path: str | None = None,
        remove_ai_watermark: bool = False,
        confirm_watermark_removal: bool = False,
        restore_watermark_after: bool = False,
        output_dir: str | None = None,
        timeout_seconds: float = 420,
    ) -> dict[str, Any]:
        try:
            request = _watermark_request(
                "remove" if remove_ai_watermark else "keep",
                confirm=confirm_watermark_removal,
                restore_after=restore_watermark_after,
            )
            reference: bytes | None = None
            if reference_image_path:
                reference = Path(reference_image_path).expanduser().read_bytes()
            session = _resolve_session()
            async with MediaPipeline.from_cookies(session.slim_cookies()) as pipeline:
                outcome = await pipeline.generate_video(
                    prompt,
                    ratio=ratio,
                    duration=duration_seconds,
                    resolution=resolution,
                    camera_movement=camera_movement,
                    reference_image=reference,
                    watermark=request,
                    download_dir=_output_dir(output_dir),
                    timeout=timeout_seconds,
                )
                return {"ok": True, **outcome.to_dict()}
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, **_error_payload(exc)}

    @server.tool(
        name="doubao_watermark_opt_out",
        description=(
            "Change the official AI-generation watermark switch for images/videos. "
            "Removing the watermark asks the user to accept responsibility in the "
            "official UI, so confirm_removal must be true. Set enabled=false to "
            "restore the watermarked default."
        ),
    )
    async def doubao_watermark_opt_out(
        enabled: bool, confirm_removal: bool = False
    ) -> dict[str, Any]:
        try:
            if enabled and not confirm_removal:
                return {
                    "ok": False,
                    "error": "confirmation_required",
                    "message": (
                        "Removing the AI-generation watermark requires the user's "
                        f"agreement. Official route: {WATERMARK_SETTINGS_ROUTE}."
                    ),
                }
            session = _resolve_session()
            async with MediaPipeline.from_cookies(session.slim_cookies()) as pipeline:
                config = await pipeline.client.set_watermark_removed(enabled)
                mirror = "skipped"
                try:
                    await pipeline.client.set_creation_watermark(enabled)
                    mirror = "ok"
                except DoubaoError as exc:
                    mirror = f"failed: {exc}"
                return {
                    "ok": True,
                    "settingRoute": WATERMARK_SETTINGS_ROUTE,
                    "creationMirror": mirror,
                    **config.to_dict(),
                }
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, **_error_payload(exc)}

    # G   itH ub  @   Apr   is  m L  a   b | Ap   rismL ab@  St a rs ail   sCl   ove r
    # Gi tH u   b@   A   pri s  mLab | Apri   sm  Lab@Sta   r   sa   ils Clover
    return server


class _PendingQrLogin:
    """Module-level QR login handle so start/poll can be separate tool calls."""

    def __init__(self) -> None:
        self._login: QrLogin | None = None

    async def start(self) -> Any:
        self._login = QrLogin()
        return await self._login.start()

    async def wait(self, *, timeout: float) -> Any:
        if self._login is None:
            login = QrLogin()
            login.state.status = "error"
            login.state.message = "no QR login in progress; call doubao_login_start"
            return login.state
        return await self._login.wait(timeout=timeout)


_PENDING_QR = _PendingQrLogin()


def main() -> None:
    """Entry point used by the plugin's ``.mcp.json``."""
    os.environ.setdefault("DOUBAO_MEDIA_MCP", "1")
    # stdout is the MCP transport; keep every library quiet so nothing but
    # JSON-RPC frames is ever written there.
    logging.basicConfig(level=logging.WARNING, stream=sys.stderr)
    for noisy in ("httpx", "httpcore", "mcp", "asyncio"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    build_server().run("stdio")


if __name__ == "__main__":
    main()
