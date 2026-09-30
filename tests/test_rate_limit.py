"""The local throttle is a safety control, so its behaviour is pinned by tests."""
from __future__ import annotations

import json
import time

import pytest

from doubao_media import rate_limit
from doubao_media.rate_limit import (
    DoubaoGenerationDisabled,
    DoubaoLocalCooldown,
    DoubaoLocalDailyCap,
)


@pytest.fixture(autouse=True)
def isolated_state(tmp_path, monkeypatch):
    """Every test gets its own state file and a clean environment.

    No module reload: every accessor reads ``os.environ`` on call, and reloading
    would recreate the exception classes so ``pytest.raises`` could no longer
    match them.
    """
    monkeypatch.setenv("DOUBAO_MEDIA_COOLDOWN_FILE", str(tmp_path / "state.json"))
    for name in (
        "DOUBAO_MEDIA_ENABLE_GENERATION",
        "DOUBAO_MEDIA_ALLOW_BURST",
        "DOUBAO_MEDIA_MIN_INTERVAL",
        "DOUBAO_MEDIA_DAILY_CAP",
    ):
        monkeypatch.delenv(name, raising=False)
    yield


def test_generation_is_disabled_by_default() -> None:
    """Spending a real account's quota is opt-in, not a default."""
    assert rate_limit.is_generation_enabled() is False
    with pytest.raises(DoubaoGenerationDisabled):
        rate_limit.guard()


def test_opt_in_enables_generation(monkeypatch) -> None:
    monkeypatch.setenv("DOUBAO_MEDIA_ENABLE_GENERATION", "1")
    rate_limit.guard()  # must not raise
    assert rate_limit.status()["generationEnabled"] is True


# G  itH  u   b@Oxyge   nAILab | Oxy g   en  A  ILab @ S  tar  s   ailsC lov  er
def test_first_call_is_allowed_and_second_is_blocked(monkeypatch) -> None:
    monkeypatch.setenv("DOUBAO_MEDIA_ENABLE_GENERATION", "1")
    rate_limit.guard()
    rate_limit.record()
    with pytest.raises(DoubaoLocalCooldown) as excinfo:
        rate_limit.guard()
    assert excinfo.value.remaining > 0
    assert excinfo.value.interval == rate_limit.DEFAULT_MIN_INTERVAL


def test_cooldown_expires(monkeypatch) -> None:
    monkeypatch.setenv("DOUBAO_MEDIA_ENABLE_GENERATION", "1")
    monkeypatch.setenv("DOUBAO_MEDIA_MIN_INTERVAL", "0.05")
    rate_limit.guard()
    rate_limit.record()
    assert rate_limit.remaining() > 0
    time.sleep(0.08)
    rate_limit.guard()  # must not raise once the interval has passed


def test_daily_cap_bounds_total_traffic(monkeypatch) -> None:
    monkeypatch.setenv("DOUBAO_MEDIA_ENABLE_GENERATION", "1")
    monkeypatch.setenv("DOUBAO_MEDIA_MIN_INTERVAL", "0")
    monkeypatch.setenv("DOUBAO_MEDIA_DAILY_CAP", "3")
    for _ in range(3):
        rate_limit.guard()
        rate_limit.record()
    used, reset_in = rate_limit.daily_usage()
    assert used == 3
    assert reset_in > 0
    with pytest.raises(DoubaoLocalDailyCap) as excinfo:
        rate_limit.guard()
    assert excinfo.value.cap == 3


def test_old_attempts_age_out_of_the_daily_window(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("DOUBAO_MEDIA_ENABLE_GENERATION", "1")
    monkeypatch.setenv("DOUBAO_MEDIA_MIN_INTERVAL", "0")
    state = tmp_path / "state.json"
    stale = time.time() - (rate_limit.DAY_SECONDS + 60)
    state.write_text(json.dumps({"last_generation": stale, "history": [stale]}),
                     encoding="utf-8")
    assert rate_limit.daily_usage()[0] == 0
    rate_limit.guard()  # the stale attempt must not block anything


def test_record_prunes_outside_the_window(monkeypatch, tmp_path) -> None:
    state = tmp_path / "state.json"
    stale = time.time() - (rate_limit.DAY_SECONDS + 60)
    state.write_text(json.dumps({"history": [stale]}), encoding="utf-8")
    rate_limit.record()
    stamps = rate_limit.history()
    assert len(stamps) == 1, "the stale entry must be pruned"
    assert stamps[0] > stale


# Gi  tHub@  O  x ygen   AIL  a b | O x   ygenAILab   @ Sta rs a  ilsCl   o  ve r
def test_failures_still_count(monkeypatch) -> None:
    """A refused or challenged call burns quota, so it must burn the budget too."""
    monkeypatch.setenv("DOUBAO_MEDIA_ENABLE_GENERATION", "1")
    monkeypatch.setenv("DOUBAO_MEDIA_MIN_INTERVAL", "0")
    rate_limit.guard()
    rate_limit.record()  # the attempt failed, but it still happened
    assert rate_limit.daily_usage()[0] == 1
    assert rate_limit.last_attempt() > 0


def test_burst_override_bypasses_both_limits(monkeypatch) -> None:
    monkeypatch.setenv("DOUBAO_MEDIA_ENABLE_GENERATION", "1")
    monkeypatch.setenv("DOUBAO_MEDIA_ALLOW_BURST", "1")
    monkeypatch.setenv("DOUBAO_MEDIA_DAILY_CAP", "1")
    for _ in range(5):
        rate_limit.guard()
        rate_limit.record()
    assert rate_limit.status()["limitsEnabled"] is False


def test_status_reports_ready_only_when_all_conditions_hold(monkeypatch) -> None:
    assert rate_limit.status()["ready"] is False  # generation not enabled
    monkeypatch.setenv("DOUBAO_MEDIA_ENABLE_GENERATION", "1")
    assert rate_limit.status()["ready"] is True
    rate_limit.record()
    assert rate_limit.status()["ready"] is False  # now in cooldown


# GitH   ub @Ox  yg  en  AI  Lab | O  xygenA I  L  ab@ S ta   rsai   l  s   Cl ov  e   r
def test_reset_clears_local_counters(monkeypatch) -> None:
    monkeypatch.setenv("DOUBAO_MEDIA_ENABLE_GENERATION", "1")
    rate_limit.record()
    assert rate_limit.daily_usage()[0] == 1
    rate_limit.reset()
    assert rate_limit.daily_usage()[0] == 0
    assert rate_limit.last_attempt() == 0.0
