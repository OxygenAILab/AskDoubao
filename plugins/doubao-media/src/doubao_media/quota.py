"""Plan-tier and quota normalisation.

Doubao exposes plan state through several layered payloads; this module folds
them into one stable shape so the skill and the MCP surface never have to know
about ``window_limit_groups`` or ``agreement_status``.

Verified live against a 标准套餐 (``doubao_personal_std``) account:

* ``/alice/commerce/sale/subscription/entry/config/``  -> plan name, upgrade CTA
* ``/alice/commerce/sale/subscription/overview/``      -> SKU, subscription window
* ``/alice/commerce/sale/subscription/list/``          -> every subscription row
* ``/alice/commerce/sale/subscription/quota/summary/`` -> window limits + usage
"""

from __future__ import annotations

import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

#: Fallback display names for SKUs seen in the wild.  A server-provided
#: ``display.short_name`` / ``membership_display_name`` always wins.
SKU_DISPLAY_NAMES: dict[str, str] = {
    "doubao_personal_std": "标准套餐",
    "doubao_personal_pro": "专业套餐",
    "doubao_personal_max": "极致套餐",
}

#: ``window_type`` semantics on quota windows.
WINDOW_TYPE_TOTAL = 1
WINDOW_TYPE_ROLLING = 2

#: ``subscription.status`` semantics.
SUBSCRIPTION_STATUS_ACTIVE = 3
SUBSCRIPTION_STATUS_EXPIRED = 4


def _ms_to_iso(timestamp_ms: Any) -> str:
    try:
        value = float(timestamp_ms)
    except (TypeError, ValueError):
        return ""
    if value <= 0:
        return ""
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(value / 1000.0))


def nice_sku(sku: str) -> str:
    """Human label for a SKU key, without depending on a server round-trip."""
    if not sku:
        return ""
    if sku in SKU_DISPLAY_NAMES:
        return SKU_DISPLAY_NAMES[sku]
    cleaned = sku
    for prefix in ("doubao_personal_", "doubao_", "personal_"):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):]
            break
    return cleaned.replace("_", " ").strip().title() or sku


@dataclass(slots=True)
class QuotaWindow:
    """One usage window reported by the quota summary."""

    window_type: int = 0
    label: str = ""
    used_percent: float = 0.0
    remaining_percent: float = 100.0
    start_time: str = ""
    end_time: str = ""
    near_limit: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "windowType": self.window_type,
            "label": self.label,
            "usedPercent": self.used_percent,
            "remainingPercent": self.remaining_percent,
            "startTime": self.start_time,
            "endTime": self.end_time,
            "nearLimit": self.near_limit,
        }


@dataclass(slots=True)
class QuotaReport:
    """Normalised quota view for one product line (image or video)."""

    product_line: str = ""
    entitled: bool = False
    usage_exhausted: bool = False
    entitlement_count: int = 0
    windows: list[QuotaWindow] = field(default_factory=list)
    feature_groups: list[str] = field(default_factory=list)
    near_limit_threshold: float = 90.0

    @property
    def used_percent(self) -> float:
        """Highest usage across the reported windows."""
        return max((w.used_percent for w in self.windows), default=0.0)

    @property
    def remaining_percent(self) -> float:
        return max(0.0, 100.0 - self.used_percent)

    @property
    def is_running_low(self) -> bool:
        """True when the account is at or past the near-limit threshold."""
        return self.usage_exhausted or self.used_percent >= self.near_limit_threshold

    @property
    def next_reset(self) -> str:
        rolling = [w for w in self.windows if w.window_type == WINDOW_TYPE_ROLLING]
        candidates = [w.end_time for w in (rolling or self.windows) if w.end_time]
        return min(candidates) if candidates else ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "productLine": self.product_line,
            "entitled": self.entitled,
            "usageExhausted": self.usage_exhausted,
            "entitlementCount": self.entitlement_count,
            "usedPercent": self.used_percent,
            "remainingPercent": self.remaining_percent,
            "runningLow": self.is_running_low,
            "nextReset": self.next_reset,
            "featureGroups": list(self.feature_groups),
            "windows": [w.to_dict() for w in self.windows],
        }


@dataclass(slots=True)
class Subscription:
    """One subscription row from ``/subscription/list/`` or ``/overview/``."""

    sku_key: str = ""
    product_name: str = ""
    status: int = 0
    is_gift: bool = False
    start_time: str = ""
    end_time: str = ""
    subscription_id: str = ""
    agreement_price: str = ""

    @property
    def is_active(self) -> bool:
        return self.status == SUBSCRIPTION_STATUS_ACTIVE

    @property
    def display_name(self) -> str:
        return self.product_name or nice_sku(self.sku_key)

    def to_dict(self) -> dict[str, Any]:
        return {
            "skuKey": self.sku_key,
            "displayName": self.display_name,
            "status": self.status,
            "active": self.is_active,
            "isGift": self.is_gift,
            "startTime": self.start_time,
            "endTime": self.end_time,
            "subscriptionId": self.subscription_id,
            "agreementPrice": self.agreement_price,
        }


@dataclass(slots=True)
class PlanStatus:
    """The complete plan picture an agent needs before choosing a generator."""

    logged_in: bool = False
    has_active_subscription: bool = False
    usr_type: int = 0
    plan_name: str = ""
    plan_sku: str = ""
    upgrade_sku: str = ""
    upgrade_name: str = ""
    upgrade_url: str = ""
    quota_management_url: str = ""
    subscriptions: list[Subscription] = field(default_factory=list)
    image: QuotaReport = field(default_factory=lambda: QuotaReport(product_line="image"))
    video: QuotaReport = field(default_factory=lambda: QuotaReport(product_line="video"))
    warnings: list[str] = field(default_factory=list)

    @property
    def tier_label(self) -> str:
        if not self.logged_in:
            return "未登录"
        if self.plan_name:
            return self.plan_name
        if self.plan_sku:
            return nice_sku(self.plan_sku)
        return "免费用户"

    def to_dict(self) -> dict[str, Any]:
        return {
            "loggedIn": self.logged_in,
            "tierLabel": self.tier_label,
            "planSku": self.plan_sku,
            "hasActiveSubscription": self.has_active_subscription,
            "usrType": self.usr_type,
            "upgrade": {
                "sku": self.upgrade_sku,
                "name": self.upgrade_name,
                "url": self.upgrade_url,
            },
            "quotaManagementUrl": self.quota_management_url,
            "subscriptions": [s.to_dict() for s in self.subscriptions],
            "image": self.image.to_dict(),
            "video": self.video.to_dict(),
            "runningLow": {
                "image": self.image.is_running_low,
                "video": self.video.is_running_low,
            },
            "warnings": list(self.warnings),
        }


def _pick_display_name(entry: Mapping[str, Any]) -> str:
    display = entry.get("display")
    if isinstance(display, Mapping):
        for key in ("short_name", "product_name"):
            value = display.get(key)
            if value:
                return str(value)
    return ""


def parse_subscription(entry: Mapping[str, Any]) -> Subscription:
    price = entry.get("agreement_price_parts") or {}
    return Subscription(
        sku_key=str(entry.get("sku_key") or ""),
        product_name=_pick_display_name(entry),
        status=int(entry.get("status") or 0),
        is_gift=bool(entry.get("is_gift")),
        start_time=_ms_to_iso(entry.get("start_time") or entry.get("effective_time")),
        end_time=_ms_to_iso(entry.get("end_time")),
        subscription_id=str(entry.get("subscription_id") or ""),
        agreement_price=str(price.get("formatted") or ""),
    )


def parse_quota(
    product_line: str,
    payload: Mapping[str, Any] | None,
    *,
    near_limit_threshold: float = 90.0,
) -> QuotaReport:
    """Fold one ``quota/summary`` payload into a :class:`QuotaReport`."""
    report = QuotaReport(
        product_line=product_line, near_limit_threshold=near_limit_threshold
    )
    if not isinstance(payload, Mapping):
        return report
    member = payload.get("member_info") or {}
    report.entitled = bool(member.get("hasActiveSubscription"))
    section = payload.get("window_limit_section") or {}
    report.usage_exhausted = bool(section.get("usage_exhausted"))
    try:
        report.entitlement_count = int(section.get("entitlement_count") or 0)
    except (TypeError, ValueError):
        report.entitlement_count = 0
    for group in section.get("window_limit_groups") or []:
        if not isinstance(group, Mapping):
            continue
        feature = str(group.get("feature_group") or "")
        if feature and feature not in report.feature_groups:
            report.feature_groups.append(feature)
        for window in group.get("window_limits") or []:
            if not isinstance(window, Mapping):
                continue
            used = float(window.get("used_percent") or 0.0)
            window_type = int(window.get("window_type") or 0)
            report.windows.append(
                QuotaWindow(
                    window_type=window_type,
                    label=(
                        "当前周期"
                        if window_type == WINDOW_TYPE_ROLLING
                        else "总额度"
                    ),
                    used_percent=used,
                    remaining_percent=max(0.0, 100.0 - used),
                    start_time=_ms_to_iso(window.get("start_time")),
                    end_time=_ms_to_iso(window.get("end_time")),
                    near_limit=used >= near_limit_threshold,
                )
            )
    return report


def parse_quota_by_line(
    payloads: Sequence[Mapping[str, Any] | None],
    product_lines: Sequence[str],
    *,
    near_limit_threshold: float = 90.0,
) -> dict[str, QuotaReport]:
    """Pair each requested product line with its quota payload by position."""
    return {
        line: parse_quota(
            line,
            payloads[index] if index < len(payloads) else None,
            near_limit_threshold=near_limit_threshold,
        )
        for index, line in enumerate(product_lines)
    }


def summarize_plan(
    *,
    entry_config: Mapping[str, Any] | None,
    overview: Mapping[str, Any] | None,
    listings: Mapping[str, Any] | None,
    quota_by_line: Mapping[str, Mapping[str, Any] | None],
    near_limit_threshold: float = 90.0,
) -> PlanStatus:
    """Merge every plan-related payload into a single :class:`PlanStatus`."""
    status = PlanStatus(logged_in=True)

    entry = (entry_config or {}).get("data") or {}
    if isinstance(entry, Mapping) and entry:
        status.has_active_subscription = bool(entry.get("has_active_subscription"))
        status.plan_name = str(entry.get("membership_display_name") or "")
        settings = entry.get("settings_page") or {}
        if isinstance(settings, Mapping):
            status.plan_name = status.plan_name or str(settings.get("title") or "")
            if settings.get("click_url"):
                status.quota_management_url = str(settings["click_url"])
        management = entry.get("settings_management_page") or {}
        if isinstance(management, Mapping) and management.get("click_url"):
            status.quota_management_url = (
                status.quota_management_url or str(management["click_url"])
            )

    over = (overview or {}).get("data") or {}
    if isinstance(over, Mapping) and over:
        current = over.get("current_subscription") or {}
        if isinstance(current, Mapping) and current:
            status.plan_sku = str(current.get("sku_key") or "")
            status.plan_name = (
                status.plan_name
                or _pick_display_name(current)
                or nice_sku(status.plan_sku)
            )
            status.subscriptions.append(parse_subscription(current))
        guide = over.get("upgrade_guide") or {}
        if isinstance(guide, Mapping):
            status.upgrade_sku = str(guide.get("highest_version_sku") or "")
            status.upgrade_name = nice_sku(status.upgrade_sku)
            status.upgrade_url = str(guide.get("order_page_url") or "")
        member = over.get("member_info") or {}
        if isinstance(member, Mapping):
            status.has_active_subscription = bool(
                member.get("hasActiveSubscription", status.has_active_subscription)
            )
            try:
                status.usr_type = int(member.get("usr_type") or 0)
            except (TypeError, ValueError):
                status.usr_type = 0

    listed = (listings or {}).get("data") or {}
    if isinstance(listed, Mapping):
        seen = {s.subscription_id for s in status.subscriptions}
        for group in listed.get("groups") or []:
            if not isinstance(group, Mapping):
                continue
            for record in group.get("records") or []:
                if not isinstance(record, Mapping):
                    continue
                parsed = parse_subscription(record)
                if parsed.subscription_id and parsed.subscription_id in seen:
                    continue
                status.subscriptions.append(parsed)
                if parsed.subscription_id:
                    seen.add(parsed.subscription_id)

    for line, payload in quota_by_line.items():
        report = parse_quota(line, payload, near_limit_threshold=near_limit_threshold)
        if line == "image":
            status.image = report
        elif line == "video":
            status.video = report
        if report.is_running_low:
            status.warnings.append(
                f"{line} quota running low (used {report.used_percent:.0f}%"
                + (", exhausted" if report.usage_exhausted else "")
                + ")"
            )

    if not status.plan_sku:
        active = next((s for s in status.subscriptions if s.is_active), None)
        if active:
            status.plan_sku = active.sku_key
            status.plan_name = status.plan_name or active.display_name
    return status
