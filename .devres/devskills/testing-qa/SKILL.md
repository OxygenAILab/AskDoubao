# Testing QA / 测试与质量保障

> Source: cursor-team-kit run-smoke-tests + verify-this + agent-skills-hub testing-patterns

## 触发路由
关键词: 测试、unittest、pytest、coverage、覆盖率、CI、smoke test、e2e、端到端、集成测试、regression

## SOP: 测试工作流

### Phase 1: 测试策略判定
| 需求类型 | 推荐测试 |
|---------|---------|
| 新功能 | Unit + Integration |
| Bug 修复 | Regression (复现→验证) |
| 重构 | Full suite + Snapshot diff |
| 紧急热修 | Smoke test → 重点区域 Unit |
| 发布前 | E2E + Smoke + Load (如适用) |

### Phase 2: 测试编写 (以 Python/pytest 为例)
```python
# 单元测试模板
def test_<function>_<scenario>():
    """Given <前置条件> When <操作> Then <预期结果>"""
    # Arrange
    # Act
    # Assert
```

### Phase 3: Smoke Test (冒烟测试)
1. 核心流程端到端: 登录→创建→查询→删除
2. 关键 API 端点 200 OK
3. 数据库读/写正常
4. 外部依赖连通性 (如支付、邮件、S3)
5. 前端页面无白屏/JS 报错

### Phase 4: 覆盖率与质量门禁

| 指标 | 最低 | 建议 | 优秀 |
|------|------|------|------|
| 行覆盖率 | 60% | 80% | 90%+ |
| 分支覆盖率 | 40% | 70% | 80%+ |
| 关键路径覆盖率 | 90% | 95% | 100% |
| 测试通过率 | 100% | 100% | 100% |

- 低于最低门禁 → 阻止合并
- 新代码覆盖率 < 80% → 建议补充测试

## 测试反模式
- ❌ 测试依赖执行顺序
- ❌ 测试中有 `time.sleep(x)`
- ❌ 只测 happy path
- ❌ Mock 万物 → 测试没测到真实行为
- ❌ 测试名称不描述场景 (如 `test1`, `test2`)

## 验证命令速查
```bash
# Python
python -m pytest -xvs --cov --cov-report=term
# Node
npx jest --coverage --verbose
# Go
go test -v -cover ./...
```
