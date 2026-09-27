# Performance Optimization / 性能优化

> Source: agent-skills-hub patterns + profiling best practices

## 触发路由
关键词: 优化、性能、慢、卡顿、memory、内存泄漏、OOM、profiling、bottleneck、latency

## SOP: 性能优化流程

### Phase 1: 量化基准 (Baseline)
1. **确认瓶颈指标**: 响应时间 P50/P95/P99、吞吐量 QPS、内存峰值、CPU 使用率
2. **建立基准**: 当前数值 + 目标数值
3. **可重复负载**: wrk/ab/locust 生成标准流量
   ```bash
   wrk -t4 -c100 -d30s --latency http://localhost:8080/api/endpoint
   ```

### Phase 2: Profiling 定位
| 语言 | 工具 |
|------|------|
| Python | `cProfile` + `snakeviz`, `py-spy`, `memory_profiler` |
| Node | `node --inspect` + Chrome DevTools, `clinic` |
| Go | `pprof`, `go tool trace` |
| Java | `jprofiler`, `async-profiler`, `JFR` |

**关键思路**: 80% 耗时在 20% 代码 → 先找热点、不是瞎改

### Phase 3: 优化策略矩阵

| 瓶颈类型 | 策略 |
|---------|------|
| CPU 密集 | 缓存结果、算法降复杂度、并行/异步、C扩展 |
| IO 密集 | 连接池、批量操作、异步 IO、CDN |
| 内存泄漏 | 对象引用追踪、weakref、及时 close、限制缓存大小 |
| 数据库慢查 | 索引优化、查询改写、连接池、读写分离、分区表 |
| 网络延迟 | 减少往返、HTTP/2 multiplex、keep-alive、就近部署 |
| GC 停顿 | 对象池、减少分配、调整 GC 参数、off-heap |

### Phase 4: 验证与回测
1. 应用优化 → 重新跑基准测试
2. 对比优化前后: P50/P95/QPS/内存
3. 回归测试: 确保功能无破损
4. 如未达标 → 回到 Phase 2 找下一个热点

## 内存泄漏排查 SOP
1. **确认泄漏**: 连续取样 3 次，内存 monotonic 增长
2. **堆快照**: 间隔 5 分钟取 2 份 heap dump
3. **Diff 分析**: 增长最多的对象类型
4. **引用链**: 从增量对象追溯 GC root
5. **修复**: 解除不需要的引用 (置 None/close/weakref/remove listener)
6. **验证**: 稳定性测试 30 分钟无 OOM

## 禁止行为
- ❌ 不量基准就直接改
- ❌ 改完不验证
- ❌ 迷信 "加缓存能解决一切"
- ❌ 不区分 I/O bound vs CPU bound
