# 监控优化工具 (monitor_app2)

现代化的网络监控与优化系统，集成 PostgreSQL 和 MySQL 数据源，支持实时指标监控、场景管理、告警分析和性能优化。

## ✨ 最新更新 (v3.0 - 2026-02-19)

### 🔍 增强的监控功能
- ✅ 网格健康检查（Grid Health Check）
- ✅ 高铁保障监控（HSR Health Check）
- ✅ 告警匹配与分析系统
- ✅ 多维度指标趋势分析

### 🚀 性能优化
- ✅ 数据库索引优化
- ✅ 并行查询处理
- ✅ 缓存机制改进
- ✅ 前端加载速度优化

### 📁 新功能模块
- ✅ 自动指标提取工具（auto_get_zhibiao）
- ✅ API 接口服务（api_v1.py）
- ✅ 性能分析工具（analyze_performance.py）
- ✅ 优化建议应用（apply_optimizations.py）

### 🔧 系统改进
- ✅ 路由模块化（routes/ 目录）
- ✅ 服务层重构（services/ 目录）
- ✅ 工具集整合（tools/ 目录）
- ✅ 配置管理优化

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置数据库

复制并编辑配置文件：

```bash
cp config.example.json config.json
```

编辑 `config.json`，配置 PostgreSQL 和 MySQL 连接信息。

### 3. 启动应用

```bash
python app.py
```

或使用启动脚本：

```bash
chmod +x start_server.sh
./start_server.sh
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
python generate_password_hash.py <新密码>

# 更新 config.json 中的 password_hash
# 重启应用
```

## 📋 主要功能

### 核心监控功能
- **全网监控**：4G/5G 流量趋势、Top 小区、RRC 用户数、话务量
- **保障监控**：场景选择、阈值配置、实时指标、趋势图
- **小区指标查询**：CGI 查询、时间范围、多粒度（15分钟/1小时）
- **场景管理**：创建/删除场景、添加/删除小区、Excel 导入导出

### 高级功能
- **网格健康检查**：网格级指标监控与告警
- **高铁保障监控**：高铁线路专项保障监控
- **告警匹配分析**：告警与小区/网格关联分析
- **性能分析**：系统性能瓶颈识别与优化建议

### 认证与权限
- **用户登录**：Session 管理、密码加密、"记住我"
- **权限控制**：普通用户/管理员角色、路由级别保护
- **管理员控制台**：系统概览、用户管理、系统日志、数据库状态

### 数据管理
- **智能单位转换**：流量（GB/TB）、话务量（Erl/万Erl）
- **Excel 导出**：中文列名、样式美化、自动列宽
- **工参表集成**：MySQL 工参表、区域自动分类
- **无数据小区显示**：CGI 不存在的小区也会显示

### 工具集
- **自动指标提取**：批量提取干扰小区指标
- **性能分析**：系统性能评估与优化建议
- **告警诊断**：告警数据分析与根因定位
- **路由验证**：API 路由完整性检查

## 📁 目录结构

```
monitor_app2/
├── app.py                          # Flask 应用主文件
├── auth.py                         # 认证管理器
├── api_v1.py                       # API 接口服务
├── config.py                       # 配置加载器
├── config.json                     # 配置文件
├── config.example.json             # 配置文件示例
├── requirements.txt                # 依赖列表
├── analyze_performance.py          # 性能分析工具
├── apply_optimizations.py          # 优化建议应用
├── generate_password_hash.py       # 密码哈希生成
├── logging.yaml                    # 日志配置
│
├── services/                       # 业务逻辑层
│   ├── metrics_service.py          # 指标查询服务
│   ├── scenario_service.py         # 场景管理服务
│   ├── engineering_params_service.py # 工参表服务
│   ├── alarm_service.py            # 告警服务
│   ├── grid_service.py             # 网格服务
│   ├── hsr_health_check.py         # 高铁健康检查
│   ├── guarantee_health_check.py   # 保障健康检查
│   └── cache.py                    # 缓存服务
│
├── db/                             # 数据库层
│   ├── pg.py                       # PostgreSQL 客户端
│   └── mysql.py                    # MySQL 客户端
│
├── routes/                         # 路由模块
│   ├── __init__.py                 # 路由初始化
│   ├── main.py                     # 主路由
│   ├── admin.py                    # 管理员路由
│   ├── alarm.py                    # 告警路由
│   ├── grid.py                     # 网格路由
│   └── export.py                   # 导出路由
│
├── templates/                      # 前端模板
│   ├── base.html                   # 基础模板
│   ├── login.html                  # 登录页面
│   ├── admin.html                  # 管理员控制台
│   ├── dashboard.html              # 全网监控
│   ├── monitor.html                # 保障监控
│   ├── cell.html                   # 小区指标查询
│   ├── scenarios.html              # 场景管理
│   ├── grid_health_check.html      # 网格健康检查
│   ├── hsr_health_check.html       # 高铁健康检查
│   └── guarantee_health_check.html # 保障健康检查
│
├── static/                         # 静态资源
│   ├── css/                        # 样式文件
│   ├── js/                         # JavaScript 文件
│   └── fonts/                      # 字体文件
│
├── utils/                          # 工具函数
│   ├── formatters.py               # 格式化工具
│   ├── validators.py               # 验证工具
│   ├── time_parser.py              # 时间解析工具
│   ├── excel_helper.py             # Excel 处理工具
│   ├── pagination.py               # 分页工具
│   ├── parallel_query.py           # 并行查询工具
│   └── performance.py              # 性能分析工具
│
├── tools/                          # 工具集
│   ├── check/                      # 检查工具
│   ├── debug/                      # 调试工具
│   ├── diagnose/                   # 诊断工具
│   ├── fix/                        # 修复工具
│   └── verify/                     # 验证工具
│
├── auto_get_zhibiao/               # 自动指标提取
│   ├── standalone_interference_extractor.py # 独立干扰提取器
│   ├── gui_interference_extractor.py # GUI 干扰提取器
│   └── interference_data_output/   # 干扰数据输出
│
├── logs/                           # 日志目录
├── temp/                           # 临时文件目录
├── sql/                            # SQL 脚本目录
└── venv/                           # 虚拟环境
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
                "password_hash": "scrypt:32768:8:1$",
                "role": "admin",
                "name": "系统管理员"
            },
            "user": {
                "password_hash": "scrypt:32768:8:1$",
                "role": "user",
                "name": "普通用户"
            }
        }
    }
}
```

### 服务配置

```json
{
    "service_config": {
        "host": "0.0.0.0",
        "port": 5000,
        "debug": false,
        "threaded": true
    }
}
```

## 🚀 部署指南

### 1. 环境准备

- Python 3.8+
- PostgreSQL 10+
- MySQL 5.7+
- pip 包管理工具

### 2. 安装步骤

```bash
# 克隆仓库
git clone git@github.com:Charlielian/-.git
cd monitor_app2

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 配置数据库
cp config.example.json config.json
# 编辑 config.json 配置数据库连接

# 启动应用
python app.py
```

### 3. 生产环境部署

```bash
# 使用 Waitress 作为生产服务器
pip install waitress

# 启动生产服务器
waitress-serve --host=0.0.0.0 --port=5000 app:app

# 或使用启动脚本
chmod +x start_server.sh
./start_server.sh
```

## 🔒 安全建议

1. **修改默认密码**（必须！）
2. **修改 Secret Key**
3. **使用 HTTPS**（生产环境）
4. **配置防火墙**
5. **定期备份配置文件**
6. **监控登录日志**
7. **限制数据库用户权限**
8. **定期更新依赖包**

## 🧪 测试与诊断

### 运行测试

```bash
# 告警匹配测试
python test_alarm_matching.py

# 高铁告警匹配测试
python test_hsr_alarm_match.py

# 小区匹配测试
python test_site_matching.py
```

### 性能分析

```bash
# 分析系统性能
python analyze_performance.py

# 应用优化建议
python apply_optimizations.py
```

### 诊断工具

```bash
# 诊断告警数据
python tools/diagnose/diagnose_alarm_data.py

# 诊断网格名称
python tools/diagnose/diagnose_grid_names.py

# 诊断应用
python tools/diagnose/diagnose_app.py
```

## 📊 权限说明

### 普通用户
- ✅ 全网监控
- ✅ 保障监控
- ✅ 小区指标查询
- ✅ 场景管理
- ✅ 数据导出
- ✅ 网格健康检查
- ✅ 高铁保障监控

### 管理员
- ✅ 所有普通用户功能
- ✅ 管理员控制台
- ✅ 系统日志查看
- ✅ 用户管理
- ✅ 数据库状态监控
- ✅ 系统配置管理

## 🚧 开发计划

- [ ] Web 界面添加/编辑用户
- [ ] 用户最后登录时间记录
- [ ] 操作日志记录
- [ ] 密码强度检查
- [ ] 双因素认证（2FA）
- [ ] 多语言支持
- [ ] 移动端适配优化
- [ ] 实时数据推送（WebSocket）

## 📞 获取帮助

### 常见问题

**Q: 无法连接数据库怎么办？**
A: 检查 config.json 中的数据库配置，确保数据库服务运行正常，网络连接畅通。

**Q: 登录失败怎么办？**
A: 检查用户名密码是否正确，查看 logs/ 目录下的错误日志。

**Q: 指标数据为空怎么办？**
A: 检查数据库中是否有对应的数据表和数据，确认 CGI 格式是否正确。

### 日志查看

```bash
# 查看应用日志
cat logs/monitoring_app.log

# 查看服务日志
cat service.log
```

## 📝 更新日志

### v3.0 (2026-02-19)
- ✅ 新增网格健康检查功能
- ✅ 新增高铁保障监控功能
- ✅ 新增告警匹配分析系统
- ✅ 新增性能分析与优化工具
- ✅ 路由模块化重构
- ✅ 服务层架构优化
- ✅ 工具集整合

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

**版本**：v3.0  
**更新日期**：2026-02-19  
**状态**：✅ 生产就绪
**仓库地址**：https://github.com/Charlielian/-