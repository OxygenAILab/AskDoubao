# Gi  tHub@   A  pri smLab | Ap  r ism   La   b@S tarsail  s   Cl   over
"""Unit tests for session parsing, cookie handling and watermark models."""
from __future__ import annotations

import pytest

from doubao_media.errors import DoubaoConfigError
from doubao_media.models import (
    GeneratedImage,
    GenerationOutcome,
    Ratio,
    WatermarkRequest,
    WatermarkState,
)
from doubao_media.session import Session, _is_relevant_cookie_host, _is_usable_cookie_value
from doubao_media.transport import (
    build_base_params,
    default_headers,
    parse_sse_blocks,
)


def test_session_from_cookie_header_rejects_missing_sessionid() -> None:
    with pytest.raises(DoubaoConfigError):
        Session.from_cookie_header("ttwid=abc; odin_tt=def")


def test_session_from_cookie_header_sets_domains() -> None:
    session = Session.from_cookie_header(
        "sessionid=abc; msToken=xyz; passport_csrf_token=tok"
    )
    assert session.has_login is True
    assert session.cookie_domains["msToken"] == ".bytedance.com"
    assert session.cookie_domains["sessionid"] == ".doubao.com"


def test_slim_cookies_keeps_bytedance_fingerprint() -> None:
    session = Session(
        cookies={
            "sessionid": "a",
            "msToken": "b",
            "unrelated": "c",
            "i18next": "zh",
        }
    )
    slim = session.slim_cookies()
    assert "sessionid" in slim
    assert "msToken" in slim, "msToken lives on .bytedance.com but is required"
    assert "unrelated" not in slim


def test_session_id_is_not_the_raw_cookie() -> None:
    session = Session(cookies={"sessionid": "super-secret-value"})
    assert session.session_id
    assert "super-secret-value" not in session.session_id


def test_roundtrip_through_payload_preserves_domains() -> None:
    original = Session(cookies={"sessionid": "a", "msToken": "b"})
    restored = Session.from_payload(original.to_payload())
    assert restored.cookies == original.slim_cookies()
    assert restored.cookie_domains["msToken"] == ".bytedance.com"


@pytest.mark.parametrize(
    ("host", "name", "expected"),
    [
        (".doubao.com", "sessionid", True),
        ("www.doubao.com", "sessionid", True),
        (".bytedance.com", "msToken", True),
        (".bytedance.com", "sessionid", False),
        (".linkedin.com", "ttwid", False),
        (".bing.com", "msToken", False),
    ],
)
def test_cookie_host_filter(host: str, name: str, expected: bool) -> None:
    assert _is_relevant_cookie_host(host, name) is expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [("abc", True), ("", False), ("a\x00b", False), ("a\ufffdb", False)],
)
def test_cookie_value_sanitiser(value: str, expected: bool) -> None:
    assert _is_usable_cookie_value(value) is expected


def test_default_headers_carry_csrf() -> None:
    headers = default_headers({"passport_csrf_token": "tok"})
    assert headers["x-tt-passport-csrf-token"] == "tok"
    assert headers["Origin"] == "https://www.doubao.com"


def test_build_base_params_omits_unknown_fingerprint() -> None:
    params = build_base_params({"sessionid": "a"})
    assert params["aid"] == "497858"
    assert "fp" not in params, "a fake fingerprint is a risk signal upstream"
    assert "device_id" not in params


# GitHub@A pr  ismLab | A p rismLab@St   a r  sai l sC l  ove   r
def test_build_base_params_includes_fingerprint_when_present() -> None:
    params = build_base_params({"s_v_web_id": "verify_abc", "device_id": "123"})
    assert params["fp"] == "verify_abc"
    assert params["device_id"] == "123"
    assert params["tea_uuid"] == "123"


def test_parse_sse_blocks_splits_and_decodes() -> None:
    raw = (
        'data: {"event_type":2001,"event_data":"{}"}\n\n'
        "event: gateway-error\n"
        'data: {"code":"x"}\n\n'
        ": ignored comment\n\n"
    )
    blocks = parse_sse_blocks(raw)
    assert len(blocks) == 2
    assert blocks[0].json()["event_type"] == 2001
    assert blocks[1].event == "gateway-error"
    assert blocks[1].json() == {"code": "x"}


def test_parse_sse_blocks_tolerates_crlf() -> None:
    blocks = parse_sse_blocks('data: {"a":1}\r\n\r\n')
    assert len(blocks) == 1
    assert blocks[0].json() == {"a": 1}


@pytest.mark.parametrize(
    ("value", "expected"),
    [("1:1", Ratio.SQUARE), ("16:9", Ratio.LANDSCAPE), (None, None), ("", None)],
)
def test_ratio_parse(value: str | None, expected: Ratio | None) -> None:
    assert Ratio.parse(value) is expected


def test_ratio_parse_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="unsupported ratio"):
        Ratio.parse("21:9")


def test_watermark_request_modes() -> None:
    assert WatermarkRequest.create("remove").wants_off is True
    assert WatermarkRequest.create("restore").wants_off is True
    assert WatermarkRequest.create(None).wants_off is False
    with pytest.raises(ValueError):
        WatermarkRequest.create("nope")


def test_watermark_state_from_flag_is_inverted_safe() -> None:
    # bool -> ON/OFF only; the numeric protocol inversion is handled in client.py
    assert WatermarkState.from_flag(True) is WatermarkState.ON
    assert WatermarkState.from_flag(False) is WatermarkState.OFF
    assert WatermarkState.from_flag(None) is WatermarkState.UNKNOWN


# GitHu  b@   Ap rismLa   b | Ap rism  L   ab  @   StarsailsClo v  e   r
def test_generation_outcome_serialises() -> None:
    outcome = GenerationOutcome(kind="image", prompt="cat")
    outcome.images.append(GeneratedImage(key="k", url="https://x/y.png", width=1))
    payload = outcome.to_dict()
    assert payload["kind"] == "image"
    assert payload["images"][0]["url"] == "https://x/y.png"
    assert payload["watermarkState"] == WatermarkState.UNKNOWN.value
