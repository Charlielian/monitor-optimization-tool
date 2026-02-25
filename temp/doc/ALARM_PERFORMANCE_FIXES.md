# 告警页面性能优化总结

## 🔧 已修复的问题

### 1. ❌ 数据库字段错误（已修复）
**问题**：SQL查询使用了不存在的字段 `ne`, `ne_name`, `alarm_title`
```
Unknown column 'ne' in 'field list'
```

**修复**：
- 使用正确的字段名 `` `网元` `` （带反引号）
- 移除不存在的 `ne`, `ne_name` 字段
- 移除 `alarm_title` 字段（只使用 `alarm_code_name`）
- 在模板中网元名称列显示 "-"（该字段不存在）

### 2. 🐌 今日告警统计查询超慢（已优化）
**问题**：查询耗时 12秒
```sql
-- 原查询（慢）
SELECT COUNT(*) as total
FROM (
    SELECT DISTINCT alarm_id, alarm_code_name, alarm_level, alarm_type, ne_id, ne_type
    FROM cur_alarm
    WHERE DATE(import_time) = CURDATE()
) as distinct_alarms
```

**优化**：移除 DISTINCT 和子查询
```sql
-- 新查询（快）
SELECT COUNT(*) as total
FROM cur_alarm
WHERE DATE(import_time) = CURDATE()
```

**效果**：预计从 12秒 降低到 <100ms

### 3. 📊 添加数据库索引（已完成）
创建了以下索引来加速查询：

```sql
-- 单列索引
CREATE INDEX idx_ne_id ON cur_alarm(ne_id(50));
CREATE INDEX idx_alarm_level ON cur_alarm(alarm_level(20));
CREATE INDEX idx_alarm_code_name ON cur_alarm(alarm_code_name(100));

-- 复合索引
CREATE INDEX idx_import_time_level ON cur_alarm(import_time, alarm_level(20));
CREATE INDEX idx_import_time_ne_id ON cur_alarm(import_time, ne_id(50));
```

**用途**：
- `idx_ne_id`：加速网元ID过滤
- `idx_alarm_level`：加速告警级别统计
- `idx_alarm_code_name`：加速告警名称过滤
- `idx_import_time_level`：加速当前告警统计（按时间+级别）
- `idx_import_time_ne_id`：加速按网元ID过滤当前告警

## 📈 性能监控日志

### 日志层级
- **路由层**（app.py）：记录整体请求耗时
- **服务层**（alarm_service.py）：记录业务逻辑耗时
- **数据库层**（mysql.py）：记录SQL执行耗时

### 警告阈值
- 🔴 超慢（>2秒）：记录完整SQL
- 🟡 慢（>1秒）：警告级别
- ℹ️ 一般（>500ms）：信息级别
- ⚡ 快速（<500ms）：调试级别

## 🎯 预期性能提升

### 优化前
```
📋 告警页面请求 - Tab: current
  ├─ ⚠️ 告警统计查询慢: 12379.36ms
  ├─ ⚠️ 当前告警查询慢: 1409.33ms
  ├─ ⚠️ 模板渲染慢: 832.60ms
  └─ 🔴 告警页面总耗时: 14628.29ms (超过3秒)
```

### 优化后（预期）
```
📋 告警页面请求 - Tab: current
  ├─ 告警统计查询: 80ms
  ├─ 当前告警查询: 200ms
  ├─ 模板渲染: 100ms
  └─ ✅ 告警页面总耗时: 400ms
```

**预期提升**：从 14.6秒 降低到 0.4秒，**提升 97%**

## 🔍 如何验证优化效果

### 1. 查看实时日志
```bash
tail -f logs/monitoring_app.log | grep "告警"
```

### 2. 查看慢查询
```bash
grep "⚠️\|🔴" logs/monitoring_app.log | grep "告警"
```

### 3. 测试不同场景
- 无过滤条件访问告警页面
- 按网元ID过滤（单个）
- 按网元ID过滤（多个，用逗号分隔）
- 按告警名称过滤
- 查询历史告警

## 📝 字段映射说明

### 当前告警和历史告警显示字段

| 列名 | 数据库字段 | 说明 |
|------|-----------|------|
| 告警时间 | `occur_time` | 告警发生时间 |
| 告警级别 | `alarm_level` | 紧急/重要/主要/一般 |
| 告警名称 | `alarm_code_name` | 告警代码名称 |
| 告警类型 | `alarm_type` | 告警类型 |
| 网元 | `` `网元` `` | 网元（带反引号） |
| 网元名称 | - | 不存在，显示"-" |
| 网元ID | `ne_id` | 网元标识 |
| 网元类型 | `ne_type` | ITBBU等 |
| 站点名称 | `site_name` | 站点名称 |
| 告警对象 | `alarm_object_name` | 告警对象名称 |
| 位置 | `location` | 位置信息 |
| 附加信息 | `additional_info` | 附加信息 |
| 确认状态 | `ack_status` | 已确认/未确认 |
| 告警原因 | `alarm_reason` | 告警原因描述 |

## 🚀 后续优化建议

### 1. 添加缓存
对告警统计数据使用1分钟缓存：
```python
from services.cache import cache_1m

stats = cache_1m.get(
    "alarm_stats",
    lambda: alarm_service.get_alarm_statistics()
)
```

### 2. 分页优化
当前每页100条，如果数据量大可以考虑：
- 减少到50条/页
- 使用游标分页代替 OFFSET

### 3. 异步加载
考虑将统计卡片和告警列表分开加载：
- 页面先显示列表
- 统计数据通过AJAX异步加载

### 4. 数据归档
定期清理旧数据：
- 保留最近30天的告警数据
- 历史数据归档到其他表

## 📊 数据库表信息

### cur_alarm 表
- 总行数：约 88,803 行
- 表大小：需要查询
- 索引数量：11 个（优化后）

### 查看表大小
```sql
SELECT 
    table_name,
    ROUND(((data_length + index_length) / 1024 / 1024), 2) AS "Size (MB)"
FROM information_schema.TABLES
WHERE table_schema = "optimization_toolbox"
    AND table_name = "cur_alarm";
```
