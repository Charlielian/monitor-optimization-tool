# 无流量小区和无性能小区统计功能 - 完成总结

## 任务状态：✅ 已完成

## 功能说明

在保障监控的场景指标汇总中，新增两个统计指标：

1. **无流量小区数**：流量 = 0 的小区数量
2. **无性能小区数**：流量 = 0 且 PRB 利用率 = 0 的小区数量（**包括关联不到指标的小区**）

### 无性能小区定义
无性能小区包括两类：
1. 数据库中有记录，但流量 = 0 且 PRB 利用率 = 0 的小区
2. 场景中配置了 CGI，但在数据表中查不到数据的小区（关联不到指标）

## 修改内容

### 1. 后端修改 - `services/scenario_service.py`

#### 4G 部分（已完成）
在 `scenario_metrics` 方法的 4G SQL 查询中添加：
```sql
COUNT(CASE WHEN total_traffic_gb = 0 THEN 1 END) AS no_traffic_cells,
COUNT(CASE WHEN total_traffic_gb = 0 AND ul_prb_utilization = 0 AND dl_prb_utilization = 0 THEN 1 END) AS no_performance_cells
```

#### 5G 部分（本次完成）
在 `scenario_metrics` 方法的 5G SQL 查询中添加：
```sql
COUNT(CASE WHEN (COALESCE("RLC_UpOctUl",0) + COALESCE("RLC_UpOctDl",0)) = 0 THEN 1 END) AS no_traffic_cells,
COUNT(CASE WHEN (COALESCE("RLC_UpOctUl",0) + COALESCE("RLC_UpOctDl",0)) = 0 
           AND COALESCE("RRU_PuschPrbAssn", 0) = 0 
           AND COALESCE("RRU_PdschPrbAssn", 0) = 0 THEN 1 END) AS no_performance_cells
```

#### 结果字典更新
- 4G 有数据情况：
  - 添加 `"无流量小区数"` 字段
  - 添加 `"无性能小区数"` 字段（= 数据库中无性能的 + 关联不到数据的）
  - 通过 `COUNT(*)` 统计有数据的小区数，计算关联不到数据的小区数
- 4G 无数据情况：添加 `"无流量小区数": 0` 和 `"无性能小区数": 0`
- 5G 有数据情况：
  - 添加 `"无流量小区数"` 字段
  - 添加 `"无性能小区数"` 字段（= 数据库中无性能的 + 关联不到数据的）
  - 通过 `COUNT(*)` 统计有数据的小区数，计算关联不到数据的小区数
- 5G 无数据情况：添加 `"无流量小区数": 0` 和 `"无性能小区数": 0`

### 2. 前端修改 - `templates/monitor.html`

#### 表格表头
在场景指标汇总表格中新增两列：
- **无流量小区**：使用灰色徽章（`badge bg-secondary`）
- **无性能小区**：使用深色徽章（`badge bg-dark`）

#### 表格数据行
添加两列数据显示：
```html
<td class="text-center">
  {% if row.get("无流量小区数", 0) > 0 %}
  <span class="badge bg-secondary">{{ row["无流量小区数"] }}</span>
  {% else %}
  <span class="text-muted">0</span>
  {% endif %}
</td>
<td class="text-center">
  {% if row.get("无性能小区数", 0) > 0 %}
  <span class="badge bg-dark">{{ row["无性能小区数"] }}</span>
  {% else %}
  <span class="text-muted">0</span>
  {% endif %}
</td>
```

#### 更新 colspan
将空数据提示的 colspan 从 11 更新为 13（增加了 2 列）

#### 更新提示文字
在表格底部的提示信息中添加：
> 无流量小区数表示流量 = 0 的小区数量，无性能小区数表示流量 = 0 且 PRB 利用率 = 0 的小区数量（包括关联不到指标的小区）

## 技术细节

### 4G 统计逻辑
- **无流量**：`total_traffic_gb = 0`
- **无性能**：
  - 数据库中：`total_traffic_gb = 0 AND ul_prb_utilization = 0 AND dl_prb_utilization = 0`
  - 关联不到数据：`场景配置的小区数 - COUNT(*) 查询到的小区数`
  - 总计：`数据库中无性能的 + 关联不到数据的`

### 5G 统计逻辑
- **无流量**：`(RLC_UpOctUl + RLC_UpOctDl) = 0`
- **无性能**：
  - 数据库中：`(RLC_UpOctUl + RLC_UpOctDl) = 0 AND RRU_PuschPrbAssn = 0 AND RRU_PdschPrbAssn = 0`
  - 关联不到数据：`场景配置的小区数 - COUNT(*) 查询到的小区数`
  - 总计：`数据库中无性能的 + 关联不到数据的`

### 实现方式
在 SQL 查询中添加 `COUNT(*) AS cells_with_data` 来统计有数据的小区数，然后计算：
```python
cells_with_data = int(row.get("cells_with_data") or 0)
cells_without_data = len(cgids) - cells_with_data
no_performance_in_db = int(row.get("no_performance_cells") or 0)
total_no_performance = no_performance_in_db + cells_without_data
```

## 视觉设计

| 指标 | 徽章颜色 | Bootstrap 类 | 说明 |
|------|---------|-------------|------|
| 超阈值小区 | 黄色 | `bg-warning` | PRB 利用率超过阈值 |
| 干扰小区 | 红色 | `bg-danger` | 干扰值 > -105 |
| 无流量小区 | 灰色 | `bg-secondary` | 流量为 0 |
| 无性能小区 | 深色 | `bg-dark` | 流量和 PRB 都为 0 |

## 测试建议

1. 选择包含 4G 和 5G 小区的场景
2. 验证场景指标汇总表格显示 13 列
3. 检查无流量小区数和无性能小区数的统计是否正确
4. 验证徽章颜色显示是否符合设计
5. 确认提示文字正确显示

## 相关文件

- `services/scenario_service.py` - 后端统计逻辑
- `templates/monitor.html` - 前端显示界面

## 完成时间

2025-12-29
