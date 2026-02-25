# MySQL 工参表集成说明

## 功能概述

系统已集成 MySQL 工参表（`engineering_params`），用于更精确的小区区域分类。

## 配置说明

### 1. MySQL 配置

在 `config.json` 中添加 MySQL 配置：

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

**配置项说明：**
- `host`: MySQL 服务器地址
- `port`: MySQL 端口（默认 3306）
- `database`: 数据库名称
- `user`: 数据库用户名
- `password`: 数据库密码

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

新增依赖：
- `pymysql>=1.1.0` - MySQL 驱动
- `sqlalchemy>=2.0.0` - 数据库 ORM

## 区域分类逻辑

系统采用三级优先级进行区域分类：

### 优先级 1: 工参表 CGI 映射（最高优先级）

从 `engineering_params` 表中根据 CGI 查找对应的区域信息。

### 优先级 2: area_compy 字段分类

根据 `area_compy`（区域公司）字段进行分类：

| area_compy 包含 | 归类至 |
|----------------|--------|
| 阳西分公司 | 阳西县 |
| 阳春分公司 | 阳春市 |
| 阳东分公司 | 阳东县 |
| 南区分公司 | 南区 |
| 江城分公司 | 江城区 |

### 优先级 3: 小区名（celname）分类

根据小区名进行分类：

| 小区名包含 | 归类至 |
|-----------|--------|
| 阳江阳西 / yangjiangyangxi | 阳西县 |
| 阳江阳春 / yangjiangyangchun | 阳春市 |
| 阳江阳东 / yangjiangyangdong | 阳东县 |
| 阳江南区 / yangjiangnanqu | 南区 |
| 阳江江城 / yangjiangjiangcheng | 江城区 |

### 默认分类

如果以上三种方式都无法确定区域，则默认归类至 **江城区**。

## 工参表结构

系统从 `engineering_params` 表中读取以下字段：

- `cgi` - 小区 CGI（主键）
- `area_compy` - 区域公司
- `celname` - 小区名

## 测试

运行测试脚本验证 MySQL 连接和工参服务：

```bash
python test_mysql_connection.py
```

测试内容：
1. MySQL 连接测试
2. 工参表记录数查询
3. CGI 映射加载
4. 区域分类示例
5. 各区域统计

## 容错机制

- 如果 MySQL 连接失败，系统会自动回退到基于小区名的分类逻辑
- 不会影响主要功能的正常运行
- 错误信息会记录到日志中

## 性能优化

- 工参表数据在服务启动时一次性加载到内存缓存
- 区域查询使用字典查找，时间复杂度 O(1)
- 支持手动刷新缓存：`engineering_params_service.reload_mapping()`

## 影响范围

以下功能使用了新的区域分类逻辑：

1. **全网监控** - 各区域流量及话务量统计
2. **日级数据查询** - 按区域统计的 4G/5G 流量和话务量

## 数据流程

```
PostgreSQL (指标数据)
    ↓
获取 cellname 和 cgi
    ↓
MySQL (工参表)
    ↓
区域分类
    ↓
按区域聚合统计
```

## 注意事项

1. 确保 MySQL 数据库可访问
2. 工参表需要包含完整的 CGI、area_compy、celname 字段
3. 建议定期更新工参表数据以保持准确性
4. 如需更新区域映射，重启应用或调用 `reload_mapping()` 方法
