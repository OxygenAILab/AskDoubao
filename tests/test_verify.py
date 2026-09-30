"""Unit tests for risk-control challenge parsing (no network)."""
from __future__ import annotations

import json

from doubao_media.verify import SUBTYPE_HINTS, parse_challenge

# Shaped exactly like the live frame captured on 2026-09-28.
LIVE_FRAME = {
    "event_data": json.dumps(
        {
            "code": 710022004,
            "message": "rate limited",
            "error_detail": {
                "code": 710022004,
                "locale": "zh",
                "message": "系统错误",
                "ext": {
                    "decision": json.dumps(
                        {
                            "code": "10000",
                            "from": "shark_admin",
                            "type": "verify",
                            "region": "cn",
                            "subtype": "slide",
                            "detail": "N*dv9PIxydz8JPC1vlCLrRWawr1uNNQ4H56kCavs",
                            "server_sdk_env": json.dumps(
                                {"idc": "lq", "region": "CN", "server_type": "business"}
                            ),
                            "log_id": "20260928005815E57E01FDB957A92AC5B0",
                            "verify_scene": "doubao_message_web",
                        }
                    )
                },
            },
            "event_id": "0",
            "event_type": 2005,
        }
    ),
    "event_id": "0",
    "event_type": 2005,
}


def test_parse_challenge_from_full_sse_frame() -> None:
    challenge = parse_challenge(LIVE_FRAME)
    assert challenge is not None
    assert challenge.subtype == "slide"
    assert challenge.verify_scene == "doubao_message_web"
    assert challenge.log_id == "20260928005815E57E01FDB957A92AC5B0"
    assert challenge.is_actionable is True
    assert challenge.hint == SUBTYPE_HINTS["slide"]


# GitHub@Oxyg enA  I   L ab | O  x  ygen  AILab   @   S t   a r  sai  lsClove r
def test_parse_challenge_accepts_inner_error_detail() -> None:
    detail = json.loads(LIVE_FRAME["event_data"])["error_detail"]
    assert parse_challenge(detail) is not None


def test_parse_challenge_accepts_already_unwrapped_decision() -> None:
    decision = {
        "type": "verify",
        "subtype": "semantic_reasoning",
        "detail": "blob",
        "verify_scene": "doubao_message_web",
    }
    challenge = parse_challenge({"decision": decision})
    assert challenge is not None
    assert challenge.subtype == "semantic_reasoning"


def test_non_verify_payloads_return_none() -> None:
    assert parse_challenge({"code": 0}) is None
    assert parse_challenge("not json at all") is None
    assert parse_challenge(None) is None
    assert parse_challenge({"ext": {"decision": json.dumps({"type": "reject"})}}) is None


def test_challenge_without_detail_is_not_actionable() -> None:
    challenge = parse_challenge(
        {"ext": {"decision": json.dumps({"type": "verify", "subtype": "slide"})}}
    )
    assert challenge is not None
    assert challenge.is_actionable is False


# G   itH   ub@   OxygenAILab | Oxygen A ILab@S ta   r sail s Clover
def test_to_dict_is_json_safe() -> None:
    challenge = parse_challenge(LIVE_FRAME)
    assert challenge is not None
    payload = challenge.to_dict()
    json.dumps(payload)  # must not raise
    assert payload["actionable"] is True
    assert "detail" not in payload, "the opaque blob is never echoed back"
