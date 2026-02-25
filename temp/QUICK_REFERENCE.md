# 快速参考卡片

## 常用导入

```python
# 常量
from constants import (
    MAX_CELL_QUERY_LIMIT,      # 200 - 最大小区查询数量
    DEFAULT_PAGE_SIZE,          # 20 - 默认分页大小
    DEFAULT_THRESHOLD_4G,       # 50.0 - 4G默认阈值
    DEFAULT_THRESHOLD_5G,       # 50.0 - 5G默认阈值
    GRANULARITY_15MIN,          # "15m" - 15分钟粒度
    GRANULARITY_1HOUR,          # "1h" - 1小时粒度
    NETWORK_4G,                 # "4G"
    NETWORK_5G,                 # "5G"
    TIME_RANGE_6H,              # "6h"
    DEFAULT_AUTO_REFRESH_INTERVAL,  # 300秒
)

# 格式化工具
from utils.formatters import (
    format_traffic_with_unit,   # 流量单位转换
    bytes_to_gb,                # 字节转GB
    format_percentage,          # 百分比格式化
)

# 时间工具
from utils.time_parser import (
    parse_time_range,           # 解析时间范围
    parse_datetime_param,       # 解析单个时间
    format_datetime_for_input,  # 格式化为input格式
)

# Excel工具
from utils.excel_helper import (
    create_styled_workbook,     # 创建工作簿
    apply_header_style,         # 应用表头样式
    write_data_to_sheet,        # 写入数据
)

# 验证工具
from utils.validators import (
    validate_and_parse_cgis,    # CGI验证
    validate_granularity,       # 粒度验证
    validate_network_type,      # 网络类型验证
    validate_time_range,        # 时间范围验证
)

# 缓存工具
from services.cache import (
    cache_5m,                   # 5分钟缓存
    cache_1m,                   # 1分钟缓存
    get_all_cache_stats,        # 获取缓存统计
)
```

## 常用代码片段

### 1. CGI验证
```python
cgi_list, warning = validate_and_parse_cgis(request.args.get("cell_cgi", ""))
if warning:
    flash(warning, "warning")
```

### 2. 时间解析
```python
start, end = parse_time_range(
    request.args.get("start_time", ""),
    request.args.get("end_time", ""),
    latest_ts=latest_timestamp,
    default_hours=6
)
```

### 3. 流量格式化
```python
traffic_gb = 1500.5
value, unit = format_traffic_with_unit(traffic_gb)
# 结果: value=1.47, unit="TB"
```

### 4. Excel导出
```python
wb, ws = create_styled_workbook("报表名称")
headers = ["列1", "列2", "列3"]
column_widths = {"列1": 20, "列2": 25, "列3": 15}
write_data_to_sheet(ws, headers, data, column_widths)

output = io.BytesIO()
wb.save(output)
output.seek(0)
return send_file(output, as_attachment=True, download_name="report.xlsx")
```

### 5. 参数验证
```python
granularity = validate_granularity(request.args.get("granularity", ""))
network = validate_network_type(request.args.get("network", ""))
range_key = validate_time_range(request.args.get("range", ""))
```

### 6. 使用常量
```python
# 替代硬编码
page_size = DEFAULT_PAGE_SIZE  # 而不是 20
threshold_4g = DEFAULT_THRESHOLD_4G  # 而不是 50.0
max_cells = MAX_CELL_QUERY_LIMIT  # 而不是 200
```

### 7. 缓存统计
```python
@app.route("/admin/cache_stats")
def cache_stats():
    stats = get_all_cache_stats()
    return jsonify(stats)
```

## 常见模式

### 路由参数处理模式
```python
@app.route("/example")
def example():
    # 1. 参数获取和验证
    param1 = validate_xxx(request.args.get("param1", ""))
    param2 = validate_yyy(request.args.get("param2", ""))
    
    # 2. 时间处理
    start, end = parse_time_range(
        request.args.get("start_time", ""),
        request.args.get("end_time", ""),
        latest_ts=get_latest_ts()
    )
    
    # 3. 业务逻辑
    data = service.query_data(param1, param2, start, end)
    
    # 4. 数据格式化
    for row in data:
        row['traffic_value'], row['traffic_unit'] = format_traffic_with_unit(row['traffic_gb'])
    
    # 5. 返回渲染
    return render_template("template.html", data=data)
```

### Excel导出模式
```python
@app.route("/export/xxx")
def export_xxx():
    # 1. 获取数据
    data = service.get_data()
    
    # 2. 创建工作簿
    wb, ws = create_styled_workbook("报表名称")
    
    # 3. 定义表头和列宽
    headers = ["列1", "列2", "列3"]
    column_widths = {"列1": 20, "列2": 25, "列3": 15}
    
    # 4. 写入数据
    write_data_to_sheet(ws, headers, data, column_widths)
    
    # 5. 返回文件
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return send_file(
        output,
        as_attachment=True,
        download_name="report.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
```

## 替换对照表

| 旧代码 | 新代码 | 说明 |
|--------|--------|------|
| `20` | `DEFAULT_PAGE_SIZE` | 分页大小 |
| `200` | `MAX_CELL_QUERY_LIMIT` | 最大查询数 |
| `50` | `DEFAULT_THRESHOLD_4G` | 4G阈值 |
| `"15m"` | `GRANULARITY_15MIN` | 时间粒度 |
| `"6h"` | `TIME_RANGE_6H` | 时间范围 |
| `300` | `DEFAULT_AUTO_REFRESH_INTERVAL` | 刷新间隔 |
| `1024` | `GB_TO_TB` | 单位转换 |

## 性能提示

### 缓存使用
```python
# 使用缓存包装查询
from services.cache import cache_5m

result = cache_5m.get(
    f"query_key:{param1}:{param2}",
    lambda: expensive_query(param1, param2)
)
```

### 批量查询
```python
# 优先使用批量查询而不是循环查询
cell_data = service.cell_timeseries_bulk(cgi_list, network, start, end)
# 而不是
# for cgi in cgi_list:
#     data = service.cell_timeseries(cgi, network, start, end)
```

## 调试技巧

### 查看缓存状态
```python
from services.cache import cache_5m, cache_1m

print(cache_5m.get_stats())
print(cache_1m.get_stats())
```

### 清理缓存
```python
# 清理过期缓存
expired = cache_5m.cleanup_expired()
print(f"清理了 {expired} 个过期缓存")

# 清空所有缓存
cache_5m.clear()
```

### 重置统计
```python
cache_5m.reset_stats()
```

## 常见错误

### ❌ 错误：硬编码值
```python
if len(cgis) > 200:  # 不好
    cgis = cgis[:200]
```

### ✅ 正确：使用常量
```python
if len(cgis) > MAX_CELL_QUERY_LIMIT:  # 好
    cgis = cgis[:MAX_CELL_QUERY_LIMIT]
```

### ❌ 错误：重复的时间解析
```python
if end_time_str:
    try:
        if 'T' in end_time_str:
            end = datetime.strptime(end_time_str, '%Y-%m-%dT%H:%M')
        # ... 更多代码
```

### ✅ 正确：使用工具函数
```python
start, end = parse_time_range(start_time_str, end_time_str, latest_ts)
```

## 文档链接

- **OPTIMIZATION_SUMMARY.md** - 优化总结
- **MIGRATION_GUIDE.md** - 迁移指南
- **OPTIMIZATION_README.md** - 使用说明

## 快速测试

```bash
# 测试导入
python3 -c "from constants import *; print('✓ 常量模块')"
python3 -c "from utils.formatters import *; print('✓ 格式化模块')"
python3 -c "from utils.validators import *; print('✓ 验证模块')"
python3 -c "from services.cache import *; print('✓ 缓存模块')"

# 查看缓存统计
python3 -c "from services.cache import get_all_cache_stats; import json; print(json.dumps(get_all_cache_stats(), indent=2))"
```
