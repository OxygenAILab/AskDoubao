---
name: digital-forensics
description: 数字取证与应急响应 — 内存分析 (Volatility 3)、磁盘时间线、PCAP 溯源、主机伪影、IOC 提炼与 IR 证据保全
---

# Digital Forensics & IR

## 适用场景

- 内存转储分析 (Volatility 3)
- 磁盘 / E01 / 落地文件时间线重建
- PCAP 溯源与协议还原 (联合 `protocol-reverse/`)
- 主机伪影: Prefetch、Shimcache、Event Log、Amcache、浏览器历史
- 应急响应 IOC 提炼 (联合 `threat-hunting/`)

## 前置条件

```bash
# 确认工具可用性
python3 -m pip install volatility3        # 内存分析
tshark --version                           # PCAP 分析 (Wireshark 套装)
# Eric Zimmerman 工具: https://ericzimmerman.github.io/
# Plaso/log2timeline: pip install plaso    # 超级时间线
```

## 工作流

### 0. 保全 (第一步，不可跳过)

```bash
# 对原始证据计算哈希
sha256sum evidence.dmp > evidence.dmp.sha256
sha256sum disk_image.E01 > disk_image.E01.sha256
sha256sum capture.pcapng > capture.pcapng.sha256

# 记录采集时间与采集命令
echo "Collected: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> chain_of_custody.txt
echo "Tool: FTK Imager 4.7.1" >> chain_of_custody.txt
echo "Operator: [你的姓名]" >> chain_of_custody.txt

# 所有分析在副本上进行，原始介质写保护
cp evidence.dmp evidence_analysis.dmp
```

### 1. 内存分析 (Volatility 3)

#### 1.1 基本信息扫描

```bash
# 内存镜像信息 (OS 版本 / 内核 / 架构)
vol -f memory.dmp windows.info

# 进程列表 (发现可疑进程)
vol -f memory.dmp windows.pslist
vol -f memory.dmp windows.psscan    # 含已终止进程

# 进程命令行 (恶意参数 / 编码命令)
vol -f memory.dmp windows.cmdline
vol -f memory.dmp windows.cmdline --pid <PID>

# 进程树 (父子关系，发现异常启动链)
vol -f memory.dmp windows.pstree
```

#### 1.2 恶意代码检测

```bash
# 进程注入检测 (Malfind — 异常的 VAD / MZ 头 / RWX 权限)
vol -f memory.dmp windows.malfind
vol -f memory.dmp windows.malfind --pid <PID>

# DLL 列表 (注入的恶意 DLL)
vol -f memory.dmp windows.dlllist
vol -f memory.dmp windows.dlllist --pid <PID>

# 检测不可信进程中的模块
vol -f memory.dmp windows.modules
```

#### 1.3 网络与凭据

```bash
# 网络连接 (C2 通信)
vol -f memory.dmp windows.netscan     # Win7+
vol -f memory.dmp windows.netstat     # WinXP/2003

# 注册表转储 (Run 键、服务等持久化)
vol -f memory.dmp windows.registry.hivelist
vol -f memory.dmp windows.registry.printkey --key "Software\Microsoft\Windows\CurrentVersion\Run"
vol -f memory.dmp windows.registry.printkey --key "SYSTEM\CurrentControlSet\Services"

# 凭据提取
vol -f memory.dmp windows.hashdump        # NTLM hashes
vol -f memory.dmp windows.lsadump         # LSA secrets
```

#### 1.4 完整取证扫描脚本

将以下命令保存为 `vol_full_scan.sh` 批量执行：

```bash
#!/bin/bash
VOL_IMG="$1"
if [ -z "$VOL_IMG" ]; then
    echo "Usage: $0 <memory.dmp>"
    exit 1
fi

OUTDIR="vol_output_$(basename "$VOL_IMG" .dmp)_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUTDIR"

echo "[*] 开始全量内存分析: $VOL_IMG"
echo "[*] 输出目录: $OUTDIR"

vol -f "$VOL_IMG" windows.info        > "$OUTDIR/01-info.txt"
vol -f "$VOL_IMG" windows.pslist       > "$OUTDIR/02-pslist.txt"
vol -f "$VOL_IMG" windows.psscan       > "$OUTDIR/03-psscan.txt"
vol -f "$VOL_IMG" windows.pstree       > "$OUTDIR/04-pstree.txt"
vol -f "$VOL_IMG" windows.cmdline      > "$OUTDIR/05-cmdline.txt"
vol -f "$VOL_IMG" windows.malfind      > "$OUTDIR/06-malfind.txt"
vol -f "$VOL_IMG" windows.dlllist      > "$OUTDIR/07-dlllist.txt"
vol -f "$VOL_IMG" windows.netscan      > "$OUTDIR/08-netscan.txt"
vol -f "$VOL_IMG" windows.hashdump     > "$OUTDIR/09-hashdump.txt"
vol -f "$VOL_IMG" windows.filescan     > "$OUTDIR/10-filescan.txt"
vol -f "$VOL_IMG" windows.registry.hivelist > "$OUTDIR/11-hivelist.txt"

echo "[+] 完成: $(ls "$OUTDIR" | wc -l) 个输出文件"
```

### 2. 主机伪影

#### 2.1 事件日志

```bash
# PowerShell 操作日志 (恶意 PS 脚本痕迹)
# 路径: C:\Windows\System32\winevt\Logs\
#   - Microsoft-Windows-PowerShell%4Operational.evtx
#   - Security.evtx (Event ID 4688/4697/4104)

# EvtxECmd (Eric Zimmerman 工具)
EvtxEcmd.exe -f Security.evtx --csv output/ --csvf security.csv

# 过滤异常进程创建 (EventID 4688)
grep -i "4688" output/security.csv | grep -vi "svchost\|csrss\|lsass"
```

#### 2.2 持久化机制

```text
检查清单:
□ Run 键: HKLM\Software\Microsoft\Windows\CurrentVersion\Run
           HKCU\Software\Microsoft\Windows\CurrentVersion\Run
□ 计划任务: C:\Windows\System32\Tasks\
□ 服务: HKLM\SYSTEM\CurrentControlSet\Services
□ WMI 事件订阅 (常见无文件持久化)
□ 启动文件夹: %APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
□ DLL 劫持: 检查 KnownDLLs 之外的不安全加载路径
```

#### 2.3 执行痕迹

```bash
# Prefetch (程序执行历史) — C:\Windows\Prefetch\
PECmd.exe -f C:\Windows\Prefetch\ --csv output/ --csvf prefetch.csv
# 时间排序可疑程序:
# sort by LastRun, filter 近期首次运行的 .exe

# Amcache (应用程序兼容性缓存)
AmcacheParser.exe -f C:\Windows\appcompat\Programs\Amcache.hve --csv output/

# BAM/DAM (Background Activity Moderator)
# HKLM\SYSTEM\CurrentControlSet\Services\bam\State\UserSettings\
```

#### 2.4 浏览器历史

```bash
# Chrome / Edge 历史
# 路径: %LOCALAPPDATA%\Google\Chrome\User Data\Default\History (SQLite)
sqlite3 History "SELECT url, title, last_visit_time/1000000-11644473600 AS visit_time FROM urls ORDER BY last_visit_time DESC LIMIT 50;"

# Firefox
# 路径: %APPDATA%\Mozilla\Firefox\Profiles\*.default-release\places.sqlite
sqlite3 places.sqlite "SELECT url, title, last_visit_date/1000000 FROM moz_places ORDER BY last_visit_date DESC LIMIT 50;"
```

### 3. 超级时间线 (Plaso/log2timeline)

```bash
# 从磁盘镜像生成超级时间线
log2timeline.py --storage-file timeline.plaso disk_image.E01

# 过滤最近 30 天的事件 → CSV
psort.py -o l2tcsv -w output_timeline.csv timeline.plaso "date > 'DATE_AGO_30'"

# 过滤特定来源
psort.py -o l2tcsv -w evt_timeline.csv timeline.plaso "parser == 'winevtx'"

# Timeline Explorer (GUI 工具) 打开 .csv 交互分析
```

### 4. PCAP 溯源

```bash
# 会话统计
tshark -r capture.pcapng -q -z conv,tcp
tshark -r capture.pcapng -q -z conv,udp

# DNS 查询统计 (C2/DGA 检测)
tshark -r capture.pcapng -q -z dns,tree

# HTTP 请求提取
tshark -r capture.pcapng -Y http.request -T fields -e http.host -e http.request.uri -e frame.time

# 导出可疑 IP 的所有流量
tshark -r capture.pcapng -w suspicious.bad_ip.pcap -Y "ip.addr == 10.99.99.99"

# 导出网络文件 (HTTP objects)
tshark -r capture.pcapng --export-objects http,exported_files/
```

**联动: 深度协议分析 → 交接给 `protocol-reverse/`**

### 5. IOC 提炼

从上述分析中提取：

```yaml
# iocs.yaml — 机器可读 IOC 清单
indicators:
  ips:
    - {address: "192.168.1.100", context: "C2 server", confidence: "high", source: "netscan"}
  domains:
    - {domain: "evil.example.com", context: "DGA domain", confidence: "medium", source: "dns_query"}
  hashes:
    - {sha256: "abc123...", filename: "malware.dll", context: "injected dll", source: "malfind"}
  mutexes:
    - {name: "Global\MalBot_Lock", context: "anti-debug mutex", source: "handles"}
  file_paths:
    - {path: "C:\Users\victim\AppData\Local\Temp\dropper.exe", context: "initial dropper", source: "prefetch"}
  registry:
    - {key: "HKLM\Software\Microsoft\Windows\CurrentVersion\Run\Updater", context: "persistence", source: "registry.printkey"}
```

## 工具链

| 工具 | 用途 | 安装 |
|------|------|------|
| Volatility 3 | 内存分析 | `pip install volatility3` |
| Plaso (log2timeline) | 超级时间线 | `pip install plaso` |
| tshark | PCAP 分析 | Wireshark 套装 |
| Eric Zimmerman 工具集 | Windows 伪影 | [下载](https://ericzimmerman.github.io/) |
| FTK Imager | 磁盘取证镜像 | [下载](https://www.exterro.com/ftk-imager) |
| Autopsy | GUI 磁盘取证 | [下载](https://www.autopsy.com/) |
| Timeline Explorer | CSV 时间线浏览 | Eric Zimmerman 套装 |

## 参考

- `references/forensics-triage.md` — 取证分诊顺序
- `../threat-hunting/` — IOC → 检测规则
- `../protocol-reverse/` — 深度协议分析
- `../reverse-engineering/` — 恶意二进制逆向

## 路由上下文

**关键词触发**: forensics, Volatility, memory dump, IR timeline, PCAP分析, 取证
**下游**: 恶意二进制 → `reverse-engineering`；检测规则 → `threat-hunting`

## 任务完成自检

- [ ] 证据哈希已计算并记录？(sha256sum + chain_of_custody)
- [ ] 所有分析均在副本上进行？原始介质写保护？
- [ ] 内存分析: info/pslist/psscan/pstree/cmdline/malfind/netscan 全部完成？
- [ ] 主机伪影: 事件日志 / 持久化 / 执行痕迹 / 浏览器历史 全覆盖？
- [ ] 超级时间线已生成并可交互浏览？
- [ ] PCAP: 会话统计 / DNS 查询 / HTTP 请求已提取？
- [ ] IOC 清单已生成 (YAML 格式，含分类与置信度)？
- [ ] 报告模板: Time | Host | Artifact | Finding | Confidence | Evidence path 已填？
