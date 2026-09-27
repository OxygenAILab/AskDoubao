# Build Release / 构建发布

> Source: cursor-team-kit fix-ci + review-and-ship + Local Workspace build.py 实践

## 触发路由
关键词: 打包、build、exe、pyinstaller、编译为、构建、release、发布、CI/CD

## SOP: 构建与发布流程

### Phase 1: 预发检查 (3分钟)
1. `git status` 确认工作区干净
2. `git log -1` 确认待发布版本号
3. 运行现有测试套件 `python _selftest.py`
4. 检查 version.json 版本号是否递增

### Phase 2: 构建 (10分钟)
1. **Python**: `python build.py` 或 `build.bat`
2. **Node**: `npm run build` 或 `npx vite build`
3. 验证产物完整性:
   - 文件大小合理 (>100KB, 非空)
   - 哈希校验值记录
   - 快速 smoke test 启动验证

### Phase 3: CI 故障诊断 (如失败)
1. 解析构建日志 → 定位首个错误
2. 对比上次成功构建的日志 (如有)
3. 环境差异检查: Python/Node 版本、依赖版本、系统库
4. 增量修复: 每次只改一个变量，重新构建验证
5. 重复 ≤3 次; 若仍失败 → 完整环境重建

### Phase 4: 发布
1. Git commit + push (含 version.json)
2. 创建 Git Tag (vX.Y.Z)
3. 上传产物到发布仓库 (Gitee Release / GitHub Release)
4. 验证下载 URL HTTP 200
5. 更新 changelog

## 修 CI 速查

| 症状 | 常见原因 | 修复 |
|------|---------|------|
| ModuleNotFoundError | 依赖未安装或版本不匹配 | pip install -r requirements.txt --upgrade |
| ImportError: DLL load failed | Cython/Pyd 平台不匹配 | 检查 Python 位宽 (32/64) |
| Permission denied | 文件被进程占用 | 杀旧进程 |
| MemoryError | 内存不足 | 限制并行度 |
| Signing failed | 证书过期 | 检查签名配置 |

## 禁止行为
- 不跳过构建后验证
- 不 commit 未测试的代码
- 不 force push 到 main/master
