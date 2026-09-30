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
<!-- GitHub@Ox   y   g en   A  ILa b | O  xygenA  I  Lab@   St   arsa   i   lsC  love  r -->

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
<!-- Gi  tHu b@Oxyge   n A I Lab | Oxyge nAIL ab@   S   tarsa il   sCl  over -->

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
<!-- G it  Hub  @   Oxygen AI  Lab | Oxy   genAI L   a b@Star sailsC   l   over -->

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
<!-- Gi   tHu   b@ Ox y   g  enAILab | OxygenAIL  ab   @Sta rsailsClo ver -->

### Tags
risk-control, 710022004, 710022002, verification, corrected

version: v26.0.0-alpha.1

***

## {FACTTime: 2026.09.30-03:35:00} DoubaoVerifyRenderSolved 005

GitCommitHashRange: (initial)-HEAD (3)

Files:
```
.\src\doubao_media\verify.py                 +180 -120
.\tests\test_verify_render_contract.py       +90 -0
.\docs\protocol.md                           +55 -20
```

### What's Happened?
安全验证的**渲染被彻底打通**：官方滑块组件（"请完成下列验证后继续"）能在可见窗口中
正确呈现。此前多轮"调用成功但什么都不显示"的原因全部定位。

### Any evidence?
1. 读 `verifySDK.renderCaptcha.toString()` 得到关键判定：
   `if (e.aid) c = e; else c = merge(myOptions)`，以及
   `if ("number" != typeof e.aid) throw new Error("...and of type int")`，
   还有 `if (window.__vc_is_render__) { ...; return }`。
2. `live`：正确调用后容器内出现 iframe
   `https://rmc.bytedance.com/verifycenter/captcha/v2?...`，尺寸 `380x384`。
3. `live` 截图：弹窗显示"请完成下列验证后继续" + 拼图 + "按住左边按钮拖动完成上方拼图"。
4. 生产代码路径（`VERIFY_DRIVE_JS`）离线重放同一 blob，断言
   `hostChildren > 0` 且 iframe 源包含 `verifycenter/captcha`，通过。

### Any Perjury?
#### Perjury1
"调用 `window.verifyCenter` 即可"——**证伪**：它是空壳包装，
`__VERIFY_CENTER_RUNTIME__.myOptions.options` 始终为 `{}`，调用无任何反应。
#### Perjury2
"用 `new bdCaptcha.CaptchaVerify` 构造即可"——**证伪**：那是 CDN 原始类，
不是产品配置的对象；正确目标是 `window.verifySDK`。
#### Perjury3
"传 `detail` 字符串即可"——**证伪**：`verify_data` 必须是 decision 对象本身。

### Researches
#### Result1
六个约束各自都会导致"静默不渲染"，必须同时满足，缺一不可：
目标对象、顶层 `aid`、`aid` 为整数、提供 `did`、容器确定尺寸、清 `__vc_is_render__`。
#### Result2
`autoRender` 会把 `renderCaptcha` 内部的异常吞掉并改写成
`"verify_data is required"`，是极强的误导来源；直接调 `renderCaptcha`
才能看到真实错误。

### Any Founds?
容器只给 `min-height` 时，`h-full w-full` 的组件会塌缩为 0×0——
"已挂载但不可见"，是最隐蔽的一条。

### Solutions
1. `verify.py` 改为模块级 `VERIFY_DRIVE_JS` 常量 + `renderCaptcha` 直调。
2. 新增 `test_verify_render_contract.py` 9 项回归测试锁定该契约。
3. 修复 `insert_watermark.py` 的字符串内部误插缺陷（该缺陷曾导致上述 JS 被污染）。

### FACTs
1. 正确调用：`window.verifySDK.renderCaptcha({aid:<int>, did, pageId, verify_data,
   ele, captchaOptions, secondVerifyWebOptions})`。
2. `verify_data` = decision 对象（不是 `detail`）。
3. 渲染已视觉验证；**solve→retry 闭环仍未做端到端实测**（验证可用时账号正处频率封禁）。
4. 水印工具曾在多行字符串内部插入水印，损坏内嵌 JS；已修复并加约束。

### Tags
verification, render-solved, risk-control, watermark-tool-fixed

version: v26.0.0-alpha.1

***

## {FACTTime: 2026.09.30-03:40:00} RepoMovedToAskDoubao 006

GitCommitHashRange: (pending) (1)

Files:
```
.\pyproject.toml                       +2 -2
.\_scripts\bc\insert_watermark.py      +6 -2
.\_scripts\bc\rewatermark.py           +100 -0
```

### What's Happened?
项目由 `AprismLab/doubao-media` 迁移至 **`OxygenAILab/AskDoubao`**（私有）。

### Any evidence?
1. `gh api orgs/OxygenAILab` 返回 `{"login":"OxygenAILab","name":"Oxygen AI Lab",
   "type":"Organization"}`。
2. `resolve-watermark.ps1 -Canonical` 在切换 origin 后输出
   `GitHub@OxygenAILab | OxygenAILab@StarsailsClover`。

### Researches
#### Result1
组织显示名 "Oxygen AI Lab" 归一化后（去非字母数字、小写）与 `OxygenAILab` 相同，
按脚本规则应**使用稳定的 GitHub 拼写**而非显示名。
#### Result2
规范要求换仓后**重新解析**水印，且明确禁止固守"上一个仓库的所有者"，
因此全部水印必须重打，不能保留 AprismLab。

### Solutions
1. `insert_watermark.CANONICAL` 更新为新解析值，并注明"换仓须重新解析"。
2. 新增 `_scripts/bc/rewatermark.py`：owner-agnostic 检测 + 全量重打，
   另带 `--check` 用于 CI 检测"过期所有者水印"。
3. 实际重打：26 个文件、移除 107 条、插入 118 条；`--check` 通过。

### FACTs
1. 新水印规范值：`GitHub@OxygenAILab | OxygenAILab@StarsailsClover`。
2. 仓库：`OxygenAILab/AskDoubao`（私有）。
3. 插件内部标识保持 `doubao-media`（skill 目录名才是 `wen-doubao`）。

### Tags
repository-migration, watermark-re-resolved, AskDoubao

version: v26.0.0-alpha.1

***

## {FACTTime: 2026.09.30-16:45:00} ThrottleSensitivity 007

GitCommitHashRange: (pending) (1)

Files:
```
.\docs\adr\0003-*.md              +14 -0
.\plugins\doubao-media\skills\wen-doubao\SKILL.md +10 -3
```

### What's Happened?
实测得到 `710022002`（频率封禁）的触发敏感度，并确认判别逻辑在真实场景下正确生效。

### Any evidence?
1. `live`：历时约 2 小时后，一次生成返回可解验证 `710022004`（slider）。
2. `live`：此后在调试窗口内又进行了少量生成调用（用于获取/复现挑战），
   再次调用时即变为 `710022002`（`block`）。
3. `live`：`e2e_flow.py` 首次尝试即命中 `710022002`，程序按设计**立即停止**、
   未做任何重试，退出码 3。
4. `live`：额度用量从 2% 升至 3%，说明被挑战/失败的调用**同样计入额度**。

### Researches
#### Result1
封禁触发门槛很低：短时间内**约 1–2 次**生成调用即可触发。
这对使用方式有直接约束——必须按"每个用户请求一次"的节奏，且请求间要有真实间隔。
#### Result2
额度是按**调用**计（含被风控拦下的调用），不是按成功产出计。
探测行为本身既触发封禁又消耗额度，属双重代价。

### Any Founds?
`710022004` 与 `710022002` 会在同一账号上**相互转换**：
封禁到期后回到可解验证；再次密集调用又退回封禁。
因此"验证通过 → 立即重试"这一步也必须克制，否则立刻回到形态 B。

### Solutions
1. 在 skill 中写明：验证通过后仅允许重试**一次**，且不得连续多次生成。
2. 在 ADR-0003 补充敏感度与额度代价的实测数据。
3. 保留 `e2e_flow.py` 作为"遇到封禁必须停止"的行为验证入口。

### FACTs
1. `710022002` 门槛极低（约 1–2 次密集调用）。
2. 被拦下的调用也计入额度（已实测 2% → 3%）。
3. 两种风控形态可相互转换。
4. `e2e_flow.py` 在封禁下正确拒绝重试（退出码 3）。
5. **solve→retry 闭环仍未完成端到端实测**（两次尝试均被频率封禁挡在门外）。

### Tags
throttling, 710022002, sensitivity, quota-consumed, honest-status

version: v26.0.0-alpha.1

***

## {FACTTime: 2026.09.30-17:20:00} AccountDegradedByOurCalls 008

GitCommitHashRange: (pending) (1)

Files:
```
.\src\doubao_media\rate_limit.py     +220 -0
.\src\doubao_media\pipeline.py       +14 -0
.\tests\test_rate_limit.py           +160 -0
.\docs\adr\0004-*.md                 +90 -0
```

### What's Happened?
**本项目把用户真实账号的风控从"场景级"打成了"账号/设备级"。**
这是必须记录在案的事故，不是待办事项。

### Any evidence?
用户原话（按时间）：
1. "我的网页端豆包用不了了，提示访问过于频繁。但是客户端豆包可以。"
2. "wtf桌面也用不了了, 仅手机端了."

代码侧对应行为：
- 反复以会话 Cookie 调用网页版 `/samantha/chat/completion`
  （`verify_scene = doubao_message_web`）；
- 为读取 Cookie 多次强制终止并重启豆包桌面端。

### Any Perjury?
#### Perjury1
FACT-003 曾写"读取类接口不受影响，所以套餐/额度/水印功能可用"——
该表述**过窄**。它暗示影响面限于我们自己的工具；
实际代价落在**用户日常使用产品**上。
#### Perjury2
"频率封禁只影响网页场景"——**已证伪**，随后扩散到桌面端。

### Researches
#### Result1
静态核查桌面端资源：桌面端调用的是**同一个**
`/samantha/chat/completion`（`36577.js` / `58448.js` / `65884.js`），
且桌面端资源中**不存在** `doubao_message_web`（只有
`doubao_message_forward_feishu_subtitle`）。
故风控**按场景/平台分桶**，一个桶被限不等于全端被限——但桶会**升级**。
#### Result2
与被拦下的调用同样消耗额度（已实测 2% → 3%），因此"探测"是双重代价。

### Any Founds?
1. 触发门槛极低（密集 1–2 次）。
2. 形态可逆：封禁过期后回到可解验证；再次密集又退回封禁。
3. 本地闸门无法减轻服务端已经生效的处罚。

### Solutions
1. 新增 `rate_limit.py`：**默认禁止生成**，需显式 `DOUBAO_MEDIA_ENABLE_GENERATION=1`；
   叠加本地冷却（默认 600s）与滚动 24h 上限（默认 20 次）；计数落盘。
2. 闸门置于 `pipeline` 生成入口，**在任何网络请求之前**；被拒不消耗额度。
3. 失败/被挑战的调用**照常计数**（因为它们确实消耗额度）。
4. skill / README / CLAUDE.md / ADR-0004 全文写明事故与不可绕过性。
5. 新增 12 项测试锁定闸门行为，避免后续被"为了让测试通过"而削弱。

### FACTs
1. 事故真实发生：网页端 → 桌面端先后不可用，仅手机可用。
2. 生成现为显式 opt-in；读取类工具不受影响。
3. 本地限制**无法**帮助已经受限的账号；恢复只能等服务端时限。
4. 后续任何协议探索**只允许**使用随包资源静态分析，禁止真实生成调用。

### Tags
incident, real-harm, account-degraded, throttle-guard, honest-status

version: v26.0.0-alpha.1
