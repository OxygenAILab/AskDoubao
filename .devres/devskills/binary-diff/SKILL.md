---
name: binary-diff
description: 二进制差异分析 — BinDiff/Diaphora/radiff2 补丁对比、安全更新差异识别、1-Day 漏洞利用开发、Patch Tuesday 逆向分析
category: 安全研究
author: Local Workspace
license: MIT
---

# Binary Diffing — Patch Analysis & 1-Day Exploit Development

二进制差异分析技能。覆盖补丁前后二进制对比 (BinDiff/Diaphora)、安全更新差异识别、1-Day 漏洞利用开发、补丁回溯 (Patch Tuesday 逆向分析)。

> **工程纪律**: diff 分析输出中的全部偏移量/函数名/结构体变化必须附带证据编号。1-Day 利用路径标记置信度 [V]/[H]/[T]。

---

## 1. 工具链

| 工具 | 用途 | 平台 |
|------|------|------|
| **BinDiff** | IDA/Ghidra 插件, 二进制函数/基本块/调用图 diff | IDA/Ghidra |
| **Diaphora** | IDA 插件, 比 BinDiff 更灵活, 支持 SQLite 导出 | IDA Pro |
| **patchdiff2** | IDA 插件, 补丁差异分析 | IDA Pro |
| **bindiff2db** | 命令行 diff, 输出 JSON | Win/Linux |
| **radiff2** | radare2 内置二进制 diff | 跨平台 |
| **TurboDiff** | .NET 程序集 diff (.exe/.dll) | Win |
| **DarunGrim** | 二进制 diff + 漏洞分类 | Win |
| **Ghidra Version Tracking** | Ghidra 内置 diff 工具 | Ghidra |

---

## 2. 分析工作流

### Phase 1: 准备两版二进制

```bash
1.1 收集目标
  ▸ 旧版 (打补丁前): 从系统备份/VSS/HFS 提取, 或从 MS Update Catalog 下载 MSU
  ▸ 新版 (打补丁后): 从已更新的系统或更新包提取

1.2 预处理
  ▸ file patched.dll         → 确认架构/格式
  ▸ certutil -hashfile patched.dll SHA256 → 存档哈希
  ▸ 如果是从 CAB/MSU 提取:
    ▸ expand -F:* update.msu temp/
    ▸ expand -F:* temp/*.cab target/
  ▸ 去混淆 (如果有): 先用 IDA/Ghidra 做基本分析
```

### Phase 2: 执行 Diff

#### BinDiff (IDA Pro)
```text
1. 在 IDA 中打开旧版 .idb → File → BinDiff → "Diff Database"
2. 选择新版 .idb → 等待 diff 完成
3. 主要视图:
   ▸ Matched Functions: 匹配的函数列表
   ▸ Primary Unmatched: 旧版有而新版没有的函数
   ▸ Secondary Unmatched: 新版有而旧版没有的函数 (新增)
   ▸ Changed Functions: 匹配但内容有变化的函数
4. 排序: 按 Similarity 升序 (变化最大的排前面)
5. 双击目标函数 → 进入 Flow Graph diff
```

#### Diaphora (IDA Pro)
```python
# 导出旧版 SQLite 数据库 (在 IDA 中运行 diaphora.py)
File → Script File → diaphora.py → Export
# 在新版中做 diff
File → Script File → diaphora.py → Diff against → 选择旧版 .sqlite

# Diaphora 输出:
# - Best matches: 相似度 > 0.95
# - Partial matches: 0.6-0.95
# - Unreliable matches: < 0.6
# - Unmatched in primary: 旧版独有
# - Unmatched in secondary: 新版独有
```markdown

#### radiff2 (命令行)
```bash
# 函数级 diff
radiff2 -C old.dll new.dll           # 函数匹配程度
radiff2 -A old_binary new_binary      # 地址映射
radiff2 -g old.dll new.dll | xdot -   # 图形化差异

# 二进制级 diff (看到字节级变化)
radiff2 -x old.dll new.dll
```

### Phase 3: 聚焦变化函数

```text
3.1 筛选高价值目标 (按优先级)
  1) Primary Unmatched → 函数被删除/重写 → 可能是旧漏洞被修复
  2) Changed Functions (Similarity 0.5-0.9) → 修改了逻辑 → 可能添加了安全检查
  3) Secondary Unmatched → 新增函数 → 可能是新增的验证逻辑或新功能

3.2 逐函数深度分析
  ▸ 观察新增的基本块 (流程图中的绿色块)
  ▸ 特别关注新增的:
    - 条件跳转 (if/switch 语句)
    - 参数校验 (长度检查/范围检查/格式检查)
    - 内存操作变化 (新增 memset/锁定/引用计数)
    - 返回值变化 (从 void 变为返回错误码)
  ▸ 反向推理: "新增了什么检查?" → "旧版缺少这个检查" → "旧版绕过这个检查可以触发什么?"

3.3 识别 CVE 修复模式
  常见修复模式:
    ▸ +if (size > MAX) return ERROR;              → 缓冲区溢出 (CWE-120)
    ▸ +if (ptr == NULL) return ERROR;              → 空指针解引用 (CWE-476)
    ▸ +if (index >= count) return ERROR;           → 越界访问 (CWE-129)
    ▸ +SanitizePath(path);                         → 路径遍历 (CWE-22)
    ▸ +ValidateCertificate(cert);                  → 证书验证绕过 (CWE-295)
    ▸ +memset(buffer, 0, size); 在释放前           → 信息泄露 (CWE-244)
    ▸ +lock(); ... critical_section ... +unlock(); → 竞态条件 (CWE-362)
```

### Phase 4: 1-Day Exploit 开发

```text
4.1 从修复反向推导 PoC
  已知: 新版在函数 F 的偏移 +offset 处添加了检查 C
  推导: 旧版缺少 C → 在调用 F 之前满足条件 X → 触发漏洞

4.2 构建触发条件
  ▸ 参数模糊: 逆推检查 C 拦截的 "错误值" → 将错误值作为输入
  ▸ 状态构造: 构造触发 F 前的内存/寄存器状态
  ▸ 路径确认: 确认旧版确实会走到 F 的可利用路径

4.3 开发利用链
  ▸ 控制流劫持: 是否可覆盖返回地址/虚表/函数指针?
  ▸ 数据流污染: 漏洞值是否传播到关键操作 (memcpy/strcpy/format string)?
  ▸ 保护绕过: ASLR/DEP/CFG/CET → 是否需要信息泄露辅助原语?

4.4 验证
  ▸ 在旧版系统/VM 上测试 PoC
  ▸ 确认新版系统上 PoC 被阻止
  ▸ 记录操作系统版本+二进制版本+SHA-256
```

---

## 3. Windows Update 补丁获取

```powershell
# 方法 1: Microsoft Update Catalog
# 搜索 KB 号 → 下载 MSU → 解压
Invoke-WebRequest -Uri "https://catalog.s.download.windowsupdate.com/...msu" -OutFile "update.msu"
mkdir msu_expanded
expand -F:* update.msu msu_expanded\

# 方法 2: 从已打补丁的系统提取
# 路径: C:\Windows\System32\*.dll (64-bit)
# 路径: C:\Windows\SysWOW64\*.dll (32-bit on 64-bit)
# 路径: C:\Windows\WinSxS\ (Side-by-Side 组件存储)

# 方法 3: 从旧系统提取 (VSS 卷影副本)
vssadmin list shadows
# 挂载旧快照 → 复制旧版文件
```markdown

---

## 4. 输出规范

```text
[BINDIFF: old.dll vs new.dll, KBxxxxxxx]
  函数总计: old=N, new=M, 匹配=K
  主要差异:
    ▸ 删除函数: N (列优先级 top 5)
    ▸ 新增函数: M (列优先级 top 5)
    ▸ 修改函数: L (相似度 <0.8 的 top 10)
  CVE 候选:
    ▸ candidate 1: (函数名+修复模式+漏洞类型+置信度)
    ▸ candidate 2: ...
  1-Day 可利用性:
    ▸ candidate 1: [V]PoC 构建中 / [H]推测可利用 / [T]需更多分析
  证据索引: E1=... E2=... E3=...
```
