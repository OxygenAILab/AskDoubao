# CLAUDE.md

Guidance for agents working in this repository.

## What this is

A Doubao (豆包) **fallback image/video generator**, exposed as a Codex plugin
(skill + MCP server). Scope is deliberately limited to media generation: no
chat, no documents, no music, no file transfer.

## Layout

| Path | Role |
|------|------|
| `src/doubao_media/` | the package - **single source of truth** |
| `plugins/doubao-media/` | the distributable plugin |
| `plugins/doubao-media/src/`, `.../docs/` | **generated** by `scripts/build_plugin.py` |
| `tests/` | unit tests, no network access |
| `docs/protocol.md` | the reverse-engineering evidence table |
| `docs/adr/` | why the design looks the way it does |
| `_scripts/bc/insert_watermark.py` | the organisation watermark tool |

## Commands

```powershell
$env:PYTHONPATH="src"
python -m pytest tests -q                  # 49 tests
python -m ruff check src tests scripts     # lint
python scripts/build_plugin.py             # regenerate the plugin payload
python scripts/build_plugin.py --check     # CI gate: the plugin must not drift
python _scripts/bc/insert_watermark.py --check
```

**`plugins/doubao-media/src` must never be edited by hand.** Edit
`src/doubao_media`, then run `build_plugin.py`. CI fails on drift.

## Hard rules

1. **Never probe with real generation calls.** Repeated attempts trigger
   `710022002` (frequency block, unsolvable - see `docs/adr/0003`). Use the
   bundled-asset tooling for protocol work, and issue at most one generation per
   user request.

   **This rule exists because it was broken and it caused real harm.** Repeated
   automated calls during development escalated risk control from
   scene-scoped (web only) to **account/device-scoped**, and the account holder
   lost both web and desktop access, keeping only mobile. See `docs/adr/0004`.
   Consequently generation is now **disabled by default**
   (`DOUBAO_MEDIA_ENABLE_GENERATION=1` to opt in) and bounded by
   `DOUBAO_MEDIA_MIN_INTERVAL` plus `DOUBAO_MEDIA_DAILY_CAP`. Do not weaken these
   guards to make a test pass.
2. **Never automate the security challenge.** `710022004` carries a verification
   blob that only the account holder may solve, in a visible window. No
   slider-solving, no blob re-signing.
3. **Never flip the watermark switch implicitly.** Removal requires explicit
   confirmation, mirroring Doubao's own consent dialog (`docs/adr/0002`).
4. **Never log or return cookie values.** Session files are DPAPI-encrypted.

## Key protocol facts

Full table in `docs/protocol.md`. The three that bite hardest:

- `/privacy/watermark_config`: `objects` **150** = image/video, **151** =
  document; `value: 1` means the watermark is **removed** (inverted from
  intuition).
- Quota endpoints take `product_lines` (a **list**). The singular form silently
  returns an empty structure instead of erroring.
- `msToken` lives on `.bytedance.com`, **not** `.doubao.com`, and is still
  required.
