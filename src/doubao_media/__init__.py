"""Doubao (豆包) media bridge - image & video generation through the official web API.

Scope discipline: this package generates images and videos only.  It deliberately
exposes no chat, no document, and no file-transfer capability.
"""

from __future__ import annotations

from .errors import (
    DoubaoAuthRequired,
    DoubaoError,
    DoubaoRateLimited,
    DoubaoRiskControl,
    DoubaoUpstreamError,
)
from .models import GeneratedImage, GeneratedVideo, MembershipStatus, Ratio, WatermarkState
from .pipeline import MediaPipeline, WatermarkRequest

__version__ = "26.0.0-alpha.1"

__all__ = [
    "DoubaoAuthRequired",
    "DoubaoError",
    "DoubaoRateLimited",
    "DoubaoRiskControl",
    "DoubaoUpstreamError",
    "GeneratedImage",
    "GeneratedVideo",
    "MediaPipeline",
    "MembershipStatus",
    "Ratio",
    "WatermarkRequest",
    "WatermarkState",
    "__version__",
]
