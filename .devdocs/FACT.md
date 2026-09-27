<p style="font-size:28px;text-align:center;"><b>doubao-media FACT 记录</b></p>

> 本文件记录本项目在开发过程中确立的、可被后续会话直接引用的事实。
> 与代码行为冲突时以代码与线上实测为准，并应立即更新本文件。

> [!NOTE]
> 每条 FACT 都标注了验证方式：`live` = 2026-09-27 对线上真实账号实测；
> `static` = 仅由官方前端资源得出；`derived` = 由其他 FACT 推理得出。

---

## {FACTTime: 2026.09.27-22:35:00} DoubaoWatermarkProtocol 001

GitCommitHashRange: (initial) (1)

Files:
```
.\docs\protocol.md +240 -0
.\src\doubao_media\endpoints.py +30 -0
```

### What's Happened?
豆包官方"AI 生成水印管理"开关的读写协议被完整定位。
<!-- Git  Hub @   Ap rismL ab | A p   ri s   m   La  b@  S t a rs   ai   lsC  lov er -->

### Any evidence?
1. 官方桌面端自带前端资源中 webpack 模块 `8990`（文件 `9816.js`）即
   `WatermarkSetting` 组件，声明：
   ```js
   i[i.ImageVideoRemoval = 150] = "ImageVideoRemoval"
   i[i.OfficeResourceRemoval = 151] = "OfficeResourceRemoval"
   n[n.Off = 0] = "Off"    // 有 · 保留水印
   n[n.On  = 1] = "On"     // 无 · 去除水印
   ```
2. `live`：`POST /privacy/watermark_config/get` 带 `{"objects":[150,151]}`
   返回 `{"code":0,"data":{"configs":[{"object":150,"value":1,"version":0},
   {"object":151,"value":0,"version":0}]}}`。
3. UI 文案 `AIwatermarking_popupwindow_pop_on_cn = "无水印"`、
   `AIwatermarking_imagevideo_btn_cn = "生成的图片、视频"`，
   与需求描述中的设置路径完全对应。

### Researches
#### Result1
`value` 语义是**反的**：`1` 表示"已开启去除"，即产物无水印。若按直觉实现会把
开关写反，因此代码中显式定义了 `WatermarkValue.KEEP=0 / REMOVED=1` 并加注释。
#### Result2
请求参数为 `objects`（复数），写入参数为 `configs`，且写入需要带 `version`
做乐观锁；`get` 返回的 `version` 可直接回填。

### Any Founds?
官方 UI 在开启该开关前弹出确认框
（`AIwatermarking_popupwindow_title_cn = "确认去除 AI 生成明水印"`），
其文案要求用户自行承担后果。

### Solutions
把开关实现为**需要显式确认**的官方设置写入，而非静默旁路：
`pipeline._apply_watermark_policy` 在 `confirm` 为假时直接抛错并回显官方设置路径。
详见 `docs/adr/0002`。

### FACTs
1. 水印开关对象：`150` = 图片/视频，`151` = 文档/表格/PPT。
2. 读：`/privacy/watermark_config/get`，入参 `{"objects":[...]}`。
3. 写：`/privacy/watermark_config/set`，入参 `{"configs":[{"object","value","version"}]}`。
4. `value=1` 为"无水印"，`value=0` 为"有水印"。
5. 另有镜像接口 `/creativity/user_config/{get,set}`（`config_type=1`，
   `config_value.watermark_option.is_on`），`live` 可读。

version: v26.0.0-alpha.1

***

## {FACTTime: 2026.09.27-22:48:00} DoubaoPlanQuotaEndpoints 002

GitCommitHashRange: (initial) (1)

Files:
```
.\src\doubao_media\quota.py +380 -0
.\tests\test_quota.py +170 -0
```

### What's Happened?
豆包账户套餐与额度可通过官方 commerce 接口完整识别，无需抓包页面。

### Any evidence?
`live`（真实账号，2026-09-27）：

| 接口 | 返回 |
|------|------|
| `/alice/commerce/sale/subscription/entry/config/` | `membership_display_name:"标准套餐"`、`settings_page.click_url` 指向额度管理页 |
| `/alice/commerce/sale/subscription/overview/` | `sku_key:"doubao_personal_std"`、`upgrade_guide.highest_version_sku:"doubao_personal_pro"` |
| `/alice/commerce/sale/subscription/quota/summary/` | `window_limit_section.window_limit_groups[].window_limits[].used_percent` |
| `/alice/commerce/sale/subscription/list/` | 全部订阅记录（含已过期） |

### Any Founds?
1. 请求体字段是 `product_lines`（数组），不是 `product_line`；用单数时服务端返回
   空结构而不报错——这是一个会静默失效的坑。
2. `window_type`：`1` 为总额度，`2` 为滚动周期；用量百分比取各窗口最大值。
3. `/subscription/detail/` 裸调（`with_capacity` 之外还缺必填）返回
   `710010202 common invalid param`，已弃用该路径。

### FACTs
1. 套餐识别：`entry/config` + `overview` 组合即可得出套餐名与 SKU。
2. 额度识别：`quota/summary` 的 `used_percent` 即用量百分比；
   `usage_exhausted` 为耗尽标志。
3. 升级信息：`overview.upgrade_guide` 给出官方升级 SKU 与下单 URL。
4. 归一化逻辑全部在 `quota.py` 中，为纯函数，已由 8 个单测覆盖。

version: v26.0.0-alpha.1

***

## {FACTTime: 2026.09.27-23:10:00} DoubaoRiskControlBlocked 003

GitCommitHashRange: (initial) (1)

Files:
```
.\docs\protocol.md +60 -0
.\README.md +20 -0
.\src\doubao_media\browser.py +520 -0
```

### What's Happened?
`/samantha/chat/completion` 的**生成**调用被服务端风控拦截，
返回 `710022004`，且已排除"缺少签名"这一常见原因。

### Any evidence?
返回帧：
```json
{"event_type":2005,"event_data":{"code":710022004,"message":"rate limited",
 "error_detail":{"ext":{"decision":{"type":"verify",
 "subtype":"semantic_reasoning","verify_scene":"doubao_message_web"}}}}}
```

对照实验（同一账号、同一 Cookie 集合）：

| 变量 | 结果 |
|------|------|
| 纯 httpx | 710022004 |
| Chromium headless 页面内 fetch | 710022004 |
| Chromium headful 页面内 fetch | 710022004 |
| Edge channel headful 页面内 fetch | 710022004 |
| 显式追加 `a_bogus` / `X-Bogus` | 710022004 |
| 补 `.bytedance.com` 的 `msToken` | 710022004 |
| 补 `device_id`/`web_id`/`tea_uuid`/`fp` | 710022004 |
| 读取类接口（水印/订阅/额度） | `code: 0` 正常 |

页面自身健康：`window.fetch` 已被 hook，
`window.bdms.frontierSign(query)` 返回 `{"X-Bogus":"60EurySOS2tUcf5V"}`。
<!-- GitH ub@A pr  i   smLab | AprismLab@St  ars   ai  lsCl over -->

### Any Perjury?
#### Perjury1
"只要用浏览器发请求就不会被风控"——被实验证伪：headless/headful/Edge 三种
浏览器路径均被拦截。
#### Perjury2
"缺 `msToken` 或 `device_id` 导致风控"——被实验伪：补齐后结果不变。

### Researches
#### Result1
`subtype = semantic_reasoning` 表明这是服务端对账户/设备的风险评分，
而非滑块验证码（`subtype` 会不同）。
#### Result2
读取类接口不受影响，说明拦截仅作用于生成类写入。

### Solutions
1. 如实记录为已知限制，不伪装成请求构造 bug（`SKILL.md` §6 给出面向用户的
   标准回复）。
2. 保留 `transport_mode="browser"` 与 `DOUBAO_MEDIA_BROWSER_PROFILE`，
   使"复用桌面端真实 profile"这一后续修复无需重构。

### FACTs
1. `710022004` 是账户/设备级风控，新建浏览器上下文无法即时清除。
2. 读取类接口（`/privacy/*`、`/creativity/user_config/get`、
   `/alice/commerce/*`）在纯 HTTP 下可用。
3. 优先级最高的后续假设：复用豆包桌面端已使用的浏览器 profile。
<!-- GitHu b@Ap  r  ismLa   b | Apri   smLa b@   S t   arsa i   ls   Clo  ve  r -->

### Tags
risk-control, 710022004, blocked, known-limitation

version: v26.0.0-alpha.1

***

## {FACTTime: 2026.09.28-02:20:00} DoubaoRiskControlIsTwoForms 004

GitCommitHashRange: (initial)-HEAD (2)

Files:
```
.\src\doubao_media\verify.py             +420 -0
.\src\doubao_media\errors.py             +45 -0
.\tests\test_risk_control.py             +120 -0
.\docs\adr\0003-*.md                     +80 -0
```

### What's Happened?
FACT-003 的结论被**修正**：`710022004` 不是"无法解决的封禁"，而是**可解的安全验证**；
并发现了第二种形态 `710022002`（不可解的频率封禁）——而后者是本项目自己造成的。

### Any evidence?
1. `live`：`710022004` 载荷内含 `ext.decision.type = "verify"`、
   `subtype = "slide"`、`detail = <blob>`、`verify_scene = "doubao_message_web"`。
2. `static`：豆包官方 `106.js` 中的调用点是
   `verifyCenter.renderCaptcha({verify_data, captchaOptions, secondVerifyWebOptions})`，
   其中 `verify_data` 就是 decision 对象本身（SDK 读它的 `.region`/`.log_id`/`.fp`）。
3. `live`：页面暴露了官方集成入口
   `window.verifyCenter`（`init`/`initVerifyCenter`/`initVerifyOptions`/`autoRender`/
   `renderCaptcha`/`renderSecondVerifyWeb`/`closeCaptcha`/`getCaptchaWebId`/`SMS`）
   与 `window.__VERIFY_CENTER_RUNTIME__`（`myOptions`/`myFp`/`myVerify`/`mySMS`）。
4. `live`：连续探测后错误码**变为** `710022002`（`"block"` /
   `"当前服务访问频繁，请稍后重试"`），**无** `decision`。

### Any Perjury?
#### Perjury1
"境外 IP 导致风控"——**已证伪**。Clash 按规则分流，国内域名直连；
用国内回显（myip.ipip.net）实测豆包链路出口为广州电信，
`www.doubao.com` 解析为国内 CDN（`113.96.150.x` / `183.60.205.x` / `183.61.231.x`）。
只有境外站点（api.ipify.org）才走东京 G-Core Labs。
#### Perjury2
"缺少签名导致风控"——**已证伪**。`bdms.frontierSign(query)` 返回有效
`X-Bogus`，显式附加后结果不变。
#### Perjury3
"是图像能力/权限问题"——**已证伪**。纯文本（`content_type: 2001`）被同样拦截。

### Researches
#### Result1
两种形态的处理方式完全相反：形态 A 解决一次即可继续；形态 B **无法解决**，
只能等待，且重试会加重。
#### Result2
形态 B 是**自找的**：本项目调试期间反复发起生成调用导致。

### Any Founds?
1. 形态 A 的 `subtype` 实测出现过 `slide` 与 `semantic_reasoning`。
2. 实现必须驱动页面自身的 `verifyCenter`，而不是自己 new CDN 类
   （后者会对 blob 调 `JSON.parse` 报错，说明包装层才是入口）。

### Solutions
1. 拆分为两个异常类型：`DoubaoRiskControl`（可解，带 challenge）与
   `DoubaoRateLimited`（不可解）。
2. 新增 MCP 工具 `doubao_verify_challenge`，由用户在**可见窗口**内完成验证。
3. 在 skill 中写入硬规则：每个用户请求最多一次生成，禁止批量与重试循环；
   禁止用真实生成调用做协议探测。
4. 不自动化验证本身（不做滑块破解、不重签 blob）——理由见 `docs/adr/0003`。

### FACTs
1. `710022004` = 可解安全验证；`710022002` = 不可解频率封禁。
2. 官方验证入口：`window.verifyCenter.renderCaptcha({verify_data, captchaOptions,
   secondVerifyWebOptions})`；`verify_data` 为 decision 对象。
3. 风控与出口 IP 无关（豆包走国内直连）、与签名无关、与模态无关。
4. 触发形态 B 的行为本身是违规操作，须避免。
5. **诚实标注**：`doubao_verify_challenge` 已按官方入口实现，但**未做端到端实测**
   （因账号当时处于形态 B，实测会加重封禁）。

### Tags
risk-control, 710022004, 710022002, verification, corrected

version: v26.0.0-alpha.1
