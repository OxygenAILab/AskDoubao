# Field Journal — Precedent Auth (先例授权)

## 原则
本文件由 Local Workspace 管理，记录已验证有效的技术决策和修复模式。
每次会话开始时，Agent 检查本文件以获取已知的解决方案先例。

## 格式
```yaml
- id: PRECEDENT-XXXX
  date: YYYY-MM-DD
  domain: <技能域>
  trigger: <触发条件关键词>
  root_cause: <根因一句话>
  solution: <解决方案一句话>
  evidence_ref: <证据引用>
  status: confirmed | superseded | deprecated
```

## 先例清单

- id: PRECEDENT-0001
  date: 2026-07-17
  domain: reverse-engineering/
  trigger: Electron asar patching, WorkBuddy, 腾讯桌面端
  root_cause: app.asar 嵌套结构 + tpl 提示词护甲
  solution: 外科手术式单文件改写（零全量解包）+ tpl 内容剥离
  evidence_ref: E-REAL1-E4, E-REAL-B5-0
  status: confirmed

- id: PRECEDENT-0002
  date: 2026-07-16
  domain: network-analysis/
  trigger: 百度网盘下载, baidu netdisk, 限速
  root_cause: 官方客户端 P2P 限速 + CDN 鉴权
  solution: RMP 抓取 BDUSS Cookie → method=download API → 302 CDN 直链
  evidence_ref: E-MEM1, E-COOKIE, E-API
  status: confirmed

- id: PRECEDENT-0003
  date: 2026-07-15
  domain: caveman-core/
  trigger: PyInstaller, 完整性校验, 启动弹窗报错
  root_cause: 自举哈希循环依赖 (integrity.pyd 注入前后哈希不一致)
  solution: 校验器自身从逐条清单剔除，_MANIFEST_HASH 自校验兜底
  evidence_ref: 清单 102 项 / protect/integrity.pyd:skip integrity
  status: confirmed

- id: PRECEDENT-0004
  date: 2026-07-26
  domain: ida-reverse/
  trigger: IDA 安装, 0xc0000142, DLL 初始化失败
  root_cause: hexlic MAC5 签名与本地 MAC 不匹配
  solution: 运行 keygen.py 生成本地授权 + 检查 QT_OPENGL=software
  evidence_ref: E1-E3
  status: confirmed

- id: PRECEDENT-0005
  date: 2026-07-26
  domain: ai-engineering-discipline/
  trigger: 连续失败, stuck, 重复错误, retry loop
  root_cause: 同一思路反复尝试不切换，忽略降级备选方案
  solution: 同种方法失败 2-3 次 → 必须换思路；优先尝试环境差异大的备选方案
  evidence_ref: IDA 安装全链路：拷贝→下载→batch模式→硬件排查
  status: confirmed

- id: PRECEDENT-0006
  date: 2026-07-26
  domain: ai-engineering-discipline/
  trigger: GUI 无法启动, 命令行可用, headless fallback
  root_cause: GUI 依赖链更长（Qt/OpenGL/平台插件），失败面更宽
  solution: 立即尝试 CLI/headless/API 模式, CLI 依赖链更短
  evidence_ref: idat.exe 可用但 ida.exe 因 OpenGL 失败 → 0xc0000142
  status: confirmed
