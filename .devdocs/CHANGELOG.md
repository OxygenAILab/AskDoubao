<p style="font-size:28px;text-align:center;"><b>doubao-media ChangeLog</b></p>

> 记录每个版本的变更。版本号遵循组织规范 `v{Year}.{Major}-Alpha {N}`。

---

## {ChangeTime: 2026.09.27-23:40:00} v26.0.0-alpha.1 首发
<!-- GitH ub @Oxyge n   AIL ab | Oxy  genA  IL ab @Starsai  lsClov er -->

GitCommitHash: (initial)

ChangedFiles:
```
.\src\doubao_media\endpoints.py         +150 -0
.\src\doubao_media\errors.py            +110 -0
.\src\doubao_media\models.py            +210 -0
.\src\doubao_media\transport.py         +330 -0
.\src\doubao_media\browser.py           +520 -0
.\src\doubao_media\session.py           +560 -0
.\src\doubao_media\client.py            +700 -0
.\src\doubao_media\quota.py             +380 -0
.\src\doubao_media\pipeline.py          +280 -0
.\src\doubao_media\cli.py               +250 -0
.\src\doubao_media\mcp\server.py        +290 -0
.\tests\test_quota.py                   +170 -0
.\tests\test_session.py                 +150 -0
.\plugins\doubao-media\**               +700 -0
.\docs\protocol.md                      +240 -0
.\docs\adr\0001-*.md                    +60 -0
.\docs\adr\0002-*.md                    +65 -0
.\scripts\build_plugin.py               +170 -0
.\scripts\live_probe.py                 +60 -0
.\scripts\refresh_session.py            +90 -0
.\scripts\adopt_browser.py              +55 -0
.\README.md                             +230 -0
.\pyproject.toml                        +80 -0
```

ChangeLog:
Num|File Name|Change Description|Change Time|Changer
----|----|----|----|----
1|endpoints.py|新增逆向所得的端点与枚举表（含出处标注）|2026.09.27-21:50:00|Codex
2|session.py|会话存储（DPAPI 加密）、浏览器 Cookie 采用、纯 HTTP QR 登录|2026.09.27-22:10:00|Codex
3|transport.py|httpx 传输层、SSE 块解析、业务错误码到类型化异常的映射|2026.09.27-22:15:00|Codex
4|client.py|生成、水印读写、套餐与额度读取|2026.09.27-22:40:00|Codex
5|quota.py|套餐/额度归一化纯函数模块|2026.09.27-22:45:00|Codex
6|browser.py|浏览器传输与 HybridTransport 路由（应对风控）|2026.09.27-23:00:00|Codex
7|pipeline.py|水印策略 → 生成 → 下载的编排与授权门槛|2026.09.27-23:05:00|Codex
8|mcp/server.py|MCP 工具面（仅 7 个工具，范围限定图像/视频）|2026.09.27-23:20:00|Codex
9|cli.py|与 MCP 对齐的命令行接口|2026.09.27-23:25:00|Codex
10|tests|36 项单测，覆盖额度归一化与协议解析|2026.09.27-23:30:00|Codex
11|build_plugin.py|自包含插件组装脚本 + CI 同步门禁|2026.09.27-23:32:00|Codex
12|docs/protocol.md|完整协议证据链与风控实验记录|2026.09.27-23:35:00|Codex

version: v26.0.0-alpha.1

---

## {ChangeTime: 2026.09.28-02:35:00} v26.0.0-alpha.1 风控双形态与安全验证

GitCommitHash: (pending)

ChangedFiles:
```
.\src\doubao_media\verify.py             +420 -0
.\src\doubao_media\errors.py             +45 -0
.\src\doubao_media\client.py             +12 -6
.\src\doubao_media\browser.py            +24 -2
.\src\doubao_media\mcp\server.py         +95 -6
.\tests\test_risk_control.py             +120 -0
.\tests\test_verify.py                   +95 -0
.\docs\adr\0003-*.md                     +80 -0
.\docs\protocol.md                       +100 -52
.\README.md                              +60 -32
.\CLAUDE.md                              +60 -0
.\plugins\doubao-media\skills\wen-doubao\SKILL.md +50 -22
```

ChangeLog:
Num|File Name|Change Description|Change Time|Changer
----|----|----|----|----
1|verify.py|新增风控挑战解析与官方验证流（驱动 window.verifyCenter）|2026.09.28-02:00:00|Codex
2|errors.py|拆分 DoubaoRiskControl（可解）与 DoubaoRateLimited（不可解）|2026.09.28-02:05:00|Codex
3|client.py|SSE 错误事件改用 parse_risk_control 分类|2026.09.28-02:08:00|Codex
4|browser.py|新增 bypass_proxy / launch_args（国内服务需绕过系统代理）|2026.09.28-01:30:00|Codex
5|mcp/server.py|新增 doubao_verify_challenge；失败信封附带 riskControl 指引|2026.09.28-02:12:00|Codex
6|tests|新增 12 项测试覆盖两种形态的判定|2026.09.28-02:15:00|Codex
7|docs/adr/0003|记录"可解但不得自动化"的决策与证据|2026.09.28-02:20:00|Codex
8|docs/protocol.md|第 5 节重写为双形态 + 已排除原因表|2026.09.28-02:25:00|Codex
9|README.md|同步能力表与风控章节|2026.09.28-02:28:00|Codex
10|SKILL.md|新增验证流程、频率封禁处理、禁止批量的硬规则|2026.09.28-02:30:00|Codex
11|CLAUDE.md|新增维护者须知与四条硬规则|2026.09.28-02:32:00|Codex

version: v26.0.0-alpha.1
<!-- Git Hub  @Ox  yg e nA   ILab | Ox  yge   nA   IL   ab@Sta   rsai lsClov   er -->

---

## {ChangeTime: 2026.09.30-03:30:00} v26.0.0-alpha.1 安全验证渲染打通 + 仓库迁移

GitCommitHash: (pending)

ChangedFiles:
```
.\src\doubao_media\verify.py             +180 -120
.\tests\test_verify_render_contract.py +90 -0
.\docs\protocol.md                      +55 -20
.\docs\adr\0003-*.md                    +9 -0
.\plugins\doubao-media\skills\wen-doubao\SKILL.md +32 -0
.\README.md                              +22 -6
.\_scripts\bc\insert_watermark.py        +6 -2
.\_scripts\bc\rewatermark.py             +100 -0
.\pyproject.toml                         +2 -2
```

ChangeLog:
Num|File Name|Change Description|Change Time|Changer
----|----|----|----|----
1|verify.py|修正验证渲染：改驱动 window.verifySDK.renderCaptcha，顶层传整数 aid + did，容器给确定尺寸|2026.09.30-03:00:00|Codex
2|verify.py|VERIFY_DRIVE_JS 提为模块级常量，便于用 node --check 做语法校验|2026.09.30-03:05:00|Codex
3|insert_watermark.py|修复字符串内部误插水印（_string_interior_lines 纳入 before_code 分支）|2026.09.30-02:10:00|Codex
4|rewatermark.py|新增换仓后全量重打水印工具（含"旧所有者水印"检测）|2026.09.30-03:20:00|Codex
5|test_verify_render_contract.py|新增 9 项回归测试，锁定六个"静默不渲染"约束|2026.09.30-03:15:00|Codex
6|docs/protocol.md|§5.1.1 记录完整调用配方与六条约束证据|2026.09.30-03:12:00|Codex
7|全仓库|水印按新仓库所有者重解析并全量重打|2026.09.30-03:25:00|Codex

version: v26.0.0-alpha.1

---

License: MIT
