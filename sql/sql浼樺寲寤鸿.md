# SQL 查询优化建议

## 📊 当前性能状况

根据最新性能分析报告（2025-12-31），系统存在以下性能问题：

### 后端查询性能
- **优化前**: Dashboard查询耗时 5.8秒
- **优化后**: Dashboard查询耗时 2.9-3.4秒
- **改善幅度**: 48-50% ✅
- **目标**: 进一步优化到 1.5秒以下

### 主要性能瓶颈
1. **时间范围查询慢** - 大量数据扫描
2. **聚合查询慢** - SUM/AVG 计算耗时
3. **多表查询** - 4G/5G表分别查询后合并
4. **缺少部分索引** - cellname、cell_id 等字段无索引

---

## 🎯 优化策略

### 1. 索引优化（立即执行）

#### 执行索引优化脚本

```bash
# 连接数据库并执行索引优化
psql -h 188.15.68.62 -p 54326 -U your_user -d data_wg -f sql/optimize_indexes.sql
```

#### 已创建的索引

**4G指标表 (cell_4g_metrics)**:
- `idx_metrics_4g_time` - 时间降序索引
- `idx_metrics_4g_cgi` - CGI索引
- `idx_metrics_4g_time_cgi` - 时间+CGI复合索引
- `idx_metrics_4g_cell_id` - 小区ID索引（新增）
- `idx_metrics_4g_cellname` - 小区名索引（新增）
- `idx_metrics_4g_prb_util` - 利用率索引（新增）

**5G指标表 (cell_5g_metrics)**:
- `idx_metrics_5g_time` - 时间降序索引
- `idx_metrics_5g_cgi` - CGI索引
- `idx_metrics_5g_time_cgi` - 时间+CGI复合索引
- `idx_metrics_5g_userlabel` - 小区标签索引（新增）

**小时粒度表**:
- 4G/5G小时表的时间、CGI、复合索引

**天粒度表**:
- 4G/5G天表的时间、CGI、cellname/userlabel索引

#### 预期效果
- 时间范围查询提速 **50-70%**
- CGI查询提速 **60-80%**
- 小区查询提速 **70-90%**

---

### 2. 查询优化建议

#### 2.1 流量时间序列查询优化

**当前查询** (`traffic_series` 方法):
```sql
SELECT
    start_time,
    '4G' AS network_type,
    SUM(COALESCE("PDCP_UpOctUl", 0) + COALESCE("PDCP_UpOctDl", 0)) / 1000.0 / 1000.0 AS total_traffic
FROM cell_4g_metrics
WHERE start_time BETWEEN %s AND %s
GROUP BY start_time
ORDER BY start_time
```

**优化建议**:

1. **使用小时粒度表减少数据量**
```sql
-- 当查询时间范围 > 6小时时，使用小时表
SELECT
    start_time,
    '4G' AS network_type,
    SUM(COALESCE("PDCP_UpOctUl", 0) + COALESCE("PDCP_UpOctDl", 0)) / 1000.0 / 1000.0 AS total_traffic
FROM cell_4g_metrics_hour  -- 使用小时表
WHERE start_time BETWEEN %s AND %s
GROUP BY start_time
ORDER BY start_time
```

2. **添加数据降采样**（已在代码中实现）
```python
# 在 MetricsService 中已添加
result = self.traffic_series(networks, start, end, granularity)
if len(result) > 100:
    result = self.downsample_data(result, 100)
```

**预期效果**: 查询时间减少 **40-60%**

---

#### 2.2 Top小区查询优化

**当前查询** (`top_cells` 方法):
```sql
SELECT
    cell_id, cellname, cgi,
    (COALESCE("PDCP_UpOctUl",0) + COALESCE("PDCP_UpOctDl",0)) / 1000.0 / 1000.0 AS total_traffic,
    CASE
        WHEN ul_prb_utilization > dl_prb_utilization THEN ul_prb_utilization
        ELSE dl_prb_utilization
    END AS max_prb_util
FROM cell_4g_metrics
WHERE start_time = %s
ORDER BY max_prb_util DESC
LIMIT 20
```

**优化建议**:

1. **使用 GREATEST 函数替代 CASE**
```sql
SELECT
    cell_id, cellname, cgi,
    (COALESCE("PDCP_UpOctUl",0) + COALESCE("PDCP_UpOctDl",0)) / 1000.0 / 1000.0 AS total_traffic,
    GREATEST(COALESCE(ul_prb_utilization,0), COALESCE(dl_prb_utilization,0)) AS max_prb_util
FROM cell_4g_metrics
WHERE start_time = %s
ORDER BY max_prb_util DESC
LIMIT 20
```

2. **添加部分索引**（已在 optimize_indexes.sql 中创建）
```sql
CREATE INDEX idx_metrics_4g_prb_util 
ON cell_4g_metrics(
    GREATEST(COALESCE(ul_prb_utilization,0), COALESCE(dl_prb_utilization,0)) DESC
) 
WHERE start_time >= NOW() - INTERVAL '7 days';
```

**预期效果**: 查询时间减少 **30-50%**

---

#### 2.3 小区时间序列查询优化

**当前查询** (`cell_timeseries` 方法):
```sql
SELECT start_time, cell_id, cgi, cellname, ...
FROM cell_4g_metrics
WHERE (cell_id = %s OR cgi = %s) AND start_time BETWEEN %s AND %s
ORDER BY start_time
```

**优化建议**:

1. **分离 cell_id 和 cgi 查询**
```sql
-- 优先使用 cgi 查询（有索引）
SELECT start_time, cell_id, cgi, cellname, ...
FROM cell_4g_metrics
WHERE cgi = %s AND start_time BETWEEN %s AND %s
ORDER BY start_time
```

2. **添加 cell_id 索引**（已创建）
```sql
CREATE INDEX idx_metrics_4g_cell_id ON cell_4g_metrics(cell_id);
```

**预期效果**: 查询时间减少 **50-70%**

---

#### 2.4 批量小区查询优化

**当前查询** (`cell_timeseries_bulk` 方法):
```sql
SELECT start_time, cell_id, ...
FROM cell_4g_metrics
WHERE start_time BETWEEN %s AND %s
  AND (cell_id IN (...) OR cgi IN (...))
ORDER BY start_time, cell_id
```

**优化建议**:

1. **使用 UNION ALL 分离查询**
```sql
-- 方案1: 使用 cgi 查询（推荐）
SELECT start_time, cell_id, ...
FROM cell_4g_metrics
WHERE cgi IN (...) AND start_time BETWEEN %s AND %s
ORDER BY start_time, cell_id
```

2. **限制查询数量**
```python
# 在代码中限制批量查询的小区数量
if len(cell_ids) > 50:
    # 分批查询
    results = []
    for i in range(0, len(cell_ids), 50):
        batch = cell_ids[i:i+50]
        results.extend(self.cell_timeseries_bulk(batch, ...))
```

**预期效果**: 查询时间减少 **40-60%**

---

#### 2.5 区域统计查询优化

**当前查询** (`daily_traffic_and_voice_by_region` 方法):
```sql
SELECT cellname, cgi,
    SUM(COALESCE("PDCP_UpOctUl", 0) + COALESCE("PDCP_UpOctDl", 0)) / 1000.0 / 1000.0 AS traffic
FROM cell_4g_metrics_day
WHERE start_time >= %s AND start_time < %s
GROUP BY cellname, cgi
```

**优化建议**:

1. **添加 cellname 索引**（已创建）
```sql
CREATE INDEX idx_metrics_4g_day_cellname ON cell_4g_metrics_day(cellname);
```

2. **使用物化视图缓存区域映射**
```sql
-- 创建区域映射物化视图
CREATE MATERIALIZED VIEW mv_cell_region_mapping AS
SELECT DISTINCT
    cgi,
    cellname,
    '4G' AS network_type,
    CASE
        WHEN cellname LIKE '%阳江阳西%' THEN '阳西县'
        WHEN cellname LIKE '%阳江阳春%' THEN '阳春市'
        WHEN cellname LIKE '%阳江阳东%' THEN '阳东县'
        WHEN cellname LIKE '%阳江南区%' THEN '南区'
        ELSE '江城区'
    END AS region
FROM cell_4g_metrics
UNION ALL
SELECT DISTINCT
    "Ncgi" AS cgi,
    userlabel AS cellname,
    '5G' AS network_type,
    CASE
        WHEN userlabel LIKE '%阳江阳西%' THEN '阳西县'
        WHEN userlabel LIKE '%阳江阳春%' THEN '阳春市'
        WHEN userlabel LIKE '%阳江阳东%' THEN '阳东县'
        WHEN userlabel LIKE '%阳江南区%' THEN '南区'
        ELSE '江城区'
    END AS region
FROM cell_5g_metrics;

-- 创建索引
CREATE INDEX idx_mv_cell_region_cgi ON mv_cell_region_mapping(cgi);
CREATE INDEX idx_mv_cell_region_network ON mv_cell_region_mapping(network_type);

-- 定期刷新（每天一次）
REFRESH MATERIALIZED VIEW mv_cell_region_mapping;
```

3. **使用物化视图优化查询**
```sql
SELECT 
    m.region,
    SUM(d.traffic) AS total_traffic
FROM cell_4g_metrics_day d
JOIN mv_cell_region_mapping m ON d.cgi = m.cgi
WHERE d.start_time >= %s AND d.start_time < %s
GROUP BY m.region
```

**预期效果**: 查询时间减少 **60-80%**

---

### 3. 数据库配置优化

#### 3.1 连接池配置

**当前问题**: 每次查询都创建新连接

**优化方案**: 使用连接池

```python
# 在 db/pg.py 中配置连接池
from psycopg2 import pool

class PostgresClient:
    def __init__(self, config):
        self.pool = pool.ThreadedConnectionPool(
            minconn=5,      # 最小连接数
            maxconn=20,     # 最大连接数
            host=config['host'],
            port=config['port'],
            database=config['database'],
            user=config['user'],
            password=config['password']
        )
    
    def get_connection(self):
        return self.pool.getconn()
    
    def return_connection(self, conn):
        self.pool.putconn(conn)
```

**预期效果**: 连接开销减少 **70-90%**

---

#### 3.2 PostgreSQL 参数优化

**建议配置** (postgresql.conf):

```ini
# 内存配置
shared_buffers = 4GB              # 共享缓冲区（系统内存的25%）
effective_cache_size = 12GB       # 有效缓存大小（系统内存的75%）
work_mem = 64MB                   # 单个查询工作内存
maintenance_work_mem = 512MB      # 维护操作内存

# 查询优化
random_page_cost = 1.1            # SSD优化
effective_io_concurrency = 200    # 并发IO数

# 并行查询
max_parallel_workers_per_gather = 4
max_parallel_workers = 8
max_worker_processes = 8

# WAL配置
wal_buffers = 16MB
checkpoint_completion_target = 0.9
```

**应用配置**:
```bash
# 编辑配置文件
sudo vim /etc/postgresql/18/main/postgresql.conf

# 重启PostgreSQL
sudo systemctl restart postgresql
```

**预期效果**: 整体查询性能提升 **20-40%**

---

### 4. 查询缓存策略

#### 4.1 应用层缓存

**使用 Redis 缓存热点数据**:

```python
# services/cache.py
import redis
import json
from datetime import timedelta

class CacheService:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def get_traffic_series(self, key, ttl=300):
        """获取缓存的流量时间序列，TTL=5分钟"""
        data = self.redis.get(key)
        if data:
            return json.loads(data)
        return None
    
    def set_traffic_series(self, key, data, ttl=300):
        """缓存流量时间序列"""
        self.redis.setex(key, ttl, json.dumps(data))
```

**在 MetricsService 中使用缓存**:
```python
def traffic_series(self, network_types, start, end, granularity="15m"):
    # 生成缓存键
    cache_key = f"traffic:{','.join(network_types)}:{start}:{end}:{granularity}"
    
    # 尝试从缓存获取
    cached = self.cache.get_traffic_series(cache_key)
    if cached:
        return cached
    
    # 查询数据库
    data = self._query_traffic_series(network_types, start, end, granularity)
    
    # 缓存结果
    self.cache.set_traffic_series(cache_key, data, ttl=300)
    
    return data
```

**预期效果**: 
- 缓存命中时响应时间 **< 50ms**
- 减少数据库负载 **60-80%**

---

#### 4.2 数据库层缓存（物化视图）

**创建常用统计物化视图**:

```sql
-- 最新时刻Top利用率小区（4G）
CREATE MATERIALIZED VIEW mv_top_util_4g AS
SELECT 
    cell_id, cellname, cgi,
    (COALESCE("PDCP_UpOctUl",0) + COALESCE("PDCP_UpOctDl",0)) / 1000.0 / 1000.0 AS total_traffic,
    GREATEST(COALESCE(ul_prb_utilization,0), COALESCE(dl_prb_utilization,0)) AS max_prb_util,
    wireless_connect_rate,
    "RRC_ConnMax" AS max_rrc_users,
    interference,
    start_time
FROM cell_4g_metrics
WHERE start_time = (SELECT MAX(start_time) FROM cell_4g_metrics)
ORDER BY max_prb_util DESC
LIMIT 50;

-- 创建索引
CREATE INDEX idx_mv_top_util_4g_prb ON mv_top_util_4g(max_prb_util DESC);

-- 定期刷新（每15分钟）
-- 使用 cron 或应用定时任务
REFRESH MATERIALIZED VIEW mv_top_util_4g;
```

**预期效果**: Top小区查询时间 **< 10ms**

---

### 5. 并行查询优化

#### 5.1 使用并行查询执行器

**已实现** (`utils/parallel_query.py`):

```python
from utils.parallel_query import ParallelQueryExecutor

# 并行查询4G和5G数据
executor = ParallelQueryExecutor(max_workers=4)

results = executor.execute_parallel([
    (self.pg.fetch_all, (sql_4g, (start, end))),
    (self.pg.fetch_all, (sql_5g, (start, end)))
])

data_4g, data_5g = results
```

**预期效果**: 多表查询时间减少 **50-70%**

---

#### 5.2 数据库并行查询

**启用 PostgreSQL 并行查询**:

```sql
-- 设置并行度
SET max_parallel_workers_per_gather = 4;

-- 强制使用并行查询
SET parallel_setup_cost = 0;
SET parallel_tuple_cost = 0;

-- 查看执行计划
EXPLAIN (ANALYZE, BUFFERS) 
SELECT ...
FROM cell_4g_metrics
WHERE start_time BETWEEN '2025-12-01' AND '2025-12-31';
```

**预期效果**: 大表扫描时间减少 **40-60%**

---

### 6. 数据维护建议

#### 6.1 定期维护任务

**创建维护脚本** (`sql/maintenance.sql`):
```sql
-- 每日维护任务（建议凌晨执行）

-- 1. 清理死元组
VACUUM ANALYZE cell_4g_metrics;
VACUUM ANALYZE cell_5g_metrics;
VACUUM ANALYZE cell_4g_metrics_hour;
VACUUM ANALYZE cell_5g_metrics_hour;
VACUUM ANALYZE cell_4g_metrics_day;
VACUUM ANALYZE cell_5g_metrics_day;

-- 2. 更新统计信息
ANALYZE cell_4g_metrics;
ANALYZE cell_5g_metrics;

-- 3. 重建索引（每周一次）
REINDEX TABLE cell_4g_metrics;
REINDEX TABLE cell_5g_metrics;

-- 4. 刷新物化视图
REFRESH MATERIALIZED VIEW mv_cell_region_mapping;
REFRESH MATERIALIZED VIEW mv_top_util_4g;
REFRESH MATERIALIZED VIEW mv_top_util_5g;
```

**设置 cron 定时任务**:
```bash
# 编辑 crontab
crontab -e

# 添加定时任务（每天凌晨2点执行）
0 2 * * * psql -h 188.15.68.62 -p 54326 -U your_user -d data_wg -f /path/to/sql/maintenance.sql
```

---

#### 6.2 数据归档策略

**问题**: 历史数据过多影响查询性能

**解决方案**: 分区表 + 数据归档

```sql
-- 创建分区表（按月分区）
CREATE TABLE cell_4g_metrics_partitioned (
    LIKE cell_4g_metrics INCLUDING ALL
) PARTITION BY RANGE (start_time);

-- 创建分区
CREATE TABLE cell_4g_metrics_2025_01 PARTITION OF cell_4g_metrics_partitioned
    FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE cell_4g_metrics_2025_02 PARTITION OF cell_4g_metrics_partitioned
    FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

-- 迁移数据
INSERT INTO cell_4g_metrics_partitioned 
SELECT * FROM cell_4g_metrics 
WHERE start_time >= '2025-01-01';

-- 归档旧数据（保留6个月）
DROP TABLE cell_4g_metrics_2024_06;
```

**预期效果**: 
- 查询性能提升 **30-50%**
- 存储空间节省 **40-60%**

---

### 7. 监控和诊断

#### 7.1 慢查询监控

**启用慢查询日志**:

```sql
-- 启用 pg_stat_statements 扩展
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- 配置慢查询阈值（postgresql.conf）
log_min_duration_statement = 1000  # 记录超过1秒的查询

-- 查看慢查询
SELECT 
    query,
    calls,
    total_exec_time,
    mean_exec_time,
    max_exec_time,
    rows
FROM pg_stat_statements
WHERE mean_exec_time > 1000  -- 平均执行时间 > 1秒
ORDER BY mean_exec_time DESC
LIMIT 20;
```

---

#### 7.2 索引使用情况监控

**查看索引使用统计**:

```sql
-- 查看索引扫描次数
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan AS scans,
    idx_tup_read AS tuples_read,
    idx_tup_fetch AS tuples_fetched,
    pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;

-- 查找未使用的索引
SELECT 
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
    AND indexrelname NOT LIKE '%_pkey'
    AND schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC;
```

---

#### 7.3 表膨胀监控

**检查表膨胀情况**:
```sql
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - pg_relation_size(schemaname||'.'||tablename)) AS indexes_size,
    n_live_tup AS live_tuples,
    n_dead_tup AS dead_tuples,
    ROUND(100 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 2) AS dead_ratio
FROM pg_stat_user_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

**建议**: 当 dead_ratio > 10% 时执行 VACUUM

---

## 📋 实施计划

### 阶段1：立即执行（预计30分钟）

1. **执行索引优化脚本**
```bash
psql -h 188.15.68.62 -p 54326 -U your_user -d data_wg -f sql/optimize_indexes.sql
```

2. **验证索引创建**
```sql
-- 查看索引列表
\di+ cell_4g_metrics*
\di+ cell_5g_metrics*
```

3. **更新统计信息**
```sql
ANALYZE cell_4g_metrics;
ANALYZE cell_5g_metrics;
```

**预期效果**: 查询性能提升 **30-50%**

---

### 阶段2：应用层优化（预计1小时）

1. **配置连接池** - 修改 `db/pg.py`
2. **启用查询缓存** - 集成 Redis
3. **应用并行查询** - 使用 `ParallelQueryExecutor`

**预期效果**: 查询性能再提升 **20-40%**

---

### 阶段3：数据库配置优化（预计30分钟）

1. **优化 PostgreSQL 参数**
2. **启用慢查询日志**
3. **配置自动 VACUUM**

**预期效果**: 整体性能再提升 **10-20%**

---

### 阶段4：长期优化（预计2-3小时）

1. **创建物化视图**
2. **实施分区表**
3. **配置定期维护任务**

**预期效果**: 长期稳定性提升，性能持续优化

---

## 🎯 预期总体效果

| 指标 | 当前 | 目标 | 改善 |
|------|------|------|------|
| Dashboard查询 | 2.9-3.4秒 | 0.8-1.2秒 | **65-75%** |
| Top小区查询 | 1.5-2.0秒 | 0.3-0.5秒 | **75-85%** |
| 小区时间序列 | 2.0-3.0秒 | 0.5-0.8秒 | **70-80%** |
| 区域统计查询 | 3.0-4.0秒 | 0.6-1.0秒 | **75-85%** |

**总体目标**: 后端查询时间从 **3秒降至1秒以内**

---

## 📞 注意事项

1. **备份数据库** - 执行优化前务必备份
```bash
pg_dump -h 188.15.68.62 -p 54326 -U your_user -d data_wg > backup_$(date +%Y%m%d).sql
```

2. **业务低峰期执行** - 建议凌晨或业务低峰期执行索引创建

3. **监控执行过程** - 使用 `pg_stat_activity` 监控长时间运行的查询

4. **逐步实施** - 不要一次性执行所有优化，逐步验证效果

5. **保留回滚方案** - 记录所有修改，必要时可以回滚

---

## 📚 相关文档

- [PostgreSQL 官方文档 - 索引](https://www.postgresql.org/docs/current/indexes.html)
- [PostgreSQL 性能优化指南](https://wiki.postgresql.org/wiki/Performance_Optimization)
- [pg_stat_statements 使用指南](https://www.postgresql.org/docs/current/pgstatstatements.html)

---

**文档创建时间**: 2025-12-31
**最后更新时间**: 2025-12-31
**维护人员**: 系统管理员
