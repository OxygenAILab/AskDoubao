# ADR 0001 — One hybrid transport, not two clients

- **Date**: 2026-09-27
- **Status**: Accepted
- **Version**: v26.0.0-alpha.1

## Context

Two reference implementations were available:

| Reference | Approach |
|-----------|----------|
| `wangchuxiaoji-oss/doubao2api` | Playwright page + in-page `fetch` for everything; documented that plain HTTP gets rate-limited |
| `LauZzL/doubao-downloader` | Extension/userscript that monkey-patches `JSON.parse` inside the page |

Both assume a browser is present.  This project must run inside an agent, where
startup cost, headless reliability and a small dependency surface matter.

## Decision

Build **one** client over a **transport interface** with three implementations
and one selector:

| `transport_mode` | Reads (plan/quota/watermark) | Generation | CDN download |
|---|---|---|---|
| `http` | plain `httpx` | plain `httpx` | plain `httpx` |
| `auto` (default) | plain `httpx` | real browser page | plain `httpx` |
| `browser` | plain `httpx` | real browser page | plain `httpx` |

`HybridTransport` owns the routing so no caller needs to know which path a
given endpoint takes.

## Rationale

1. **Measured, not assumed.** Read-only endpoints were verified to answer
   `code: 0` over plain HTTP on a real session (`watermark_config/get`,
   `subscription/entry/config`, `subscription/overview`, `subscription/list`,
   `subscription/quota/summary`). Paying browser startup for them would be pure
   waste.
2. **Generation is different.** It is the only surface that returns
   `710022004`, so it is the only surface that gets the browser.
3. **Downloads are plain HTTP.** CDN URLs are signed and not risk-controlled;
   streaming them through a browser page would be slower and more fragile.
4. **One selector, no forks.** Two parallel clients would drift. The mode is a
   constructor argument, and `http` stays available for environments without
   Playwright — with the honest caveat that generation may be refused.

## Consequences

- Playwright is an **optional** dependency; the plan/quota/watermark features
  work without it.
- `710022004` remains reachable even through the browser (see
  `docs/protocol.md` §5). The transport choice narrows the risk surface; it does
  not eliminate the server-side decision. This is documented rather than papered
  over.
- A future fix (profile reuse, warm-up) means changing `BrowserTransport` only,
  because routing already lives in one place.
