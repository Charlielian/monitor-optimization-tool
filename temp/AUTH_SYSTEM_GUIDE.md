# 认证系统使用指南

## 概述

保障指标监控系统现已集成 **Session 登录认证系统**，提供用户登录、权限管理和管理员控制台功能。

## 功能特性

### 1. 用户认证
- ✅ 登录/登出功能
- ✅ Session 管理
- ✅ "记住我" 功能
- ✅ 密码加密存储（scrypt 算法）
- ✅ 登录失败提示

### 2. 权限管理
- ✅ 普通用户：访问所有监控功能
- ✅ 管理员：额外访问管理员控制台
- ✅ 路由级别的权限控制

### 3. 管理员控制台
- ✅ 系统概览（场景数、小区数、用户数）
- ✅ 用户管理（查看用户列表）
- ✅ 系统日志（最近50条）
- ✅ 数据库状态监控

## 默认账号

系统预置了两个默认账号：

| 用户名 | 密码 | 角色 | 权限 |
|--------|------|------|------|
| admin  | admin123 | 管理员 | 全部功能 + 管理员控制台 |
| user   | user123  | 普通用户 | 全部监控功能 |

⚠️ **安全提示**：首次部署后请立即修改默认密码！

## 使用方法

### 登录系统

1. 访问系统首页：`http://localhost:5000/`
2. 自动跳转到登录页面
3. 输入用户名和密码
4. 点击"登录"按钮

### 访问管理员控制台

1. 使用管理员账号登录（admin / admin123）
2. 点击导航栏右上角的用户名下拉菜单
3. 选择"管理员控制台"
4. 或直接访问：`http://localhost:5000/admin`

### 登出系统

1. 点击导航栏右上角的用户名
2. 选择"退出登录"

## 配置说明

### 启用/禁用认证

编辑 `config.json`：

```json
{
    "auth_config": {
        "enable_auth": true,  // true=启用认证，false=禁用认证
        "session_lifetime_hours": 24,  // Session 有效期（小时）
        "users": {
            // 用户配置
        }
    }
}
```

### 添加新用户

#### 方法 1：使用密码哈希生成工具

1. 生成密码哈希：
```bash
python3 generate_password_hash.py <密码>
```

2. 复制生成的哈希值

3. 编辑 `config.json`，添加用户：
```json
{
    "auth_config": {
        "users": {
            "newuser": {
                "password_hash": "scrypt:32768:8:1$...",
                "role": "user",  // "user" 或 "admin"
                "name": "新用户"
            }
        }
    }
}
```

4. 重启应用

#### 方法 2：通过管理员控制台（开发中）

未来版本将支持通过 Web 界面添加用户。

### 修改密码

1. 生成新密码的哈希值：
```bash
python3 generate_password_hash.py <新密码>
```

2. 更新 `config.json` 中对应用户的 `password_hash`

3. 重启应用

### 删除用户

1. 编辑 `config.json`
2. 删除对应的用户配置
3. 重启应用

## 安全建议

### 1. 修改默认密码

⚠️ **重要**：首次部署后立即修改默认密码！

```bash
# 生成新密码哈希
python3 generate_password_hash.py <新密码>

# 更新 config.json
# 重启应用
```

### 2. 使用强密码

- 至少 8 个字符
- 包含大小写字母、数字和特殊字符
- 不使用常见密码

### 3. 定期更换密码

建议每 3-6 个月更换一次密码。

### 4. 限制管理员账号

- 只给必要的人员分配管理员权限
- 定期审查管理员账号

### 5. 启用 HTTPS

生产环境建议使用 HTTPS：

```bash
# 使用 Nginx 反向代理
# 配置 SSL 证书
```

### 6. 配置 Session 安全

编辑 `config.json`：

```json
{
    "secret_key": "your-random-secret-key-here",  // 使用随机字符串
    "auth_config": {
        "session_lifetime_hours": 8  // 缩短 Session 有效期
    }
}
```

生成随机密钥：

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

## 权限说明

### 普通用户权限

- ✅ 全网监控
- ✅ 保障监控
- ✅ 小区指标查询
- ✅ 场景管理
- ✅ 数据导出
- ❌ 管理员控制台

### 管理员权限

- ✅ 所有普通用户权限
- ✅ 管理员控制台
- ✅ 查看系统日志
- ✅ 查看用户列表
- ✅ 查看数据库状态
- 🚧 添加/删除用户（开发中）

## 故障排查

### 问题 1：无法登录

**症状**：输入正确的用户名和密码，仍然提示错误

**解决方法**：
1. 检查 `config.json` 中的密码哈希是否正确
2. 确认用户名拼写正确（区分大小写）
3. 查看日志文件：`logs/monitoring_app.log`

### 问题 2：Session 过期太快

**症状**：频繁需要重新登录

**解决方法**：
1. 编辑 `config.json`
2. 增加 `session_lifetime_hours` 的值
3. 重启应用

### 问题 3：管理员控制台无法访问

**症状**：点击"管理员控制台"后显示权限不足

**解决方法**：
1. 确认当前用户的 `role` 为 `"admin"`
2. 检查 `config.json` 配置
3. 重新登录

### 问题 4：忘记密码

**解决方法**：
1. 编辑 `config.json`
2. 生成新密码哈希并替换
3. 重启应用

## API 端点

### 公开端点

- `GET /login` - 登录页面
- `POST /login` - 登录处理

### 需要认证的端点

- `GET /` - 全网监控
- `GET /cell` - 小区指标查询
- `GET /monitor` - 保障监控
- `GET /scenarios` - 场景管理
- `GET /logout` - 登出

### 管理员端点

- `GET /admin` - 管理员控制台
- `POST /admin/add_user` - 添加用户（开发中）
- `POST /admin/delete_user` - 删除用户（开发中）

## 开发计划

### 即将推出

- [ ] Web 界面添加/编辑/删除用户
- [ ] 用户最后登录时间记录
- [ ] 操作日志（谁在什么时间做了什么）
- [ ] 密码强度检查
- [ ] 密码重置功能
- [ ] 双因素认证（2FA）

### 未来计划

- [ ] LDAP/AD 集成
- [ ] OAuth2 支持
- [ ] API Token 认证
- [ ] IP 白名单
- [ ] 登录失败锁定

## 相关文件

- `auth.py` - 认证管理器和装饰器
- `config.json` - 用户配置
- `config.py` - 配置加载器
- `app.py` - 路由和认证集成
- `templates/login.html` - 登录页面
- `templates/admin.html` - 管理员控制台
- `templates/base.html` - 导航栏（含用户菜单）
- `generate_password_hash.py` - 密码哈希生成工具

## 技术细节

### 密码加密

- 算法：scrypt（Werkzeug 默认）
- 参数：N=32768, r=8, p=1
- 盐值：自动生成（随机）

### Session 管理

- 存储：Flask Session（服务器端）
- 加密：使用 `secret_key` 签名
- 有效期：可配置（默认 24 小时）

### 权限控制

- 装饰器：`@login_required`、`@admin_required`
- 检查：基于 Session 中的 `role` 字段
- 重定向：未登录用户跳转到登录页

## 常见问题

**Q: 如何禁用认证系统？**

A: 编辑 `config.json`，设置 `"enable_auth": false`，重启应用。

**Q: 可以使用数据库存储用户吗？**

A: 当前版本使用配置文件。未来版本将支持数据库存储。

**Q: 支持 LDAP 认证吗？**

A: 当前版本不支持。已列入未来计划。

**Q: 如何查看登录日志？**

A: 查看 `logs/monitoring_app.log` 文件。

**Q: Session 存储在哪里？**

A: 存储在服务器内存中（Flask Session）。重启应用后 Session 失效。

## 联系支持

如有问题或建议，请联系系统管理员。

---

**文档版本**：v1.0  
**更新日期**：2025-12-29  
**适用版本**：v2.4+
