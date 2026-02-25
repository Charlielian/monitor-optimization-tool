# MySQL 集成安装指南

## 快速开始

### 1. 安装依赖

```bash
# 激活虚拟环境（如果使用）
source venv/bin/activate

# 安装新依赖
pip install pymysql sqlalchemy
```

或者重新安装所有依赖：

```bash
pip install -r requirements.txt
```

### 2. 配置 MySQL

编辑 `config.json`，确保包含 MySQL 配置：

```json
{
  "pgsql_config": {
    "host": "192.168.31.51",
    "port": 5432,
    "database": "postgres",
    "user": "postgres",
    "password": "103001"
  },
  "mysql_config": {
    "host": "192.168.31.175",
    "port": 3306,
    "database": "optimization_toolbox",
    "user": "root",
    "password": "103001"
  }
}
```

**配置项说明：**
- `host`: MySQL 服务器地址
- `port`: MySQL 端口（默认 3306）
- `database`: 数据库名称
- `user`: 数据库用户名
- `password`: 数据库密码

### 3. 测试连接

```bash
python test_mysql_connection.py
```

**预期输出：**
```
============================================================
测试 MySQL 连接
============================================================
MySQL 配置:
  Host: 192.168.31.175
  Port: 3306
  Database: optimization_toolbox
  User: root
✓ MySQL 连接成功
✓ 工参表记录数: XXXX

============================================================
测试工参服务
============================================================
✓ 工参服务初始化成功，加载了 XXXX 条 CGI 映射

============================================================
测试区域分类
============================================================
CGI: 460000123456789... -> 区域: 阳西县
  area_compy: 阳西分公司
  celname: 阳江阳西某某小区

============================================================
各区域 CGI 数量统计
============================================================
江城区: XXX 个小区
南区: XXX 个小区
阳东县: XXX 个小区
阳春市: XXX 个小区
阳西县: XXX 个小区

✓ 测试完成
```

### 4. 启动应用

```bash
python app.py
```

应用会自动：
1. 连接 PostgreSQL（指标数据）
2. 连接 MySQL（工参表）
3. 加载 CGI 区域映射到内存
4. 启动 Flask 服务

## 故障排查

### 问题 1: MySQL 连接失败

**错误信息：**
```
MySQL 连接失败: (2003, "Can't connect to MySQL server...")
```

**解决方案：**
1. 检查 MySQL 服务是否运行
2. 检查主机地址、端口是否正确
3. 检查用户名和密码
4. 检查防火墙设置
5. 确认数据库名称正确

### 问题 2: 工参表不存在

**错误信息：**
```
MySQL 查询失败: (1146, "Table 'optimization_toolbox.engineering_params' doesn't exist")
```

**解决方案：**
1. 确认数据库中存在 `engineering_params` 表
2. 检查表名拼写是否正确
3. 确认用户有访问该表的权限

### 问题 3: pymysql 未安装

**错误信息：**
```
ModuleNotFoundError: No module named 'pymysql'
```

**解决方案：**
```bash
pip install pymysql sqlalchemy
```

### 问题 4: 工参服务初始化失败但应用仍能运行

这是正常的容错机制。应用会：
1. 记录警告日志
2. 回退到基于小区名的分类逻辑
3. 继续正常运行

**日志示例：**
```
WARNING - 工参服务初始化失败，将使用默认区域分类: ...
```

## 验证功能

### 1. 访问全网监控页面

```
http://localhost:5000/
```

### 2. 查看各区域统计

在"4G/5G总流量及话务量"卡片中，查看"各区域流量及话务量统计"部分。

### 3. 检查日志

```bash
tail -f logs/monitoring_app.log
```

查找以下日志：
- `工参服务初始化成功`
- `工参表区域映射加载完成，共 XXX 条记录`

## 性能说明

- **启动时间**：首次加载工参表需要 1-3 秒（取决于记录数）
- **内存占用**：每 10000 条 CGI 映射约占用 1-2 MB 内存
- **查询性能**：区域查询为 O(1) 时间复杂度，无性能影响

## 数据更新

如果工参表数据更新，有两种方式刷新：

### 方式 1: 重启应用（推荐）

```bash
# 停止应用
Ctrl+C

# 重新启动
python app.py
```

### 方式 2: 调用刷新接口（需要自行实现）

可以在 `app.py` 中添加管理接口：

```python
@app.route("/admin/reload_engineering_params")
def reload_engineering_params():
    if engineering_params_service:
        engineering_params_service.reload_mapping()
        return {"status": "success", "message": "工参表映射已刷新"}
    return {"status": "error", "message": "工参服务未启用"}
```

## 配置优化

### 连接池配置

如需调整 MySQL 连接池大小，修改 `db/mysql.py`：

```python
self.engine = create_engine(
    self.url,
    poolclass=QueuePool,
    pool_size=5,        # 连接池大小
    max_overflow=10,    # 最大溢出连接数
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False
)
```

### 日志级别

在 `config.json` 中调整日志级别：

```json
{
  "log_level": "DEBUG"
}
```

## 安全建议

1. **不要在代码中硬编码密码**
2. **使用环境变量存储敏感信息**
3. **限制数据库用户权限**（只需 SELECT 权限）
4. **定期更新依赖包**

示例：使用环境变量

```bash
export MYSQL_HOST="192.168.31.175"
export MYSQL_PORT="3306"
export MYSQL_DATABASE="optimization_toolbox"
export MYSQL_USER="root"
export MYSQL_PASSWORD="103001"
```

修改 `config.py`：

```python
import os

mysql_config = {
    "host": os.environ.get("MYSQL_HOST") or data.get("mysql_config", {}).get("host"),
    "port": int(os.environ.get("MYSQL_PORT", 3306)),
    "database": os.environ.get("MYSQL_DATABASE") or data.get("mysql_config", {}).get("database"),
    "user": os.environ.get("MYSQL_USER") or data.get("mysql_config", {}).get("user"),
    "password": os.environ.get("MYSQL_PASSWORD") or data.get("mysql_config", {}).get("password"),
}
self.mysql_config = mysql_config
```
