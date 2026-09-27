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
<!-- GitH ub@Apr   i sm La  b | A  prismLab@   Starsa  ilsCl over -->

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
<!-- G  i tH  ub  @A  p  r   ism  La b | A  pri   sm   Lab@Starsa ils  Cl   o  v  er -->

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

## 5 Risk control - two distinct forms

Any generation call answers HTTP 200 with a single SSE error frame. There are
**two** forms and they must not be conflated.

### 5.1 Form A - `710022004`, a solvable challenge

The payload carries a complete verification instruction:

```
{"event_type": 2005, "event_data": "{\"code\":710022004, \"message\":\"rate limited\",
 \"error_detail\":{\"code\":710022004,\"message\":\"\u7cfb\u7edf\u9519\u8bef\",
  \"ext\":{\"decision\":\"{\\\"code\\\":\\\"10000\\\",\\\"from\\\":\\\"shark_admin\\\",
   \\\"type\\\":\\\"verify\\\",\\\"subtype\\\":\\\"slide\\\",
   \\\"verify_scene\\\":\\\"doubao_message_web\\\",\\\"log_id\\\":\\\"...\\\"}\"}}}"}
```

`subtype` has been observed as `slide` and as `semantic_reasoning`. The
`decision` object is exactly what Doubao's own verifier consumes as
`verify_data`.

### 5.1.1 The first-party verification entry point

The loaded page exposes the integration point the product itself uses:

```
window.verifyCenter  ->  init | initVerifyCenter | initVerifyOptions
                         autoRender | renderCaptcha | renderSecondVerifyWeb
                         closeCaptcha | getCaptchaWebId | SMS
window.__VERIFY_CENTER_RUNTIME__  ->  myOptions | myFp | myVerify | mySMS
```

Call shape, confirmed from the bundled `106.js`:

```js
verifyCenter.initVerifyOptions({commonOptions: {aid, pageId},
                                captchaOptions: {fp, ...}})
verifyCenter.renderCaptcha({verify_data, captchaOptions: {successCb, closeCb,
                            errorCb}, secondVerifyWebOptions: {scene: "4", ...}})
```

`verify_data` is the **parsed `decision` object** (the SDK reads `.region`,
`.log_id` and `.fp` from it). Passing only `decision.detail` is wrong: the SDK
then attempts `JSON.parse` on the opaque blob.

### 5.2 Form B - `710022002`, a plain frequency block

No `decision`, no challenge:

```
{"code": 710022002, "message": "block",
 "error_detail": {"code": 710022002,
                  "message": "\u5f53\u524d\u670d\u52a1\u8bbf\u95ee\u9891\u7e41\uff0c\u8bf7\u7a0d\u540e\u91cd\u8bd5"}}
```

Form B is **self-inflicted by over-calling** and cannot be solved - only waited
out. It appeared in this project after repeated generation probing, which is why
the skill now forbids batching and retry loops.

Read-only endpoints (`user_config`, `subscription/*`, `watermark_config`) are
unaffected by either form, which is why the plan/quota/watermark features work
regardless.

### 5.3 What is *not* the cause

Both obvious explanations were tested and rejected:

| Hypothesis | Verdict | Evidence |
|---|---|---|
| Foreign egress IP is distrusted | **Rejected** | Clash routes by rule: domestic hosts go **direct**. Measured with a domestic echo: the Doubao path egresses from Guangzhou Telecom, and `www.doubao.com` resolves to domestic CDN IPs (`113.96.150.x`, `183.60.205.x`, `183.61.231.x`). Only foreign hosts (e.g. `api.ipify.org`) take the Tokyo route. |
| The request lacks a signature | **Rejected** | `window.bdms.frontierSign(query)` returns `{"X-Bogus":"..."}`; attaching it explicitly changes nothing. |

The block is also **not modality-specific**: a plain text completion
(`content_type: 2001`, no image request at all) is refused identically, so this
is not an image-entitlement problem.

Earlier variants, all reproducing the same result, are retained here for
completeness: plain `httpx`; headless Chromium in-page `fetch`; headful
Chromium; the Edge channel; after adding the `.bytedance.com` `msToken`; with
`device_id` / `web_id` / `tea_uuid` / `fp` supplied; and using the desktop
client's own session.

### 5.4 Conclusion and honest status

Form A is recoverable: `doubao_verify_challenge` drives `window.verifyCenter` in
a visible window for the account holder to solve, after which one retry is
permitted. Form B is not recoverable and must be waited out.

`doubao_verify_challenge` is implemented against the first-party entry point but
was **not exercised end-to-end**, because doing so would have required
generating while the account was already under Form B. The render path is
therefore verified only as far as the SDK hand-off.

### 5.5 Operational rule

Do **not** use live generation calls for exploratory probing - that is exactly
what produced Form B. Prefer the bundled-asset tooling (`extract_api.py`,
`g2.py`) for protocol work, and issue at most one generation per user request.


## 6 Security and privacy notes

* The session file is **DPAPI-encrypted** (current user scope) by default;
  plaintext is only used when explicitly requested or on non-Windows hosts.
* Cookie values are never logged or returned by any tool.
* Reading a browser profile touches a third-party credential store; it is
  local-only, requires no elevation, and is never uploaded.
* All generated assets are written under a caller-specified directory.
<!-- G i t  H u  b  @  Apri smLab | Ap rism  L ab@ S tar sail s   C  l ov  er -->
