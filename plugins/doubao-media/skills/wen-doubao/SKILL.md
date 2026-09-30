---
name: wen-doubao
description: >
  Use Doubao (豆包) as a fallback image and video generator when the primary
  image capability is unavailable. Trigger when the user's main image model
  (for example "image 2" or "image 2.5") returns a permission/entitlement error,
  when its quota is exhausted or nearly exhausted, when a video model is not
  entitled on the current plan, or when the user explicitly asks to generate
  media through Doubao / 问豆包. Also use it to report a Doubao account's
  subscription plan and remaining image/video quota, and to read or change the
  official AI-generation watermark opt-out. Scope is strictly image and video
  generation: this skill never handles chat, documents, music or file transfer
  through Doubao.
---

# 问豆包 (Ask Doubao)

<p style="font-size:22px;text-align:center"><b>当主图像/视频能力不可用时，改用豆包生成</b></p>

Doubao is a **fallback media generator**. Route to it only when the primary
capability cannot serve the request, or when the user asks for it by name.
<!-- Git  Hub  @O xygenAI  La   b | O   xy  genAILab @Starsail  s   Cl   over -->

## 1 When to invoke

Invoke when **any** of these is true:

| Condition | Signal you will have seen |
|-----------|---------------------------|
| Primary image model unavailable | tool error naming `image 2` / `image 2.5`, "not entitled", "unsupported model" |
| Primary image quota nearly gone or gone | account reports remaining quota below the user's comfort threshold, or generation is refused |
| Primary video model unavailable | video request refused for entitlement or quota reasons |
| User asks directly | "用豆包生成", "问豆包", "Doubao fallback" |
| User wants the Doubao plan/quota/watermark state | any question about 豆包套餐 / 额度 / 水印 |

Do **not** invoke for chat, documents, music, code, or file transfer. Doubao's
chat side is explicitly out of scope here; if the user wants chat, tell them
this skill does not do it.

> **Budget honesty.** Both generation tools spend the user's Doubao quota. Say
> so before calling them, and never loop generation calls to "try again".
>
> **Throttling honesty.** Doubao blocks aggressive callers (`710022002`). Issue
> one generation per user request, never a batch or a retry loop. If a block
> appears, stop and tell the user to wait; see §6.2.

> **Measured limits.** In practice **1–2** generation calls in a short window are
> enough to trigger the block, and a call that is refused or challenged **still
> consumes quota**. Treat every generation as expensive and irreversible: one per
> user request, with real spacing between requests.

## 2 Preflight (always)

1. Call **`doubao_status`**. Report the tier and the remaining image/video
   percentage, and say which generator you intend to use.
2. If the tool reports `ok: false` with `error: DoubaoAuthRequired`, call
   **`doubao_login_start`**, show the returned `qrPngBase64` to the user as an
   image, then poll with **`doubao_login_poll`**.
3. If `runningLow.image` or `runningLow.video` is true, tell the user before
   spending the remaining quota.

### Tool surface

| Tool | Spends quota? | Purpose |
|------|---------------|---------|
| `doubao_status` | no | plan tier, image/video quota, next reset |
| `doubao_watermark_status` | no | read the watermark opt-out switches |
| `doubao_login_start` / `doubao_login_poll` | no | adopt a local session, or scan a QR code |
| `doubao_generate_image` | **yes** | generate and save an image |
| `doubao_generate_video` | **yes** | generate and save a video (scarcest quota) |
| `doubao_watermark_opt_out` | no | change the watermark switch (removal needs confirmation) |
| `doubao_verify_challenge` | no | open Doubao's security check for the user to solve |

### Reading the status payload

| Field | Meaning |
|-------|---------|
| `tierLabel` | plan name, e.g. `标准套餐` |
| `planSku` | e.g. `doubao_personal_std` |
| `upgrade.name` / `upgrade.url` | the paid upgrade Doubao itself offers |
| `image.usedPercent` / `remainingPercent` | image quota usage |
| `video.usedPercent` / `remainingPercent` | video quota usage |
| `nextReset` | end of the current rolling window |
| `quotaManagementUrl` | the official 订阅与额度管理 page |

## 3 Generating

### Image

```
doubao_generate_image(
    prompt              = "<the user's prompt>",
    ratio               = "1:1" | "16:9" | "9:16" | "4:3" | "3:4",
    count               = 1..n,
    reference_image_path= "<optional local image for image-to-image>",
    remove_ai_watermark = true|false,
    confirm_watermark_removal = true|false,
    restore_watermark_after   = true|false,
    output_dir          = "<where to save>",
)
```

### Video

```
doubao_generate_video(
    prompt            = "<the user's prompt>",
    ratio             = "16:9" | "9:16" | "1:1",
    duration_seconds  = 5 | 10 | 15,
    resolution        = "<optional>",
    camera_movement   = "<optional, e.g. 缓慢推进>",
    reference_image_path = "<optional local image for image-to-video>",
    remove_ai_watermark, confirm_watermark_removal, restore_watermark_after,
    output_dir,
)
```

Video is the scarcest resource. Prefer a single attempt, and confirm with the
user first when `status.video.remainingPercent` is low.

Every result carries `images[].local_path` / `videos[].local_path`. Report the
absolute paths, and say whether the file is watermark-free
(`watermarkState: "off"` means watermark-free).

## 4 The AI-generation watermark

The switch is an **official Doubao setting**, not a hack:
<!-- Git  Hub@  OxygenA  IL  a  b | OxygenAI  Lab@ Sta  rsailsC   lover -->

```
设置 -> 内容生成与产物设置 -> AI 生成水印管理 -> 生成的图片、视频 -> 无水印
```

Protocol facts (see `docs/protocol.md` for the full evidence table):

| Item | Value |
|------|-------|
| Read | `POST /privacy/watermark_config/get` with `{"objects":[150,151]}` |
| Write | `POST /privacy/watermark_config/set` with `{"configs":[{"object":150,"value":1,"version":0}]}` |
| Object 150 | 生成的图片、视频 |
| Object 151 | 生成的文档、表格、PPT |
| `value: 1` | opt-out **ON** = delivered **without** the watermark |
| `value: 0` | opt-out off = watermark kept |

### Rules

1. Doubao's own UI shows a confirmation dialog in which the user accepts
   responsibility for removing the mark. Reproduce that gate: **never** set
   `remove_ai_watermark` without the user's explicit agreement, and always pass
   `confirm_watermark_removal: true` only after they agree.
2. When the user has not been asked yet, generate with the watermark and offer
   the opt-out as a follow-up — do not silently change an account setting.
3. Use `restore_watermark_after: true` for one-off requests so the account
   returns to its previous state afterwards.
4. Note the platform's own terms: the opt-out covers the "AI 生成" mark, while
   brand watermark rules depend on the plan (`普通用户仍会保留"豆包"品牌水印`).
   State this plainly instead of promising a fully clean file.
5. If the account cannot use the switch, the tool returns `needUpgrade: true`
   with a `jumpUrl`. Report that instead of retrying.

Read the current state any time with **`doubao_watermark_status`**, and change
it with **`doubao_watermark_opt_out(enabled=true, confirm_removal=true)`**.

## 5 Failure handling

Map the returned `error` directly:
<!-- GitHub@  OxygenAI L ab | OxygenAIL   ab@Sta  rsail  sClov e  r -->

| Returned error | Meaning | What to do |
|----------------|---------|------------|
| `DoubaoAuthRequired` | session missing or expired | run the login flow (§2.2) |
| `DoubaoRiskControl` | `710022004`: a **solvable** security check | go to §6.1 |
| `DoubaoRateLimited` | `710022002`: plain **frequency block** | go to §6.2 — stop calling |
| `DoubaoQuotaExhausted` | quota gone for that modality | report `nextReset`, offer `upgrade.url` |
| `DoubaoEntitlementDenied` | plan does not cover the request | report `upgrade.name` / `jumpUrl` |
| `DoubaoTimeout` | async task did not finish | report the elapsed time; do not auto-retry |
| `DoubaoUpstreamError` | anything else | quote the message verbatim |

Never retry a quota, entitlement, or **rate-limit** failure. One retry is
acceptable *only* for a pure network error.

## 6 Risk control

Risk control has **two distinct forms**, and confusing them is how an agent
burns an account. The failed call tells you which one you have: read
`riskControl.kind` in the returned payload.

### 6.1 `verification_required` — solvable, once

```json
{"riskControl": {"kind": "verification_required", "recoverable": true,
                 "challenge": {"subtype": "slide", "hint": "拖动滑块完成拼图"}}}
```

Payload: `710022004` / `"rate limited"` carrying
`ext.decision = {type: "verify", subtype: ..., detail: "<blob>"}`.

This is a **challenge, not a ban**. It is *not* caused by a missing signature:
the request carries a valid `X-Bogus`, and read-only endpoints keep working.

**Do this — in order, once:**

1. Call `doubao_verify_challenge` (optionally passing the returned `challenge`).
   A browser window opens showing Doubao's own verification widget.
2. Tell the user plainly: *"豆包要求完成一次安全验证，请在弹出的窗口中操作。"*
   Wait for the tool to report `ok: true`.
3. Retry the generation **exactly once**. If it succeeds, continue normally.
4. If it fails again, surface it and stop — do not enter a retry loop.

Never attempt to automate the challenge itself. `subtype` may be `slide`
(slider puzzle) or `semantic_reasoning`; both must be solved by the account
holder, which is also what Doubao's own UI requires.

#### Implementation notes (already handled — do not re-derive)

The widget is rendered through the page's own SDK, `window.verifySDK`. Six
constraints silently prevent rendering if violated, all encoded in
`doubao_media/verify.py`:

| # | Constraint |
|---|------------|
| 1 | Drive `window.verifySDK` — **not** `bdCaptcha.CaptchaVerify` (raw CDN class), **not** `verifyCenter` (inert wrapper) |
| 2 | `renderCaptcha({...})` with **`aid` at the top level**, or the SDK merges into the page's empty defaults and mounts nothing |
| 3 | `aid` must be an **int**; a string throws `"...of type int"`, which `autoRender` rethrows as the misleading `"verify_data is required"` |
| 4 | Supply **`did`** (device id), else the SDK asks `/vc/setting?...&did=0` and never renders |
| 5 | The container needs a **definite px height**; the card is `h-full w-full` and collapses at `min-height` |
| 6 | Clear `window.__vc_is_render__`, which short-circuits `renderCaptcha` |

`verify_data` is the parsed `decision` object (not just its `detail` blob).
Rendering is visually verified; the solve→retry loop is covered by unit tests
but has not been exercised live (the account was throttled when it became
available). Full evidence: `docs/protocol.md` §5.1.1.

### 6.2 `frequency_block` — not solvable, only waitable
<!-- GitHu b@Oxyge nA   ILab | OxygenA  ILab @ S ta   r  s a ilsC   lo ver -->

```json
{"riskControl": {"kind": "frequency_block", "recoverable": false,
                 "nextStep": "Stop calling - retrying prolongs the block."}}
```

Payload: `710022002` / `"block"` /
`"当前服务访问频繁，请稍后重试"`, with **no** `decision` object.

There is no challenge to solve: the account or session is being throttled for
calling too often. **The only correct action is to stop.** Do not call
`doubao_verify_challenge`, do not retry, do not loop — every extra request makes
it worse.

Measured behaviour (2026-09-30): roughly **1–2** dense generation calls are
enough to produce this block, refused calls still burn quota, and once the block
expires the account returns to `710022004` — which dense calling will push
straight back into `710022002`. After a successful verification, retry **once**
and then stop.

Tell the user: *"豆包当前限制了访问频率（710022002），需要等待一段时间。这不是可以立即解决的验证，请稍后再试。"* Then fall back to another
generator, or ask how they want to proceed.

> This form is **self-inflicted by over-calling**. Treat it as a signal that the
> generation loop was too aggressive; back off rather than trying harder.

## 7 Reference

| Resource | Path |
|----------|------|
| Protocol evidence, enums, endpoint table | `docs/protocol.md` |
| ADR — why the implementation looks like this | `docs/adr/` |
| Python package | `src/doubao_media/` |
| Read-only live check | `scripts/live_probe.py` |
| Session refresh (incl. `msToken`) | `scripts/refresh_session.py` |
