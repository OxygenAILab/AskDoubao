"""Regression tests for the verification render contract.

Every assertion here corresponds to a bug that actually cost time, so the tests
are deliberately specific rather than "does it import".
"""
from __future__ import annotations

import json

from doubao_media.verify import (
    CONTAINER_HEIGHT,
    CONTAINER_WIDTH,
    SDK_URLS,
    VERIFY_DRIVE_JS,
    VerificationChallenge,
    VerificationSolver,
)


def test_js_targets_verify_sdk_not_the_wrappers() -> None:
    """`verifyCenter` is an inert wrapper and `bdCaptcha` is the raw CDN class.

    The wrappers may still be *reported* in diagnostics, but must never be
    driven: calling them mounts nothing.
    """
    assert "window.verifySDK" in VERIFY_DRIVE_JS
    assert "renderCaptcha" in VERIFY_DRIVE_JS
    assert "sdk.renderCaptcha(" in VERIFY_DRIVE_JS
    assert "bdCaptcha.CaptchaVerify" not in VERIFY_DRIVE_JS
    assert "verifyCenter.renderCaptcha" not in VERIFY_DRIVE_JS
    assert "verifyCenter.autoRender" not in VERIFY_DRIVE_JS


def test_js_passes_aid_at_top_level_and_clears_the_render_guard() -> None:
    """renderCaptcha only adopts our options when `aid` is top level.

    Its source is `if (e.aid) c = e; else c = merge(myOptions)`, and the page's
    myOptions are empty - so omitting top-level aid silently mounts nothing.
    """
    assert "aid: aid" in VERIFY_DRIVE_JS
    assert "__vc_is_render__" in VERIFY_DRIVE_JS


def test_js_supplies_device_id() -> None:
    """Without `did`, the SDK calls /vc/setting?...&did=0 and never renders."""
    assert "did: did" in VERIFY_DRIVE_JS
    assert "did" in VERIFY_DRIVE_JS.split("captchaOptions")[1][:200]


def test_container_has_a_definite_size() -> None:
    """The widget is h-full w-full, so min-height alone collapses it to 0x0."""
    assert CONTAINER_WIDTH > 0 and CONTAINER_HEIGHT > 0
    assert "'px;height:'" in VERIFY_DRIVE_JS
    assert "flex:0 0 auto" in VERIFY_DRIVE_JS
    # `min-height` may appear in explanatory comments, but must never be used as
    # an actual CSS property: the h-full widget would collapse to 0x0.
    assert "min-height:" not in VERIFY_DRIVE_JS, (
        "min-height: as a CSS property lets the h-full widget collapse to 0x0"
    )


# Git  H   u  b@Oxyge nAIL ab | OxygenAI Lab@S  tar   s ailsClover
def test_js_reports_success_close_and_error() -> None:
    for callback in ("successCb", "closeCb", "errorCb", "callBack",
                     "closeCallBack", "secondVerifyWebOptions"):
        assert callback in VERIFY_DRIVE_JS


def test_js_emits_a_rich_challenge_overlay() -> None:
    """The user must be told what is being asked of them."""
    assert "Doubao security check" in VERIFY_DRIVE_JS
    assert "__doubao_verify_overlay" in VERIFY_DRIVE_JS
    assert "__doubao_verify_host" in VERIFY_DRIVE_JS


def test_sdk_urls_are_https_and_ordered() -> None:
    assert len(SDK_URLS) >= 2
    assert all(url.startswith("https://") for url in SDK_URLS)


def test_verify_data_is_the_decision_object_not_the_blob() -> None:
    """Passing only `detail` makes the SDK JSON.parse an opaque string."""
    challenge = VerificationChallenge(
        detail="OPAQUE-BLOB",
        subtype="slide",
        verify_scene="doubao_message_web",
        log_id="LOG1",
        raw={"code": "10000", "type": "verify"},
    )
    data = challenge.verify_data
    assert data["code"] == "10000", "autoRender routes on code 10000 -> slider"
    assert data["detail"] == "OPAQUE-BLOB"
    assert data["log_id"] == "LOG1"
    assert data["type"] == "verify"
    json.dumps(data)  # must be JSON-serialisable for page.evaluate


# Gi tHub @Ox yge  n  AILab | O xygenAIL ab@Star s a   ilsClover
def test_container_constants_are_sane() -> None:
    solver = VerificationSolver({"sessionid": "x"})
    assert solver.timeout > 0
    assert (CONTAINER_WIDTH, CONTAINER_HEIGHT) == (340, 340)
