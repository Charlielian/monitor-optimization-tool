# 无数据小区显示功能说明

## 更新日期
2025-12-29

## 功能描述

在保障监控中，即使某个小区的 CGI 在数据表中查不到任何指标数据，也会在结果中显示这个小区，只是指标值都为空值（显示为 "-"）。这样可以清楚地看到哪些小区没有数据。

## 应用场景

1. **新增小区**：刚添加到场景中的小区，可能还没有数据上报
2. **CGI 错误**：小区 CGI 填写错误，导致无法匹配到数据
3. **数据缺失**：某些小区在特定时间段没有数据
4. **监控盲点**：快速识别哪些小区需要检查

## 实现细节

### 1. 后端逻辑 (`services/scenario_service.py`)

#### `scenario_cell_metrics` 方法

**核心逻辑：**
1. 从场景表中获取所有小区列表（包括 CGI）
2. 查询数据库中有数据的小区
3. 合并两个结果：
   - 有数据的小区：显示实际指标值，`has_data=True`
   - 无数据的小区：显示空值，`has_data=False`
4. 排序：有数据的按 PRB 利用率降序，无数据的排在后面

**代码示例：**
```python
# 创建小区映射（CGI -> 小区信息）
cell_map = {}
for c in cells:
    cgi = c.get("cgi", "")
    if cgi:
        cell_map[cgi] = {
            "scenario": c.get("scenario", ""),
            "cell_id": c.get("cell_id", ""),
            "cell_name": c.get("cell_name", ""),
            "cgi": cgi,
        }

# 查询数据库中有数据的小区
metrics_map = {}
# ... SQL 查询 ...

# 合并小区信息和指标数据
all_cells = []
for cgi, cell_info in cell_map.items():
    if cgi in metrics_map:
        # 有数据的小区
        all_cells.append({
            ...metrics_map[cgi],
            "has_data": True,
        })
    else:
        # 没有数据的小区
        all_cells.append({
            "scenario": cell_info["scenario"],
            "cell_id": cell_info["cell_id"],
            "cgi": cgi,
            "cellname": cell_info["cell_name"],
            "traffic_gb": 0,
            "ul_prb_util": 0,
            "dl_prb_util": 0,
            "max_prb_util": 0,
            "connect_rate": 0,
            "rrc_users": 0,
            "interference": 0,
            "has_data": False,
        })

# 排序：有数据的按max_prb_util降序，没数据的排在后面
all_cells.sort(key=lambda x: (not x["has_data"], -x["max_prb_util"]))
```

### 2. 前端显示 (`templates/monitor.html`)

#### 视觉标识

**无数据小区的特征：**
1. **行背景色**：淡黄色（`table-warning`），透明度 0.7
2. **警告徽章**：小区名后显示 "⚠️ 无数据" 徽章
3. **指标值**：所有指标显示为 "-"
4. **鼠标悬停提示**：显示 "该小区CGI在数据表中未找到"

**代码示例：**
```html
{% set has_data = cell.get('has_data', True) %}
<tr {% if not has_data %}class="table-warning" style="opacity: 0.7;"{% endif %}>
  <td class="text-center">
    {{ cell.cellname or cell.cell_id }}
    {% if not has_data %}
    <span class="badge bg-warning text-dark ms-1" title="该小区CGI在数据表中未找到">
      <i class="bi bi-exclamation-triangle"></i> 无数据
    </span>
    {% endif %}
  </td>
  <td class="text-center">
    {{ "%.2f"|format(cell.interference or 0) if has_data else '-' }}
  </td>
  <!-- 其他字段类似 -->
</tr>
```

### 3. 导出功能 (`app.py`)

#### Excel 导出

**导出逻辑：**
1. 获取所有场景小区列表
2. 查询数据库中有数据的小区
3. 合并结果：
   - 有数据的小区：输出所有时间点的数据，状态列显示 "有数据"
   - 无数据的小区：输出一行空值，状态列显示 "无数据"

**Excel 列：**
- 场景
- 小区ID
- CGI
- 小区名
- 时间
- 流量(GB)
- 上行PRB利用率(%)
- 下行PRB利用率(%)
- 最大PRB利用率(%)
- 无线接通率(%)
- 最大用户数
- 干扰
- **数据状态**（新增列）

**代码示例：**
```python
# 合并小区信息和指标数据
for cgi, cell_info in cell_map.items():
    if cgi in metrics_map:
        # 有数据的小区，输出所有时间点的数据
        for row in metrics_map[cgi]:
            ws.append([
                cell_info["scenario"],
                row.get("cell_id"),
                cgi,
                row.get("cellname"),
                row.get("start_time"),
                f"{traffic_gb:.2f}",
                # ... 其他指标 ...
                "有数据",
            ])
    else:
        # 没有数据的小区，输出一行空值
        ws.append([
            cell_info["scenario"],
            cell_info["cell_id"],
            cgi,
            cell_info["cell_name"],
            "-",
            "-",
            "-",
            # ... 其他指标 ...
            "无数据",
        ])
```

## 使用示例

### 场景 1：添加新小区

1. 在场景管理中添加一个新小区：
   - 小区ID: `123456-7`
   - CGI: `460-00-123456-7`
   - 制式: `4G`

2. 在保障监控中选择该场景

3. 结果显示：
   - 该小区会出现在列表中
   - 行背景为淡黄色
   - 小区名后显示 "⚠️ 无数据" 徽章
   - 所有指标显示为 "-"

### 场景 2：CGI 错误

1. 小区 CGI 填写错误：`460-00-999999-9`（数据库中不存在）

2. 在保障监控中查看：
   - 该小区会显示在列表中
   - 标记为 "无数据"
   - 可以快速识别并修正 CGI

### 场景 3：导出数据

1. 导出保障监控数据（Excel）

2. Excel 文件包含：
   - Sheet1: 45G整体（场景汇总）
   - Sheet2: 4G小区指标（包含无数据小区）
   - Sheet3: 5G小区指标（包含无数据小区）

3. 无数据小区特征：
   - 时间列显示 "-"
   - 所有指标列显示 "-"
   - 数据状态列显示 "无数据"

## 优势

1. **完整性**：显示所有配置的小区，不遗漏
2. **可见性**：快速识别哪些小区没有数据
3. **可追溯**：导出的 Excel 文件包含完整信息
4. **易排查**：通过 "无数据" 标识快速定位问题

## 注意事项

1. **CGI 必填**：添加小区时必须提供 CGI，否则无法匹配
2. **排序规则**：无数据的小区排在有数据的小区后面
3. **分页影响**：无数据小区也计入总数，影响分页
4. **导出大小**：如果有很多无数据小区，导出文件会包含这些记录

## 相关文件

- `services/scenario_service.py` - 后端查询逻辑
- `templates/monitor.html` - 前端显示模板
- `app.py` - 导出功能实现
- `CGI_MATCHING_SUMMARY.md` - CGI 匹配策略说明

## 版本信息

- **更新日期**: 2025-12-29
- **版本**: v2.3
- **主要变更**: 支持显示无数据小区
