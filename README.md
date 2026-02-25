# 保障指标监控系统（Flask 版）

重构版前端，直接从 PostgreSQL 读取 `cell_4g_metrics` / `cell_5g_metrics`，集成 MySQL 工参表，支持用户认证和权限管理。

## ✨ 最新更新 (v2.4 - 2025-12-29)

### 🔐 Session 登录认证系统
- ✅ 用户登录/登出功能
- ✅ 密码加密存储（scrypt）
- ✅ 权限管理（普通用户/管理员）
- ✅ 管理员专属控制台
- ✅ Session 管理和"记住我"功能

### 📊 无数据小区显示
- ✅ 显示 CGI 不存在的小区（指标为空）
- ✅ 视觉标识（淡黄色背景 + 徽章）
- ✅ Excel 导出包含数据状态

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置数据库

编辑 `config.json`，配置 PostgreSQL 和 MySQL 连接信息。

### 3. 启动应用

```bash
python app.py
```

### 4. 访问系统

打开浏览器访问：`http://localhost:5000/`

### 5. 登录

使用默认账号登录：

| 用户名 | 密码 | 角色 |
|--------|------|------|
| admin  | admin123 | 管理员 |
| user   | user123  | 普通用户 |

⚠️ **重要**：首次部署后请立即修改默认密码！

```bash
# 生成新密码哈希
python3 generate_password_hash.py <新密码>

# 更新 config.json 中的 password_hash
# 重启应用
```

## 📋 主要功能

### 监控功能
- **全网监控**：4G/5G 流量趋势、Top 小区、RRC 用户数、话务量
- **保障监控**：场景选择、阈值配置、实时指标、趋势图
- **小区指标查询**：CGI 查询、时间范围、多粒度（15分钟/1小时）
- **场景管理**：创建/删除场景、添加/删除小区、Excel 导入导出

### 认证功能
- **用户登录**：Session 管理、密码加密、"记住我"
- **权限控制**：普通用户/管理员角色、路由级别保护
- **管理员控制台**：系统概览、用户管理、系统日志、数据库状态

### 数据功能
- **智能单位转换**：流量（GB/TB）、话务量（Erl/万Erl）
- **Excel 导出**：中文列名、样式美化、自动列宽
- **工参表集成**：MySQL 工参表、区域自动分类
- **无数据小区显示**：CGI 不存在的小区也会显示

## 📁 目录结构

```
保障指标监控系统/
├── app.py                          # Flask 应用主文件
├── auth.py                         # 认证管理器
├── config.py                       # 配置加载器
├── config.json                     # 配置文件
├── requirements.txt                # 依赖列表
│
├── services/                       # 业务逻辑层
│   ├── metrics_service.py          # 指标查询服务
│   ├── scenario_service.py         # 场景管理服务
│   ├── engineering_params_service.py # 工参表服务
│   └── cache.py                    # 缓存服务
│
├── db/                             # 数据库层
│   ├── pg.py                       # PostgreSQL 客户端
│   └── mysql.py                    # MySQL 客户端
│
├── templates/                      # 前端模板
│   ├── base.html                   # 基础模板
│   ├── login.html                  # 登录页面
│   ├── admin.html                  # 管理员控制台
│   ├── dashboard.html              # 全网监控
│   ├── monitor.html                # 保障监控
│   ├── cell.html                   # 小区指标查询
│   └── scenarios.html              # 场景管理
│
├── static/                         # 静态资源
│   ├── css/                        # 样式文件
│   └── js/                         # JavaScript 文件
│
├── utils/                          # 工具函数
│   ├── formatters.py               # 格式化工具
│   ├── validators.py               # 验证工具
│   └── time_parser.py              # 时间解析工具
│
├── logs/                           # 日志目录
│   └── monitoring_app.log          # 应用日志
│
└── 文档/
    ├── README.md                   # 本文档
    ├── AUTH_SYSTEM_GUIDE.md        # 认证系统指南
    ├── QUICKSTART_AUTH.md          # 快速启动指南
    ├── DEPLOYMENT_SUMMARY.md       # 部署总结
    ├── START_CHECKLIST.md          # 启动检查清单
    └── FINAL_SUMMARY.md            # 完整总结
```

## 🔧 配置说明

### 数据库配置

```json
{
    "pgsql_config": {
        "host": "localhost",
        "port": 5432,
        "database": "postgres",
        "user": "postgres",
        "password": "your_password"
    },
    "mysql_config": {
        "host": "localhost",
        "port": 3306,
        "database": "optimization_toolbox",
        "user": "root",
        "password": "your_password"
    }
}
```

### 认证配置

```json
{
    "auth_config": {
        "enable_auth": true,
        "session_lifetime_hours": 24,
        "users": {
            "admin": {
                "password_hash": "scrypt:32768:8:1$...",
                "role": "admin",
                "name": "系统管理员"
            }
        }
    }
}
```

## 📚 文档

- [认证系统完整指南](AUTH_SYSTEM_GUIDE.md) - 详细使用说明
- [快速启动指南](QUICKSTART_AUTH.md) - 5分钟快速开始
- [部署总结](DEPLOYMENT_SUMMARY.md) - 完整部署指南
- [启动检查清单](START_CHECKLIST.md) - 部署前检查
- [最终总结](FINAL_SUMMARY.md) - 项目完成总结

## 🔒 安全建议

1. **修改默认密码**（必须！）
2. **修改 Secret Key**
3. **使用 HTTPS**（生产环境）
4. **配置防火墙**
5. **定期备份配置文件**
6. **监控登录日志**

## 🧪 测试

```bash
# 测试认证系统
python3 test_auth.py

# 生成密码哈希
python3 generate_password_hash.py <密码>
```

## 📊 权限说明

### 普通用户
- ✅ 全网监控
- ✅ 保障监控
- ✅ 小区指标查询
- ✅ 场景管理
- ✅ 数据导出

### 管理员
- ✅ 所有普通用户功能
- ✅ 管理员控制台
- ✅ 系统日志查看
- ✅ 用户管理
- ✅ 数据库状态监控

## 🚧 开发计划

- [ ] Web 界面添加/编辑用户
- [ ] 用户最后登录时间
- [ ] 操作日志记录
- [ ] 密码强度检查
- [ ] 双因素认证（2FA）

## 📞 获取帮助

- 查看文档：[AUTH_SYSTEM_GUIDE.md](AUTH_SYSTEM_GUIDE.md)
- 查看日志：`logs/monitoring_app.log`
- 运行测试：`python3 test_auth.py`

## 📝 更新日志

### v2.4 (2025-12-29)
- ✅ 新增 Session 登录认证系统
- ✅ 新增管理员控制台
- ✅ 新增无数据小区显示功能

### v2.3 (2025-12-29)
- ✅ 无数据小区显示功能

### v2.2 (2025-12-29)
- ✅ 统一 CGI 匹配策略

### v2.1 (2025-12-29)
- ✅ 小区指标查询增强（RRC用户数、话务量）

### v2.0 (2025-12-29)
- ✅ MySQL 工参表集成

---

**版本**：v2.4  
**更新日期**：2025-12-29  
**状态**：✅ 生产就绪

