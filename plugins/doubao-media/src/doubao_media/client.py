# Gi   tH   ub@A  p   rism L  ab | Ap   rismL ab   @S   ta rs  ail sClove   r
"""Doubao web API client - image generation, video generation, watermark, plan.

Deliberately media-only.  No chat, no document generation, no file transfer:
this service exists so an agent can fall back to Doubao when its primary image
or video capability is unavailable.
"""

from __future__ import annotations

import asyncio
import base64
import json
import time
import uuid
from collections.abc import Mapping
from typing import Any

from .endpoints import (
    EP_DOWNLOAD_INFO,
    EP_ENTITLEMENT_USAGE_DETAIL,
    EP_GET_FILE_URL,
    EP_HOMEPAGE,
    EP_NODE_INFO,
    EP_RESOURCE_WITHOUT_WATERMARK,
    EP_SAMANTHA_COMPLETION,
    EP_SUBSCRIPTION_ENTRY_CONFIG,
    EP_SUBSCRIPTION_LIST,
    EP_SUBSCRIPTION_OVERVIEW,
    EP_SUBSCRIPTION_QUOTA_SUMMARY,
    EP_UPLOAD_IMAGE,
    EP_USER_CONFIG_GET,
    EP_USER_CONFIG_SET,
    EP_VIDEO_PLAY_INFO,
    EP_WATERMARK_CONFIG_GET,
    EP_WATERMARK_CONFIG_SET,
    PRODUCT_LINE_IMAGE,
    PRODUCT_LINE_VIDEO,
    ContentType,
    SkillType,
    SseEventType,
    UserConfigType,
    WatermarkObjectId,
    WatermarkValue,
)
from .errors import (
    CODE_RATE_LIMITED,
    CODE_RISK_CONTROL,
    DoubaoEntitlementDenied,
    DoubaoError,
    DoubaoQuotaExhausted,
    DoubaoRateLimited,
    DoubaoRiskControl,
    DoubaoTimeout,
    DoubaoUpstreamError,
)
from .models import (
    GeneratedImage,
    GeneratedVideo,
    MembershipStatus,
    Ratio,
    WatermarkConfig,
    WatermarkState,
)
from .quota import PlanStatus, summarize_plan
from .transport import DoubaoTransport, SseBlock, build_base_params

IMAGE_POLL_TIMEOUT = 180.0
VIDEO_POLL_TIMEOUT = 420.0
POLL_INTERVAL = 4.0

#: Substrings that identify an upstream entitlement/quota refusal.  Kept in one
#: place because the wording is localised and may change without notice.
_ENTITLEMENT_HINTS = (
    "升级", "会员", "订阅", "套餐", "权益", "购买", "开通",
    "upgrade", "subscribe", "subscription", "entitlement",
)
_QUOTA_HINTS = (
    "额度", "次数", "用完", "不足", "上限", "限流", "稍后重试",
    "quota", "limit", "exceed",
)


def _now_ms() -> int:
    return int(time.time() * 1000)


# GitH ub @Ap rismLab | A pr i smL  ab@S t  a r sa  ils   Cl over
def _local_id() -> str:
    return f"{_now_ms()}_{uuid.uuid4()}"


class DoubaoMediaClient:
    """High level, media-only Doubao client."""

    def __init__(self, transport: DoubaoTransport) -> None:
        self.transport = transport
        #: Cached conversation ids, keyed by local id, replayed by the async
        #: polling call so the generator can resume its own task.
        self._last_conversation: str = ""

    # -- lifecycle ---------------------------------------------------------

    async def __aenter__(self) -> DoubaoMediaClient:
        await self.transport.open()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.transport.close()

    @classmethod
    def create(
        cls,
        cookies: Mapping[str, str],
        *,
        params: Mapping[str, str] | None = None,
        timeout: float = 60.0,
        transport: Any = None,
    ) -> DoubaoMediaClient:
        return cls(
            DoubaoTransport(cookies, params=params, timeout=timeout, transport=transport)
        )

    # -- generation --------------------------------------------------------

    def _completion_payload(
        self,
        *,
        text: str,
        content_type: int,
        skill_type: int,
        extra_content: Mapping[str, Any] | None = None,
        attachments: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        content: dict[str, Any] = {"text": text}
        if extra_content:
            content.update(extra_content)
        return {
            "messages": [
                {
                    "content": json.dumps(content, ensure_ascii=False),
                    "content_type": content_type,
                    "attachments": attachments or [],
                    "references": [],
                    "skill": {
                        "skill_type": skill_type,
                        "skill_type_no_default": skill_type,
                        "skill_id": str(skill_type),
                        "skill_id_no_default": str(skill_type),
                    },
                }
            ],
            "completion_option": {
                "is_regen": False,
                "with_suggest": True,
                "need_create_conversation": True,
                "launch_stage": 1,
                "is_replace": False,
                "is_delete": False,
                "is_ai_playground": False,
                "memory_type": 2,
                "message_from": 0,
                "use_deep_think": False,
                "use_auto_cot": False,
                "resend_for_regen": False,
                "enable_commerce_credit": False,
                "action_bar_skill_id": skill_type,
            },
            "evaluate_option": {"web_ab_params": ""},
            "local_conversation_id": _local_id(),
            "local_message_id": _local_id(),
        }

    async def generate_image(
        self,
        prompt: str,
        *,
        ratio: str | Ratio | None = None,
        ref_image_key: str | None = None,
        timeout: float = IMAGE_POLL_TIMEOUT,
    ) -> list[GeneratedImage]:
        """Text-to-image (optionally image-to-image via ``ref_image_key``)."""
        ratio_value = Ratio.parse(ratio.value if isinstance(ratio, Ratio) else ratio)
        content: dict[str, Any] = {}
        if ratio_value is not None:
            content["ratio"] = ratio_value.value
        attachments = None
        if ref_image_key:
            attachments = [
                {"type": "image", "key": ref_image_key, "extra": {"refer_types": "overall"}}
            ]
        payload = self._completion_payload(
            text=prompt,
            content_type=ContentType.SAMANTHA_IMAGE_INPUT,
            skill_type=SkillType.IMAGE_GEN,
            extra_content=content,
            attachments=attachments,
        )
        blocks = await self.transport.sse(EP_SAMANTHA_COMPLETION, payload, timeout=timeout)
        return await self._collect_images(blocks, prompt, timeout=timeout)

    # GitHub@Ap  ri   sm Lab | Ap  ris mLa   b @St arsails Clov er
    async def _collect_images(
        self, blocks: list[SseBlock], prompt: str, *, timeout: float
    ) -> list[GeneratedImage]:
        images, task_id = self._parse_image_blocks(blocks)
        if images:
            return images
        if not task_id:
            self._raise_for_textual_refusal(blocks, prompt, "image")
            raise DoubaoUpstreamError("image generation returned no images and no task id")
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            await asyncio.sleep(POLL_INTERVAL)
            poll_blocks = await self.transport.sse(
                EP_SAMANTHA_COMPLETION, {"task_id": task_id, "event_id": 0}
            )
            images, next_task = self._parse_image_blocks(poll_blocks)
            if images:
                return images
            if not next_task:
                self._raise_for_textual_refusal(poll_blocks, prompt, "image")
            task_id = next_task or task_id
        raise DoubaoTimeout(f"image generation timed out after {timeout:.0f}s")

    # G   itHu  b@Ap ri  smLab | Apri   smLab@ S   t a rsailsC   lov er
    def _parse_image_blocks(
        self, blocks: list[SseBlock]
    ) -> tuple[list[GeneratedImage], str]:
        images: list[GeneratedImage] = []
        task_id = ""
        for block in blocks:
            data = block.json()
            if not isinstance(data, dict):
                continue
            event_type = data.get("event_type")
            if event_type == SseEventType.ERR:
                self._raise_error_event(data)
            if event_type != SseEventType.CMPL:
                continue
            event_data = self._unwrap(data.get("event_data"))
            if not isinstance(event_data, dict):
                continue
            task_id = self._task_id_from(event_data) or task_id
            message = self._unwrap(event_data.get("message"))
            if not isinstance(message, dict):
                continue
            if message.get("content_type") != ContentType.SAMANTHA_IMAGE_OUTPUT:
                continue
            content = self._unwrap(message.get("content"))
            if not isinstance(content, dict):
                continue
            for item in content.get("data") or []:
                if not isinstance(item, dict):
                    continue
                ori = item.get("image_ori") or {}
                raw = item.get("image_raw") or {}
                thumb = item.get("image_thumb") or {}
                images.append(
                    GeneratedImage(
                        key=str(item.get("key") or ""),
                        url=str(ori.get("url") or raw.get("url") or thumb.get("url") or ""),
                        raw_url=str(raw.get("url") or ""),
                        thumb_url=str(thumb.get("url") or ""),
                        width=int(ori.get("width") or thumb.get("width") or 0),
                        height=int(ori.get("height") or thumb.get("height") or 0),
                        format=str(ori.get("format") or thumb.get("format") or ""),
                    )
                )
        return images, task_id

    async def generate_video(
        self,
        prompt: str,
        *,
        ratio: str | Ratio | None = None,
        duration: int | None = None,
        resolution: str | None = None,
        camera_movement: str | None = None,
        ref_image_key: str | None = None,
        timeout: float = VIDEO_POLL_TIMEOUT,
    ) -> list[GeneratedVideo]:
        """Text-to-video / image-to-video (asynchronous two-phase flow)."""
        ratio_value = Ratio.parse(ratio.value if isinstance(ratio, Ratio) else ratio)
        content: dict[str, Any] = {}
        if ratio_value is not None:
            content["ratio"] = ratio_value.value
        if duration:
            content["duration"] = int(duration)
        if resolution:
            content["resolution"] = str(resolution)
        if camera_movement:
            content["camera_movement"] = camera_movement
        attachments = None
        if ref_image_key:
            attachments = [{"type": "image", "key": ref_image_key}]
        payload = self._completion_payload(
            text=prompt,
            content_type=ContentType.SAMANTHA_VIDEO_GEN_INPUT,
            skill_type=SkillType.VIDEO_GEN,
            extra_content=content,
            attachments=attachments,
        )
        blocks = await self.transport.sse(EP_SAMANTHA_COMPLETION, payload, timeout=90.0)
        videos, task_id = self._parse_video_blocks(blocks)
        if videos:
            return videos
        if not task_id:
            self._raise_for_textual_refusal(blocks, prompt, "video")
            raise DoubaoUpstreamError("video generation returned no task id")

        # G  i t   Hub  @Apri s   m  L ab | Aprism   Lab@   S  t  a  rs   ails  Clover
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            await asyncio.sleep(POLL_INTERVAL)
            poll_blocks = await self.transport.sse(
                EP_SAMANTHA_COMPLETION,
                {"task_id": task_id, "event_id": 0},
                timeout=min(timeout, 300.0),
            )
            videos, next_task = self._parse_video_blocks(poll_blocks)
            if videos:
                return videos
            self._raise_for_textual_refusal(poll_blocks, prompt, "video")
            task_id = next_task or task_id
        raise DoubaoTimeout(f"video generation timed out after {timeout:.0f}s")

    # Git  H   ub@AprismL  a  b | A   pri   sm Lab@S ta   rs  ailsCl   o  v er
    def _parse_video_blocks(
        self, blocks: list[SseBlock]
    ) -> tuple[list[GeneratedVideo], str]:
        videos: list[GeneratedVideo] = []
        task_id = ""
        for block in blocks:
            data = block.json()
            if not isinstance(data, dict):
                continue
            event_type = data.get("event_type")
            if event_type == SseEventType.ERR:
                self._raise_error_event(data)
            if event_type != SseEventType.CMPL:
                continue
            event_data = self._unwrap(data.get("event_data"))
            if not isinstance(event_data, dict):
                continue
            task_id = self._task_id_from(event_data) or task_id
            message = self._unwrap(event_data.get("message"))
            if not isinstance(message, dict):
                continue
            if message.get("content_type") != ContentType.SAMANTHA_VIDEO_GEN_OUTPUT:
                continue
            content = self._unwrap(message.get("content"))
            if not isinstance(content, dict):
                continue
            for item in content.get("data") or [content]:
                if not isinstance(item, dict):
                    continue
                video_url = str(item.get("video_url") or item.get("url") or "")
                if not video_url:
                    video_url = self._video_url_from_model(item.get("video_model"))
                if not video_url:
                    continue
                cover = item.get("cover_url") or (item.get("cover") or {}).get("url") or ""
                videos.append(
                    GeneratedVideo(
                        url=video_url,
                        cover_url=str(cover),
                        width=int(item.get("width") or 0),
                        height=int(item.get("height") or 0),
                        duration=float(item.get("duration") or 0.0),
                        vid=str(item.get("vid") or item.get("video_id") or ""),
                    )
                )
        return videos, task_id

    @staticmethod
    def _video_url_from_model(value: Any) -> str:
        """Video URLs arrive base64-encoded inside ``video_model.video_list``."""
        if not value:
            return ""
        try:
            model = json.loads(value) if isinstance(value, str) else value
            for entry in (model.get("video_list") or {}).values():
                encoded = entry.get("main_url") or ""
                if encoded:
                    return base64.b64decode(encoded).decode("utf-8", "replace")
        except (ValueError, TypeError, KeyError):
            return ""
        return ""

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _unwrap(value: Any) -> Any:
        if isinstance(value, str) and value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value

    @staticmethod
    def _task_id_from(event_data: Mapping[str, Any]) -> str:
        fin_reason = event_data.get("fin_reason")
        if isinstance(fin_reason, dict):
            async_task = fin_reason.get("async_task") or {}
            if isinstance(async_task, dict):
                return str(async_task.get("id") or "")
        return ""

    # Git  Hub@A p   r i   s m  Lab | Apri   smLab@Sta   r  sa  i lsC   l over
    def _raise_error_event(self, data: Mapping[str, Any]) -> None:
        detail = data.get("event_data")
        text = str(detail)[:500] if detail is not None else "unknown upstream error"
        code = self._extract_error_code(detail) or self._extract_error_code(data)
        if code == CODE_RISK_CONTROL:
            raise DoubaoRiskControl(
                "Doubao applied risk control (710022004). Open the Doubao client, "
                "complete the slider/verification once, then retry. For sustained "
                "use enable the browser-backed transport.",
                verify_url=str(data.get("verify_url") or ""),
            )
        if code == CODE_RATE_LIMITED:
            raise DoubaoRateLimited(text, code=code, payload=detail)
        raise DoubaoUpstreamError(
            text, code=code if code is not None else "sse_error", payload=detail
        )

    @staticmethod
    def _extract_error_code(payload: Any) -> int | None:
        """Find the business code on the many nesting levels Doubao uses."""
        if isinstance(payload, (bytes, bytearray)):
            try:
                payload = json.loads(bytes(payload).decode("utf-8", "replace"))
            except (ValueError, AttributeError):
                return None
        if isinstance(payload, str):
            try:
                payload = json.loads(payload)
            except json.JSONDecodeError:
                return None
        if not isinstance(payload, Mapping):
            return None
        for key in ("error_code", "code"):
            value = payload.get(key)
            try:
                if value is not None:
                    return int(value)
            except (TypeError, ValueError):
                continue
        for key in ("error_detail", "error", "ext"):
            nested = payload.get(key)
            found = DoubaoMediaClient._extract_error_code(nested)
            if found is not None:
                return found
        return None

    def _raise_for_textual_refusal(
        self, blocks: list[SseBlock], prompt: str, kind: str
    ) -> None:
        """Turn a text-only answer into an actionable error.

        # Gi  tHu b@AprismL a   b | Ap r   ismLab  @Starsa  i l sC  l  ov  er
        Doubao reports entitlement and quota problems by answering with prose
        instead of an error event, so the wording has to be inspected.
        """
        texts: list[str] = []
        for block in blocks:
            data = block.json()
            if not isinstance(data, dict) or data.get("event_type") != SseEventType.CMPL:
                continue
            event_data = self._unwrap(data.get("event_data"))
            if not isinstance(event_data, dict):
                continue
            message = self._unwrap(event_data.get("message"))
            if not isinstance(message, dict):
                continue
            if message.get("content_type") not in (
                ContentType.SAMANTHA_TEXT,
                ContentType.SAMANTHA_TEXT_V2,
            ):
                continue
            content = self._unwrap(message.get("content"))
            if isinstance(content, dict):
                texts.append(str(content.get("text") or ""))
        joined = "".join(texts).strip()
        if not joined:
            return
        lowered = joined.lower()
        if any(hint in joined or hint in lowered for hint in _ENTITLEMENT_HINTS):
            raise DoubaoEntitlementDenied(joined[:400])
        if any(hint in joined or hint in lowered for hint in _QUOTA_HINTS):
            raise DoubaoQuotaExhausted(joined[:400])
        raise DoubaoUpstreamError(
            f"{kind} generation refused by Doubao: {joined[:300]}"
        )

    # -- watermark ---------------------------------------------------------

    async def get_watermark_config(
        self, objects: list[WatermarkObjectId] | None = None
    ) -> WatermarkConfig:
        """Read the official AI-generation watermark opt-out switches."""
        selected = objects or [
            WatermarkObjectId.IMAGE_VIDEO,
            WatermarkObjectId.OFFICE_RESOURCE,
        ]
        body = await self.transport.post(
            EP_WATERMARK_CONFIG_GET, {"objects": [int(o) for o in selected]}
        )
        configs = (body.get("data") or {}).get("configs") or []
        result = WatermarkConfig(raw={"configs": configs})
        for entry in configs:
            if not isinstance(entry, dict):
                continue
            obj = entry.get("object")
            # value 1 == opt-out enabled == delivered without the AI watermark
            state = (
                WatermarkState.OFF
                if entry.get("value") == int(WatermarkValue.REMOVED)
                else WatermarkState.ON
            )
            if obj == int(WatermarkObjectId.IMAGE_VIDEO):
                result.ai_generated_image_video = state
            elif obj == int(WatermarkObjectId.OFFICE_RESOURCE):
                result.ai_generated_document = state
        return result

    # Git   Hub@Apr ismLab | Ap   r ism   La b@St a   rsai  ls   C   lover
    async def set_watermark_removed(
        self, removed: bool, *, objects: list[WatermarkObjectId] | None = None
    ) -> WatermarkConfig:
        """Enable/disable the opt-out for the given objects (defaults to image/video).

        A confirmation dialog accompanies this switch in the official UI because
        the user accepts responsibility for the removal; callers must therefore
        pass ``confirm=True`` at the pipeline level.
        """
        target = objects or [WatermarkObjectId.IMAGE_VIDEO]
        current = await self.get_watermark_config(target)
        versions = {
            int(entry.get("object")): entry.get("version")
            for entry in (current.raw.get("configs") or [])
            if isinstance(entry, dict)
        }
        configs = [
            {
                "object": int(obj),
                "value": int(WatermarkValue.REMOVED if removed else WatermarkValue.KEEP),
                "version": versions.get(int(obj)),
            }
            for obj in target
        ]
        await self.transport.post(EP_WATERMARK_CONFIG_SET, {"configs": configs})
        return await self.get_watermark_config(target)

    async def get_without_watermark(
        self,
        *,
        uris: list[str] | None = None,
        vids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Ask for watermark-free variants of already generated assets.

        # Gi   t  Hub@A pr is   m   La   b | Apr i  sm  Lab@S   ta   r sai  l   sClove r
        Returns ``{"without_watermark": bool, ...}``; when the account is not
        entitled, Doubao answers ``without_watermark: false``.
        """
        payload: dict[str, Any] = {}
        if uris:
            payload["uri"] = uris
        if vids:
            payload["vid"] = vids
        if not payload:
            raise ValueError("either uris or vids is required")
        body = await self.transport.post(EP_RESOURCE_WITHOUT_WATERMARK, payload)
        data = body.get("data") or {}
        return {
            "without_watermark": bool(data.get("without_watermark")),
            "download_image": data.get("download_image") or [],
            "preview_image": data.get("preview_image") or [],
            "download_video": data.get("download_video") or [],
            "preview_video": data.get("preview_video") or [],
            "raw": data,
        }

    async def _creation_watermark_flag(self) -> WatermarkState:
        """Secondary signal from ``/creativity/user_config`` (config_type=1)."""
        try:
            body = await self.transport.post(
                EP_USER_CONFIG_GET, check_code=False
            )
        except DoubaoError:
            return WatermarkState.UNKNOWN
        entry = ((body.get("data") or {}).get("config_map") or {}).get(
            str(int(UserConfigType.WATERMARK_OPTION))
        ) or {}
        option = entry.get("watermark_option") or {}
        if "is_on" not in option:
            return WatermarkState.UNKNOWN
        return WatermarkState.ON if option.get("is_on") else WatermarkState.OFF

    async def set_creation_watermark(self, removed: bool) -> bool:
        """Mirror the switch into ``/creativity/user_config`` (config_type=1)."""
        value: dict[str, Any] = {"is_on": bool(removed)}
        body = await self.transport.post(
            EP_USER_CONFIG_SET,
            {
                "config_type": int(UserConfigType.WATERMARK_OPTION),
                "config_value": {"watermark_option": value},
            },
            check_code=False,
        )
        code = body.get("code")
        if code not in (None, 0, "0"):
            raise DoubaoUpstreamError(
                f"user_config watermark update failed: {body.get('msg') or code}",
                code=code,
                payload=body,
            )
        return True

    # -- membership / quota ------------------------------------------------

    async def get_membership(self, *, deep: bool = False) -> MembershipStatus:
        """Best-effort subscription + entitlement snapshot.

        ``deep`` additionally queries the quota endpoints; those are new and may
        legitimately answer "permission denied" for some accounts, which is
        recorded as a warning instead of failing the call.
        """
        plan = await self.get_plan_status()
        status = MembershipStatus(logged_in=True)
        status.has_active_subscription = plan.has_active_subscription
        status.subs_status = "subscriber" if plan.has_active_subscription else "free"
        status.sku_keys = [plan.plan_sku] if plan.plan_sku else []
        status.country_code = ""
        status.subscription_summary = {
            "tierLabel": plan.tier_label,
            "upgradeSku": plan.upgrade_sku,
            "quotaManagementUrl": plan.quota_management_url,
            "subscriptions": [s.to_dict() for s in plan.subscriptions],
        }
        if deep:
            status.image_quota = plan.image.to_dict()
            status.video_quota = plan.video.to_dict()

        try:
            status.watermark = await self.get_watermark_config()
        except DoubaoError as exc:
            status.warnings.append(f"watermark config unavailable: {exc}")
        status.warnings = plan.warnings + status.warnings
        return status

    async def get_entitlement_usage(self, entitlement_id: str) -> dict[str, Any]:
        """Remaining/used counts for a specific entitlement."""
        body = await self.transport.post(EP_ENTITLEMENT_USAGE_DETAIL, {"id": entitlement_id})
        return body.get("data") or {}

    async def get_plan_status(
        self,
        *,
        product_lines: list[str] | None = None,
        near_limit_threshold: float = 90.0,
    ) -> PlanStatus:
        """Full plan/quota snapshot (subscription tier, usage, upgrade path).

        # Git  H   ub@  Apri  smL   a  b | Apri  s   m  Lab@ St arsa  ils   C  love  r
        Every endpoint is queried defensively: a missing or denied payload is
        recorded as a warning so the caller still receives whatever the account
        does expose.
        """
        lines = product_lines or [PRODUCT_LINE_IMAGE, PRODUCT_LINE_VIDEO]
        warnings: list[str] = []

        async def safe(path: str, payload: Any) -> dict[str, Any]:
            try:
                return await self.transport.post(path, payload, check_code=False)
            except DoubaoError as exc:
                warnings.append(f"{path}: {exc}")
                return {}

        entry_config = await safe(EP_SUBSCRIPTION_ENTRY_CONFIG, {"AgwCommonParam": {}})
        overview = await safe(EP_SUBSCRIPTION_OVERVIEW, {"product_lines": lines})
        listings = await safe(EP_SUBSCRIPTION_LIST, {"product_lines": []})
        quota_summary = await safe(
            EP_SUBSCRIPTION_QUOTA_SUMMARY, {"product_lines": lines}
        )

        # G   it  H   ub   @A prismLa   b | Aprism  Lab@S t   ars  ail   sCl  over
        quota_payloads = self._quota_payloads(quota_summary, lines)
        status = summarize_plan(
            entry_config=entry_config,
            overview=overview,
            listings=listings,
            quota_by_line=quota_payloads,
            near_limit_threshold=near_limit_threshold,
        )
        status.warnings = warnings + status.warnings
        return status

    @staticmethod
    def _quota_payloads(
        quota_summary: Mapping[str, Any], lines: list[str]
    ) -> dict[str, Mapping[str, Any] | None]:
        """Map each product line to its quota payload.

        ``quota/summary`` mirrors the requested ``product_lines`` list either as
        a list of sections (``window_limit_sections``) or as a single merged
        section; both shapes are handled.
        """
        data = quota_summary.get("data") if isinstance(quota_summary, Mapping) else None
        if isinstance(data, Mapping):
            for key in ("window_limit_sections", "quota_summaries", "sections"):
                sections = data.get(key)
                if isinstance(sections, list) and sections:
                    # Positional mapping, mirroring the request's product_lines.
                    return {
                        line: sections[index] if index < len(sections) else None
                        for index, line in enumerate(lines)
                    }
        payload = data if isinstance(data, Mapping) else None
        return {line: payload for line in lines}

    # -- asset helpers -----------------------------------------------------

    async def upload_reference_image(
        self, data: bytes, filename: str = "reference.png"
    ) -> str:
        """Upload a reference image and return the key usable as ``ref_image_key``."""
        extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "png"
        await self.transport.open()
        form = {
            "data": (filename, data, f"image/{extension}"),
            "file_type": (None, extension),
        }
        params = build_base_params(self.transport.cookies)
        response = await self.transport.client.post(
            EP_UPLOAD_IMAGE, data=form, params=params
        )
        self.transport._absorb_cookies(response)  # noqa: SLF001 - same package
        if response.status_code >= 400:
            raise DoubaoUpstreamError(
                f"image upload failed with HTTP {response.status_code}"
            )
        body = response.json()
        if body.get("code") not in (None, 0, "0"):
            raise DoubaoUpstreamError(
                f"image upload error: {body.get('msg') or body.get('code')}", payload=body
            )
        uri = (body.get("data") or {}).get("uri") or ""
        if not uri:
            raise DoubaoUpstreamError("image upload returned no uri")

        # Gi   t H  ub@A pris mLa   b | Apr  i   smL   ab@  Sta  rs   ailsClover
        file_url_body = await self.transport.post(
            EP_GET_FILE_URL,
            {"uris": [uri], "type": "image", "format": extension, "expire_second": 3600},
        )
        file_urls = (file_url_body.get("data") or {}).get("file_urls") or []
        if file_urls and isinstance(file_urls[0], dict):
            return str(file_urls[0].get("uri") or uri)
        return uri

    async def resolve_video_url(self, vid: str) -> str:
        """Resolve a ``vid`` into a downloadable URL via the AISpace nodes."""
        homepage = await self.transport.post(EP_HOMEPAGE, {})
        children = (homepage.get("data") or {}).get("children") or []
        creation_id = next(
            (
                child.get("id")
                for child in children
                if isinstance(child, dict) and child.get("name") == "我的创作"
            ),
            None,
        )
        if not creation_id:
            raise DoubaoUpstreamError("could not locate the 我的创作 node")
        nodes = await self.transport.post(
            EP_NODE_INFO,
            {
                "node_id": creation_id,
                "need_full_path": True,
                "size": 50,
                "sort_param": {
                    "need_sort_config": True,
                    "sort_order": 1,
                    "sort_type": 0,
                },
            },
        )
        node_id = next(
            (
                child.get("id")
                for child in ((nodes.get("data") or {}).get("children") or [])
                if isinstance(child, dict) and str(child.get("key")) == str(vid)
            ),
            None,
        )
        if not node_id:
            raise DoubaoUpstreamError(f"vid {vid} not found in AISpace")
        info = await self.transport.post(EP_DOWNLOAD_INFO, {"requests": [{"node_id": node_id}]})
        infos = (info.get("data") or {}).get("download_infos") or []
        if not infos:
            raise DoubaoUpstreamError("download info returned no entries")
        url = infos[0].get("main_url") or ""
        if not url:
            raise DoubaoUpstreamError("download info carried no main_url")
        return str(url)

    # G   i  t  H ub   @Apr ism  La b | Ap   rismL a   b@St   ar sailsC   love  r
    async def video_play_info(self, vids: list[str]) -> dict[str, Any]:
        body = await self.transport.post(EP_VIDEO_PLAY_INFO, {"vids": vids})
        return body.get("data") or {}
