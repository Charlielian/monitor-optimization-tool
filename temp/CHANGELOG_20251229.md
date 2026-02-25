# 更新日志 - 2025-12-29

## 版本 v2.3 - 无数据小区显示功能

### 新增功能

#### 1. 无数据小区显示 ⭐

**功能描述：**
在保障监控中，即使小区 CGI 在数据表中查不到任何指标数据，也会在结果中显示该小区，指标值显示为空值（"-"）。

**应用场景：**
- 新增小区还没有数据上报
- 小区 CGI 填写错误
- 数据缺失或监控盲点
- 快速识别需要检查的小区

**实现细节：**

1. **后端查询逻辑** (`services/scenario_service.py`)
   - 从场景表获取所有配置的小区（包括 CGI）
   - 查询数据库中有数据的小区
   - 合并两个结果集
   - 为每个小区添加 `has_data` 标识
   - 排序：有数据的按 PRB 利用率降序，无数据的排在后面

2. **前端视觉标识** (`templates/monitor.html`)
   - 无数据小区行背景色：淡黄色（`table-warning`），透明度 0.7
   - 小区名后显示 "⚠️ 无数据" 徽章
   - 所有指标列显示 "-"
   - 鼠标悬停提示："该小区CGI在数据表中未找到"

3. **导出功能增强** (`app.py`)
   - Excel 导出新增 "数据状态" 列
   - 有数据的小区：显示 "有数据"
   - 无数据的小区：显示 "无数据"，所有指标列显示 "-"

**影响范围：**
- ✅ 保障监控 - 4G 小区详细指标
- ✅ 保障监控 - 5G 小区详细指标
- ✅ 导出完整数据（Excel）

**不影响：**
- ❌ 场景指标汇总（只统计有数据的小区）
- ❌ 趋势图（只显示有数据的小区）
- ❌ 全网监控
- ❌ 小区指标查询

### 修改的文件

#### 1. `services/scenario_service.py`

**修改方法：** `scenario_cell_metrics`

**主要变更：**
```python
# 修改前：只返回数据库中有数据的小区
rows = self.pg.fetch_all(sql, params)
return {"data": rows, "total": len(rows), ...}

# 修改后：返回所有配置的小区，包括无数据的
# 1. 创建小区映射
cell_map = {cgi: cell_info for cgi, cell_info in ...}

# 2. 查询有数据的小区
metrics_map = {cgi: metrics for cgi, metrics in ...}

# 3. 合并结果
all_cells = []
for cgi, cell_info in cell_map.items():
    if cgi in metrics_map:
        all_cells.append({...metrics, "has_data": True})
    else:
        all_cells.append({...empty_metrics, "has_data": False})

# 4. 排序
all_cells.sort(key=lambda x: (not x["has_data"], -x["max_prb_util"]))
```

**代码行数：** +120 行

#### 2. `templates/monitor.html`

**修改位置：** 4G 和 5G 小区详细指标表格

**主要变更：**
```html
<!-- 修改前 -->
<tr>
  <td>{{ cell.cellname }}</td>
  <td>{{ cell.interference }}</td>
  ...
</tr>

<!-- 修改后 -->
{% set has_data = cell.get('has_data', True) %}
<tr {% if not has_data %}class="table-warning" style="opacity: 0.7;"{% endif %}>
  <td>
    {{ cell.cellname }}
    {% if not has_data %}
    <span class="badge bg-warning text-dark">
      <i class="bi bi-exclamation-triangle"></i> 无数据
    </span>
    {% endif %}
  </td>
  <td>{{ cell.interference if has_data else '-' }}</td>
  ...
</tr>
```

**代码行数：** +60 行

#### 3. `app.py`

**修改方法：** `export_monitor_xlsx_full`

**主要变更：**
```python
# 修改前：只导出有数据的小区
rows = pg.fetch_all(sql, params)
for row in rows:
    ws.append([row["scenario"], row["cell_id"], ...])

# 修改后：导出所有小区，包括无数据的
# 1. 创建小区映射
cell_map = {cgi: cell_info for ...}

# 2. 查询有数据的小区
metrics_map = {cgi: [metrics] for ...}

# 3. 合并并导出
for cgi, cell_info in cell_map.items():
    if cgi in metrics_map:
        for row in metrics_map[cgi]:
            ws.append([..., "有数据"])
    else:
        ws.append([..., "-", "-", ..., "无数据"])
```

**新增列：** "数据状态"

**代码行数：** +80 行

### 新增文档

1. **`CELL_WITHOUT_DATA_FEATURE.md`**
   - 功能详细说明
   - 实现细节
   - 使用示例
   - 注意事项

2. **`TEST_CELL_WITHOUT_DATA.md`**
   - 测试指南
   - 测试步骤
   - 预期结果
   - 常见问题

3. **`CHANGELOG_20251229.md`**
   - 本次更新日志

### 测试建议

#### 单元测试

```python
# 测试无数据小区显示
def test_scenario_cell_metrics_with_no_data():
    # 1. 添加一个不存在的 CGI
    scenario_service.add_cells(scenario_id, [{
        "cell_id": "TEST-001",
        "cgi": "460-00-999999-9",
        "network_type": "4G"
    }])
    
    # 2. 查询场景小区指标
    result = scenario_service.scenario_cell_metrics([scenario_id])
    
    # 3. 验证结果
    assert len(result["4G"]["data"]) > 0
    no_data_cells = [c for c in result["4G"]["data"] if not c["has_data"]]
    assert len(no_data_cells) == 1
    assert no_data_cells[0]["cgi"] == "460-00-999999-9"
    assert no_data_cells[0]["traffic_gb"] == 0
```

#### 集成测试

1. 添加无数据小区到场景
2. 访问保障监控页面
3. 验证显示效果
4. 导出 Excel 文件
5. 验证导出内容

### 性能影响

**查询性能：**
- 无明显影响（仍然只查询一次数据库）
- 额外的内存操作：合并小区列表和指标数据

**页面渲染：**
- 无明显影响（模板渲染逻辑略微复杂）

**导出性能：**
- 无数据小区只增加一行记录
- 对文件大小影响很小

### 兼容性

**向后兼容：**
- ✅ 完全兼容现有功能
- ✅ 不影响已有的小区数据显示
- ✅ 不影响场景统计和趋势图

**数据库兼容：**
- ✅ 无需修改数据库结构
- ✅ 无需数据迁移

### 已知限制

1. **CGI 必填**
   - 添加小区时必须提供 CGI
   - 如果 CGI 为空，无法判断是否有数据

2. **排序规则**
   - 无数据小区始终排在有数据小区后面
   - 无法按其他字段排序无数据小区

3. **分页影响**
   - 无数据小区计入总数
   - 可能导致某些页面只显示无数据小区

### 未来改进

1. **可配置显示**
   - 添加开关，允许隐藏无数据小区
   - 添加过滤器，只显示有数据或无数据的小区

2. **数据状态详情**
   - 显示最后一次有数据的时间
   - 显示数据缺失的时长

3. **批量检查**
   - 提供批量检查 CGI 是否存在的功能
   - 自动修正常见的 CGI 格式错误

### 相关链接

- [功能详细说明](CELL_WITHOUT_DATA_FEATURE.md)
- [测试指南](TEST_CELL_WITHOUT_DATA.md)
- [CGI 匹配策略](CGI_MATCHING_SUMMARY.md)
- [项目说明](README.md)

### 贡献者

- 开发：System
- 测试：待定
- 文档：System

### 版本历史

- **v2.3** (2025-12-29): 新增无数据小区显示功能
- **v2.2** (2025-12-29): 统一 CGI 匹配策略
- **v2.1** (2025-12-29): 小区指标查询增强
- **v2.0** (2025-12-29): MySQL 工参表集成
- **v1.0** (2025-12-28): 初始版本

---

**更新时间：** 2025-12-29 14:30:00  
**更新人员：** System  
**审核状态：** 待审核
