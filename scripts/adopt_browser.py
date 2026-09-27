"""Adopt a Doubao session from a local Chromium-based browser profile.

Usage:
    python scripts/adopt_browser.py [browser ...]

``browser`` may be any key from ``browser_profiles()``; with no arguments every
detected profile is tried and the first usable one wins.

Note: a running Chromium keeps an exclusive lock on its cookie database.  Close
the browser first (the Doubao desktop client is handled automatically by
``scripts/refresh_session.py``).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from doubao_media.errors import DoubaoConfigError  # noqa: E402
from doubao_media.session import (  # noqa: E402
    adopt_browser_session,
    browser_profiles,
    save_session,
)


def main(argv: list[str]) -> int:
    profiles = browser_profiles()
    if not profiles:
        print("no Chromium-based profiles detected")
        return 2
    wanted = argv or sorted(profiles)
    failures: list[str] = []
    for name in wanted:
        if name not in profiles:
            failures.append(f"{name}: not detected")
            continue
        try:
            session = adopt_browser_session(name, profiles[name])
        except DoubaoConfigError as exc:
            failures.append(f"{name}: {exc}")
            continue
        path = save_session(session)
        slim = session.slim_cookies()
        print(
            f"{name}: OK  cookies={len(session.cookies)} kept={len(slim)} "
            f"msToken={'yes' if 'msToken' in slim else 'no'} "
            f"session={session.session_id} -> {path}"
        )
        return 0
    for failure in failures:
        print(f"  {failure}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
