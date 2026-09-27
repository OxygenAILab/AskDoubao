---
name: ida-reverse
description: IDA Pro/Ghidra 高级逆向工作流 — IDAPython 脚本、反编译优化、结构体重建、交叉引用追踪、加密算法常量/API识别、反反编译技术应对全链路
category: 安全研究
author: Local Workspace
license: MIT
---

# IDA Pro / Ghidra Advanced Reverse Engineering

IDA Pro (含 Freeware 8.4) 和 Ghidra 11+ 的高级工作流技能。覆盖 IDAPython 脚本、反编译优化、结构体重建、交叉引用追踪、加密算法识别、Ghidra 脚本 (Java/Python) 全链路。

> **与工程纪律兼容性**: 所有地址/偏移量附带证据编号。IDA/Ghidra 输出不可压缩。函数重命名/结构体定义标记来源。

---

## 1. 工具选择决策树

```text
需要分析 x86/x64 Windows 二进制?
  ├─ 有 IDA Pro 许可证 → IDA Pro + Hex-Rays Decompiler + IDAPython
  └─ 没有 → Ghidra (免费, NSA 开源, 反编译器质量接近)

需要分析 ARM/MIPS/嵌入式计算?
  ├─ IDA Pro: 更好的调试器支持 + 更多处理器模块
  └─ Ghidra: 处理器支持广泛, 但调试器较弱

需要团队协作?
  └─ Ghidra: 自带协作服务器 (shared project)

需要插件生态?
  └─ IDA Pro: 大量社区插件 (keypatch, findcrypt, LazyIDA...)
```

---

## 2. IDA Pro 工作流

### 2.1 加载与预处理

```text
1. 文件 → 新建 → 选择二进制 (PE/ELF/Mach-O/Raw)
2. 加载选项:
   ▸ Manual load: 完全控制 section 映射
   ▸ Load resources: 加载 PE 资源段
   ▸ Rename DLL entries: 重命名导入函数
   ▸ Create segments: 自动创建 .text/.data/.rdata 段
3. 初始自动分析: 勾选 "Make final analysis pass" + "Kernel options"
```

### 2.2 核心操作速查

```markdown
# 导航
G           — 跳转到地址
Ctrl+X      — 交叉引用 (xrefs) 到当前符号
Ctrl+J      — 向前跳转引用
X           — 引用当前光标处符号/字符串
Esc         — 返回上一视图
Space       — 文本/图表视图切换

# 分析
A           — 转换为 ASCII 字符串
C           — 转换为代码
D           — 转换为数据 (byte/word/dword)
P           — 创建函数 (从当前地址)
U           — 取消定义 (转为原始字节)
N           — 重命名 (函数/变量/标签)
Y           — 设置类型 (函数签名/变量类型)
T           — 结构体偏移量标注
Shift+F1    — 添加/编辑局部类型
Ctrl+F9     — 创建结构体

# 反编译 (Hex-Rays)
F5          — 反编译当前函数
Tab         — 反编译/汇编视图切换
;           — 添加注释 (汇编视图)
/           — 添加注释 (反编译视图)
\           — 隐藏/显示反编译 casts
```

### 2.3 IDAPython 脚本模板

```python
# 1. 搜索所有交叉引用到目标函数
import idaapi, idautils, idc

target = idaapi.get_name_ea(idaapi.BADADDR, "target_function")
for xref in idautils.XrefsTo(target):
    print(f"XREF at {hex(xref.frm)}: {idc.generate_disasm_line(xref.frm, 0)}")

# 2. 遍历所有函数并筛选
for func_ea in idautils.Functions():
    name = idc.get_func_name(func_ea)
    if "encrypt" in name.lower() or "crypt" in name.lower():
        print(f"[CRYPTO] {name} @ {hex(func_ea)}")

# 3. 搜索二进制中的常量模式
import ida_bytes
pattern = bytes.fromhex("0123456789abcdef")
ea = ida_bytes.bin_search(0, 0xFFFFFFFF, pattern, None, ida_bytes.BIN_SEARCH_FORWARD)
while ea != idaapi.BADADDR:
    print(f"Pattern found at {hex(ea)}")
    ea = ida_bytes.bin_search(ea + 1, 0xFFFFFFFF, pattern, None, ida_bytes.BIN_SEARCH_FORWARD)

# 4. 提取所有字符串并按地址排序
import idautils
strings = []
for s in idautils.Strings():
    strings.append((s.ea, str(s)))
strings.sort()
for addr, s in strings:
    if any(kw in s.lower() for kw in ['key', 'pass', 'secret', 'token', 'http']):
        print(f"{hex(addr)}: {s}")
```markdown

### 2.4 常用 IDA 插件

| 插件 | 用途 |
|------|------|
| **findcrypt3** | 自动识别加密常量 (AES S-Box, CRC tables, TEA delta...) |
| **keypatch** | 二进制 patch (内联汇编编辑) |
| **LazyIDA** | 一键转换/提取/复制/搜索快捷操作 |
| **D810** | 自动去混淆 (OLLVM/Control Flow Flattening) |
| **efiXplorer** | UEFI 固件分析 |
| **ClassInformer** | C++ RTTI/虚表扫描 |
| **HRDevHelper** | Hex-Rays AST 遍历/修改 |
| **Diaphora** | 二进制 diff (关联 IDA 数据库) |

---

## 3. Ghidra 工作流

### 3.1 项目创建与加载

```text
1. File → New Project → Non-Shared Project → 命名
2. 导入: File → Import File → 选择二进制
   ▸ Format: PE/ELF/Mach-O/Raw Binary
   ▸ Language: 自动检测或手动指定
3. 打开: 双击导入的文件 → 点 "Yes" 运行自动分析
4. 分析选项:
   ▸ Decompiler Parameter ID: 恢复函数参数名
   ▸ Windows x86 PE Exception Handling: 恢复 SEH
   ▸ Shared Return Calls: 识别共享返回模式
```markdown

### 3.2 核心操作

```text
G           — 跳转到地址
Ctrl+Shift+F — 搜索内存 (字节/字符串/正则)
Ctrl+L      — 重命名 (函数/变量/标签)
Ctrl+E      — 反编译当前函数
F           — 创建函数
D           — 取消定义 (转为未定义)
C           — 清除代码/数据
T           — 设置数据类型
L           — 创建标签
;           — 添加注释
Ctrl+Shift+A — 创建数组
```markdown

### 3.3 Ghidra Python 脚本

```python
# 搜索加密常量 (在 Ghidra Script Manager 中运行)
from ghidra.program.model.mem import MemoryBlock
from ghidra.util.task import ConsoleTaskMonitor

AES_SBOX = bytes([0x63, 0x7c, 0x77, 0x7b, 0xf2, ...])
fm = currentProgram.getMemory()
blocks = fm.getBlocks()
while blocks.hasNext():
    block = blocks.next()
    if block.isInitialized():
        data = fm.getBlockBytes(block.start, ConsoleTaskMonitor())
        # 搜索 S-Box
```

### 3.4 Ghidra 常用扩展

| 扩展 | 用途 |
|------|------|
| **GhidraGolf** | 代码搜索/模式匹配 |
| **OoAnalyzer** | OOP C++ 分析 |
| **Ghidra Data Type Manager** | Windows API 类型定义 |
| **FindCrypt Ghidra** | 加密常量搜索 |
| **GhidraBowl** | Web UI 协作 |
| **Ghidra Bridge** | VSCode 集成 |

---

## 4. 加密算法识别方法论

### 4.1 常量识别

| 常量/模式 | 算法 |
|----------|------|
| `0x9E3779B9` (32-bit) | TEA delta |
| `0xC6EF3720` (32-bit) | XTEA delta |
| AES S-Box (256 bytes from `0x63`) | AES |
| `0x67452301, 0xEFCDAB89, 0x98BADCFE, 0x10325476` | MD5 IV |
| `0x6A09E667...` (8×32-bit) | SHA-256 IV |
| CRC32 table (256 entries from `0x00000000`) | CRC32 |
| Base64 alphabet (`ABCDEFGHIJKLMNOPQRSTUVWXYZabcdef...`) | Base64 encoding |
| `expand 32-byte k` (ASCII) | Salsa20/ChaCha20 constant |

### 4.2 API 调用识别

```text
Windows:
  ▸ CryptEncrypt / CryptDecrypt → 旧版 CryptoAPI
  ▸ BCryptEncrypt / BCryptDecrypt → CNG API
  ▸ CryptAcquireContext → 获取 CSP
  ▸ CryptGenRandom / RtlGenRandom → 随机数生成

Linux:
  ▸ EVP_EncryptInit / EVP_DecryptInit → OpenSSL
  ▸ AES_set_encrypt_key → OpenSSL AES
  ▸ HMAC / HMAC_Init → HMAC
```

---

## 5. 反反编译技术应对

| 反反编译技术 | 表现 | 应对 |
|-------------|------|------|
| Opaque Predicate | 永远不执行的分支但反编译器无法简化 | 手动 NOP/修改条件 |
| Control Flow Flattening | switch 分发器 + 状态变量 | D810 插件 / 手动跟踪状态 |
| Indirect Calls | `call [rax+offset]` | 动态调试确认实际 callee |
| Stack String | 逐字节构造栈上字符串 | IDAPython 模拟栈操作 |
| Import Obfuscation | 动态解析 API (GetProcAddress + hash) | 动态调试获取真实 API 名 |

---

## 6. 输出规范

```text
[IDA/GHIDRA: binary_name, arch]
  加载地址/SHA-256: ...
  函数总数: N, 已分析: M
  加密算法: (名称+偏移+证据: 常量/API/行为)
  关键函数: (名称+地址+功能描述)
  交叉引用图: (入口→关键函数→数据流)
  反反编译: (发现X处, 应对方案)
  证据索引: E1=... E2=...
```
