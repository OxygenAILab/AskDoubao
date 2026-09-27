---
name: apk-reverse
description: Android APK 专用逆向工程 — DEX/ODEX 反编译、Smali 修改、SO 分析、动态调试、脱壳、Frida 插桩、签名绕过全链路
category: 安全研究
author: Local Workspace
license: MIT
---

# APK Reverse Engineering — Dedicated Skill

Android APK 专用逆向工程技能。覆盖 DEX/ODEX 反编译、Smali 修改、SO 分析、动态调试、脱壳、Frida 插桩全链路。

## 与工程纪律的兼容性

- 证据编号 (E1/E2/E3…) 映射到 apk 文件偏移、类名、方法签名、SHA-256
- 脱壳/重打包/签名绕过步骤标记 [V] 已验证 / [H] 高置信 / [T] 推测
- 内存偏移量、加密密钥提取结果 → 不可压缩，不可省略

---

## 1. 环境与工具链 (NOW: 必须先校验)

```markdown
# 核心工具 (MUST 全部就位后才能开始分析)
1. apktool        — 反编译/重打包          验证: apktool --version
2. jadx / jadx-gui — DEX→Java 反编译      验证: jadx --version
3. dex2jar        — DEX→JAR 转换          验证: d2j-dex2jar --help
4. JD-GUI / CFR   — JAR→Java 反编译      验证: java -jar cfr.jar --help
5. Android Studio — 官方工具链            验证: adb --version
6. Frida          — 动态插桩              验证: frida --version
7. objection      — Frida 高级封装         验证: objection version
8. Android SDK tools — adb/apksigner/zipalign/apksigner
9. uber-apk-signer — 通用签名工具
10. baksmali/smali — DEX↔Smali 互转      验证: java -jar baksmali.jar --version
```

### 可选 (按需)
```markdown
- FART / BlackDex / Youpk — 脱壳机 (加壳 APK 专用)
- R0capture / PCAPdroid  — HTTPS 抓包
- Xposed / LSPosed       — 不脱壳时的动态 hook
- Fiddler / Burp Suite   — HTTP/HTTPS 代理抓包
- Ghidra / IDA Pro       — SO 文件 Native 层分析
```

---

## 2. 标准分析流程

### Phase 1: 前置检查 (确定性步骤)

```bash
STEP 1.1: adb devices                   — 确认设备连接
STEP 1.2: adb shell getprop ro.build.version.sdk — 确认 Android API 版本
STEP 1.3: adb shell getprop ro.product.cpu.abi   — 确认 CPU 架构
STEP 1.4: file target.apk | sha256sum target.apk  — 文件识别 + 哈希存档
STEP 1.5: aapt dump badging target.apk  — 提取包名/版本/权限
STEP 1.6: apktool d target.apk -o apktool_out/ -f  — 反编译资源+Smali
STEP 1.7: jadx -d jadx_out/ target.apk  — DEX→Java 反编译
```

### Phase 2: 静态分析

```bash
2.1 AndroidManifest.xml 审查
  ▸ debuggable 标记 → 决定能否 attach debugger
  ▸ allowBackup → 可能暴露 SharedPreferences
  ▸ exported Activities/Services/Receivers → 攻击面入口
  ▸ uses-permission 列表 → 推断功能边界

2.2 反编译代码审计
  ▸ 搜索关键字符串: "http", "secret", "key", "token", "password", "encrypt", "decrypt", "sign"
  ▸ 搜索 native 方法声明: loadLibrary, System.load, native 关键字
  ▸ 追踪 onCreate / onResume / doInBackground → 业务入口
  ▸ 识别加固/混淆标记: 类名/方法名是否被混淆 (a/b/c/d 常见于 ProGuard)

2.3 SO 文件预处理
  ▸ 提取所有 lib/*.so 文件列表
  ▸ 对每个 SO: file + strings + readelf -s + objdump -T
  ▸ 识别动态注册的 JNI 方法: 搜索 JNI_OnLoad → RegisterNatives
  ▸ 后续可挂 Ghidra/IDA 做深度静态分析

2.4 签名验证定位
  ▸ 搜索: getPackageManager().getPackageInfo, Signature, toCharsString
  ▸ 搜索: context.getPackageManager() + checkSignatures
  ▸ SO 层: 搜索 JNI 调用 getPackageInfo / fopen("/proc/self/maps", "r")
```

### Phase 3: 动态调试

```java
3.1 Frida 基础 hook
  ▸ frida -U -l hook.js com.example.app  — 设备上运行
  ▸ Hook 目标类: Java.perform(() => { Java.use("target.class").method.implementation = ... })
  ▸ Hook Native: Module.findExportByName, Interceptor.attach

3.2 objection 探索
  ▸ objection -g com.example.app explore
  ▸ android hooking list classes    — 列出所有已加载类
  ▸ android hooking search classes keyword — 关键词搜索
  ▸ android hooking watch class     — watch 类方法调用
  ▸ android keystore list           — 查看 KeyStore 条目

3.3 SSL Pinning 绕过
  ▸ objection: android sslpinning disable (最通用)
  ▸ Frida 脚本: 多种 bypass 方案 (自定义 TrustManager, OkHttp, TrustKit 等)
  ▸ Xposed: JustTrustMe / SSLUnpinning 模块
  ▸ 回退: 使用 http 而非 https 抓包 (仅开发/本地环境)

3.4 抓包
  ▸ R0capture: python r0capture.py -U com.example.app -p capture.pcap
  ▸ PCAPdroid: 无需 root 的本地抓包
  ▸ adb reverse tcp:8080 tcp:8080 + Burp Suite 代理
```

### Phase 4: 修改与重打包

```bash
4.1 Smali 编辑
  ▸ 修改 apktool_out/smali/ 下目标文件
  ▸ 常见 patch: 跳过付费校验 / 移除 root 检测 / 绕过签名校验
  ▸ 注释: 始终在修改行上方添加 # MODIFIED: YYYY-MM-DD reason

4.2 重打包
  ▸ apktool b apktool_out/ -o patched_unsigned.apk
  ▸ zipalign -v 4 patched_unsigned.apk patched_aligned.apk

4.3 签名
  ▸ uber-apk-signer --apks patched_aligned.apk
  ▸ 或: apksigner sign --ks debug.keystore patched_aligned.apk
  ▸ 验证: apksigner verify -v --print-certs patched_signed.apk

4.4 安装与测试
  ▸ adb install -r patched_signed.apk
  ▸ adb logcat | grep -E "AndroidRuntime|FATAL|crash"  — 监控崩溃
```

---

## 3. 加固/加壳应对

### 识别壳类型
```markdown
方式 A: jadx 反编译结果中类数量极少 (常 < 10 个) → 已加壳
方式 B: AndroidManifest.xml 中 Application 类名包含 "Stub" / "Wrapper" / "Proxy" → 大概率加壳
方式 C: apktool 报错或资源异常 → 加固可能导致

常见壳:
- 360 加固 (libjiagu.so)
- 腾讯乐固 (libshell.so, libtup.so)
- 梆梆加固 (libDexHelper.so)
- 爱加密 (libexec.so, libexecmain.so)
```

### 脱壳方法 (按成功率降序)
```bash
1. FART 脱壳机           — 刷入 ROM 或用 VirtualApp + FART 模块
2. BlackDex              — Xposed 模块，脱壳后自动保存 DEX
3. Youpk                 — AOSP 修改版，dumpMethod 全覆盖
4. frida-dexdump         — Frida 脚本 dump 内存中完整 DEX
5. 最后手段: 动态 GDB 附加 → dump /proc/PID/maps + /proc/PID/mem
```

---

## 4. SO (Native) 层分析速查

```javascript
# 静态
readelf -h libtarget.so    → 头信息 (架构/入口)
readelf -d libtarget.so    → 动态段 (依赖库)
readelf -s libtarget.so    → 符号表
objdump -T libtarget.so    → 动态符号表 (看导出函数)
strings libtarget.so | grep -iE "key|encrypt|decrypt|sign|verify"
strings libtarget.so | grep "Java_"  → 静态注册的 JNI 函数

# 动态 (Frida)
Interceptor.attach(Module.findExportByName("libtarget.so", "Java_com_example_MainActivity_check"), {
    onEnter: function(args) { console.log("args:", args[0], args[1], args[2]); },
    onLeave: function(retval) { console.log("retval:", retval); }
});

# 动态 (GDB)
adb forward tcp:1234 tcp:1234
adb shell gdbserver :1234 --attach PID
target remote :1234
```

---

## 5. 常见场景速查

| 场景 | 关键步骤 | 关键词搜索 |
|------|---------|-----------|
| 破解付费 | Smali 改 `if-eqz` / `if-nez` 跳转 | `pay`, `vip`, `isVip`, `premium` |
| 绕过 Root 检测 | Hook `Runtime.exec("su")` / `File("/system/app/Superuser.apk").exists()` | `root`, `su`, `Superuser`, `exec` |
| 获取 API Key | Frida hook `SharedPreferences.getString` | `api`, `key`, `secret`, `token` |
| 修改游戏数据 | Frida hook setter 改内存值 / Cheat Engine + GG | `gold`, `coin`, `diamond`, `score` |
| 抓 HTTPS 包 | objection sslpinning disable + Burp | `setCertificatePinner` |
| 提取 SO 算法 | IDA/Ghidra 静态 + unicorn 模拟执行 | JNI exported functions |

---

## 6. 参考资料

- 移动端逆向完整指南: `_bundled_skills/reverse-engineering/references/mobile-re.md`
- [Frida 官方文档](https://frida.re/docs/android/)
- [APKLab (VSCode 插件)](https://github.com/APKLab/APKLab)
- [Android 开发者文档 - App Manifest](https://developer.android.com/guide/topics/manifest/manifest-intro)

---

## 7. 输出规范

每次 APK 分析完成后必须输出:
```text
[APK: com.example.app v1.2.3]
  包名/版本/签名/SHA-256: ...
  加固状态: [ ] 未加固 / [V]xxx壳 / [H]推测xxx壳
  Manifest 关键项: debuggable=, exported Activities=...
  发现的密钥/Token: (偏移+证据编号)
  Smali 修改清单: (文件+行号+修改目的)
  重打包状态: [V]成功安装 / [ ]失败 (原因)
  证据索引: E1=... E2=... E3=...
```
