---
name: js-reverse
description: JavaScript 专用逆向工程 — 混淆还原、Webpack 拆包、AST 解混淆、环境模拟与算法提取、微信小程序反编译、Electron asar 逆向全链路
category: 安全研究
author: Local Workspace
license: MIT
---

# JavaScript Reverse Engineering — Dedicated Skill

JavaScript 专用逆向工程技能。覆盖混淆还原、Webpack 拆包、AST 解混淆、V8/JSC 引擎利用、微信小程序反编译、Electron 逆向全链路。

## 与工程纪律的兼容性

- 证据编号 E1/E2… 映射到 JS 文件路径、函数名、代码偏移
- AST 变换规则标记 [V] 已验证 / [H] 高置信推断（变换语义保真）
- 提取的 API key/sign 算法必须附带原文位置 + 哈希

---

## 1. 工具链

```text
MUST (核心):
  node / deno    — JS 运行时
  Chrome DevTools — 调试/格式化/断点
  Babel / @babel/parser + @babel/traverse + @babel/generator — AST 操作

按需:
  webcrack       — Webpack bundle 拆解/解混淆
  de4js          — 在线解混淆 (多重 encode/decode)
  js-beautify    — 代码格式化
  synchrony / prepack — 反混淆 + 常量折叠
  obfuscator-io-deobfuscator — 针对 obfuscator.io 的专用还原
  electron-extract — Electron asar 解包
  wxappUnpacker  — 微信小程序反编译
  deobfuscator / JStillery / jsnice — 变量名推测/还原
```

---

## 2. 标准分析流程

### Phase 1: 识别与分类

```html
1.1 识别 JS 文件类型
  ▸ 独立 .js 文件 → 直接分析
  ▸ Webpack bundle → webcrack -o unpacked/ bundle.js
  ▸ Electron asar → asar extract app.asar asar_out/
  ▸ 微信小程序 → wxappUnpacker
  ▸ HTML 内嵌 <script> → 提取到独立文件
  ▸ 服务端 Node.js → 检查 require/exports/module.exports

1.2 识别混淆类型
  ▸ obfuscator.io 特征: _0x1234, 0x1a2b + shift, 字符串数组 _0xabc1
  ▸ JJEncode: $=~[]; $={___:++$...  (eval 内)
  ▸ AAEncode: 表情符号编码 (ﾟωﾟﾉ...)
  ▸ JSFuck: []()!+ 六字符编码
  ▸ Eval 链: eval(eval(eval(...)))
  ▸ Webpack 乱序: __webpack_require__ + 模块 ID 数量极大
  ▸ 自定义混淆: 无明显已知模式 → 需要 AST 分析
```

### Phase 2: 多层解码

```text
2.1 文本级解码 (无 AST，仅字符串变换)
  ▸ Base64 / Base32 / Hex: atob / Buffer.from(x,'base64').toString()
  ▸ URL 编码: decodeURIComponent()
  ▸ 简单 Caesar/XOR: 单字节 XOR (如每个 char ^ 0x5A)
  ▸ 多重 encode: 循环 decode 直到无变化

2.2 AST 级解混淆 (用 Babel)
  步骤 1: 解析 → const ast = parser.parse(code);
  步骤 2: 遍历 + 变换:
    ▸ VariableDeclaration → 移除死代码 / 合并声明
    ▸ StringLiteral → 替换字符串数组引用 (e.g., _0xabc1('0x4') → "real_string")
    ▸ BinaryExpression → 常量折叠 (e.g., 1+2*3 → 7)
    ▸ IfStatement → 移除永真/永假分支
    ▸ CallExpression → 展开内联函数
    ▸ ReturnStatement → 简化 (e.g., !![] → true)
    ▸ MemberExpression → 还原计算属性名 (a["b"] → a.b)
    ▸ SequenceExpression → 摊平逗号表达式
  步骤 3: 生成 → generator(ast).code

2.3 Webpack Bundle 还原 (webcrack)
  命令: webcrack bundle.js -o unpacked/
  如果 webcrack 不支持 → 手动 AST:
    a. 找到 __webpack_require__ 定义 → 模拟 module cache
    b. 找到模块入口: __webpack_require__(入口ID)
    c. 重命名模块 ID 为有意义名称 (按 exports/功能)
    d. 重建模块依赖图
```

### Phase 3: 动态分析与 Hook

```javascript
3.1 浏览器环境 (Chrome DevTools)
  ▸ 在关键函数设断点
  ▸ Override 本地文件: Sources → Overrides → 本地保存 + 修改
  ▸ Console: 直接调用函数验证理解
  ▸ Network tab: 观察 HTTP 请求/响应 payload 中的加密数据

3.2 Node.js 环境
  ▸ node --inspect-brk script.js → Chrome DevTools attach
  ▸ 或: ndb node script.js
  ▸ require.cache 拦截模块
  ▸ Module._load 劫持

3.3 函数 Hook 模板
```javascript
// 劫持加密函数，记录输入输出
(function() {
  const original = target.encryptFunc;
  target.encryptFunc = function(data, key) {
    console.log('[HOOK] encrypt INPUT:', data, 'KEY:', key);
    const result = original.call(this, data, key);
    console.log('[HOOK] encrypt OUTPUT:', result);
    return result;
  };
})();
```text

### Phase 4: 加密算法逆向

```text
4.1 识别 Web Crypto API 调用
  ▸ crypto.subtle.encrypt / decrypt → AES-GCM / RSA-OAEP
  ▸ crypto.subtle.sign / verify → ECDSA / RSASSA-PKCS1-v1_5
  ▸ crypto.subtle.digest → SHA-256 / SHA-512
  ▸ crypto.subtle.deriveKey → HKDF / PBKDF2
  ▸ crypto.getRandomValues → CSPRNG 种子

4.2 识别常见 JS 加密库
  ▸ CryptoJS: CryptoJS.AES.encrypt, CryptoJS.MD5, CryptoJS.HmacSHA256
  ▸ jsencrypt: new JSEncrypt(), encrypt(), decrypt()
  ▸ forge: forge.md.sha256.create(), forge.pki.rsa
  ▸ tweetnacl: nacl.box, nacl.secretbox
  ▸ elliptic: new elliptic.ec('secp256k1'), key.sign()
  ▸ sjcl: sjcl.encrypt, sjcl.decrypt

4.3 签名算法特征
  ▸ 字符串拼接后 MD5/SHA: data + "&key=" + secret → md5 → sign
  ▸ HMAC: 先拼接再 HMAC-SHA256 → base64
  ▸ 非对称: JSON 排序 → RSA sign → base64 → 附加到请求头
  ▸ 自定义: 自定义位运算/查表/魔数 → 需要逐行逆向
```text

### Phase 5: 环境模拟 (Node.js 下运行浏览器 JS)

```javascript
5.1 最小 DOM mock
  window = { location: { href: "https://target.com" }, navigator: { userAgent: "..." } };
  document = { createElement: () => ({}), cookie: "", body: { appendChild: ()=>{}} };

5.2 完整方案: jsdom / linkedom / cheerio
  const { JSDOM } = require('jsdom');
  const dom = new JSDOM('<!DOCTYPE html>', { url: "https://target.com" });
  global.window = dom.window;
  global.document = dom.window.document;
  global.navigator = dom.window.navigator;

5.3 自动提取
  isolated-vm: 沙箱运行 + 监控全局变量修改 (vm2 已废弃且有沙箱逃逸 CVE, 不可用)
```javascript

---

## 3. 常见混淆特征速查表

| 混淆器 | 特征 | 解混淆方案 |
|--------|------|----------|
| obfuscator.io | `_0x[a-f0-9]+`, `function(_0x...`, 字符串数组旋转 | AST 遍历替换 + 死代码消除 |
| javascript-obfuscator | `var _0x... = function(...)` + Control Flow Flattening | webcrack 或 custom Babel plugin |
| Webpack v4/v5 | `__webpack_require__`, `webpackJsonp`, `__webpack_module_cache__` | webcrack / webpack-bundle-analyzer |
| Terser/UglifyJS | 单字母变量, 死代码已消除, 常量折叠 | js-beautify + jsnice 变量名推测 |
| JJEncode | `$=~[]; $={___:++$` | 直接 eval 或 cat 输出 |
| Eval 链 | `eval(eval(...("...".replace(...))))` | 逐层 console.log 或 node 执行捕获 |

---

## 4. 微信小程序逆向专属

```bash
▸ 工具: wxappUnpacker
▸ 步骤:
  1. adb pull /data/data/com.tencent.mm/MicroMsg/.../appbrand/pkg/xxx.wxapkg
  2. node wuWxapkg.js xxx.wxapkg
  3. 得到反编译后的项目目录 (含 app.json / pages / utils / app-service.js)
▸ 关键文件:
  ▸ app-service.js       — 逻辑代码 (Page/App 注册, 时间/网络 api)
  ▸ app-config.json      — 配置 (window/networkTimeout/permission)
  ▸ page-frame.html      — 渲染层
▸ Hook 要点:
  ▸ wx.request → 拦截网络请求
  ▸ wx.getStorageSync / wx.setStorageSync → 本地存储操作
  ▸ wx.login → OAuth 流程分析
```text

---

## 5. 输出规范

```text
[JS-RE: target.js / bundle.xxx.js]
  文件大小/SHA-256: ...
  混淆类型: [V]xxx / [H]推测xxx
  Webpack: [ ] 是 / [ ] 否, 模块数: ...
  解码步骤: 1) ... 2) ...
  发现的 API/Sign 算法: (函数名+偏移+输入输出示例)
  环境依赖: [ ] 浏览器 / [ ] Node.js / [ ] 小程序
  证据索引: E1=... E2=...
```

## 6. 参考

- Web 逆向通用指南: `_bundled_skills/reverse-engineering/references/web-re.md`
- 加密算法识别方法论: `_bundled_skills/reverse_flow_skill/references/crypto-analysis.md`
- [AST Explorer](https://astexplorer.net/) — 在线 AST 分析
- [Babel Handbook](https://github.com/jamiebuilds/babel-handbook)
- [webcrack](https://github.com/j4k0xb/webcrack)
