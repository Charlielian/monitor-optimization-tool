# 代码迁移指南

本文档说明如何将 `app.py` 中的代码迁移到新的优化架构。

## 快速开始

### 1. 导入新模块

在 `app.py` 顶部添加以下导入：

```python
# 常量
from constants import (
    MAX_CELL_QUERY_LIMIT,
    DEFAULT_PAGE_SIZE,
    DEFAULT_THRESHOLD_4G,
    DEFAULT_THRESHOLD_5G,
    GRANULARITY_15MIN,
    DEFAULT_AUTO_REFRESH_INTERVAL,
    DATETIME_FORMAT,
    FILENAME_DATETIME_FORMAT,
)

# 工具函数
from utils.formatters import format_traffic_with_unit, format_percentage
from utils.time_parser import parse_time_range, parse_datetime_param, format_datetime_for_input
from utils.excel_helper import (
    create_styled_workbook,
    apply_header_style,
    set_column_widths,
    write_data_to_sheet,
)
from utils.validators import (
    validate_and_parse_cgis,
    validate_granularity,
    validate_network_type,
    validate_time_range,
)
```

## 2. 具体迁移示例

### 2.1 CGI输入验证

**旧代码**：
```python
cell_cgi = request.args.get("cell_cgi", "").strip()
cgi_list = [c.strip() for c in cell_cgi.split(',') if c.strip()]
if len(cgi_list) > 200:
    flash(f"最多只能查询200个小区，当前输入了{len(cgi_list)}个，已自动截取前200个", "warning")
    cgi_list = cgi_list[:200]
```

**新代码**：
```python
cell_cgi = request.args.get("cell_cgi", "").strip()
cgi_list, warning = validate_and_parse_cgis(cell_cgi)
if warning:
    flash(warning, "warning")
```

### 2.2 时间解析

**旧代码**：
```python
start_time_str = request.args.get("start_time", "")
end_time_str = request.args.get("end_time", "")

latest = scenario_service.latest_time()
latest_ts_candidates = [latest.get("4g"), latest.get("5g")]
latest_ts = max((ts for ts in latest_ts_candidates if ts), default=None)
now = datetime.now()
end = latest_ts or now
start = end - timedelta(hours=6)

if end_time_str:
    try:
        if 'T' in end_time_str:
            end = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M')
        else:
            end = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
    except Exception as e:
        logging.warning(f"解析结束时间失败: {end_time_str}, 错误: {e}")
        pass
if start_time_str:
    try:
        if 'T' in start_time_str:
            start = datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M')
        else:
            start = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
    except Exception as e:
        logging.warning(f"解析开始时间失败: {start_time_str}, 错误: {e}")
        pass
```

**新代码**：
```python
start_time_str = request.args.get("start_time", "")
end_time_str = request.args.get("end_time", "")

latest = scenario_service.latest_time()
latest_ts_candidates = [latest.get("4g"), latest.get("5g")]
latest_ts = max((ts for ts in latest_ts_candidates if ts), default=None)

start, end = parse_time_range(
    start_time_str,
    end_time_str,
    latest_ts=latest_ts,
    default_hours=6,
    max_days=30
)
```

### 2.3 Excel导出

**旧代码**：
```python
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

wb = Workbook()
ws = wb.active
ws.title = "数据报表"

# 写入表头
headers = ["列1", "列2", "列3"]
ws.append(headers)

# 写入数据
for row in data:
    ws.append([row.get(h) for h in headers])

# 设置表头样式
header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
header_font = Font(bold=True, color="FFFFFF", size=12)
header_alignment = Alignment(horizontal="center", vertical="center")

for cell in ws[1]:
    cell.fill = header_fill
    cell.font = header_font
    cell.alignment = header_alignment

# 设置列宽
ws.column_dimensions['A'].width = 20
ws.column_dimensions['B'].width = 25
```

**新代码**：
```python
from utils.excel_helper import create_styled_workbook, write_data_to_sheet

wb, ws = create_styled_workbook("数据报表")

headers = ["列1", "列2", "列3"]
column_widths = {
    "列1": 20,
    "列2": 25,
    "列3": 15,
}

write_data_to_sheet(ws, headers, data, column_widths)
```

### 2.4 参数验证

**旧代码**：
```python
granularity = request.args.get("granularity", "15m")
network = request.args.get("network", "4G")
range_key = request.args.get("range", "6h")
```

**新代码**：
```python
from utils.validators import validate_granularity, validate_network_type, validate_time_range

granularity = validate_granularity(request.args.get("granularity", ""))
network = validate_network_type(request.args.get("network", ""))
range_key = validate_time_range(request.args.get("range", ""))
```

### 2.5 流量单位转换

**旧代码**：
```python
traffic_gb = row.get("total_traffic", 0)
if traffic_gb >= 1024:
    traffic_value = traffic_gb / 1024
    traffic_unit = "TB"
else:
    traffic_value = traffic_gb
    traffic_unit = "GB"
```

**新代码**：
```python
from utils.formatters import format_traffic_with_unit

traffic_gb = row.get("total_traffic", 0)
traffic_value, traffic_unit = format_traffic_with_unit(traffic_gb)
```

### 2.6 使用常量替代硬编码

**旧代码**：
```python
page_size = 20
threshold_4g = float(request.args.get("thr4g", 50))
threshold_5g = float(request.args.get("thr5g", 50))
auto_interval = int(request.args.get("auto_interval", 300))
```

**新代码**：
```python
from constants import DEFAULT_PAGE_SIZE, DEFAULT_THRESHOLD_4G, DEFAULT_THRESHOLD_5G, DEFAULT_AUTO_REFRESH_INTERVAL

page_size = DEFAULT_PAGE_SIZE
threshold_4g = float(request.args.get("thr4g", DEFAULT_THRESHOLD_4G))
threshold_5g = float(request.args.get("thr5g", DEFAULT_THRESHOLD_5G))
auto_interval = int(request.args.get("auto_interval", DEFAULT_AUTO_REFRESH_INTERVAL))
```

## 3. 完整路由迁移示例

### 迁移 `/cell` 路由

**优化前**：
```python
@app.route("/cell")
def cell():
    cell_cgi = request.args.get("cell_cgi", "").strip()
    cell_network = request.args.get("cell_network", "4G")
    start_time_str = request.args.get("start_time", "")
    end_time_str = request.args.get("end_time", "")
    granularity = request.args.get("granularity", "15m")
    
    # 大量重复的时间解析代码...
    # 大量重复的CGI验证代码...
    
    return render_template("cell.html", ...)
```

**优化后**：
```python
@app.route("/cell")
def cell():
    # 参数获取和验证
    cell_cgi = request.args.get("cell_cgi", "").strip()
    cell_network = validate_network_type(request.args.get("cell_network", ""))
    granularity = validate_granularity(request.args.get("granularity", ""))
    
    # CGI验证
    cgi_list, warning = validate_and_parse_cgis(cell_cgi)
    if warning:
        flash(warning, "warning")
    
    # 时间解析
    latest = scenario_service.latest_time()
    latest_ts = max((ts for ts in [latest.get("4g"), latest.get("5g")] if ts), default=None)
    
    start, end = parse_time_range(
        request.args.get("start_time", ""),
        request.args.get("end_time", ""),
        latest_ts=latest_ts,
        default_hours=6
    )
    
    # 查询数据
    cell_data = []
    if cgi_list:
        cell_data = service.cell_timeseries_bulk(cgi_list, cell_network, start, end, granularity)
        # 补齐数据
        for row in cell_data:
            if 'cgi' not in row or not row.get('cgi'):
                row['cgi'] = row.get('cell_id')
            if 'cell_id' not in row or not row.get('cell_id'):
                row['cell_id'] = row.get('cgi')
        
        if not cell_data:
            flash("未查询到该小区的指标数据，请确认CGI与制式是否正确。", "warning")
    
    return render_template(
        "cell.html",
        cell_cgi=cell_cgi,
        cell_network=cell_network,
        start_time=format_datetime_for_input(start),
        end_time=format_datetime_for_input(end),
        cell_data=cell_data,
        granularity=granularity,
    )
```

## 4. 迁移优先级

建议按以下优先级迁移：

### 高优先级（立即迁移）
1. ✅ 常量替换 - 简单且影响大
2. ✅ 输入验证 - 提高安全性
3. ✅ 时间解析 - 消除大量重复代码

### 中优先级（逐步迁移）
4. Excel导出 - 在修改导出功能时迁移
5. 格式化函数 - 在修改显示逻辑时迁移

### 低优先级（可选）
6. 其他工具函数 - 根据需要逐步迁移

## 5. 测试建议

迁移后建议测试以下场景：

1. **CGI输入验证**
   - 输入单个CGI
   - 输入多个CGI（逗号分隔）
   - 输入超过200个CGI
   - 输入空值

2. **时间解析**
   - 不提供时间参数（使用默认值）
   - 提供有效的时间参数
   - 提供无效的时间参数
   - 开始时间晚于结束时间

3. **Excel导出**
   - 导出空数据
   - 导出正常数据
   - 检查样式是否正确

## 6. 回滚方案

如果迁移后出现问题，可以：

1. 保留旧代码作为注释
2. 使用Git回滚到迁移前的版本
3. 逐个功能迁移，便于定位问题

## 7. 性能监控

迁移后可以通过以下方式监控性能：

```python
from services.cache import get_all_cache_stats

@app.route("/admin/cache_stats")
def cache_stats():
    """查看缓存统计"""
    stats = get_all_cache_stats()
    return jsonify(stats)
```

## 8. 常见问题

### Q: 是否需要一次性迁移所有代码？
A: 不需要。建议逐步迁移，先迁移新功能，再逐步重构旧代码。

### Q: 迁移会影响现有功能吗？
A: 不会。新工具函数与旧代码兼容，可以共存。

### Q: 如何验证迁移是否成功？
A: 运行现有测试用例，确保所有功能正常工作。

### Q: 遇到问题怎么办？
A: 查看日志文件，检查错误信息，必要时回滚到旧版本。
