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
<!-- Git   Hub@Apris   mLab | Apris mLab@Star  sa  i  ls Clov  e r -->

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

## 2 Preflight (always)

1. Call **`doubao_status`**. Report the tier and the remaining image/video
   percentage, and say which generator you intend to use.
2. If the tool reports `ok: false` with `error: DoubaoAuthRequired`, call
   **`doubao_login_start`**, show the returned `qrPngBase64` to the user as an
   image, then poll with **`doubao_login_poll`**.
3. If `runningLow.image` or `runningLow.video` is true, tell the user before
   spending the remaining quota.

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
<!-- G   i   t  Hub@   A  pr  i   sm  La  b | A pri   smLab@  Star   sailsClo  v   er -->

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
<!-- G itH   u  b  @Ap  ri  s  mLab | Apr ism  L  ab@  S  tarsail   sC love r -->

| Returned error | Meaning | What to do |
|----------------|---------|------------|
| `DoubaoAuthRequired` | session missing or expired | run the login flow (§2.2) |
| `DoubaoRiskControl` | `710022004`: known, see §6 | report honestly, do not retry blindly |
| `DoubaoQuotaExhausted` | quota gone for that modality | report `nextReset`, offer `upgrade.url` |
| `DoubaoEntitlementDenied` | plan does not cover the request | report `upgrade.name` / `jumpUrl` |
| `DoubaoTimeout` | async task did not finish | report the elapsed time; do not auto-retry |
| `DoubaoUpstreamError` | anything else | quote the message verbatim |

Never retry a quota or entitlement failure. One retry is acceptable *only* for
a pure network error.

## 6 Known limitation — risk control (`710022004`)

Doubao may answer a generation request with
`{"code":710022004,"message":"rate limited"}` together with
`ext.subtype = "semantic_reasoning"` and `verify_scene = "doubao_message_web"`.

This is a server-side risk decision on the account/device. It is **not** caused
by a missing signature: the request carries a valid `X-Bogus`, and read-only
endpoints on the same session keep working. It was reproduced identically
through plain HTTPS, through headless Chromium, through headful Chromium,
through the Edge channel, and with the desktop client's own session.

When this happens:

1. Tell the user the account is under Doubao risk control, quoting the code.
2. Suggest opening the Doubao client once and completing any verification it
   shows, then retrying later.
3. Fall back to another generator, or ask the user how to proceed.

Do not present this as a bug in the request we build, and do not loop.

## 7 Reference

| Resource | Path |
|----------|------|
| Protocol evidence, enums, endpoint table | `docs/protocol.md` |
| ADR — why the implementation looks like this | `docs/adr/` |
| Python package | `src/doubao_media/` |
| Read-only live check | `scripts/live_probe.py` |
| Session refresh (incl. `msToken`) | `scripts/refresh_session.py` |
