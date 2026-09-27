# API Design / API 设计

> Source: agent-skills-hub api-design-principles + api-patterns

## 触发路由
关键词: API、接口、REST、GraphQL、swagger、endpoint、路由、OpenAPI、接口文档

## SOP: API 设计流程

### Phase 1: 需求分析
1. 明确资源/实体类型
2. 确定 CRUD 操作集合
3. 识别关系: 一对一/一对多/多对多
4. 确定认证方式: JWT/OAuth2/API Key

### Phase 2: 设计 (以 RESTful 为例)

**URL 设计原则**:
```
✅ GET    /api/v1/users           # 列表 (分页+筛选)
✅ GET    /api/v1/users/{id}      # 详情
✅ POST   /api/v1/users           # 创建
✅ PUT    /api/v1/users/{id}      # 全量更新
✅ PATCH  /api/v1/users/{id}      # 部分更新
✅ DELETE /api/v1/users/{id}      # 删除
✅ GET    /api/v1/users/{id}/orders  # 子资源

❌ GET  /api/v1/getUsers          # 动词命名
❌ POST /api/v1/user/create       # URL 含动词
❌ GET  /api/v1/deleteUser?id=1   # GET 做写操作
```

**请求/响应规范**:
```yaml
请求:
  - 参数校验 (类型/范围/必填)
  - 分页: ?page=1&limit=20 (默认 limit=20, max=100)
  - 排序: ?sort=-created_at (前缀 - 降序)
  - 筛选: ?status=active&role=admin

响应:
  - 统一信封: { "code": 0, "data": {...}, "message": "ok" }
  - 分页: { "items": [...], "total": 100, "page": 1, "limit": 20 }
  - 错误: { "code": 40001, "message": "参数无效", "details": [...] }
```

### Phase 3: 文档与测试
1. **OpenAPI 3.0 / Swagger**: 自动从代码注解生成
2. **自动测试生成**: 从 OpenAPI spec 生成 pytest/jest 测试
3. **Mock Server**: 前端可独立开发

```yaml
# OpenAPI 片段
paths:
  /api/v1/users:
    get:
      summary: 获取用户列表
      parameters:
        - name: page
          in: query
          schema: { type: integer, default: 1 }
      responses:
        '200':
          description: 成功
```

### Phase 4: 版本策略
- URL 版本: `/api/v1/`, `/api/v2/` (推荐)
- Header 版本: `Accept: application/vnd.api+v2+json`
- 废弃通知: SunSet header `Sunset: Sat, 31 Dec 2026 23:59:59 GMT`

## API 设计反模式
- ❌ 用 GET 做写操作
- ❌ 返回整个数据库表 (无限分页前先查 count)
- ❌ 错误码返回 200 + body error
- ❌ 把所有字段放在一个端点 (God API)
- ❌ 无 rate limiting
- ❌ 无请求 body 大小限制

## HTTP 状态码速查
| 场景 | 状态码 |
|------|--------|
| 创建成功 | 201 Created |
| 请求成功 (无 body) | 204 No Content |
| 参数错误 | 400 Bad Request |
| 未认证 | 401 Unauthorized |
| 无权限 | 403 Forbidden |
| 不存在 | 404 Not Found |
| 冲突 (重复) | 409 Conflict |
| 参数校验失败 | 422 Unprocessable Entity |
| 频率限制 | 429 Too Many Requests |
| 服务端错误 | 500 Internal Server Error |
