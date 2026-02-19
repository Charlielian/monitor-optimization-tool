# SQL 优化脚本执行总结

## 📋 表结构说明

系统包含6个指标表，分为3个粒度：

### 4G表
- **cell_4g_metrics** - 15分钟粒度
- **cell_4g_metrics_hour** - 小时粒度  
- **cell_4g_metrics_day** - 天粒度

### 5G表
- **cell_5g_metrics** - 15分钟粒度
- **cell_5g_metrics_hour** - 小时粒度
- **cell_5g_metrics_day** - 天粒度

---

## 🎯 优化脚本说明

### optimize_indexes.sql
为所有6个表创建以下索引：

**每个表的索引**:
1. **时间索引** - `start_time DESC` (降序，用于最新数据查询)
2. **CGI索引** - `cgi` 或 `Ncgi` (用于小区查询)
3. **复合索引** - `start_time + cgi` (用于时间范围+小区查询)
4. **小区标识索引** - `cell_id` (4G) 或保持 `Ncgi` (5G)
5. **小区名索引** - `cellname` (4G) 或 `userlabel` (5G，用于区域分类)

**总计**: 30个索引（每个表5个索引 × 6个表）

---

## ⚡ 执行步骤

### 1. 检查表是否存在

```bash
psql -h 188.15.68.62 -p 54326 -U your_user -d data_wg -f sql/check_tables.sql
```

**预期输出**: 显示6个表及其大小

---

### 2. 备份数据库（必须）

```bash
# 完整备份
pg_dump -h 188.15.68.62 -p 54326 -U your_user -d data_wg > backup_$(date +%Y%m%d_%H%M%S).sql

# 或仅备份表结构
pg_dump -h 188.15.68.62 -p 54326 -U your_user -d data_wg --schema-only > schema_backup.sql
```

---

### 3. 执行索引优化

```bash
psql -h 188.15.68.62 -p 54326 -U your_user -d data_wg -f sql/optimize_indexes.sql
```

**执行过程**:
1. 优化 cell_4g_metrics (15分钟)
2. 优化 cell_5g_metrics (15分钟)
3. 优化 cell_4g_metrics_hour (小时)
4. 优化 cell_5g_metrics_hour (小时)
5. 优化 cell_4g_metrics_day (天)
6. 优化 cell_5g_metrics_day (天)
7. 更新所有表统计信息
8. 显示索引创建结果

**预期时间**: 5-10分钟（取决于数据量）

---

### 4. 验证优化效果

```bash
# 运行性能诊断
psql -h 188.15.68.62 -p 54326 -U your_user -d data_wg -f sql/diagnostics.sql

# 分析应用日志
python analyze_performance.py logs/monitoring_app.log
```

---

## 📊 预期效果

### 查询性能提升

| 查询类型 | 优化前 | 优化后 | 改善 |
|---------|--------|--------|------|
| Dashboard查询 | 3.0秒 | 1.0秒 | 67% ⬇️ |
| Top小区查询 | 2.0秒 | 0.4秒 | 80% ⬇️ |
| 小区时间序列 | 2.5秒 | 0.6秒 | 76% ⬇️ |
| 区域统计查询 | 3.5秒 | 0.8秒 | 77% ⬇️ |

### 索引效果

- **时间范围查询**: 提速 50-70%
- **CGI查询**: 提速 60-80%
- **小区查询**: 提速 70-90%
- **区域统计**: 提速 60-80%

---

## 🔍 验证索引创建

### 查看索引列表

```sql
-- 查看4G表索引
\di+ cell_4g_metrics*

-- 查看5G表索引
\di+ cell_5g_metrics*
```

### 查看索引使用情况

```sql
SELECT 
    tablename,
    indexname,
    idx_scan AS scans,
    pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE tablename LIKE 'cell_%_metrics%'
ORDER BY tablename, idx_scan DESC;
```

### 测试查询性能

```sql
-- 测试时间范围查询
\timing on
SELECT COUNT(*) FROM cell_4g_metrics 
WHERE start_time > NOW() - INTERVAL '1 day';

-- 测试CGI查询
SELECT COUNT(*) FROM cell_4g_metrics 
WHERE cgi = 'your_cgi_value';

-- 测试复合查询
SELECT * FROM cell_4g_metrics 
WHERE start_time > NOW() - INTERVAL '6 hours' 
  AND cgi = 'your_cgi_value';
```

---

## 🛠️ 定期维护

### 配置自动维护

```bash
# 编辑 crontab
crontab -e

# 添加定时任务（每天凌晨2点）
0 2 * * * psql -h 188.15.68.62 -p 54326 -U your_user -d data_wg -f /path/to/sql/maintenance.sql >> /var/log/pg_maintenance.log 2>&1
```

### 手动维护

```bash
# 执行维护脚本
psql -h 188.15.68.62 -p 54326 -U your_user -d data_wg -f sql/maintenance.sql
```

**维护内容**:
- VACUUM ANALYZE 所有6个表
- 检查表膨胀情况
- 检查索引使用情况

---

## ⚠️ 注意事项

### 1. 执行时机
- **推荐**: 业务低峰期（凌晨）
- **避免**: 业务高峰期

### 2. 磁盘空间
- 索引创建需要额外磁盘空间
- 建议预留至少20%的空闲空间

### 3. 锁表影响
- `CREATE INDEX IF NOT EXISTS` 会短暂锁表
- 对于大表，可能需要几分钟
- 建议在维护窗口执行

### 4. 监控执行
```sql
-- 查看正在执行的操作
SELECT pid, query, NOW() - query_start AS duration
FROM pg_stat_activity
WHERE state = 'active' AND query LIKE '%CREATE INDEX%';
```

---

## 🆘 问题排查

### 问题1: 连接超时

**原因**: 数据库连接配置错误或网络问题

**解决**:
```bash
# 测试连接
psql -h 188.15.68.62 -p 54326 -U your_user -d data_wg -c "SELECT version();"
```

### 问题2: 权限不足

**原因**: 用户没有创建索引的权限

**解决**:
```sql
-- 检查权限
\du

-- 授予权限（需要超级用户）
GRANT CREATE ON SCHEMA public TO your_user;
```

### 问题3: 磁盘空间不足

**原因**: 索引创建需要额外空间

**解决**:
```bash
# 检查磁盘空间
df -h

# 清理不必要的文件
# 或扩展磁盘空间
```

### 问题4: 索引创建时间过长

**原因**: 表数据量大

**解决**:
- 耐心等待（大表可能需要10-30分钟）
- 或分批创建索引（注释掉部分表）

---

## 📚 相关文档

- [sql/optimize_indexes.sql](./optimize_indexes.sql) - 索引优化脚本
- [sql/sql优化建议.md](./sql优化建议.md) - 完整优化方案
- [sql/README.md](./README.md) - 详细使用指南
- [sql/QUICK_START.md](./QUICK_START.md) - 快速开始

---

## ✅ 执行检查清单

- [ ] 检查6个表是否都存在 (`check_tables.sql`)
- [ ] 备份数据库
- [ ] 检查磁盘空间（至少20%空闲）
- [ ] 确认在业务低峰期执行
- [ ] 执行 `optimize_indexes.sql`
- [ ] 验证索引创建成功
- [ ] 运行性能诊断 (`diagnostics.sql`)
- [ ] 测试查询性能
- [ ] 配置定期维护任务
- [ ] 监控优化效果

---

**创建时间**: 2025-12-31  
**最后更新**: 2025-12-31  
**状态**: ✅ 就绪
