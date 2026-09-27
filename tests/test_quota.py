"""Unit tests for plan/quota normalisation (no network)."""
from __future__ import annotations

from doubao_media.quota import (
    PlanStatus,
    QuotaReport,
    parse_quota,
    parse_subscription,
    summarize_plan,
)

# Captured from a live 标准套餐 account on 2026-09-27 (trimmed).
OVERVIEW = {
    "data": {
        "current_subscription": {
            "sku_key": "doubao_personal_std",
            "status": 3,
            "is_gift": True,
            "start_time": 1789586742227,
            "end_time": 1792178742227,
            "subscription_id": "7686207800678350899",
            "display": {"product_name": "个人订阅", "short_name": "标准套餐"},
            "agreement_price_parts": {"formatted": "¥0.00"},
        },
        "upgrade_guide": {
            "highest_version_sku": "doubao_personal_pro",
            "order_page_url": "https://www.doubao.com/member/subscription?x=1",
        },
        "member_info": {"hasActiveSubscription": True, "usr_type": 1},
    }
}

ENTRY_CONFIG = {
    "data": {
        "has_active_subscription": True,
        "membership_display_name": "标准套餐",
        "settings_page": {
            "title": "标准套餐",
            "click_url": "https://www.doubao.com/member/quota-management?enter_method=setting",
        },
    }
}

LISTINGS = {
    "data": {
        "groups": [
            {
                "group_type": 2,
                "records": [
                    {
                        "sku_key": "",
                        "status": 4,
                        "end_time": 1785418624741,
                        "subscription_id": "7657164817899307027",
                        "agreement_price_parts": {"formatted": "¥68.00"},
                        "display": {"product_name": "标准套餐"},
                    }
                ],
            }
        ]
    }
}

QUOTA = {
    "data": {
        "member_info": {"hasActiveSubscription": True},
        "window_limit_section": {
            "entitlement_count": 1,
            "usage_exhausted": False,
            "window_limit_groups": [
                {
                    "feature_group": "general",
                    "window_limits": [
                        {"window_type": 1, "used_percent": 0},
                        {
                            "window_type": 2,
                            "used_percent": 2,
                            "start_time": 1790187153877,
                            "end_time": 1790791953877,
                        },
                    ],
                }
            ],
        },
    }
}


def test_parse_subscription_active() -> None:
    sub = parse_subscription(OVERVIEW["data"]["current_subscription"])
    assert sub.sku_key == "doubao_personal_std"
    assert sub.is_active is True
    assert sub.display_name == "标准套餐"
    assert sub.start_time.startswith("2026-")
    assert sub.agreement_price == "¥0.00"


def test_parse_subscription_expired_row() -> None:
    sub = parse_subscription(LISTINGS["data"]["groups"][0]["records"][0])
    assert sub.is_active is False
    assert sub.sku_key == ""


def test_parse_quota_windows_and_usage() -> None:
    report = parse_quota("image", QUOTA["data"])
    assert report.entitled is True
    assert report.usage_exhausted is False
    assert report.entitlement_count == 1
    assert [w.window_type for w in report.windows] == [1, 2]
    # Highest usage wins; window 2 reports 2%.
    assert report.used_percent == 2.0
    assert report.remaining_percent == 98.0
    assert report.is_running_low is False
    assert report.next_reset.startswith("2026-")


def test_parse_quota_missing_payload_is_safe() -> None:
    report = parse_quota("video", None)
    assert report == QuotaReport(product_line="video")
    assert report.used_percent == 0.0
    assert report.is_running_low is False


def test_running_low_at_threshold() -> None:
    payload = {
        "member_info": {"hasActiveSubscription": True},
        "window_limit_section": {
            "usage_exhausted": False,
            "window_limit_groups": [
                {"window_limits": [{"window_type": 2, "used_percent": 91}]}
            ],
        },
    }
    report = parse_quota("video", payload, near_limit_threshold=90)
    assert report.used_percent == 91.0
    assert report.is_running_low is True
    assert report.windows[0].near_limit is True


def test_exhausted_marks_running_low() -> None:
    payload = {
        "member_info": {"hasActiveSubscription": True},
        "window_limit_section": {"usage_exhausted": True, "window_limit_groups": []},
    }
    report = parse_quota("image", payload)
    assert report.usage_exhausted is True
    assert report.is_running_low is True


def test_summarize_plan_merges_sources() -> None:
    status = summarize_plan(
        entry_config=ENTRY_CONFIG,
        overview=OVERVIEW,
        listings=LISTINGS,
        quota_by_line={"image": QUOTA["data"], "video": None},
    )
    assert isinstance(status, PlanStatus)
    assert status.logged_in is True
    assert status.tier_label == "标准套餐"
    assert status.plan_sku == "doubao_personal_std"
    assert status.upgrade_sku == "doubao_personal_pro"
    assert status.upgrade_name == "专业套餐"
    assert status.quota_management_url.endswith("quota-management?enter_method=setting")
    # Two subscriptions: the active one plus the expired historical row.
    assert len(status.subscriptions) == 2
    assert status.image.used_percent == 2.0
    assert status.video.used_percent == 0.0
    payload = status.to_dict()
    assert payload["runningLow"] == {"image": False, "video": False}


def test_summarize_plan_without_data_is_offline_safe() -> None:
    status = summarize_plan(
        entry_config=None, overview=None, listings=None, quota_by_line={}
    )
    assert status.logged_in is True
    assert status.plan_sku == ""
    assert status.tier_label == "免费用户"
    assert status.image.used_percent == 0.0
