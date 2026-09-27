# 代码审计清单

- [ ] 所有外部输入入口列表
- [ ] 鉴权/鉴权中间件覆盖
- [ ] 多租户 ID 是否绑定会话
- [ ] 反序列化 / pickle / YAML load
- [ ] SSRF 出网与协议限制
- [ ] 密钥与 token 存储
- [ ] 文件上传路径与类型
- [ ] 危险 exec/system/Runtime/eval
- [ ] SQL 注入 (参数化查询覆盖率)
- [ ] XSS / 模板注入
- [ ] CORS 配置
- [ ] CSRF Token
- [ ] 敏感信息泄露 (日志、错误页面)
- [ ] 依赖项已知 CVE
