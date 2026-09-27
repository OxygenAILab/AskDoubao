---
name: ghidra-reverse
description: Ghidra 开源逆向工程 — headless 批量分析、Java/Python 脚本、MCP 桥接、与 binary-diff/patch-diff-exploit 联动
---

# Ghidra Reverse Engineering

## 适用场景

- 无 IDA 许可证时的主逆向入口
- 批量 headless 分析（CI/CD 反编译流水线）
- Ghidra 脚本自动化（Java / Jython / PyGhidra）
- 与 `binary-diff` / `patch-diff-exploit` 的 ghidriff 联动

## 与 IDA 分工

| 需求 | 优先 |
|------|------|
| 已有 IDA MCP 深挖 | `ida-reverse/` |
| 开源 / 批量 / 教学 / CI | **本 skill** |
| 仅 CLI 快速侦察 | `radare2/` |

## 环境确认 (第一步)

```bash
# 检查 Ghidra 安装路径
# 常见位置:
#   Windows: C:\ghidra_11.x\ 或 %GHIDRA_HOME%
#   Linux/macOS: /opt/ghidra/ 或 $GHIDRA_HOME
echo %GHIDRA_HOME%           # Windows
echo $GHIDRA_HOME            # Linux/macOS

# 验证可执行
%GHIDRA_HOME%\support\analyzeHeadless.bat   # Windows
$GHIDRA_HOME/support/analyzeHeadless         # Linux/macOS

# 若未安装: 下载 https://github.com/NationalSecurityAgency/ghidra/releases
```

## 工作流

### 1. 创建项目与导入

```bash
# 创建项目目录
mkdir -p ghidra_projects/$(basename $TARGET)

# headless 导入 + 自动分析
$GHIDRA_HOME/support/analyzeHeadless \
  ghidra_projects \
  $(basename $TARGET) \
  -import $TARGET \
  -overwrite \
  -postScript GhidraAnalysisLogger.java  # 自定义脚本，无则省略

# 输出: .gpr 项目文件 + .rep 仓库目录
```

**GUI 路径：** File → New Project → Import File → 全选默认分析器 → Analyze

### 2. 信息收集 (标准侦察)

在 Ghidra GUI 或 headless 脚本中依次执行：

- [ ] **入口点**: `_start` / `main` / `DllMain` / 导出表 → 记录地址
- [ ] **字符串**: Search → For Strings → 筛选关键串（URL/IP/路径/注册表/错误信息）
- [ ] **导入表**: 按库分组 → 标记关键 API：
  - 文件操作: `CreateFile`、`WriteFile`、`fopen`
  - 网络: `socket`、`connect`、`WinHttpOpen`、`URLDownloadToFile`
  - 注册表: `RegOpenKey`、`RegSetValue`
  - 进程: `CreateProcess`、`OpenProcess`、`VirtualAlloc`
  - 加密: `CryptAcquireContext`、`CryptEncrypt`、`BCrypt*`
- [ ] **交叉引用 (Xrefs)**: 从关键字符串/API 反向追踪调用链

### 3. 关键函数深度分析

对每个关键函数 (从字符串/API xref 定位)：

```text
□ 重命名函数: 按 L → 输入语义化名称 (如 "DecryptConfig_RC4" 而非 "FUN_00401000")
□ 重命名变量: 右键 → Rename Variable → 语义化 (如 "encrypted_buf" 而非 "local_38")
□ Plate Comment: 按 ; → 描述函数总体行为
□ Disassembly Comment: 在关键指令右侧注释 "检查返回值" "循环边界"
□ 记录调用链: 谁调用此函数 → 此函数调用谁
□ 标记关键分支: if/switch 中的 magic number → 注释其含义
```

**反编译优化技巧：**
- 函数签名修正: 右键 → Edit Function Signature → 补充参数类型
- 结构体恢复: 右键 → Auto Create Structure
- 类型传播: 选择变量 → 右键 → Retype Variable → 选择已知类型

### 4. Headless 脚本自动化

#### Java 脚本 (推荐，原生 API)

```java
// ExportFunctions.java — 导出所有函数反编译到文件
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.FunctionIterator;
import java.io.FileWriter;
import java.io.PrintWriter;

public class ExportFunctions extends GhidraScript {
    public void run() throws Exception {
        DecompInterface decomp = new DecompInterface();
        decomp.openProgram(currentProgram);

        PrintWriter pw = new PrintWriter(
            new FileWriter(currentProgram.getName() + "_decompiled.c"));

        FunctionIterator funcs = currentProgram.getFunctionManager()
            .getFunctions(true);
        while (funcs.hasNext()) {
            Function f = funcs.next();
            if (f.isThunk()) continue;  // 跳过 thunk

            DecompileResults dr = decomp.decompileFunction(f, 30, monitor);
            if (dr != null && dr.decompileCompleted()) {
                pw.println("// ── " + f.getName() + " @ " + f.getEntryPoint());
                pw.println(dr.getDecompiledFunction().getC());
                pw.println();
            }
        }
        pw.close();
        println("Done: " + currentProgram.getName() + "_decompiled.c");
    }
}
```

使用：
```bash
# 将 ExportFunctions.java 放入 Ghidra 脚本目录
# 默认: %GHIDRA_HOME%\Ghidra\Features\Base\ghidra_scripts\
cp ExportFunctions.java $GHIDRA_HOME/Ghidra/Features/Base/ghidra_scripts/

# headless 执行
$GHIDRA_HOME/support/analyzeHeadless \
  ghidra_projects ProjName \
  -process sample.bin \
  -postScript ExportFunctions.java
```

#### Python (Jython) 脚本

```python
# list_strings.py — 导出所有定义字符串
from ghidra.program.model.listing import CodeUnit

fm = currentProgram.getFunctionManager()
funcs = fm.getFunctions(True)
for f in funcs:
    if f.getName().startswith("FUN_"):
        continue
    print("[func] {} @ {}".format(f.getName(), f.getEntryPoint()))

listing = currentProgram.getListing()
data_iter = listing.getDefinedData(True)
while data_iter.hasNext():
    d = data_iter.next()
    if d.hasStringValue():
        addr = d.getAddress()
        val = d.getDefaultValueRepresentation()
        print("[str] {}: {}".format(addr, val))
```

### 5. Ghidra MCP 桥接 (AI 自动化)

```bash
# 安装 ghidra-mcp (开源 MCP server for Ghidra)
git clone https://github.com/your-org/ghidra-mcp.git
cd ghidra-mcp
pip install -r requirements.txt

# 启动 MCP server (默认端口 8765)
python mcp_server.py --port 8765

# 在 Ghidra 中加载 Script: ghidra_mcp_connector.py
# Window → Script Manager → 运行 ghidra_mcp_connector

# 验证连接
curl http://localhost:8765/health
# → {"status": "ok", "program": "sample.bin", "functions": 1234}
```

**MCP 能力 (通过 AI 调用):**
- `get_decompilation(addr)` — 指定地址反编译
- `get_xrefs_to(addr)` — 交叉引用查询
- `rename_function(addr, new_name)` — 批量重命名
- `set_comment(addr, comment)` — 注释注入
- `list_functions()` / `list_strings()` — 批量枚举
- `search_pattern(pattern_hex)` — 字节模式搜索

### 6. 与其他技能的联动

| 场景 | 联动目标 |
|------|---------|
| 发现加密算法 (反编译中识别) | → `reverse-engineering/` 算法还原章 |
| CVE 补丁 diff | → `patch-diff-exploit/` ghidriff 差分 |
| 1-day 二进制 diff | → `binary-diff/` |
| 需要动态验证 | → `reverse_flow_skill/` Frida/GDB 章 |
| Stack/heap 漏洞 | → `pwn-chain/` 利用开发 |
| Go 二进制符号恢复 | → `go-rust-reverse/` (GoReSym 预处理后再入 Ghidra) |

## 工具链

| 工具 | 用途 | 获取方式 |
|------|------|---------|
| Ghidra 11.x | 反编译主引擎 | [GitHub Release](https://github.com/NationalSecurityAgency/ghidra/releases) |
| ghidra-mcp | AI 桥接 MCP server | pip install / git clone |
| ghidriff | 补丁差分引擎 | pip install ghidriff |
| Java JDK 17+ | Ghidra 运行时依赖 | `java -version` 确认 ≥ 17 |

## 参考

- `references/ghidra-cheatsheet.md` — 快捷键速查
- `../ida-reverse/` — IDA 商业深挖
- `../radare2/` — CLI 快速侦察
- `../binary-diff/` — 二进制差分
- `../patch-diff-exploit/` — 补丁利用

## 路由上下文

**关键词触发**: ghidra, analyzeHeadless, no IDA, 开源反编译
**同级**: `ida-reverse` (商业) / `radare2` (轻量 CLI)
**下游**: 动态验证 → `reverse_flow_skill`；利用 → `pwn-chain`

## 任务完成自检

- [ ] 环境确认: `$GHIDRA_HOME` 有效且 `analyzeHeadless` 可执行？
- [ ] 项目创建 + 导入成功？
- [ ] 所有关键函数已重命名并注释？
- [ ] 字符串/导入表/交叉引用已全部分析？
- [ ] 反编译输出已导出 (Java 脚本或手动保存)？
- [ ] 所有地址、函数名、注释、调用链均已记录？
- [ ] 联动需求已交接给对应技能域？
