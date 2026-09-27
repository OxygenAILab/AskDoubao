"""Read-only live check of the Doubao media bridge against a real account.

Nothing here mutates account state: it only logs in from a local browser
profile and reads the plan / watermark / quota views.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from doubao_media import errors  # noqa: E402
from doubao_media.client import DoubaoMediaClient  # noqa: E402
from doubao_media.session import Session, discover_session, load_session  # noqa: E402
from doubao_media.transport import DoubaoTransport  # noqa: E402


async def main() -> int:
    print("== 1. session discovery ==")
    session: Session | None = None
    try:
        session = load_session()
        print("  loaded saved session")
    except errors.DoubaoError as exc:
        print(f"  no saved session ({type(exc).__name__}); discovering browser profile")
    if session is None:
        try:
            session = discover_session(prefer="doubao-desktop")
        except errors.DoubaoConfigError as exc:
            print(f"  FAILED: {exc}")
            return 1
    print(f"  source={session.source} id={session.session_id} "
          f"cookies={len(session.cookies)}")

    transport = DoubaoTransport(session.slim_cookies())
    client = DoubaoMediaClient(transport)
    async with client:
        print("\n== 2. watermark config (read-only) ==")
        try:
            config = await client.get_watermark_config()
            print(f"  image/video={config.ai_generated_image_video.value} "
                  f"document={config.ai_generated_document.value}")
        except errors.DoubaoError as exc:
            print(f"  {type(exc).__name__}: {exc}")

        print("\n== 3. membership (cheap) ==")
        status = await client.get_membership(deep=False)
        print(json.dumps(status.to_dict(), ensure_ascii=False, indent=2)[:1800])

        print("\n== 4. membership (deep: quota endpoints) ==")
        deep = await client.get_membership(deep=True)
        print(json.dumps(
            {"imageQuota": deep.image_quota, "videoQuota": deep.video_quota,
             "warnings": deep.warnings},
            ensure_ascii=False, indent=2)[:2000])
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
