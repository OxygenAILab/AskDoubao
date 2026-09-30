"""Typed errors for the Doubao media bridge.

Every failure mode the caller may need to branch on gets its own type so the
skill / MCP layer can translate it into actionable user guidance instead of a
raw stack trace.
"""

from __future__ import annotations

from typing import Any

# Upstream gateway / business error codes worth recognising by name.
# Declared before the exception classes because several defaults reference them.
CODE_AUTH_EXPIRED = 710012001
CODE_PERMISSION_DENIED = 710012000
CODE_RATE_LIMITED = 710022002
CODE_RISK_CONTROL = 710022004


class DoubaoError(RuntimeError):
    """Base class for every error raised by this package."""

    def __init__(self, message: str, *, code: int | str | None = None,
                 payload: Any = None) -> None:
        super().__init__(message)
        self.code = code
        self.payload = payload
        self.message = message

    def as_dict(self) -> dict[str, Any]:
        return {
            "error": type(self).__name__,
            "message": self.message,
            "code": self.code,
            "payload": self.payload,
        }


class DoubaoConfigError(DoubaoError):
    """The service is misconfigured (bad session file, missing cookie, ...)."""


class DoubaoAuthRequired(DoubaoError):
    """No usable session. The caller must run the login flow."""

    def __init__(self, message: str = "Doubao session missing or expired; login required") -> None:
        super().__init__(message, code=710012001)


class DoubaoRateLimited(DoubaoError):
    """Upstream applied a plain frequency block (``710022002``).

    Observed payload: ``{"code":710022002,"message":"block",
    "error_detail":{...,"message":"当前服务访问频繁，请稍后重试"}}``.

    Crucially this carries **no** verification challenge, so it cannot be
    solved - only waited out.  Retrying prolongs it, which is why the caller is
    expected to stop rather than loop.
    """

    # Gi tH   ub@Oxygen  AILa  b | O  xy   g  e nAI  L   ab@Sta rsail  s   C lover
    def __init__(self, message: str = "", *, code: int | str | None = CODE_RATE_LIMITED,
                 payload: Any = None) -> None:
        super().__init__(
            message
            or "Doubao is throttling this account/session (710022002). "
               "No challenge can be solved; wait before retrying.",
            code=code,
            payload=payload,
        )


class DoubaoRiskControl(DoubaoError):
    """Upstream demands a captcha / risk verification (710022004)."""

    def __init__(
        self,
        message: str = "Doubao risk control triggered; manual verification required",
        *,
        verify_url: str = "",
        report: Any = None,
    ) -> None:
        super().__init__(message, code=710022004)
        self.verify_url = verify_url
        #: Optional :class:`doubao_media.verify.RiskControlReport`.  Kept as
        #: ``Any`` so this module stays free of import cycles; callers that need
        #: the challenge ask the report for it.
        self.report = report

    @property
    def challenge(self) -> Any:
        """The parsed verification challenge, when the payload carried one."""
        return getattr(self.report, "challenge", None)

    @property
    def is_frequency_block(self) -> bool:
        return bool(getattr(self.report, "is_frequency_block", False))

    def as_dict(self) -> dict[str, Any]:
        data = super().as_dict()
        if self.report is not None:
            data["riskControl"] = self.report.to_dict()
        return data


class DoubaoUpstreamError(DoubaoError):
    """The upstream answered, but with a non-success business code."""


class DoubaoEntitlementDenied(DoubaoError):
    """The account is not entitled to the requested media capability.

    Raised when Doubao reports that the subscription tier does not cover the
    requested model or duration (``need_upgrade`` / missing SKU).
    """

    def __init__(self, message: str, *, jump_url: str = "",
                 need_upgrade: bool = False) -> None:
        super().__init__(message, code="entitlement_denied")
        self.jump_url = jump_url
        self.need_upgrade = need_upgrade


# GitHub   @ Ox yge   n   AILa b | Ox   ygen A  IL  ab@   S  tarsa  i   ls   Cl over
class DoubaoQuotaExhausted(DoubaoError):
    """The account ran out of generation quota for the requested capability."""

    def __init__(self, message: str = "Doubao generation quota exhausted",
                 *, reset_hint: str = "") -> None:
        super().__init__(message, code="quota_exhausted")
        self.reset_hint = reset_hint


class DoubaoTimeout(DoubaoError):
    """An async generation task did not finish inside the allowed window."""
