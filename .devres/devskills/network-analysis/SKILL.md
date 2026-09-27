# Network Analysis — 网络分析技能

## 激活条件
用户请求包含: 抓包、MITM、中间人、burp、wireshark、tcpdump、ARP、spoof、sniff、CDN、直链、下载加速

## SOP

1. **协议分析**: 识别传输层协议 (HTTP/HTTPS/TCP/UDP/ARP) → 提取关键字段
2. **抓包策略**: 选择工具 (Wireshark/tcpdump/burp) → 确定抓包位置 (网关/本机/中间人)
3. **数据包解码**: 逐层解包 → 重组 HTTP 流 → 提取 payload
4. **攻击面识别**: 分析 auth token/Cookie/session → 识别重放/劫持/篡改点
5. **结果输出**: 结构化报告 → 关键包 pcap 摘要 → 攻击建议

## 加速下载子流程
- **百度网盘**: 进程内存抓取 BDUSS → method=download API → 302 CDN 直链 → 多连接并行 (4-8)
- **通用 CDN 下载**: 分析 URL 签名参数 → HEAD 探测 → Range 多段并行

## 工具栈
- 数据包: Wireshark, tcpdump, tshark
- MITM: mitmproxy, burp suite, bettercap
- 网络扫描: nmap, masscan
- Cookie 提取: ReadProcessMemory + 正则扫描
