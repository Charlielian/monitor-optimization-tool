# 无性能小区统计更新 - 包括关联不到指标的小区

## 更新时间
2025-12-29

## 更新说明

根据用户需求，**无性能小区数**的统计现在包括两类小区：

1. **数据库中有记录但无性能的小区**：流量 = 0 且 PRB 利用率 = 0
2. **关联不到指标的小区**：场景中配置了 CGI，但在数据表中查不到数据

## 实现逻辑

### 统计方法

在 SQL 查询中添加 `COUNT(*) AS cells_with_data` 来统计有数据的小区数：

```sql
-- 4G
COUNT(*) AS cells_with_data

-- 5G  
COUNT(*) AS cells_with_data
```

### 计算公式

```python
# 1. 从数据库查询结果中获取有数据的小区数
cells_with_data = int(row.get("cells_with_data") or 0)

# 2. 计算关联不到数据的小区数
cells_without_data = len(cgids) - cells_with_data

# 3. 计算数据库中无性能的小区数
no_performance_in_db = int(row.get("no_performance_cells") or 0)

# 4. 总的无性能小区数 = 数据库中无性能的 + 关联不到数据的
total_no_performance = no_performance_in_db + cells_without_data
```

## 修改文件

### 1. `services/scenario_service.py`

#### 4G 部分修改
- SQL 查询添加 `COUNT(*) AS cells_with_data`
- 计算 `cells_without_data = len(cgids) - cells_with_data`
- 计算 `total_no_performance = no_performance_in_db + cells_without_data`
- 结果字典使用 `total_no_performance`

#### 5G 部分修改
- SQL 查询添加 `COUNT(*) AS cells_with_data`
- 计算 `cells_without_data = len(cgids) - cells_with_data`
- 计算 `total_no_performance = no_performance_in_db + cells_without_data`
- 结果字典使用 `total_no_performance`

### 2. `templates/monitor.html`

更新提示文字：
```
无性能小区数表示流量 = 0 且 PRB 利用率 = 0 的小区数量（包括关联不到指标的小区）
```

## 示例场景

假设某场景配置了 10 个 4G 小区：

| 情况 | 小区数 | 说明 |
|------|--------|------|
| 数据库中有数据的小区 | 8 | `cells_with_data = 8` |
| 关联不到数据的小区 | 2 | `cells_without_data = 10 - 8 = 2` |
| 数据库中无性能的小区 | 3 | 流量=0且PRB=0 |
| **总无性能小区数** | **5** | `3 + 2 = 5` |

## 业务意义

这个更新使得无性能小区的统计更加全面：

1. **完整性**：不仅统计有数据但无性能的小区，还包括完全没有数据的小区
2. **问题发现**：帮助快速识别配置错误或数据采集问题
3. **运维价值**：关联不到数据的小区可能是：
   - CGI 配置错误
   - 小区未开通
   - 数据采集失败
   - 小区已下线但未从场景中移除

## 测试验证

建议测试以下场景：

1. **正常场景**：所有小区都有数据
   - 验证 `cells_without_data = 0`
   - 无性能小区数 = 数据库中无性能的小区数

2. **部分无数据场景**：部分小区关联不到数据
   - 验证 `cells_without_data` 计算正确
   - 无性能小区数 = 数据库中无性能的 + 关联不到数据的

3. **全部无数据场景**：所有小区都关联不到数据
   - 验证 `cells_without_data = len(cgids)`
   - 无性能小区数 = 场景配置的总小区数

## 相关文档

- `TASK4_NO_TRAFFIC_NO_PERFORMANCE_SUMMARY.md` - 完整功能总结
- `CELL_WITHOUT_DATA_FEATURE.md` - 无数据小区显示功能说明
