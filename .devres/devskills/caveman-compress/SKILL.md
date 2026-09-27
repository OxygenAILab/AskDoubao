---
name: caveman-compress
description: >-
  将自然语言文件（CLAUDE.md, README, 记忆文件等）批处理压缩为 caveman 格式，
  节省输入 token。保留所有技术实质、代码、URL 和结构。压缩版覆写原文件，
  可读备份保存为 FILE.original.md。
  触发词："/caveman-compress <文件路径>"、"压缩记忆文件"、"compress memory file"。
  支持本地离线压缩 (zh_compress 模块) 和远程 LLM 压缩 (Anthropic/DeepSeek API)。
category: 输出优化
license: MIT
author: JuliusBrussee (caveman), adapted by Local Workspace
source: https://github.com/JuliusBrussee/caveman
---

# Caveman Compress — 文件批量压缩

## 与 Local Workspace的兼容性

- 证据编号 (E1/E2…) 在压缩时永不触碰 — 自动识别为受保护内容
- 文件路径、偏移量、哈希值、函数名保持原样
- 代码块和命令行输出不会被压缩
- 敏感文件自动跳过（.env、credentials.*、*.pem、.ssh/ 等）
- 压缩前创建 .original.md 备份 → 可逆、可审计

## 目的

将自然语言文件 (CLAUDE.md, README, todos, preferences) 压缩为 caveman 风格，减少输入 token 消耗。压缩版覆写原文件。人类可读备份保存为 `<filename>.original.md`。

## 触发

`/caveman-compress <filepath>` 或用户要求压缩某个记忆文件。

## 处理流程

1. 压缩脚本位于 `scripts/`（与此 SKILL.md 相邻）。如果路径不可直接访问，搜索 `scripts/__main__.py`（紧邻此 SKILL.md）。

2. 在此 SKILL.md 所在目录下运行：

```bash
python -m scripts <文件绝对路径>
```

3. CLI 将：
- 检测文件类型（零 token 开销）
- 调用 LLM 压缩
- 验证输出（零 token 开销）
- 如有错误：精准修复（仅修复错误项，不重压整个文件）
- 最多重试 2 次
- 2 次重试后仍失败：向用户报告错误，保持原文件不变

4. 返回结果给用户

## 压缩规则

### 删除
- 冠词：a, an, the
- 填充词：just, really, basically, actually, simply, essentially, generally
- 客套语："sure", "certainly", "of course", "happy to", "I'd recommend"
- 弱化语："it might be worth", "you could consider", "it would be good to"
- 冗余表达："in order to" → "to", "make sure to" → "ensure"
- 连接填充："however", "furthermore", "additionally", "in addition"

### 精确保留（永不修改）
- 代码块（fenced ``` 和 缩进）
- 行内代码（`反引号内容`）
- URL 和链接（完整 URL、Markdown 链接）
- 文件路径（`/src/components/...`、`./config.yaml`）
- 命令（`npm install`、`git commit`、`docker build`）
- 技术术语（库名、API 名、协议、算法）
- 专有名词（项目名、人名、公司名）
- 日期、版本号、数值
- 环境变量（`$HOME`、`NODE_ENV`）

### 保留结构
- 所有 Markdown 标题（保持精确文本，压缩下方正文）
- 列表层级（保持嵌套层级）
- 编号列表（保持编号）
- 表格（压缩单元格文本，保持结构）
- Frontmatter / YAML 头

### 压缩
- 用短同义词："big" 而非 "extensive"，"fix" 而非 "implement a solution for"
- 碎片句 OK："Run tests before commit" 而非 "You should always run tests before committing"
- 删除 "you should"、"make sure to"、"remember to" — 直接陈述动作
- 合并表述相同的冗余条目
- 多个示例展示同一模式时，保留一个

**关键规则：**
`` ```...``` `` 内的任何内容必须**精确复制**。
不得：删除注释、删空格、调整行序、缩短命令、简化任何内容。

行内代码（`` `...` ``）必须**精确保留**。
不得修改反引号内的任何内容。

## 离线压缩（Local Workspace特有）

本工具包内置了 `zh_compress` 纯规则本地压缩器（零网络、零 API、零数据外泄）：

```python
from core.zh_compress import compress
result = compress(text, locale="auto")
# result["compressed"]  # 压缩后文本
# result["ratio"]       # 压缩率
```

适用于无 API key、内网环境、或敏感文件不想上传的场景。

## 边界

- 仅压缩自然语言文件（.md, .txt, .typ, .typst, .tex, 无扩展名）
- 绝不修改：.py, .js, .ts, .json, .yaml, .yml, .toml, .env, .lock, .css, .html, .xml, .sql, .sh
- 混合内容（散文+代码）：仅压缩散文段落
- 不确定是代码还是散文：保持原样
- 原文件在覆写前备份为 FILE.original.md
- 绝不压缩 FILE.original.md（跳过）
