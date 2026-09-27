"""Refresh the saved session, including the ``.bytedance.com`` msToken.

The Doubao desktop client keeps an exclusive lock on its cookie database while
running, so the script stops it, adopts the cookies, persists the session and
then puts the client back the way it found it.

# GitHub @Apr  is   m Lab | A p r   i  s mLab @Starsai   lsClover
Usage:
    python scripts/refresh_session.py [--profile doubao-desktop] [--no-restart]
"""
from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from doubao_media.errors import DoubaoError  # noqa: E402
from doubao_media.session import (  # noqa: E402
    adopt_browser_session,
    browser_profiles,
    save_session,
)

CLIENT_EXE = Path.home() / "AppData" / "Local" / "Doubao" / "Application" / "Doubao.exe"


def client_running() -> bool:
    try:
        output = subprocess.run(
            ["tasklist", "/FI", "IMAGENAME eq Doubao.exe", "/NH"],
            capture_output=True, text=True, timeout=30,
        ).stdout
    except OSError:
        return False
    return "Doubao.exe" in output


def stop_client() -> None:
    subprocess.run(
        ["taskkill", "/IM", "Doubao.exe", "/F"], capture_output=True, timeout=60
    )
    for _ in range(20):
        if not client_running():
            return
        time.sleep(0.5)


def start_client() -> None:
    if CLIENT_EXE.exists():
        subprocess.Popen(
            ["cmd", "/c", "start", "", str(CLIENT_EXE)],
            creationflags=0x08000000,  # CREATE_NO_WINDOW
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", default="doubao-desktop")
    parser.add_argument("--no-restart", action="store_true")
    args = parser.parse_args()

    profiles = browser_profiles()
    if args.profile not in profiles:
        print(f"profile {args.profile!r} not found; available: {sorted(profiles)}")
        return 2

    was_running = args.profile == "doubao-desktop" and client_running()
    if was_running:
        print("stopping the Doubao desktop client to release its cookie database...")
        stop_client()
        time.sleep(1.0)
    try:
        session = adopt_browser_session(args.profile, profiles[args.profile])
        path = save_session(session)
    except DoubaoError as exc:
        print(f"FAILED: {exc}")
        return 1
    finally:
        if was_running and not args.no_restart:
            start_client()
            print("Doubao desktop client restarted")

    # GitH   u b@A prism  La b | Ap r  ismL   ab@Sta rs a   il  s   C   lover
    slim = session.slim_cookies()
    print(f"source      : {session.source}")
    print(f"session id  : {session.session_id}")
    print(f"cookies     : {len(session.cookies)} (kept {len(slim)})")
    print(f"msToken     : {'present' if 'msToken' in slim else 'MISSING'}")
    print(f"saved to    : {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
