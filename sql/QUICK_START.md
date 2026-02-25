# SQL 优化快速开始

## ⚡ 3分钟快速优化

### 步骤0: 检查表是否存在（可选）

```bash
psql -h 188.15.68.62 -p 54326 -U your_user -d data_wg -f sql/check_tables.sql
```

应该显示6个表：
- cell_4g_metrics (15分钟)
- cell_4g_metrics_hour (小时)
- cell_4g_metrics_day (天)
- cell_5g_metrics (15分钟)
- cell_5g_metrics_hour (小时)
- cell_5g_metrics_day (天)

---

### 步骤1: 执行索引优化（必须）

```bash
psql -h 188.15.68.62 -p 54326 -U your_user -d data_wg -f sql/optimize_indexes.sql
```

**优化内容**:
- 为所有6个表创建时间、CGI、cell_id/Ncgi、cellname/userlabel索引
- 创建复合索引（时间+CGI）
- 更新表统计信息

**预期效果**: 查询性能提升 30-50%  
**执行时间**: 5-10分钟

---

### 步骤2: 验证效果

```bash
# 运行性能诊断
psql -h 188.15.68.62 -p 54326 -U your_user -d data_wg -f sql/diagnostics.sql

# 分析应用日志
python analyze_performance.py logs/monitoring_app.log
```

---

### 步骤3: 配置定期维护（推荐）

```bash
# 编辑 crontab
crontab -e

# 添加以下行（每天凌晨2点执行）
0 2 * * * psql -h 188.15.68.62 -p 54326 -U your_user -d data_wg -f /path/to/sql/maintenance.sql >> /var/log/pg_maintenance.log 2>&1
```

---

## 📊 预期效果

| 查询类型 | 优化前 | 优化后 | 改善 |
|---------|--------|--------|------|
| Dashboard | 3.0秒 | 1.0秒 | 67% ⬇️ |
| Top小区 | 2.0秒 | 0.4秒 | 80% ⬇️ |
| 小区时间序列 | 2.5秒 | 0.6秒 | 76% ⬇️ |
| 区域统计 | 3.5秒 | 0.8秒 | 77% ⬇️ |

---

## 📁 文件说明

- `optimize_indexes.sql` - 索引优化（立即执行）⭐
- `maintenance.sql` - 日常维护（定期执行）
- `diagnostics.sql` - 性能诊断（问题排查）
- `sql优化建议.md` - 完整优化方案（详细阅读）
- `README.md` - 使用指南（参考文档）

---

## ⚠️ 注意事项

1. **备份数据库**（必须）
```bash
pg_dump -h 188.15.68.62 -p 54326 -U your_user -d data_wg > backup_$(date +%Y%m%d).sql
```

2. **业务低峰期执行**（建议凌晨）

3. **监控执行过程**
```sql
SELECT pid, query, NOW() - query_start AS duration
FROM pg_stat_activity WHERE state = 'active';
```

---

## 🆘 遇到问题？

查看详细文档：
- [sql优化建议.md](./sql优化建议.md) - 完整优化方案
- [README.md](./README.md) - 详细使用指南

---

**立即开始**: `psql -h 188.15.68.62 -p 54326 -U your_user -d data_wg -f sql/optimize_indexes.sql`
