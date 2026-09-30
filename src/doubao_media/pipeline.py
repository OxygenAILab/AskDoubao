"""Orchestration: watermark handling + generation + download in one call."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .browser import BrowserTransport, HybridTransport
from .client import DoubaoMediaClient
from .endpoints import WATERMARK_SETTINGS_ROUTE
from .errors import DoubaoError, DoubaoUpstreamError
from .models import (
    GeneratedImage,
    GeneratedVideo,
    GenerationOutcome,
    MembershipStatus,
    Ratio,
    WatermarkRequest,
    WatermarkState,
)
from .quota import PlanStatus
from .rate_limit import guard as _guard_generation
from .rate_limit import record as _record_generation
from .rate_limit import status as _throttle_status
from .transport import DoubaoTransport

_IMAGE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/avif": ".avif",
}


def _extension_from_url(url: str, fallback: str) -> str:
    path = url.split("?", 1)[0]
    suffix = Path(path).suffix
    if 1 < len(suffix) <= 6 and suffix[1:].isalnum():
        return suffix
    return fallback


class MediaPipeline:
    """The single entry point used by the skill and the MCP server.

    Responsibilities kept here (and deliberately nowhere else):

    1. Apply the requested watermark policy around a generation, restoring the
       account's previous state afterwards when asked.
    2. Run the generation and, optionally, download the resulting assets.
    3. Normalise every failure into a typed :class:`DoubaoError`.
    """

    # G   itHub @ O xyg e nA   ILab | Oxyg  enAI   Lab@S   t   ar  s   ails Clover
    def __init__(self, client: DoubaoMediaClient) -> None:
        self.client = client

    @classmethod
    def from_cookies(
        cls,
        cookies: Mapping[str, str],
        *,
        params: Mapping[str, str] | None = None,
        timeout: float = 60.0,
        transport: Any = None,
    ) -> MediaPipeline:
        return cls(
            DoubaoMediaClient.create(
                cookies, params=params, timeout=timeout, transport=transport
            )
        )

    @classmethod
    def from_session(
        cls,
        session: Any,
        *,
        transport_mode: str = "auto",
        headless: bool = True,
        browser_channel: str | None = None,
        timeout: float = 60.0,
    ) -> MediaPipeline:
        """Build a pipeline over the hybrid transport.

        ``transport_mode``:

        * ``"auto"`` (default) - plain HTTP for reads and CDN, real browser page
          for the risk-controlled generation endpoints.
        * ``"browser"`` - every write goes through the page (slowest, most robust).
        * ``"http"`` - no browser at all; fastest, but generation may be refused
          by ByteDance risk control with ``710022004``.
        """
        cookies = session.slim_cookies() if hasattr(session, "slim_cookies") else dict(session)
        cookie_domains = getattr(session, "cookie_domains", None)

        http = DoubaoTransport(cookies, timeout=timeout)
        browser = None
        if transport_mode in ("auto", "browser"):
            browser = BrowserTransport(
                cookies,
                cookie_domains=cookie_domains,
                headless=headless,
                channel=browser_channel,
            )
        return cls(
            DoubaoMediaClient(HybridTransport(http, browser, mode=transport_mode))
        )

    # Gi  t   H  ub@Oxyg  en  AILab | OxygenA  ILab   @Sta   r sailsC l   ov   er
    async def __aenter__(self) -> MediaPipeline:
        await self.client.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.client.__aexit__(exc_type, exc, tb)

    # -- watermark policy --------------------------------------------------

    async def _apply_watermark_policy(
        self, request: WatermarkRequest, outcome: GenerationOutcome
    ) -> WatermarkState | None:
        """Prepare the account watermark state; return the state to restore."""
        if not request.wants_off:
            return None
        if not request.confirm:
            raise DoubaoError(
                "removing the AI-generation watermark needs explicit confirmation: "
                f"official route is {WATERMARK_SETTINGS_ROUTE}. Pass confirm=True "
                "after the user agrees, or use mode='keep'."
            )
        current = await self.client.get_watermark_config()
        previous = current.ai_generated_image_video
        if previous is WatermarkState.OFF:
            outcome.watermark_state = previous.value
            return None  # already watermark-free; nothing to restore
        await self.client.set_watermark_removed(True)
        outcome.watermark_state = WatermarkState.OFF.value
        try:
            await self.client.set_creation_watermark(True)
        except DoubaoError as exc:
            outcome.warnings.append(f"user_config mirror not updated: {exc}")
        return previous

    async def _restore_watermark(
        self, previous: WatermarkState | None, outcome: GenerationOutcome
    ) -> None:
        if previous is None:
            return
        try:
            await self.client.set_watermark_removed(previous is WatermarkState.OFF)
            await self.client.set_creation_watermark(previous is WatermarkState.OFF)
            outcome.watermark_restored = True
        except DoubaoError as exc:
            outcome.warnings.append(f"watermark restore failed: {exc}")

    # -- generation --------------------------------------------------------

    async def generate_image(
        self,
        prompt: str,
        *,
        ratio: str | Ratio | None = None,
        reference_image: str | bytes | None = None,
        count: int = 1,
        watermark: WatermarkRequest | None = None,
        download_dir: str | Path | None = None,
        timeout: float | None = None,
    ) -> GenerationOutcome:
        """Generate one or more images, optionally watermark-free and downloaded."""
        _guard_generation()
        request = watermark or WatermarkRequest()
        outcome = GenerationOutcome(kind="image", prompt=prompt)
        ref_key = reference_image
        if isinstance(reference_image, (bytes, bytearray)):
            ref_key = await self.client.upload_reference_image(bytes(reference_image))

        # G  i   tH u  b   @O xyge nAI   La  b | O xyg  e   nA   ILa   b @S tarsail   sCl  o  ve r
        _record_generation()
        previous = await self._apply_watermark_policy(request, outcome)
        try:
            for _ in range(max(1, int(count))):
                kwargs: dict[str, Any] = {"ratio": ratio, "ref_image_key": ref_key}
                if timeout is not None:
                    kwargs["timeout"] = timeout
                images = await self.client.generate_image(prompt, **kwargs)
                for image in images:
                    image.watermarked = outcome.watermark_state == WatermarkState.ON.value
                    image.watermark_state = outcome.watermark_state
                outcome.images.extend(images)
        finally:
            if request.restore_after or request.mode == WatermarkRequest.RESTORE:
                await self._restore_watermark(previous, outcome)

        if download_dir is not None and outcome.images:
            await self.download_images(outcome.images, download_dir)
        return outcome

    async def generate_video(
        self,
        prompt: str,
        *,
        ratio: str | Ratio | None = None,
        duration: int | None = None,
        resolution: str | None = None,
        camera_movement: str | None = None,
        reference_image: str | bytes | None = None,
        watermark: WatermarkRequest | None = None,
        download_dir: str | Path | None = None,
        timeout: float | None = None,
    ) -> GenerationOutcome:
        """Generate a video, optionally watermark-free and downloaded."""
        _guard_generation()
        request = watermark or WatermarkRequest()
        outcome = GenerationOutcome(kind="video", prompt=prompt)
        ref_key = reference_image
        if isinstance(reference_image, (bytes, bytearray)):
            ref_key = await self.client.upload_reference_image(bytes(reference_image))

        _record_generation()
        previous = await self._apply_watermark_policy(request, outcome)
        try:
            kwargs: dict[str, Any] = {
                "ratio": ratio,
                "duration": duration,
                "resolution": resolution,
                "camera_movement": camera_movement,
                "ref_image_key": ref_key,
            }
            if timeout is not None:
                kwargs["timeout"] = timeout
            videos = await self.client.generate_video(prompt, **kwargs)
            for video in videos:
                video.watermarked = outcome.watermark_state == WatermarkState.ON.value
            outcome.videos.extend(videos)
        finally:
            if request.restore_after or request.mode == WatermarkRequest.RESTORE:
                await self._restore_watermark(previous, outcome)

        # GitHu   b   @Oxyge  n A  ILab | O x   y gen   AILab@ Sta r   s  ai l   sC lover
        if download_dir is not None and outcome.videos:
            await self.download_videos(outcome.videos, download_dir)
        return outcome

    # -- downloads ---------------------------------------------------------

    async def download_images(
        self, images: list[GeneratedImage], directory: str | Path
    ) -> None:
        target = Path(directory).expanduser()
        target.mkdir(parents=True, exist_ok=True)
        for index, image in enumerate(images, start=1):
            url = image.url or image.raw_url
            if not url:
                continue
            extension = _extension_from_url(url, ".png")
            path = target / f"image-{index:02d}{extension}"
            await self.client.transport.download_to(url, str(path))
            image.local_path = str(path)

    async def download_videos(
        self, videos: list[GeneratedVideo], directory: str | Path
    ) -> None:
        target = Path(directory).expanduser()
        target.mkdir(parents=True, exist_ok=True)
        for index, video in enumerate(videos, start=1):
            url = video.url
            if not url:
                continue
            extension = _extension_from_url(url, ".mp4")
            path = target / f"video-{index:02d}{extension}"
            await self.client.transport.download_to(url, str(path))
            video.local_path = str(path)

    async def fetch_watermark_free(
        self,
        *,
        uris: list[str] | None = None,
        vids: list[str] | None = None,
        download_dir: str | Path | None = None,
    ) -> dict[str, Any]:
        """Request watermark-free variants for assets that already exist."""
        result = await self.client.get_without_watermark(uris=uris, vids=vids)
        if not result["without_watermark"]:
            return result
        if download_dir is not None:
            target = Path(download_dir).expanduser()
            target.mkdir(parents=True, exist_ok=True)
            saved: list[str] = []
            urls = list(result["download_image"]) + list(result["download_video"])
            for index, url in enumerate(urls, start=1):
                if not isinstance(url, str) or not url.startswith("http"):
                    continue
                path = target / f"nowm-{index:02d}{_extension_from_url(url, '.bin')}"
                await self.client.transport.download_to(url, str(path))
                saved.append(str(path))
            result["local_paths"] = saved
        return result

    # -- status ------------------------------------------------------------

    async def membership(self, *, deep: bool = False) -> MembershipStatus:
        return await self.client.get_membership(deep=deep)

    # G   itHub@Ox  y g   enAIL a b | O  x   ygenAILab@S   ta rs ai   lsClover
    async def plan_status(
        self, *, near_limit_threshold: float = 90.0
    ) -> PlanStatus:
        """Subscription tier + image/video quota usage (the primary status call)."""
        return await self.client.get_plan_status(
            near_limit_threshold=near_limit_threshold
        )

    @staticmethod
    def throttle_status() -> dict[str, Any]:
        """Local generation throttle state (cooldown, daily budget)."""
        return _throttle_status()


async def run(coro: Any) -> Any:
    """Convenience wrapper for synchronous call sites (CLI / tests)."""
    return await coro


__all__ = ["MediaPipeline", "WatermarkRequest", "run", "DoubaoUpstreamError"]
