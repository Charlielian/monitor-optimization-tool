# 🚀 启动检查清单

## 📋 部署前检查

### 1. 环境准备 ✅

```bash
# 检查 Python 版本（需要 3.8+）
python3 --version

# 安装依赖
pip install -r requirements.txt

# 验证安装
python3 -c "import flask; print(f'Flask {flask.__version__}')"
```

### 2. 配置检查 ✅

```bash
# 检查配置文件是否存在
ls -la config.json

# 查看认证配置
cat config.json | grep -A 20 "auth_config"

# 确认包含以下配置：
# - enable_auth: true
# - session_lifetime_hours: 24
# - users: admin 和 user
```

### 3. 测试认证系统 ✅

```bash
# 运行测试脚本
python3 test_auth.py

# 预期输出：所有测试通过 ✅
```

### 4. 安全配置 ⚠️

```bash
# 生成新的管理员密码
python3 generate_password_hash.py <新密码>

# 更新 config.json 中的 password_hash

# 生成新的 secret_key
python3 -c "import secrets; print(secrets.token_hex(32))"

# 更新 config.json 中的 secret_key
```

## 🚀 启动应用

### 开发环境

```bash
# 默认端口 5000
python app.py

# 或指定端口
python app.py --port 5010

# 启用调试模式（仅开发环境）
python app.py --debug
```

### 生产环境

```bash
# 使用 Gunicorn（推荐）
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:create_app()

# 或使用 uWSGI
pip install uwsgi
uwsgi --http :5000 --wsgi-file app.py --callable create_app()
```

## 🧪 功能测试

### 1. 访问测试

```bash
# 打开浏览器
http://localhost:5000/

# 应该自动跳转到登录页面
http://localhost:5000/login
```

### 2. 登录测试

**管理员账号：**
- 用户名：`admin`
- 密码：`admin123`（请立即修改！）

**普通用户账号：**
- 用户名：`user`
- 密码：`user123`（请立即修改！）

### 3. 功能验证

#### 普通用户
- [ ] 登录成功
- [ ] 访问全网监控 (`/`)
- [ ] 访问保障监控 (`/monitor`)
- [ ] 访问小区指标查询 (`/cell`)
- [ ] 访问场景管理 (`/scenarios`)
- [ ] 无法访问管理员控制台 (`/admin`)
- [ ] 登出成功

#### 管理员
- [ ] 登录成功
- [ ] 访问所有普通用户功能
- [ ] 访问管理员控制台 (`/admin`)
- [ ] 查看系统概览
- [ ] 查看用户列表
- [ ] 查看系统日志
- [ ] 查看数据库状态
- [ ] 登出成功

### 4. 无数据小区测试

- [ ] 在场景管理中添加不存在的 CGI
- [ ] 在保障监控中查看该场景
- [ ] 确认无数据小区显示（淡黄色背景 + 徽章）
- [ ] 导出 Excel，确认包含 "数据状态" 列

## 🔒 安全检查

### 必须完成（生产环境）

- [ ] 已修改默认管理员密码
- [ ] 已修改默认用户密码
- [ ] 已修改 secret_key
- [ ] 已配置 HTTPS
- [ ] 已配置防火墙
- [ ] 已限制访问 IP（可选）

### 建议完成

- [ ] 已配置日志轮转
- [ ] 已设置定期备份
- [ ] 已配置监控告警
- [ ] 已准备应急预案

## 📊 监控检查

### 应用监控

```bash
# 查看应用日志
tail -f logs/monitoring_app.log

# 查看错误日志
grep ERROR logs/monitoring_app.log

# 查看登录日志
grep "登录" logs/monitoring_app.log
```

### 数据库监控

```bash
# 检查 PostgreSQL 连接
# 访问 /health 端点
curl http://localhost:5000/health

# 预期输出：
# {
#   "status": "ok",
#   "pgsql": true,
#   "latest": {...}
# }
```

### 系统资源

```bash
# 查看进程
ps aux | grep python

# 查看端口占用
lsof -i :5000

# 查看内存使用
top -p $(pgrep -f "python app.py")
```

## 🐛 故障排查

### 问题 1：无法启动

**检查：**
```bash
# 端口是否被占用
lsof -i :5000

# 依赖是否安装
pip list | grep Flask

# 配置文件是否正确
python3 -c "import json; json.load(open('config.json'))"
```

### 问题 2：无法登录

**检查：**
```bash
# 查看日志
tail -20 logs/monitoring_app.log

# 测试认证系统
python3 test_auth.py

# 验证密码哈希
python3 -c "from werkzeug.security import check_password_hash; print(check_password_hash('scrypt:...', 'admin123'))"
```

### 问题 3：管理员控制台无法访问

**检查：**
```bash
# 确认用户角色
cat config.json | grep -A 5 "admin"

# 确认 role 为 "admin"
```

## 📞 获取帮助

### 文档

- [快速启动指南](QUICKSTART_AUTH.md)
- [完整认证系统指南](AUTH_SYSTEM_GUIDE.md)
- [部署总结](DEPLOYMENT_SUMMARY.md)
- [最终总结](FINAL_SUMMARY.md)

### 日志

```bash
# 应用日志
tail -f logs/monitoring_app.log

# 错误日志
grep ERROR logs/monitoring_app.log
```

### 测试

```bash
# 认证系统测试
python3 test_auth.py

# 密码哈希生成
python3 generate_password_hash.py <密码>
```

## ✅ 启动成功标志

当你看到以下内容时，说明启动成功：

```
 * Serving Flask app 'app'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment.
 * Running on http://0.0.0.0:5000
Press CTRL+C to quit
```

访问 `http://localhost:5000/` 应该：
1. 自动跳转到登录页面
2. 显示美观的登录界面
3. 可以使用默认账号登录
4. 登录后显示全网监控页面
5. 右上角显示用户信息

## 🎉 恭喜！

如果所有检查都通过，系统已成功启动！

现在你可以：
1. 使用默认账号登录
2. 探索各个功能模块
3. 访问管理员控制台（管理员账号）
4. 修改默认密码
5. 添加新用户
6. 开始使用系统

---

**检查清单版本**：v1.0  
**更新日期**：2025-12-29  
**状态**：✅ 就绪
