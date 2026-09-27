# Deploy Infra / 部署基础设施

> Source: cursor-team-kit review-and-ship + docker/kubernetes deployment patterns

## 触发路由
关键词: docker、容器、k8s、kubernetes、部署、deploy、CI/CD、nginx、helm、terraform

## SOP: 部署流程

### Phase 1: 部署前检查
1. 确认目标环境: dev / staging / production
2. 检查所有环境变量/密钥已配置 (不在代码中硬编码)
3. 确认数据库迁移脚本已准备
4. 确认回滚方案存在 (旧版本镜像/包)

### Phase 2: 容器化
1. **Dockerfile 最佳实践**:
   - 多阶段构建减小镜像体积
   - 非 root 用户运行
   - HEALTHCHECK 指令
   - `.dockerignore` 排除不必要文件
2. **docker-compose**: 服务编排、网络、卷
3. **K8s**: Deployment + Service + Ingress + ConfigMap/Secret

### Phase 3: 部署执行
1. 灰度/金丝雀: 先 10% 流量 → 监控 → 全量
2. 蓝绿部署: 新环境就绪后切换流量
3. 健康检查: HTTP 200 /ready + /healthz
4. 日志监控: 启动后 5 分钟内无错误激增

### Phase 4: 部署后验证
1. Smoke test: 关键 API 端点 HTTP 200
2. 数据库连接正常
3. 前端页面可访问
4. 监控面板指标正常 (CPU、内存、延迟、错误率)

## 环境差异矩阵

| 配置项 | Dev | Staging | Production |
|--------|-----|---------|------------|
| 副本数 | 1 | 2 | 3+ |
| 日志级别 | DEBUG | INFO | WARN |
| 资源限制 | 256Mi | 512Mi | 2Gi |
| 自动扩缩 | 关 | 开 (保守) | 开 (标准) |
| 备份 | 无 | 每日 | 每小时 + 异地 |

## 回滚 SOP
1. 触发条件: 错误率 >5% 持续 2 分钟
2. 执行: `kubectl rollout undo deployment/app` 或 docker 切换镜像标签
3. 验证: 回滚后重新 smoke test
4. 记录: 回滚原因 + 影响范围 + 修复计划

## 禁止行为
- 不跳过灰度直接全量
- 不把密钥提交到仓库
- 不忽略健康检查失败
