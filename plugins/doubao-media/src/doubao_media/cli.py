"""Command-line interface for the Doubao media bridge.

Mirrors the MCP tool surface so the same operations can be scripted and tested
without an agent in the loop::

    doubao-media login [--profile NAME]
    doubao-media status [--json]
    doubao-media watermark [--set on|off] [--confirm]
    doubao-media image "一只猫" --ratio 1:1 --out ./out
    doubao-media video "一只猫在跑" --duration 5 --out ./out

Scope is image and video generation only, matching the MCP server.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from .errors import DoubaoError
from .models import WatermarkRequest
from .pipeline import MediaPipeline
from .session import (
    QrLogin,
    discover_session,
    load_session,
    save_session,
)


def _resolve_session(*, profile: str | None = None) -> Any:
    try:
        return load_session()
    except DoubaoError:
        return discover_session(prefer=profile or "doubao-desktop")


def _dump(payload: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    if not isinstance(payload, dict):
        print(payload)
        return
    for key, value in payload.items():
        if isinstance(value, (dict, list)):
            print(f"{key}:")
            print(json.dumps(value, ensure_ascii=False, indent=2))
        else:
            print(f"{key}: {value}")


async def _cmd_login(args: argparse.Namespace) -> int:
    if args.profile:
        try:
            session = discover_session(prefer=args.profile)
            path = save_session(session)
            print(f"adopted {session.source} -> {path}")
            return 0
        except DoubaoError as exc:
            print(f"browser adoption failed: {exc}")
    login = QrLogin()
    state = await login.start(on_progress=lambda s, m: print(f"[{s}] {m}"))
    if state.status == "error":
        print(f"error: {state.message}")
        return 1
    qr_path = Path("doubao-login-qr.png")
    import base64

    qr_path.write_bytes(base64.b64decode(state.qr_png_base64))
    print(f"scan this QR code with the Doubao app: {qr_path.resolve()}")
    state = await login.wait(on_progress=lambda s, m: print(f"[{s}] {m}"),
                             timeout=args.timeout)
    if state.status != "confirmed" or state.session is None:
        print(f"login did not complete: {state.status} ({state.message})")
        return 1
    path = save_session(state.session)
    print(f"login confirmed; session saved to {path}")
    qr_path.unlink(missing_ok=True)
    return 0


async def _cmd_status(args: argparse.Namespace) -> int:
    session = _resolve_session(profile=args.profile)
    async with MediaPipeline.from_cookies(session.slim_cookies()) as pipeline:
        plan = await pipeline.plan_status(near_limit_threshold=args.threshold)
        watermark = await pipeline.client.get_watermark_config()
        payload = plan.to_dict()
        payload["watermark"] = watermark.to_dict()
        payload["sessionSource"] = session.source
        _dump(payload, args.json)
    return 0


async def _cmd_watermark(args: argparse.Namespace) -> int:
    session = _resolve_session(profile=args.profile)
    async with MediaPipeline.from_cookies(session.slim_cookies()) as pipeline:
        if args.set is None:
            _dump(
                {"ok": True, **(
                    await pipeline.client.get_watermark_config()
                ).to_dict()},
                args.json,
            )
            return 0
        enable = args.set == "off"  # --set off means "remove the watermark"
        if enable and not args.confirm:
            print(
                "refusing to remove the watermark without --confirm: the official "
                "UI makes the user accept responsibility first "
                "(设置 -> 内容生成与产物设置 -> AI 生成水印管理)"
            )
            return 2
        config = await pipeline.client.set_watermark_removed(enable)
        mirror = "skipped"
        try:
            await pipeline.client.set_creation_watermark(enable)
            mirror = "ok"
        except DoubaoError as exc:
            mirror = f"failed: {exc}"
        _dump({"ok": True, "creationMirror": mirror, **config.to_dict()}, args.json)
    return 0


async def _cmd_generate(args: argparse.Namespace) -> int:
    session = _resolve_session(profile=args.profile)
    request = WatermarkRequest.create(
        "restore" if args.restore_watermark else ("remove" if args.no_watermark else "keep"),
        confirm=args.confirm,
        restore_after=args.restore_watermark,
    )
    reference = Path(args.reference).read_bytes() if args.reference else None
    mode = "http" if args.no_browser else "auto"
    async with MediaPipeline.from_session(
        session, transport_mode=mode, headless=not args.show_browser
    ) as pipeline:
        if args.kind == "image":
            outcome = await pipeline.generate_image(
                args.prompt,
                ratio=args.ratio,
                count=args.count,
                reference_image=reference,
                watermark=request,
                download_dir=args.out,
                timeout=args.timeout,
            )
        else:
            outcome = await pipeline.generate_video(
                args.prompt,
                ratio=args.ratio,
                duration=args.duration,
                resolution=args.resolution,
                camera_movement=args.camera,
                reference_image=reference,
                watermark=request,
                download_dir=args.out,
                timeout=args.timeout,
            )
        _dump({"ok": True, **outcome.to_dict()}, args.json)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="doubao-media", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--profile", help="preferred browser profile for adoption")
    sub = parser.add_subparsers(dest="command", required=True)

    login = sub.add_parser("login", help="adopt a browser session or scan a QR code")
    login.add_argument("--timeout", type=float, default=180.0)
    login.set_defaults(func=_cmd_login)

    status = sub.add_parser("status", help="plan, quota and watermark status")
    status.add_argument("--json", action="store_true")
    status.add_argument("--threshold", type=float, default=90.0,
                        help="usage percentage that counts as 'running low'")
    status.set_defaults(func=_cmd_status)

    watermark = sub.add_parser("watermark", help="read or change the watermark opt-out")
    watermark.add_argument("--set", choices=["on", "off"],
                           help="on = keep the watermark, off = remove it")
    watermark.add_argument("--confirm", action="store_true",
                           help="required when removing the watermark")
    watermark.add_argument("--json", action="store_true")
    watermark.set_defaults(func=_cmd_watermark)

    for kind, help_text in (("image", "generate an image"),
                            ("video", "generate a video")):
        gen = sub.add_parser(kind, help=help_text)
        gen.add_argument("prompt")
        gen.add_argument("--ratio", required=False)
        gen.add_argument("--out", default=str(Path.home() / "Documents" / "DoubaoMedia"))
        gen.add_argument("--reference", help="local image for image-to-image/video")
        gen.add_argument("--no-watermark", action="store_true",
                         help="remove the AI watermark for this run (needs --confirm)")
        gen.add_argument("--restore-watermark", action="store_true",
                         help="remove for this run, then restore the previous state")
        gen.add_argument("--confirm", action="store_true",
                         help="user has agreed to the watermark opt-out")
        gen.add_argument("--no-browser", action="store_true",
                         help="plain HTTP only (faster, may trip risk control)")
        gen.add_argument("--show-browser", action="store_true",
                         help="run the browser transport with a visible window")
        gen.add_argument("--json", action="store_true")
        gen.set_defaults(func=_cmd_generate, kind=kind)
        if kind == "image":
            gen.add_argument("--count", type=int, default=1)
        else:
            gen.add_argument("--duration", type=int)
            gen.add_argument("--resolution")
            gen.add_argument("--camera")
        gen.add_argument("--timeout", type=float,
                         default=180.0 if kind == "image" else 420.0)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return asyncio.run(args.func(args))
    except DoubaoError as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        if getattr(exc, "payload", None):
            print(json.dumps(exc.payload, ensure_ascii=False)[:600], file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
