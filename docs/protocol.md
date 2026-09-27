# Doubao Web API — Reverse-Engineering Notes

<p style="font-size:28px;text-align:center"><b>豆包 Web API 逆向记录</b></p>

> Every endpoint below was verified against the live service on 2026-09-27
> unless the row is explicitly marked *static only*.

---

## 1 How these facts were obtained

Three independent sources were cross-checked; a fact is only trusted when at
least two agree.

| # | Source | What it gives |
|---|--------|---------------|
| 1 | The **bundled web assets of the Doubao desktop client** (`%LOCALAPPDATA%\Doubao\Application\app\local_webcontents\extensions\ai-views`) | Authoritative endpoint paths, enum values, request shapes, UI copy |
| 2 | **Live HTTP traffic** against `https://www.doubao.com` with a real session | Confirmation that the endpoint accepts the request, and the true response shape |
| 3 | The two reference repositories (`wangchuxiaoji-oss/doubao2api`, `LauZzL/doubao-downloader`) | Protocol context, risk-control codes, watermark-free asset fields |

Extraction helper: `work/_scratch/extract_api.py` (method ↔ path pairs) and
`work/_scratch/dump_mod.py` (single webpack module).

---

## 2 Transport facts

| Item | Value | Evidence |
|------|-------|----------|
| Origin | `https://www.doubao.com` | live |
| `aid` | `497858` (web) | live; also `582478` in older bundles |
| Common query block | `aid`, `real_aid`, `device_platform=web`, `language=zh`, `pkg_type=release_version`, `version_code=20800` | client bundle |
| Cookie auth | `sessionid`, `sessionid_ss`, `sid_guard`, `sid_tt`, `sid_ucp_v1`, `ssid_ucp_v1`, `uid_tt`, `ttwid`, `odin_tt`, `s_v_web_id`, `passport_csrf_token` | live |
| CSRF header | `x-tt-passport-csrf-token: <passport_csrf_token>` | client bundle |
| **`msToken`** | Lives on **`.bytedance.com`**, *not* `.doubao.com`, and must still be sent | client bundle + cookie-store inspection |
| `device_id` / `web_id` | Read from the page's `localStorage` (`samantha_web_web_id`, `__tea_cache_tokens_497858`) | client bundle |

### 2.1 Login (QR) — proven to work with plain HTTP, no browser

```
GET  /                                       -> picks up ttwid / basic cookies
GET  /passport/safe/csrf_token/?aid=497858    -> passport_csrf_token
GET  /passport/web/get_qrcode/?next=&aid=     -> token + base64 PNG
GET  /passport/web/check_qrconnect/?token=    -> new | scanned | confirmed
GET  <redirect_url>                           -> sessionid family
```

Verified end-to-end: the QR PNG was rendered and `check_qrconnect` answered
`{"status":"new"}` with `error_code: 0`.

---

## 3 Endpoints used by this project

| Path | Method | Purpose | Status |
|------|--------|---------|--------|
| `/samantha/chat/completion` | POST | Image / video / music generation (SSE) | live (risk-controlled, see section 5) |
| `/creativity/user_config/get` | POST | Watermark mirror (`config_type=1`) | **live, code 0** |
| `/creativity/user_config/set` | POST | Watermark mirror write | static only |
| `/privacy/watermark_config/get` | POST | **Official watermark switch read** | **live, code 0** |
| `/privacy/watermark_config/set` | POST | **Official watermark switch write** | static only |
| `/creativity/resource/get_without_watermark` | POST | Watermark-free variant of an existing asset | static only |
| `/alice/commerce/sale/subscription/entry/config/` | POST | Plan name, upgrade CTA | **live, code 0** |
| `/alice/commerce/sale/subscription/overview/` | POST | SKU, subscription window | **live, code 0** |
| `/alice/commerce/sale/subscription/list/` | POST | Every subscription row | **live, code 0** |
| `/alice/commerce/sale/subscription/quota/summary/` | POST | **Quota windows + usage %** | **live, code 0** |
| `/alice/commerce/sale/entitlement/usage_detail/` | POST | Usage detail for one entitlement | live, code 0 |
| `/alice/commerce/intake/entitlement/query` | POST | Entitlement by scene | static only |
| `/samantha/aispace/homepage` | POST | "我的创作" node id | static only |
| `/samantha/aispace/node_info` | POST | `vid` to node id | static only |
| `/samantha/aispace/get_download_info` | POST | node id to `main_url` | static only |
| `/samantha/video/get_play_info` | POST | `vid` to playable URL | static only |
| `/samantha/pages/upload_image` | POST (multipart) | Reference image upload | static only |
| `/alice/message/get_file_url` | POST | Short uri to CDN uri | static only |

---

## 4 Enums

### 4.1 SSE `event_type`

| Value | Name | Meaning |
|-------|------|---------|
| 1 | HEARTBEAT | keep-alive |
| 2001 | CMPL | completion chunk |
| 2002 | ACK | message ack (carries `conversation_id`) |
| 2003 | FIN | stream end |
| 2004 | CMD | command |
| 2005 | ERR | **error** |
| 2010 | VERBOSE | metadata |

### 4.2 `content_type`

| Value | Name | Meaning |
|-------|------|---------|
| 2001 | SamanthaText | plain text |
| 2002 | SamanthaSuggest | suggested questions |
| 2003 | SamanthaLoading | loading state |
| 2005 | SamanthaMusicGenInput | music input |
| 2008 | SamanthaSearchText | thinking delta |
| 2009 | SamanthaImageInput | **image generation request** |
| 2010 | SamanthaImageOutput | **image generation result** |
| 2020 | SamanthaVideoGenerationInput | **video generation request** |
| 2021 | SamanthaVideoGenerationOutput | **video generation result** |
| 10000 | SamanthaTextV2 | main answer text |
| 10040 | BlockTypeThink | thinking block |

### 4.3 `skill_type`

| Value | Skill |
|-------|-------|
| 3 | image generation (`SkillImageGen`) |
| 17 | video generation (`SkillVideoGeneration`) |

### 4.4 Watermark (`/privacy/watermark_config`)

Source: webpack module `8990` in `9816.js`, the `WatermarkSetting` component.

```js
i[i.ImageVideoRemoval = 150] = "ImageVideoRemoval"          // 生成的图片、视频
i[i.OfficeResourceRemoval = 151] = "OfficeResourceRemoval"  // 生成的文档、表格、PPT
n[n.Off = 0] = "Off"                                        // 有 · 保留水印
n[n.On  = 1] = "On"                                         // 无 · 去除水印
```

Request / response shapes:

```jsonc
// GET  /privacy/watermark_config/get
{ "objects": [150, 151] }
// -> {"code":0,"data":{"configs":[{"object":150,"value":1,"version":0}, ...]}}

// POST /privacy/watermark_config/set
{ "configs": [{ "object": 150, "value": 1, "version": 0 }] }
```

> **Semantics gotcha.** `value: 1` means *the opt-out is ON*, i.e. the product
> is delivered **without** the "AI 生成" watermark.  The UI confirms it:
> `AIwatermarking_popupwindow_pop_on_cn = "无水印"`.  Do not invert this.

The official UI always shows a confirmation dialog
(`AIwatermarking_popupwindow_title_cn = "确认去除 AI 生成明水印"`) whose copy
states the user bears the consequences; our tools therefore require an explicit
`confirm` flag.

### 4.5 Watermark mirror (`/creativity/user_config`)

```jsonc
// config_type 1 = WatermarkOption, 2 = AuthorizationOption
{ "config_type": 1, "config_value": { "watermark_option": { "is_on": true } } }
```

Read shape: `data.config_map["1"].watermark_option.is_on`.

### 4.6 Quota windows (`/subscription/quota/summary/`)

| `window_type` | Meaning |
|---------------|---------|
| 1 | total allowance |
| 2 | current rolling period |

| `subscription.status` | Meaning |
|-----------------------|---------|
| 3 | active |
| 4 | expired |

### 4.7 Subscription SKUs

| SKU | Display |
|-----|---------|
| `doubao_personal_std` | 标准套餐 |
| `doubao_personal_pro` | 专业套餐 (offered as the upgrade CTA) |

---

## 5 Risk control (`710022004`) — the one unsolved problem

### 5.1 Symptom

Any generation call answers HTTP 200 with a single SSE frame:

```json
{"event_type": 2005, "event_data": "{\"code\":710022004,
 \"message\":\"rate limited\",
 \"error_detail\":{\"code\":710022004,\"message\":\"系统错误\",
   \"ext\":{\"decision\":\"{\\\"code\\\":\\\"10000\\\",\\\"from\\\":\\\"shark_admin\\\",
     \\\"type\\\":\\\"verify\\\",\\\"subtype\\\":\\\"semantic_reasoning\\\",
     \\\"verify_scene\\\":\\\"doubao_message_web\\\", ...}\"}}}"}
```

Read-only endpoints (`user_config`, `subscription/*`, `watermark_config`) are
**not** affected, which is why the plan/quota/watermark features work today.

### 5.2 What was tested

| Variant | Result |
|---------|--------|
| Plain `httpx` POST with the full cookie set | `710022004` |
| Playwright Chromium, in-page `fetch`, headless | `710022004` |
| Playwright Chromium, in-page `fetch`, headful | `710022004` |
| Microsoft Edge channel, in-page `fetch`, headful | `710022004` |
| After adding the `.bytedance.com` `msToken` to the cookie set | `710022004` |
| Device-param variants (`device_id`, `web_id`, `tea_uuid`, `fp`) | `710022004` |
| Session taken directly from the logged-in desktop client | `710022004` |

The page itself is healthy in every variant: `fetch` is hooked and
`window.bdms.frontierSign` is a function, so `a_bogus` *is* attached.
`subtype = semantic_reasoning` indicates a server-side behaviour/content model
rather than the slider captcha path.

### 5.3 Conclusion

The block is account- or device-level risk scoring that a fresh browser context
cannot clear immediately.  Two credible paths remain, neither implemented:

1. **Reuse the client's own profile** so the browser context *is* the trusted
   device (the reference implementation's `launch_persistent_context` against a
   profile the user has actually used).
2. **First-party risk attribution** — carry the exact headers and parameters the
   official client sends and let a session warm up before generating.

`transport_mode="browser"` and `DOUBAO_MEDIA_BROWSER_PROFILE` exist so path 1
can be pursued without further refactoring.

---

## 6 Security and privacy notes

* The session file is **DPAPI-encrypted** (current user scope) by default;
  plaintext is only used when explicitly requested or on non-Windows hosts.
* Cookie values are never logged or returned by any tool.
* Reading a browser profile touches a third-party credential store; it is
  local-only, requires no elevation, and is never uploaded.
* All generated assets are written under a caller-specified directory.
