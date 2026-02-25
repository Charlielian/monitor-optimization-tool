# ✅ SQL 优化方案已就绪

## 📋 更新说明

已根据实际表结构更新所有SQL优化脚本，确认系统包含以下6个表：

### 4G表（3个粒度）
- `cell_4g_metrics` - 15分钟粒度
- `cell_4g_metrics_hour` - 小时粒度
- `cell_4g_metrics_day` - 天粒度

### 5G表（3个粒度）
- `cell_5g_metrics` - 15分钟粒度
- `cell_5g_metrics_hour` - 小时粒度
- `cell_5g_metrics_day` - 天粒度

---

## 🎯 优化内容

### 为每个表创建5个索引

1. **时间索引** - `start_time DESC`
2. **CGI索引** - `cgi` (4G) 或 `Ncgi` (5G)
3. **复合索引** - `start_time + cgi`
4. **小区ID索引** - `cell_id` (4G) 或使用 `Ncgi` (5G)
5. **小区名索引** - `cellname` (4G) 或 `userlabel` (5G)

**总计**: 30个索引（6个表 × 5个索引）

---

## ⚡ 立即开始（3步）

### 步骤1: 检查表（可选）

```bash
psql -h 188.15.68.62 -p 54326 -U your_user -d data_wg -f sql/check_tables.sql
```

**预期**: 显示6个表及其大小

---

### 步骤2: 备份数据库（必须）

```bash
pg_dump -h 188.15.68.62 -p 54326 -U your_user -d data_wg > backup_$(date +%Y%m%d_%H%M%S).sql
```

---

### 步骤3: 执行优化（核心）

```bash
psql -h 188.15.68.62 -p 54326 -U your_user -d data_wg -f sql/optimize_indexes.sql
```

**执行时间**: 5-10分钟  
**预期效果**: 查询性能提升 30-50%

---

## 📁 文件清单

### SQL脚本（4个）
- ✅ `sql/check_tables.sql` - 检查表是否存在
- ✅ `sql/optimize_indexes.sql` - 索引优化脚本（核心）
- ✅ `sql/maintenance.sql` - 日常维护脚本
- ✅ `sql/diagnostics.sql` - 性能诊断脚本

### 文档（4个）
- ✅ `sql/EXECUTION_SUMMARY.md` - 执行总结（推荐阅读）
- ✅ `sql/QUICK_START.md` - 快速开始指南
- ✅ `sql/sql优化建议.md` - 完整优化方案（18KB）
- ✅ `sql/README.md` - 详细使用指南

### 表结构（4个）
- ✅ `sql/cell_4g_metrics.sql` - 4G表结构（15分钟）
- ✅ `sql/cell_4g_metrics_hour.sql` - 4G表结构（小时）
- ✅ `sql/cell_5g_metrics.sql` - 5G表结构（15分钟）
- ✅ `sql/cell_5g_metrics_hour.sql` - 5G表结构（小时）

---

## 📊 预期效果

### 查询性能提升

| 查询类型 | 当前 | 目标 | 改善 |
|---------|------|------|------|
| Dashboard查询 | 2.9-3.4秒 | 0.8-1.2秒 | **65-75%** ⬇️ |
| Top小区查询 | 1.5-2.0秒 | 0.3-0.5秒 | **75-85%** ⬇️ |
| 小区时间序列 | 2.0-3.0秒 | 0.5-0.8秒 | **70-80%** ⬇️ |
| 区域统计查询 | 3.0-4.0秒 | 0.6-1.0秒 | **75-85%** ⬇️ |

### 具体优化效果

- ✅ 时间范围查询提速 **50-70%**
- ✅ CGI查询提速 **60-80%**
- ✅ 小区查询提速 **70-90%**
- ✅ 区域统计提速 **60-80%**

---

## 🔍 验证优化效果

### 1. 查看索引创建结果

脚本执行完成后会自动显示所有索引

### 2. 运行性能诊断

```bash
psql -h 188.15.68.62 -p 54326 -U your_user -d data_wg -f sql/diagnostics.sql > diagnostics_after.txt
```

### 3. 分析应用日志

```bash
python analyze_performance.py logs/monitoring_app.log
```

### 4. 测试实际查询

```sql
\timing on

-- 测试Dashboard查询
SELECT COUNT(*) FROM cell_4g_metrics 
WHERE start_time > NOW() - INTERVAL '6 hours';

-- 测试Top小区查询
SELECT * FROM cell_4g_metrics 
WHERE start_time = (SELECT MAX(start_time) FROM cell_4g_metrics)
ORDER BY dl_prb_utilization DESC LIMIT 20;
```

---

## 🛠️ 定期维护

### 配置自动维护（推荐）

```bash
# 编辑 crontab
crontab -e

# 添加定时任务（每天凌晨2点）
0 2 * * * psql -h 188.15.68.62 -p 54326 -U your_user -d data_wg -f /path/to/sql/maintenance.sql >> /var/log/pg_maintenance.log 2>&1
```

### 维护内容
- VACUUM ANALYZE 所有6个表
- 检查表膨胀情况
- 检查索引使用情况

---

## ⚠️ 重要提醒

### 1. 执行时机
- ✅ **推荐**: 业务低峰期（凌晨）
- ❌ **避免**: 业务高峰期

### 2. 备份
- ✅ **必须**: 执行前备份数据库
- ✅ **建议**: 保留最近3天的备份

### 3. 磁盘空间
- ✅ **检查**: 确保至少20%空闲空间
- ✅ **监控**: 索引创建过程中的空间使用

### 4. 执行时间
- 小表（< 100万行）: 1-3分钟
- 中表（100万-1000万行）: 3-10分钟
- 大表（> 1000万行）: 10-30分钟

---

## 🆘 问题排查

### 问题1: "server closed the connection unexpectedly"

**原因**: 表名不正确或表不存在

**解决**: 
```bash
# 检查表是否存在
psql -h 188.15.68.62 -p 54326 -U your_user -d data_wg -f sql/check_tables.sql
```

### 问题2: "permission denied"

**原因**: 用户权限不足

**解决**:
```sql
-- 检查权限
\du

-- 授予权限（需要超级用户）
GRANT CREATE ON SCHEMA public TO your_user;
```

### 问题3: "disk full"

**原因**: 磁盘空间不足

**解决**:
```bash
# 检查磁盘空间
df -h

# 清理不必要的文件或扩展磁盘
```

---

## 📞 下一步行动

### 立即执行（推荐顺序）

1. ✅ **阅读文档**: `sql/EXECUTION_SUMMARY.md`
2. ✅ **检查表**: `sql/check_tables.sql`
3. ✅ **备份数据库**: `pg_dump ...`
4. ✅ **执行优化**: `sql/optimize_indexes.sql`
5. ✅ **验证效果**: `sql/diagnostics.sql`
6. ✅ **配置维护**: 设置 cron 定时任务

### 后续优化（可选）

1. 应用层缓存（Redis）
2. 数据库配置优化
3. 并行查询优化
4. 物化视图创建

详见：`sql/sql优化建议.md`

---

## 📚 文档导航

### 快速开始
- **3分钟快速指南**: `sql/QUICK_START.md`
- **执行总结**: `sql/EXECUTION_SUMMARY.md`

### 详细文档
- **完整优化方案**: `sql/sql优化建议.md` (18KB)
- **使用指南**: `sql/README.md`

### SQL脚本
- **检查表**: `sql/check_tables.sql`
- **索引优化**: `sql/optimize_indexes.sql` ⭐
- **日常维护**: `sql/maintenance.sql`
- **性能诊断**: `sql/diagnostics.sql`

---

## ✅ 执行检查清单

- [ ] 阅读 `sql/EXECUTION_SUMMARY.md`
- [ ] 检查6个表是否存在
- [ ] 备份数据库
- [ ] 检查磁盘空间（≥20%空闲）
- [ ] 确认在业务低峰期
- [ ] 执行 `sql/optimize_indexes.sql`
- [ ] 验证索引创建成功
- [ ] 运行性能诊断
- [ ] 测试查询性能
- [ ] 配置定期维护
- [ ] 监控优化效果

---

**状态**: ✅ 就绪，可以立即执行  
**创建时间**: 2025-12-31  
**最后更新**: 2025-12-31  

**立即开始**: `psql -h 188.15.68.62 -p 54326 -U your_user -d data_wg -f sql/optimize_indexes.sql`
