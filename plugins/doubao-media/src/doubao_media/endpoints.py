"""Endpoint + enum tables reverse engineered from the official Doubao front end.

Every constant here was confirmed against the bundled desktop web assets
(``%LOCALAPPDATA%\\Doubao\\Application\\app\\local_webcontents\\extensions\\ai-views``)
and, where marked, against a live request.  The detailed evidence table lives in
``docs/protocol.md``.
"""

from __future__ import annotations

from enum import IntEnum

BASE_URL = "https://www.doubao.com"
"""Origin used by every endpoint below (verified live)."""

AID = "497858"
"""Doubao web application id (verified live in the desktop client bundle)."""

WEB_VERSION_CODE = "20800"
PC_VERSION = "2.1.7"
CHROMIUM_BUILD = "148.0.7816.0"
CHROME_VERSION = "148.0.0.0"


class SseEventType(IntEnum):
    """SSE ``event_type`` values on ``/samantha/chat/completion``."""

    HEARTBEAT = 1
    CMPL = 2001
    ACK = 2002
    FIN = 2003
    CMD = 2004
    ERR = 2005
    VERBOSE = 2010


class ContentType(IntEnum):
    """``content_type`` values carried inside SSE ``message`` objects."""

    SAMANTHA_TEXT = 2001
    SAMANTHA_SUGGEST = 2002
    SAMANTHA_LOADING = 2003
    SAMANTHA_MUSIC_GEN_INPUT = 2005
    SAMANTHA_SEARCH_TEXT = 2008
    SAMANTHA_IMAGE_INPUT = 2009
    SAMANTHA_IMAGE_OUTPUT = 2010
    SAMANTHA_VIDEO_GEN_INPUT = 2020
    SAMANTHA_VIDEO_GEN_OUTPUT = 2021
    SAMANTHA_TEXT_V2 = 10000
    BLOCK_TYPE_THINK = 10040


class SkillType(IntEnum):
    """``skill.skill_type`` selector used by the generation requests."""

    IMAGE_GEN = 3
    VIDEO_GEN = 17


class UserConfigType(IntEnum):
    """``/creativity/user_config/{get,set}`` ``config_type`` values."""

    WATERMARK_OPTION = 1
    AUTHORIZATION_OPTION = 2


class WatermarkObjectId(IntEnum):
    """``/privacy/watermark_config`` ``objects`` selectors.

    Verified in the desktop bundle (webpack module ``8990`` of ``9816.js``,
    the ``WatermarkSetting`` component)::

        # G  i tHub@ Apris m   Lab | A   p   rismLab@ St ar  sail  sCl o ver
        i[i.ImageVideoRemoval=150]; i[i.OfficeResourceRemoval=151]
    """

    IMAGE_VIDEO = 150          # 生成的图片、视频
    OFFICE_RESOURCE = 151      # 生成的文档、表格、PPT


# Gi tHub@A prismL  ab | A  p ri   s   m Lab@St   ar  sa ils  Cl   over
class WatermarkValue(IntEnum):
    """``value`` field semantics for a watermark config entry.

    Note the inversion: ``ON`` means the opt-out switch is on, i.e. the
    product is delivered **without** the "AI 生成" watermark.  The UI confirms
    this - ``AIwatermarking_popupwindow_pop_on_cn = "无水印"``.
    """

    KEEP = 0      # "Off"  -> 有 · 保留 AI 生成水印
    REMOVED = 1   # "On"   -> 无 · 去除 AI 生成水印


class TaskStatus(IntEnum):
    """Generic async-task state (``/alice/resource/watermark_task`` family)."""

    PENDING = 0
    RUNNING = 1
    SUCCESS = 2
    FAILED = 3


# ---------------------------------------------------------------------------
# Endpoint table - path constants only; the transport adds the common query.
# ---------------------------------------------------------------------------

EP_SAMANTHA_COMPLETION = "/samantha/chat/completion"
EP_USER_CONFIG_GET = "/creativity/user_config/get"
EP_USER_CONFIG_SET = "/creativity/user_config/set"
EP_RESOURCE_WITHOUT_WATERMARK = "/creativity/resource/get_without_watermark"
EP_WATERMARK_CONFIG_GET = "/privacy/watermark_config/get"
EP_WATERMARK_CONFIG_SET = "/privacy/watermark_config/set"
EP_SUBSCRIPTION_ENTRY_CONFIG = "/alice/commerce/sale/subscription/entry/config/"
EP_SUBSCRIPTION_DETAIL = "/alice/commerce/sale/subscription/detail/"
EP_SUBSCRIPTION_LIST = "/alice/commerce/sale/subscription/list/"
EP_SUBSCRIPTION_OVERVIEW = "/alice/commerce/sale/subscription/overview/"
EP_SUBSCRIPTION_QUOTA_SUMMARY = "/alice/commerce/sale/subscription/quota/summary/"
EP_ENTITLEMENT_USAGE_DETAIL = "/alice/commerce/sale/entitlement/usage_detail/"
EP_USER_ENTITLEMENT = "/alice/commerce/intake/entitlement/query"
EP_HOMEPAGE = "/samantha/aispace/homepage"
EP_NODE_INFO = "/samantha/aispace/node_info"
EP_DOWNLOAD_INFO = "/samantha/aispace/get_download_info"
EP_VIDEO_PLAY_INFO = "/samantha/video/get_play_info"
EP_VIDEO_GEN_INFO = "/samantha/video/query_video_gen_info"
EP_GET_FILE_URL = "/alice/message/get_file_url"
EP_UPLOAD_IMAGE = "/samantha/pages/upload_image"
EP_PREPARE_UPLOAD = "/alice/resource/prepare_upload"
EP_LOGIN_CSRF = "/passport/safe/csrf_token/"
EP_LOGIN_QRCODE = "/passport/web/get_qrcode/"
EP_LOGIN_CHECK = "/passport/web/check_qrconnect/"

#: Commerce "product line" values used by the quota / overview endpoints.
PRODUCT_LINE_IMAGE = "image"
PRODUCT_LINE_VIDEO = "video"

#: Entitlement scenes (``/alice/commerce/intake/entitlement/query``).
ENTITLEMENT_SCENE_FINGERPRINT = "fingerprint"

#: Doubao's documented settings route for the official watermark opt-out.
WATERMARK_SETTINGS_ROUTE = (
    "设置 -> 内容生成与产物设置 -> AI 生成水印管理 -> 生成的图片、视频 -> 无水印"
)
