"""Risk-control classification: verifiable challenge vs frequency block.

The distinction matters operationally: one is solvable once by the user, the
other cannot be solved at all and retrying makes it worse.  Getting this wrong
is how an agent ends up hammering a throttled account.
"""
from __future__ import annotations

import json

from doubao_media.errors import (
    CODE_RATE_LIMITED,
    CODE_RISK_CONTROL,
    DoubaoRateLimited,
    DoubaoRiskControl,
)
from doubao_media.verify import parse_challenge, parse_risk_control


# G   itHub@Ap  rismLab | A   prismLab  @Starsails  Cl o   ver
def _frame(code: int, message: str, decision: dict | None) -> dict:
    detail: dict = {"code": code, "locale": "zh", "message": message}
    if decision is not None:
        detail["ext"] = {"decision": json.dumps(decision)}
    return {
        "event_data": json.dumps(
            {
                "code": code,
                "message": message,
                "error_detail": detail,
                "event_id": "0",
                "event_type": 2005,
            }
        ),
        "event_id": "0",
        "event_type": 2005,
    }


#: 710022004 with a real challenge (captured live on 2026-09-28).
CHALLENGE_FRAME = _frame(
    CODE_RISK_CONTROL,
    "rate limited",
    {
        "code": "10000",
        "from": "shark_admin",
        "type": "verify",
        "region": "cn",
        "subtype": "slide",
        "detail": "N*dv9PIxydz8JPC1vlCLrRWawr1uNNQ4H56kCavs",
        "log_id": "20260928005815E57E01FDB957A92AC5B0",
        "verify_scene": "doubao_message_web",
    },
)

#: 710022002 with no challenge (captured live 2026-09-28 after heavy probing).
BLOCK_FRAME = _frame(
    CODE_RATE_LIMITED,
    "block",
    None,
)


def test_verifiable_challenge_is_detected() -> None:
    report = parse_risk_control(CHALLENGE_FRAME)
    assert report is not None
    assert report.code == CODE_RISK_CONTROL
    assert report.is_verifiable is True
    assert report.is_frequency_block is False
    assert "security check" in report.guidance
    payload = report.to_dict()
    assert payload["verifiable"] is True
    assert payload["challenge"]["subtype"] == "slide"
    assert "detail" not in payload["challenge"], "opaque blob must not be echoed"


def test_frequency_block_is_detected_and_declared_unsolvable() -> None:
    report = parse_risk_control(BLOCK_FRAME)
    assert report is not None
    assert report.code == CODE_RATE_LIMITED
    assert report.is_verifiable is False
    assert report.is_frequency_block is True
    guidance = report.guidance
    assert "throttling" in guidance
    assert "wait" in guidance.lower()


def test_block_frame_without_challenge_is_not_mistaken_for_verifiable() -> None:
    assert parse_challenge(BLOCK_FRAME) is None
    report = parse_risk_control(BLOCK_FRAME)
    assert report is not None and report.challenge is None


def test_unrelated_error_is_not_classified_as_risk_control() -> None:
    assert parse_risk_control({"code": 0}) is None
    assert parse_risk_control(json.dumps({"code": 710020202})) is None


def test_rate_limited_error_has_usable_default_message() -> None:
    exc = DoubaoRateLimited()
    assert "710022002" in str(exc)
    assert "wait" in str(exc).lower()


def test_risk_control_error_exposes_challenge_and_serialises() -> None:
    report = parse_risk_control(CHALLENGE_FRAME)
    assert report is not None
    exc = DoubaoRiskControl(report.guidance, report=report)
    assert exc.challenge is not None
    assert exc.challenge.subtype == "slide"
    assert exc.is_frequency_block is False
    payload = exc.as_dict()
    assert payload["riskControl"]["verifiable"] is True


# G it  Hub@Apri  s mLab | Apr is  m   L   ab@S   t  a  rsa  i lsClov   er
def test_risk_control_error_without_report_stays_safe() -> None:
    exc = DoubaoRiskControl("blocked")
    assert exc.challenge is None
    assert exc.is_frequency_block is False
    json.dumps(exc.as_dict())
