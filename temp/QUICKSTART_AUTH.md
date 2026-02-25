# 认证系统快速启动指南

## 🚀 5分钟快速开始

### 1. 启动应用

```bash
python app.py
```

### 2. 访问系统

打开浏览器访问：`http://localhost:5000/`

### 3. 登录

使用默认账号登录：

**管理员账号：**
- 用户名：`admin`
- 密码：`admin123`

**普通用户账号：**
- 用户名：`user`
- 密码：`user123`

### 4. 访问管理员控制台

使用管理员账号登录后：
1. 点击右上角用户名下拉菜单
2. 选择"管理员控制台"
3. 或直接访问：`http://localhost:5000/admin`

## 📋 功能清单

### ✅ 已实现

- [x] 登录/登出功能
- [x] Session 管理
- [x] 密码加密存储
- [x] 权限控制（普通用户/管理员）
- [x] 管理员控制台
- [x] 系统概览
- [x] 用户列表查看
- [x] 系统日志查看
- [x] 数据库状态监控
- [x] 导航栏用户菜单
- [x] 路由级别权限保护

### 🚧 开发中

- [ ] Web 界面添加/编辑用户
- [ ] 用户最后登录时间
- [ ] 操作日志记录

## 🔐 安全提示

⚠️ **重要**：首次部署后请立即修改默认密码！

```bash
# 1. 生成新密码哈希
python3 generate_password_hash.py <新密码>

# 2. 更新 config.json 中的 password_hash

# 3. 重启应用
```

## 📝 修改密码

### 方法 1：使用工具生成

```bash
# 生成密码哈希
python3 generate_password_hash.py mynewpassword

# 输出示例：
# 密码: mynewpassword
# 哈希: scrypt:32768:8:1$...
```

### 方法 2：直接编辑配置

编辑 `config.json`：

```json
{
    "auth_config": {
        "users": {
            "admin": {
                "password_hash": "scrypt:32768:8:1$...",  // 替换为新哈希
                "role": "admin",
                "name": "系统管理员"
            }
        }
    }
}
```

重启应用后生效。

## 👥 添加新用户

### 步骤 1：生成密码哈希

```bash
python3 generate_password_hash.py userpassword
```

### 步骤 2：编辑配置文件

编辑 `config.json`，在 `auth_config.users` 中添加：

```json
{
    "auth_config": {
        "users": {
            "newuser": {
                "password_hash": "scrypt:32768:8:1$...",
                "role": "user",  // "user" 或 "admin"
                "name": "新用户名"
            }
        }
    }
}
```

### 步骤 3：重启应用

```bash
# 停止应用（Ctrl+C）
# 重新启动
python app.py
```

## 🔧 配置选项

### 启用/禁用认证

编辑 `config.json`：

```json
{
    "auth_config": {
        "enable_auth": true,  // false=禁用认证
        "session_lifetime_hours": 24  // Session 有效期
    }
}
```

### 修改 Session 有效期

```json
{
    "auth_config": {
        "session_lifetime_hours": 8  // 8小时后自动登出
    }
}
```

### 修改 Secret Key

```bash
# 生成随机密钥
python3 -c "import secrets; print(secrets.token_hex(32))"
```

编辑 `config.json`：

```json
{
    "secret_key": "your-random-secret-key-here"
}
```

## 🎯 权限说明

### 普通用户（role: "user"）

可以访问：
- ✅ 全网监控
- ✅ 保障监控
- ✅ 小区指标查询
- ✅ 场景管理
- ✅ 数据导出

不能访问：
- ❌ 管理员控制台

### 管理员（role: "admin"）

可以访问：
- ✅ 所有普通用户功能
- ✅ 管理员控制台
- ✅ 系统日志
- ✅ 用户管理
- ✅ 数据库状态

## 🐛 故障排查

### 问题：无法登录

**检查清单：**
1. 用户名是否正确（区分大小写）
2. 密码是否正确
3. `config.json` 中的密码哈希是否正确
4. 查看日志：`logs/monitoring_app.log`

### 问题：管理员控制台无法访问

**检查清单：**
1. 确认用户 `role` 为 `"admin"`
2. 重新登录
3. 检查浏览器控制台错误

### 问题：Session 过期太快

**解决方法：**
增加 `session_lifetime_hours` 的值。

## 📚 相关文档

- [完整认证系统指南](AUTH_SYSTEM_GUIDE.md)
- [配置文件说明](CONFIG_GUIDE.md)
- [项目说明](README.md)

## 🧪 测试认证系统

运行测试脚本：

```bash
python3 test_auth.py
```

预期输出：
```
============================================================
认证系统测试
============================================================

测试 1：正确的用户名和密码
  admin / admin123: ✅ 通过
  user / user123: ✅ 通过

...

所有测试完成！
============================================================
```

## 📞 获取帮助

如有问题，请查看：
1. [完整文档](AUTH_SYSTEM_GUIDE.md)
2. 日志文件：`logs/monitoring_app.log`
3. 联系系统管理员

---

**快速启动指南版本**：v1.0  
**更新日期**：2025-12-29
