# doubao-media · 问豆包

<p style="font-size:22px;text-align:center"><b>豆包（Doubao）图像 / 视频生成降级通道</b></p>

> 当主图像模型（如 **image 2 / image 2.5**）无权限、额度耗尽或额度不足时，
> 通过豆包官方 Web 接口生成图片与视频，并保存到本地。
> 同时提供**套餐/额度状态识别**与**官方 AI 生成水印开关**（设置 → 内容生成与产物设置 → AI 生成水印管理）。

> [!IMPORTANT]
> 本项目的范围被刻意限定为**图像与视频生成**。不含对话、文档、音乐、文件中转。
> 生成会消耗你的豆包额度，每个工具都会明确提示这一点。

---

## 1 能力一览

| 能力 | 状态 | 说明 |
|------|------|------|
| 套餐 / 订阅状态识别 | 已实测 | 标准套餐 / doubao_personal_std / 升级 CTA |
| 图像 / 视频额度用量识别 | 已实测 | 滚动周期用量百分比、下次重置时间、是否接近上限 |
| 官方 AI 生成水印开关（读取） | 已实测 | objects 150/151；value 1 = 无水印 |
| 官方 AI 生成水印开关（写入） | 代码完成，写入未实测 | 与官方 UI 同样的确认语义 |
| 图像生成（文生图 / 图生图） | 代码完成，受风控限制（见 §5） | |
| 视频生成（文生视频 / 图生视频） | 代码完成，受风控限制（见 §5） | |
| 已生成素材转无水印 | 客户端已实现，未暴露为工具 | version 握手未能实测 |

---

## 2 安装

```powershell
# 核心（状态 / 水印 / 套餐：仅需 httpx + mcp）
pip install -e .

# 浏览器传输层（生成所需）
pip install -e ".[browser]"
python -m playwright install chromium

# 读取 Windows 浏览器 Cookie（采用已登录会话时）
pip install -e ".[windows]"
```

作为 Codex 插件安装（推荐）：

```powershell
codex plugin add doubao-media@doubao-media
```

---

## 3 使用

### 3.1 MCP 工具

| 工具 | 是否消耗额度 | 用途 |
|------|--------------|------|
| `doubao_status` | 否 | 套餐、图像/视频额度、水印状态 |
| `doubao_watermark_status` | 否 | 读取水印开关 |
| `doubao_login_start` / `doubao_login_poll` | 否 | 采用本地会话，或扫码登录 |
| `doubao_generate_image` | **是** | 生成图片并保存 |
| `doubao_generate_video` | **是** | 生成视频并保存（额度最稀缺） |
| `doubao_watermark_opt_out` | 否 | 修改水印开关（去除需 confirm_removal） |

### 3.2 命令行

```powershell
doubao-media status --json
doubao-media watermark                       # 读取
doubao-media watermark --set off --confirm   # 去水印（需确认）
doubao-media image "一只白色的猫坐在窗边" --ratio 1:1 --out .\out
doubao-media video "一只橘猫在草地上奔跑" --duration 5 --out .\out
```

### 3.3 Python

```python
import asyncio
from doubao_media import MediaPipeline
from doubao_media.session import load_session

async def main():
    session = load_session()
    async with MediaPipeline.from_session(session, transport_mode="auto") as p:
        plan = await p.plan_status()
        print(plan.tier_label, plan.image.remaining_percent)
        outcome = await p.generate_image("一只猫", ratio="1:1", download_dir="./out")
        print(outcome.images[0].local_path)

asyncio.run(main())
```

---

## 4 架构

```
src/doubao_media/
├── endpoints.py   端点与枚举表（逆向自官方前端，含出处注释）
├── transport.py   httpx 传输、SSE 解析、错误码映射
├── browser.py     浏览器传输 + HybridTransport 路由
├── session.py     会话存储（DPAPI 加密）、浏览器 Cookie 采用、QR 登录
├── client.py      豆包 API 客户端：生成 / 水印 / 套餐额度
├── quota.py       套餐与额度归一化（纯函数，可单测）
├── pipeline.py    编排：水印策略 → 生成 → 下载
├── cli.py         命令行
└── mcp/server.py  MCP 工具面
```

传输路由决策见 `docs/adr/0001`；水印开关的授权边界见 `docs/adr/0002`。

### 4.1 传输选择

| `transport_mode` | 读取 | 生成 | CDN 下载 |
|---|---|---|---|
| `http` | httpx | httpx | httpx |
| `auto`（默认） | httpx | 浏览器页面 | httpx |
| `browser` | httpx | 浏览器页面 | httpx |

读取类接口已实测在纯 HTTP 下返回 code 0，因此不为它们付出浏览器启动成本。

---

## 5 已知限制：风控 710022004

生成请求可能返回：

```json
{"event_type":2005,"event_data":"{\"code\":710022004,\"message\":\"rate limited\",
 \"error_detail\":{\"ext\":{\"decision\":\"{\\\"type\\\":\\\"verify\\\",
 \\\"subtype\\\":\\\"semantic_reasoning\\\",\\\"verify_scene\\\":\\\"doubao_message_web\\\"}\"}}}"}
```

**已排除的原因**：不是缺少签名。请求携带有效的 `X-Bogus`
（`bdms.frontierSign` 在页面内可调用），同一会话的读取类接口全部正常。

**已实测无效的组合**：

| 组合 | 结果 |
|------|------|
| 纯 httpx + 完整 Cookie | 710022004 |
| Chromium 页面内 fetch（headless / headful） | 710022004 |
| Edge 通道页面内 fetch（headful） | 710022004 |
| 补上 `.bytedance.com` 的 `msToken` | 710022004 |
| 补齐 `device_id` / `web_id` / `tea_uuid` / `fp` | 710022004 |
| 直接使用已登录桌面端会话 | 710022004 |

**结论**：这是服务端基于账户/设备的风险判定，新建浏览器上下文无法即时清除。
遇到时请按 `SKILL.md` 第 6 节处理，向用户如实说明，不要盲目重试。

后续可尝试方向（尚未实现）：复用桌面端真实 profile、请求头完全对齐官方客户端并预热会话。

---

## 6 安全与隐私

- 会话文件默认以 Windows DPAPI（当前用户）加密落盘，Cookie 明文不落地。
- 任何工具都不会记录或返回 Cookie 值；日志中只出现不可逆的会话指纹。
- 读取浏览器 Cookie 属本地操作，无需提权，不发起任何外传请求。
- 去水印前必须显式确认，与豆包官方 UI 的确认步骤一致。

---

## 7 开发

```powershell
$env:PYTHONPATH="src"
python -m pytest tests -q      # 36 项单测
python -m ruff check src tests scripts
python scripts/build_plugin.py            # 组装自包含插件
python scripts/build_plugin.py --check    # CI 门禁：校验插件与源码同步
python scripts/live_probe.py              # 只读线上自检
```

### 版本

严格遵循组织版本规范 `v{Year}.{Major}-Alpha {N}`。当前 **v26.0.0-alpha.1**。

---

## 8 参考

| 仓库 | 借鉴内容 |
|------|----------|
| wangchuxiaoji-oss/doubao2api | `/samantha/chat/completion` 请求体、`content_type` / `skill_type` 枚举、`a_bogus` 与风控背景 |
| LauZzL/doubao-downloader | 无水印资源字段、AISpace 视频解析链路 |

豆包桌面端自带前端资源（`local_webcontents`）为本项目端点与枚举的权威来源，
证据链见 `docs/protocol.md`。

---

## 9 免责声明

本项目仅用于个人学习与自动化研究，请遵守豆包用户协议。
水印开关为豆包官方功能；去除 AI 生成标识带来的后果由使用者自行承担。

---

License: MIT
