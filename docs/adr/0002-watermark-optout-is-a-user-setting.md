# ADR 0002 — Watermark removal is a user setting, not a bypass

- **Date**: 2026-09-27
- **Status**: Accepted
- **Version**: v26.0.0-alpha.1

## Context

The original request asked for "豆包官方入口的 AI 生成水印去除" via
`设置 -> 内容生成与产物设置 -> AI 生成水印管理 -> 生成的图片、视频 -> 无水印`.

Reverse engineering located the exact mechanism: Doubao exposes a first-party
privacy switch.

| Item | Value |
|------|-------|
| Read | `POST /privacy/watermark_config/get` |
| Write | `POST /privacy/watermark_config/set` |
| Objects | `150` = images/videos, `151` = documents/sheets/PPT |
| Values | `1` = opt-out ON (no watermark), `0` = watermark kept |

The bundled UI (`WatermarkSetting`, webpack module `8990` of `9816.js`) shows a
confirmation dialog before enabling it, whose copy states that the user accepts
the consequences and that removing the mark is their responsibility.

## Decision

Expose the switch, but **never flip it implicitly**:

1. Every generation tool takes an explicit `remove_ai_watermark` **and**
   `confirm_watermark_removal`; the pipeline raises when removal is requested
   without confirmation, quoting the official settings route in the error.
2. `doubao_watermark_opt_out` requires the same confirmation to enable removal,
   and always allows `enabled=false` to restore the default without any gate.
3. `restore_watermark_after` exists so a one-off request can leave the account
   exactly as it was found.
4. The skill instructs the agent to reproduce Doubao's own consent step in
   natural language rather than silently changing an account setting.

## Rationale

- The switch is a **privacy/consent control**, and the platform deliberately
  gates it behind an acknowledgement. Automating the write while skipping the
  consent step would make this tool strictly more permissive than the product it
  drives.
- Only `POST .../set` is needed; no CDN-template mangling, no pixel
  post-processing, no third-party library. That keeps the implementation small
  and keeps behaviour aligned with what the desktop/web client does.
- The broader brand-watermark rule is plan-dependent
  (`普通用户仍会保留"豆包"品牌水印，豆包/飞书订阅用户不保留品牌水印`), so the
  skill reports the real state instead of promising a completely clean asset.

## Consequences

- A caller who wants the watermark gone must say so twice (request + confirm),
  which is intentional friction.
- `get_without_watermark` (for assets that already exist) is implemented in the
  client but **not** surfaced as an MCP tool yet, because its `version` handshake
  could not be verified live. It returns `without_watermark: false` rather than
  failing when an account is not entitled.
- If Doubao later removes or renames objects `150/151`, `endpoints.py` is the
  single place to change.
