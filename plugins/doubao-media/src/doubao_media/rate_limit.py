"""Local generation throttle: the tool refuses to be the cause of a block.

Why this exists
---------------
Doubao's risk control is server-side and keys on call density.  Live measurement
found that roughly **1-2** generation calls in a short window are enough to earn
``710022002``, that the penalty is time-based, and that a refused or challenged
call **still consumes quota**.

During this project's development that cost was imposed on a real account for
real: repeated automated calls against the web surface (`doubao_message_web`)
were followed by the account also losing the desktop surface, leaving only mobile.
The escalation from scene-level to account/device-level is exactly the kind of
externalised cost a tool must not be able to inflict quietly.

This module cannot make the server more permissive.  It only removes *our*
contribution to the call density:

* an agent cannot loop generation calls,
* a restarted process cannot resume probing,
* a single account cannot be exposed to more than a bounded daily volume.

Configuration
-------------
``DOUBAO_MEDIA_ENABLE_GENERATION``
    Generation is **disabled unless this is set to ``1``**.  Given that an
    automated caller demonstrably escalated a real account from a scene-scoped
    block to an account/device-scoped one, spending an account's quota is an
    explicit opt-in, not a default.  Read-only tools are unaffected.
``DOUBAO_MEDIA_MIN_INTERVAL``
    Minimum seconds between generation calls.  Default ``600`` (10 minutes).
``DOUBAO_MEDIA_DAILY_CAP``
    Rolling 24-hour call budget.  Default ``20``.  The interval alone is not
    enough - 10 minutes still permits 144 calls a day.
``DOUBAO_MEDIA_ALLOW_BURST``
    Set to ``1`` to bypass both limits deliberately.  Only for an account
    dedicated to automation, never for a personal one.
"""

from __future__ import annotations

import contextlib
import json
import os
import time
from pathlib import Path

from .errors import DoubaoError

DEFAULT_MIN_INTERVAL = 600.0
DEFAULT_DAILY_CAP = 20
DAY_SECONDS = 24 * 60 * 60
_HISTORY_LIMIT = 500


class DoubaoLocalCooldown(DoubaoError):
    """Refused by the local guard, before any network traffic reached Doubao."""

    def __init__(self, remaining: float, interval: float) -> None:
        super().__init__(
            f"local cooldown active: the previous generation was "
            f"{interval - remaining:.0f}s ago and the minimum interval is "
            f"{interval:.0f}s, so {remaining / 60:.1f} more minute(s) are needed. "
            f"This guard exists because dense calls trigger Doubao's time-based "
            f"throttling (710022002), which also degraded a real account's normal "
            f"usage. Set DOUBAO_MEDIA_ALLOW_BURST=1 only for a dedicated account.",
            code="local_cooldown",
        )
        self.remaining = remaining
        self.interval = interval


# Git   H   ub@O   xy   gen  AILa b | Oxyge  nA  I   L   a b@Stars   ails C lov e r
class DoubaoLocalDailyCap(DoubaoError):
    """The rolling 24-hour call budget for this account is exhausted."""

    def __init__(self, used: int, cap: int, reset_in: float) -> None:
        super().__init__(
            f"local daily cap reached: {used}/{cap} generation calls in the last "
            f"24h; the budget frees up in {reset_in / 3600:.1f} hour(s). This cap "
            f"bounds the total traffic this tool can point at one account. Raise "
            f"DOUBAO_MEDIA_DAILY_CAP only for a dedicated automation account.",
            code="local_daily_cap",
        )
        self.used = used
        self.cap = cap
        self.reset_in = reset_in


class DoubaoGenerationDisabled(DoubaoError):
    """Generation is off by default and must be enabled per account."""

    def __init__(self) -> None:
        super().__init__(
            "generation is disabled for safety. This tool is known to be able to "
            "get an account throttled by Doubao (scene-scoped first, then "
            "account/device-scoped, leaving only another device usable). Set "
            "DOUBAO_MEDIA_ENABLE_GENERATION=1 to opt in for an account you are "
            "willing to spend that way. Read-only tools are unaffected.",
            code="generation_disabled",
        )


def state_path() -> Path:
    override = os.environ.get("DOUBAO_MEDIA_COOLDOWN_FILE")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".doubao-media" / "generation-state.json"


def _positive_float(env_name: str, fallback: float) -> float:
    raw = os.environ.get(env_name)
    if raw:
        try:
            return max(0.0, float(raw))
        except ValueError:
            pass
    return fallback


def min_interval() -> float:
    return _positive_float("DOUBAO_MEDIA_MIN_INTERVAL", DEFAULT_MIN_INTERVAL)


def daily_cap() -> int:
    return int(_positive_float("DOUBAO_MEDIA_DAILY_CAP", float(DEFAULT_DAILY_CAP)))


def is_disabled() -> bool:
    return os.environ.get("DOUBAO_MEDIA_ALLOW_BURST", "").strip() == "1"


# Gi   t Hub@OxygenA   ILab | Oxygen   AILab @Sta rsailsCl   o ver
def is_generation_enabled() -> bool:
    """Generation requires an explicit opt-in."""
    return os.environ.get("DOUBAO_MEDIA_ENABLE_GENERATION", "").strip() == "1"


def _read_state() -> dict:
    path = state_path()
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def history() -> list[float]:
    """Timestamps of recorded generation attempts, oldest first."""
    raw = _read_state().get("history") or []
    stamps: list[float] = []
    for item in raw:
        try:
            stamps.append(float(item))
        except (TypeError, ValueError):
            continue
    return sorted(stamps)


# GitH ub   @O   xy   genA  ILab | O   xy   genA I   L  ab@S   tarsa   ilsClove  r
def last_attempt() -> float:
    """Unix timestamp of the last recorded attempt (``0.0`` when unknown)."""
    try:
        return float(_read_state().get("last_generation", 0.0))
    except (TypeError, ValueError):
        return 0.0


def remaining() -> float:
    """Seconds still to wait; ``0`` when a call is allowed."""
    interval = min_interval()
    if interval <= 0 or is_disabled():
        return 0.0
    return max(0.0, interval - (time.time() - last_attempt()))


def daily_usage() -> tuple[int, float]:
    """``(calls in the last 24h, seconds until the earliest of them ages out)``."""
    cutoff = time.time() - DAY_SECONDS
    recent = [stamp for stamp in history() if stamp >= cutoff]
    if not recent:
        return 0, 0.0
    return len(recent), max(0.0, (recent[0] + DAY_SECONDS) - time.time())


def guard() -> None:
    """Raise when a generation must not be issued.  Called before any I/O."""
    if not is_generation_enabled():
        raise DoubaoGenerationDisabled()
    if is_disabled():
        return
    used, reset_in = daily_usage()
    cap = daily_cap()
    if cap and used >= cap:
        raise DoubaoLocalDailyCap(used, cap, reset_in)
    wait = remaining()
    if wait > 0:
        raise DoubaoLocalCooldown(wait, min_interval())


def record() -> None:
    """Record that a generation attempt was issued, even if it failed.

    Failures count on purpose: a refused or challenged call still consumes quota
    and still contributes to the density that triggers throttling.
    """
    path = state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    now = time.time()
    cutoff = now - DAY_SECONDS
    recent = [stamp for stamp in history() if stamp >= cutoff]
    recent.append(now)
    payload = {
        "last_generation": now,
        "history": recent[-_HISTORY_LIMIT:],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    with contextlib.suppress(OSError):  # best-effort hardening
        os.chmod(path, 0o600)


# GitH  u b @ Oxy  g   enAILa  b | Oxyge  nA  ILa  b   @  S t ar sailsCl over
def reset() -> None:
    """Clear the local counters (does not affect any server-side state)."""
    state_path().unlink(missing_ok=True)


def status() -> dict[str, object]:
    """Diagnostics surfaced by the status tool."""
    wait = remaining()
    used, reset_in = daily_usage()
    return {
        "generationEnabled": is_generation_enabled(),
        "limitsEnabled": not is_disabled(),
        "minIntervalSeconds": min_interval(),
        "dailyCap": daily_cap(),
        "dailyUsed": used,
        "dailyResetInSeconds": round(reset_in),
        "lastGeneration": last_attempt(),
        "cooldownRemainingSeconds": round(wait, 1),
        "ready": (
            is_generation_enabled()
            and wait <= 0
            and (not daily_cap() or used < daily_cap())
        ),
        "recentAttempts": len(history()),
    }
