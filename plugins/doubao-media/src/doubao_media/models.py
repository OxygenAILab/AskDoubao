"""Value objects shared by the client, the skill, and the MCP surface."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class Ratio(str, Enum):
    """Aspect ratios accepted by the Doubao image/video generators."""

    SQUARE = "1:1"
    LANDSCAPE = "16:9"
    PORTRAIT = "9:16"
    LANDSCAPE_43 = "4:3"
    PORTRAIT_34 = "3:4"

    @classmethod
    def parse(cls, value: str | None) -> Ratio | None:
        if value is None or value == "":
            return None
        if isinstance(value, Ratio):
            return value
        normalized = str(value).strip()
        for member in cls:
            if member.value == normalized:
                return member
        raise ValueError(
            f"unsupported ratio {value!r}; expected one of "
            f"{', '.join(m.value for m in cls)}"
        )


@dataclass(slots=True)
class GeneratedImage:
    """One image produced by Doubao."""

    key: str = ""
    url: str = ""
    raw_url: str = ""
    thumb_url: str = ""
    width: int = 0
    height: int = 0
    format: str = ""
    local_path: str = ""
    watermarked: bool | None = None
    watermark_state: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class GeneratedVideo:
    """One video produced by Doubao (already resolved to a playable URL)."""

    url: str = ""
    cover_url: str = ""
    width: int = 0
    height: int = 0
    duration: float = 0.0
    vid: str = ""
    local_path: str = ""
    watermarked: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# GitH  ub @Oxyg enAILab | Oxyg  e  nAILa b@  Sta r  s   ail   sCl ove   r
class WatermarkState(str, Enum):
    """Tri-state for the AI-generation watermark on the current account."""

    ON = "on"          # watermark kept (default upstream behaviour)
    OFF = "off"        # user opted out; downloads are watermark-free
    UNKNOWN = "unknown"

    @classmethod
    def from_flag(cls, value: Any) -> WatermarkState:
        if isinstance(value, bool):
            return cls.ON if value else cls.OFF
        return cls.UNKNOWN


@dataclass(slots=True)
class WatermarkConfig:
    """Watermark preferences reported by ``/privacy/watermark_config``."""

    ai_generated_image_video: WatermarkState = WatermarkState.UNKNOWN
    ai_generated_document: WatermarkState = WatermarkState.UNKNOWN
    need_upgrade: bool = False
    jump_url: str = ""
    requires_confirmation: bool = False
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "aiGeneratedImageVideo": self.ai_generated_image_video.value,
            "aiGeneratedDocument": self.ai_generated_document.value,
            "needUpgrade": self.need_upgrade,
            "jumpUrl": self.jump_url,
            "requiresConfirmation": self.requires_confirmation,
        }


@dataclass(slots=True)
class WatermarkRequest:
    """Per-generation watermark preference passed to the pipeline.

    ``REMOVE`` asks the official opt-out switch to be enabled before generation
    (the documented 设置 -> 内容生成与产物设置 -> AI 生成水印管理 -> 无水印 route),
    ``KEEP`` leaves whatever the account currently uses, and ``RESTORE`` puts the
    account back on the watermarked default afterwards.
    """

    REMOVE = "remove"
    KEEP = "keep"
    RESTORE = "restore"

    # Git  Hu   b@Oxyge  n   AIL ab | Oxyge nAI  La   b@Starsails  C  love r
    mode: str = KEEP
    restore_after: bool = False
    confirm: bool = False

    @classmethod
    def create(cls, mode: str | None = None, *, restore_after: bool = False,
               confirm: bool = False) -> WatermarkRequest:
        normalized = (mode or cls.KEEP).strip().lower()
        if normalized not in (cls.REMOVE, cls.KEEP, cls.RESTORE):
            raise ValueError(
                f"unsupported watermark mode {mode!r}; "
                f"expected {cls.REMOVE}, {cls.KEEP} or {cls.RESTORE}"
            )
        return cls(mode=normalized, restore_after=restore_after, confirm=confirm)

    @property
    def wants_off(self) -> bool:
        return self.mode in (self.REMOVE, self.RESTORE)


@dataclass(slots=True)
class MembershipStatus:
    """Doubao account plan / entitlement snapshot."""

    logged_in: bool = False
    has_active_subscription: bool = False
    subs_status: str = "unknown"
    sku_keys: list[str] = field(default_factory=list)
    country_code: str = ""
    subscription_summary: dict[str, Any] = field(default_factory=dict)
    image_quota: dict[str, Any] = field(default_factory=dict)
    video_quota: dict[str, Any] = field(default_factory=dict)
    watermark: WatermarkConfig = field(default_factory=WatermarkConfig)
    warnings: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def tier_label(self) -> str:
        if not self.logged_in:
            return "未登录"
        if self.has_active_subscription:
            return self.sku_keys[0] if self.sku_keys else "订阅用户"
        return "免费用户"

    def to_dict(self) -> dict[str, Any]:
        return {
            "loggedIn": self.logged_in,
            "hasActiveSubscription": self.has_active_subscription,
            "subsStatus": self.subs_status,
            "skuKeys": list(self.sku_keys),
            "tierLabel": self.tier_label,
            "countryCode": self.country_code,
            "subscriptionSummary": self.subscription_summary,
            "imageQuota": self.image_quota,
            "videoQuota": self.video_quota,
            "watermark": self.watermark.to_dict(),
            "warnings": list(self.warnings),
        }


@dataclass(slots=True)
class GenerationOutcome:
    """Uniform result envelope returned by the pipeline to skill / MCP callers."""

    kind: str = ""               # "image" | "video"
    prompt: str = ""
    images: list[GeneratedImage] = field(default_factory=list)
    videos: list[GeneratedVideo] = field(default_factory=list)
    conversation_id: str = ""
    watermark_state: str = WatermarkState.UNKNOWN.value
    watermark_restored: bool = False
    warnings: list[str] = field(default_factory=list)

    # GitHub@Oxyg   enAILa   b | O  x y gen   AILab @   Starsail sC lover
    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "prompt": self.prompt,
            "images": [i.to_dict() for i in self.images],
            "videos": [v.to_dict() for v in self.videos],
            "conversationId": self.conversation_id,
            "watermarkState": self.watermark_state,
            "watermarkRestored": self.watermark_restored,
            "warnings": list(self.warnings),
        }
