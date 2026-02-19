# SQL 优化脚本使用指南

## 📁 文件说明

### 1. 表结构文件
- `cell_4g_metrics.sql` - 4G指标表结构（15分钟粒度）
- `cell_5g_metrics.sql` - 5G指标表结构（15分钟粒度）
- `cell_4g_metrics_hour.sql` - 4G指标表结构（小时粒度）
- `cell_5g_metrics_hour.sql` - 5G指标表结构（小时粒度）

### 2. 优化脚本
- `optimize_indexes.sql` - 索引优化脚本（立即执行）
- `maintenance.sql` - 日常维护脚本（定期执行）
- `diagnostics.sql` - 性能诊断脚本（问题排查）

### 3. 文档
- `sql优化建议.md` - 完整的SQL优化建议文档
- `README.md` - 本文件

---

## 🚀 快速开始

### 步骤1：执行索引优化（必须）

```bash
# 连接数据库并执行索引优化
psql -h 188.15.68.62 -p 54326 -U your_user -d data_wg -f sql/optimize_indexes.sql
```

**预期效果**: 查询性能提升 30-50%

**执行时间**: 约 5-10 分钟（取决于数据量）

---

### 步骤2：运行性能诊断（可选）

```bash
# 诊断当前数据库性能状况
psql -h 188.15.68.62 -p 54326 -U your_user -d data_wg -f sql/diagnostics.sql
```

**输出内容**:
- 数据库大小
- 表大小统计
- 索引使用情况
- 慢查询统计
- 表膨胀情况
- 缓存命中率

---

### 步骤3：配置定期维护（推荐）

```bash
# 编辑 crontab
crontab -e

# 添加定时任务（每天凌晨2点执行）
0 2 * * * psql -h 188.15.68.62 -p 54326 -U your_user -d data_wg -f /path/to/sql/maintenance.sql >> /var/log/pg_maintenance.log 2>&1
```

**维护内容**:
- 清理死元组
- 更新统计信息
- 检查表膨胀
- 检查索引使用

---

## 📋 详细使用说明

### optimize_indexes.sql - 索引优化

**用途**: 创建和优化数据库索引

**执行时机**: 
- 首次部署时立即执行
- 查询性能下降时执行
- 添加新表或字段后执行

**执行方式**:
```bash
# 方式1: 使用 psql 命令行
psql -h 188.15.68.62 -p 54326 -U your_user -d data_wg -f sql/optimize_indexes.sql

# 方式2: 在 psql 交互模式中
\i sql/optimize_indexes.sql

# 方式3: 使用管道
cat sql/optimize_indexes.sql | psql -h 188.15.68.62 -p 54326 -U your_user -d data_wg
```

**验证结果**:
```sql
-- 查看创建的索引
SELECT 
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE tablename LIKE 'cell_%_metrics%'
ORDER BY tablename, indexname;
```

---

### maintenance.sql - 日常维护

**用途**: 定期维护数据库性能

**执行时机**: 
- 每天凌晨执行（推荐）
- 业务低峰期执行
- 发现性能下降时手动执行

**执行方式**:
```bash
# 手动执行
psql -h 188.15.68.62 -p 54326 -U your_user -d data_wg -f sql/maintenance.sql

# 配置 cron 定时任务
0 2 * * * psql -h 188.15.68.62 -p 54326 -U your_user -d data_wg -f /path/to/sql/maintenance.sql >> /var/log/pg_maintenance.log 2>&1
```

**输出内容**:
- 维护任务执行状态
- 表膨胀情况
- 索引使用统计

---

### diagnostics.sql - 性能诊断

**用途**: 诊断数据库性能问题

**执行时机**: 
- 发现性能问题时
- 定期健康检查（每周一次）
- 优化前后对比

**执行方式**:
```bash
# 执行诊断并保存结果
psql -h 188.15.68.62 -p 54326 -U your_user -d data_wg -f sql/diagnostics.sql > diagnostics_$(date +%Y%m%d).txt

# 只查看特定部分（例如慢查询）
psql -h 188.15.68.62 -p 54326 -U your_user -d data_wg -c "
SELECT 
    LEFT(query, 100) AS query_preview,
    calls,
    ROUND(mean_exec_time::numeric, 2) AS mean_time_ms
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
"
```

**诊断指标**:
- **缓存命中率** > 95% 为良好
- **死元组比例** < 10% 为正常
- **平均查询时间** < 100ms 为优秀

---

## 🔧 常用命令

### 连接数据库

```bash
# 使用 psql 连接
psql -h 188.15.68.62 -p 54326 -U your_user -d data_wg

# 使用密码文件（避免交互输入密码）
echo "188.15.68.62:54326:data_wg:your_user:your_password" > ~/.pgpass
chmod 600 ~/.pgpass
psql -h 188.15.68.62 -p 54326 -U your_user -d data_wg
```

### 查看表信息

```sql
-- 查看所有表
\dt

-- 查看表结构
\d cell_4g_metrics

-- 查看索引
\di+ cell_4g_metrics*

-- 查看表大小
\dt+ cell_4g_metrics
```

### 查看查询执行计划

```sql
-- 查看执行计划
EXPLAIN SELECT * FROM cell_4g_metrics WHERE start_time > NOW() - INTERVAL '1 day';

-- 查看详细执行计划（包含实际执行时间）
EXPLAIN ANALYZE SELECT * FROM cell_4g_metrics WHERE start_time > NOW() - INTERVAL '1 day';

-- 查看缓冲区使用情况
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM cell_4g_metrics WHERE start_time > NOW() - INTERVAL '1 day';
```

### 手动维护

```sql
-- 清理死元组
VACUUM cell_4g_metrics;

-- 清理并更新统计信息
VACUUM ANALYZE cell_4g_metrics;

-- 完全清理（锁表，慎用）
VACUUM FULL cell_4g_metrics;

-- 更新统计信息
ANALYZE cell_4g_metrics;

-- 重建索引
REINDEX TABLE cell_4g_metrics;
```

---

## 📊 性能监控

### 实时监控查询

```sql
-- 查看当前活动查询
SELECT 
    pid,
    usename,
    state,
    NOW() - query_start AS duration,
    query
FROM pg_stat_activity
WHERE state = 'active'
    AND pid != pg_backend_pid()
ORDER BY duration DESC;

-- 终止长时间运行的查询
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE pid = 12345;  -- 替换为实际 PID
```

### 查看慢查询

```sql
-- 启用 pg_stat_statements（首次执行）
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- 查看慢查询
SELECT 
    LEFT(query, 150) AS query,
    calls,
    ROUND(mean_exec_time::numeric, 2) AS avg_ms,
    ROUND(total_exec_time::numeric, 2) AS total_ms
FROM pg_stat_statements
WHERE mean_exec_time > 100  -- 平均执行时间 > 100ms
ORDER BY mean_exec_time DESC
LIMIT 20;

-- 重置统计信息
SELECT pg_stat_statements_reset();
```

---

## ⚠️ 注意事项

### 1. 备份数据库

**执行任何优化前务必备份**:

```bash
# 完整备份
pg_dump -h 188.15.68.62 -p 54326 -U your_user -d data_wg > backup_$(date +%Y%m%d_%H%M%S).sql

# 仅备份表结构
pg_dump -h 188.15.68.62 -p 54326 -U your_user -d data_wg --schema-only > schema_backup.sql

# 压缩备份
pg_dump -h 188.15.68.62 -p 54326 -U your_user -d data_wg | gzip > backup_$(date +%Y%m%d).sql.gz
```

### 2. 业务低峰期执行

- 索引创建会锁表，建议凌晨执行
- VACUUM FULL 会完全锁表，慎用
- REINDEX 会锁表，建议使用 REINDEX CONCURRENTLY

### 3. 监控执行过程

```sql
-- 查看正在创建的索引
SELECT 
    pid,
    query,
    NOW() - query_start AS duration
FROM pg_stat_activity
WHERE query LIKE '%CREATE INDEX%';
```

### 4. 磁盘空间检查

```bash
# 检查磁盘空间
df -h

# 检查数据库目录空间
du -sh /var/lib/postgresql/18/main/
```

---

## 🎯 优化效果验证

### 执行前后对比

```sql
-- 1. 记录优化前的查询时间
\timing on
SELECT COUNT(*) FROM cell_4g_metrics WHERE start_time > NOW() - INTERVAL '1 day';

-- 2. 执行优化脚本
\i sql/optimize_indexes.sql

-- 3. 记录优化后的查询时间
SELECT COUNT(*) FROM cell_4g_metrics WHERE start_time > NOW() - INTERVAL '1 day';
```

### 查看索引效果

```sql
-- 查看索引扫描次数
SELECT 
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE tablename = 'cell_4g_metrics'
ORDER BY idx_scan DESC;
```

---

## 📞 问题排查

### 问题1: 索引创建失败

**可能原因**:
- 磁盘空间不足
- 权限不足
- 索引已存在

**解决方案**:
```sql
-- 检查磁盘空间
SELECT pg_size_pretty(pg_database_size(current_database()));

-- 检查权限
\du

-- 删除已存在的索引
DROP INDEX IF EXISTS idx_metrics_4g_time;
```

### 问题2: 查询仍然很慢

**排查步骤**:
1. 查看执行计划: `EXPLAIN ANALYZE SELECT ...`
2. 检查索引是否被使用
3. 检查统计信息是否更新: `ANALYZE table_name`
4. 检查表膨胀情况: 运行 `diagnostics.sql`

### 问题3: 维护任务执行时间过长

**解决方案**:
- 使用 `VACUUM` 代替 `VACUUM FULL`
- 分批执行维护任务
- 调整 `maintenance_work_mem` 参数

---

## 📚 相关文档

- [sql优化建议.md](./sql优化建议.md) - 完整优化建议
- [PostgreSQL 官方文档](https://www.postgresql.org/docs/)
- [性能分析报告](../LATEST_PERFORMANCE_REPORT.md)

---

**文档创建时间**: 2025-12-31  
**维护人员**: 系统管理员
