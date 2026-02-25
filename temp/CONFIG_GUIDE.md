# 配置文件说明

## 配置文件位置

配置文件查找优先级：
1. 环境变量 `MONITOR_CONFIG` 指定的路径
2. 当前项目目录下的 `config.json`
3. 上一级目录下的 `config.json`（兼容旧项目）

## 配置项说明

### 1. PostgreSQL 配置 (pgsql_config)

用于存储和查询指标数据。

```json
{
  "pgsql_config": {
    "host": "192.168.31.51",
    "port": 5432,
    "database": "postgres",
    "user": "postgres",
    "password": "103001",
    "pool_min": 1,
    "pool_max": 10,
    "connect_timeout": 10,
    "application_name": "monitoring_app"
  }
}
```

**必填项：**
- `host`: PostgreSQL 服务器地址
- `port`: PostgreSQL 端口（默认 5432）
- `database`: 数据库名称
- `user`: 数据库用户名
- `password`: 数据库密码

**可选项：**
- `pool_min`: 连接池最小连接数（默认 1）
- `pool_max`: 连接池最大连接数（默认 10）
- `connect_timeout`: 连接超时时间（秒，默认 10）
- `application_name`: 应用名称（默认 "monitoring_app"）

---

### 2. MySQL 配置 (mysql_config)

用于读取工参表，提供更精确的区域分类。

```json
{
  "mysql_config": {
    "host": "192.168.31.175",
    "port": 3306,
    "database": "optimization_toolbox",
    "user": "root",
    "password": "103001"
  }
}
```

**必填项：**
- `host`: MySQL 服务器地址
- `port`: MySQL 端口（默认 3306）
- `database`: 数据库名称
- `user`: 数据库用户名
- `password`: 数据库密码

**注意：**
- MySQL 配置是可选的
- 如果 MySQL 连接失败，系统会自动回退到基于小区名的分类
- 建议配置以提高区域分类准确性

---

### 3. 日志配置

```json
{
  "log_level": "INFO",
  "log_file": "logs/monitoring_app.log"
}
```

**可选项：**
- `log_level`: 日志级别，可选值：DEBUG, INFO, WARNING, ERROR, CRITICAL（默认 INFO）
- `log_file`: 日志文件路径（默认 "logs/monitoring_app.log"）

---

### 4. 应用安全配置

```json
{
  "secret_key": "your-secret-key-here"
}
```

**可选项：**
- `secret_key`: Flask 应用密钥，用于会话加密（默认 "dev-monitoring-app"）

**安全建议：**
- 生产环境必须修改默认密钥
- 使用随机生成的长字符串
- 不要在代码中硬编码

生成随机密钥：
```python
import secrets
print(secrets.token_hex(32))
```

---

### 5. UI 默认配置 (ui_config)

```json
{
  "ui_config": {
    "default_range": "6h",
    "default_networks": ["4G", "5G"],
    "auto_refresh_interval": 300,
    "max_cell_query": 200
  }
}
```

**可选项：**
- `default_range`: 默认时间范围，可选值：6h, 12h, 24h（默认 "6h"）
- `default_networks`: 默认网络类型（默认 ["4G", "5G"]）
- `auto_refresh_interval`: 自动刷新间隔（秒，默认 300）
- `max_cell_query`: 最大小区查询数量（默认 200）

---

### 6. Streamlit 配置 (streamlit_config)

如果使用 Streamlit 版本。

```json
{
  "streamlit_config": {
    "port": 8808,
    "server_address": "0.0.0.0"
  }
}
```

---

### 7. 数据传输配置 (transfer_config)

用于数据同步任务。

```json
{
  "transfer_config": {
    "enable_raw_to_metrics": true,
    "skip_if_pg_has_data": true,
    "check_data_hours": 1
  }
}
```

---

## 完整配置示例

参考 `config.example.json` 文件。

---

## 环境变量支持

可以通过环境变量覆盖配置：

### 指定配置文件路径
```bash
export MONITOR_CONFIG="/path/to/config.json"
```

### 指定 Flask 密钥
```bash
export FLASK_SECRET_KEY="your-secret-key"
```

### MySQL 配置（需要修改 config.py）
```bash
export MYSQL_HOST="192.168.31.175"
export MYSQL_PORT="3306"
export MYSQL_DATABASE="optimization_toolbox"
export MYSQL_USER="root"
export MYSQL_PASSWORD="103001"
```

---

## 配置验证

### 检查配置是否正确

```bash
python -c "from config import Config; cfg = Config(); print('配置加载成功')"
```

### 测试数据库连接

```bash
# 测试 PostgreSQL
python -c "from config import Config; from db.pg import PostgresClient; cfg = Config(); pg = PostgresClient(cfg.pgsql_config); print('PG 连接:', pg.test_connection())"

# 测试 MySQL
python test_mysql_connection.py
```

---

## 常见问题

### Q1: 配置文件找不到？

**A:** 检查：
1. 当前目录是否有 `config.json`
2. 上级目录是否有 `config.json`
3. 环境变量 `MONITOR_CONFIG` 是否设置

### Q2: 数据库连接失败？

**A:** 检查：
1. 数据库服务是否运行
2. 主机地址、端口是否正确
3. 用户名和密码是否正确
4. 防火墙是否允许连接
5. 数据库是否存在

### Q3: 如何使用不同环境的配置？

**A:** 创建多个配置文件：
- `config.dev.json` - 开发环境
- `config.prod.json` - 生产环境
- `config.test.json` - 测试环境

使用环境变量指定：
```bash
export MONITOR_CONFIG="config.prod.json"
python app.py
```

---

## 安全最佳实践

1. **不要提交包含密码的配置文件到版本控制**
   - 将 `config.json` 添加到 `.gitignore`
   - 提供 `config.example.json` 作为模板

2. **使用环境变量存储敏感信息**
   - 密码、密钥等敏感信息使用环境变量
   - 生产环境使用密钥管理服务

3. **限制数据库用户权限**
   - PostgreSQL: 只需 SELECT, INSERT, UPDATE 权限
   - MySQL: 只需 SELECT 权限（只读工参表）

4. **定期更新密码**
   - 定期更换数据库密码
   - 定期更换 Flask 密钥

5. **使用 SSL/TLS 连接**
   - 生产环境建议启用数据库 SSL 连接
   - 配置 SSL 证书路径
