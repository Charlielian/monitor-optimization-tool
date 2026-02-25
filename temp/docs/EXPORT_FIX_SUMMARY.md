# 保障监控导出功能修复总结

## 问题描述
用户在保障场景页面选择时间范围并导出数据时，遇到 500 Internal Server Error。

## 根本原因
在 `/export/monitor_xlsx_full` 路由中，处理数据库查询结果时，某些字段可能返回 `None` 值。当尝试将 `None` 转换为 `float` 或 `int` 时会抛出 `TypeError`，导致服务器返回 500 错误。

### 具体问题点：
1. **数据类型转换错误**：
   - `float(row.get("traffic_gb", 0))` - 当值为 `None` 时，`get` 返回 `None` 而不是默认值 0
   - `float(row.get("ul_prb_util", 0))` - 同样的问题
   - 其他数值字段也存在相同问题

2. **时间戳格式化问题**：
   - `row.get("start_time", "")` 可能返回 datetime 对象，需要转换为字符串

## 修复方案

### 1. 修复数值类型转换
将所有数值字段的处理从：
```python
float(row.get("field_name", 0))
```
改为：
```python
float(row.get("field_name") or 0)
```

这样可以正确处理 `None` 值，因为 `None or 0` 会返回 0。

### 2. 修复时间戳格式化
将时间字段的处理从：
```python
row.get("start_time", "")
```
改为：
```python
str(row.get("start_time", ""))
```

确保 datetime 对象被转换为字符串。

### 3. 添加异常处理和日志
- 在函数开始添加 `try-except` 块
- 添加关键步骤的日志记录，便于问题诊断
- 捕获异常后返回友好的错误信息

## 修改的文件
- `app.py` - `/export/monitor_xlsx_full` 路由

## 修改的代码位置

### Sheet2: 4G小区指标（约第 920-940 行）
```python
# 修复前
traffic_gb = float(row.get("traffic_gb", 0))
f"{float(row.get('ul_prb_util', 0)):.2f}"

# 修复后
traffic_gb = float(row.get("traffic_gb") or 0)
f"{float(row.get('ul_prb_util') or 0):.2f}"
str(row.get("start_time", ""))
```

### Sheet3: 5G小区指标（约第 1040-1060 行）
同样的修复应用到 5G 数据处理部分。

### 添加的日志记录
```python
logging.info(f"开始导出保障监控数据，场景ID: {selected}")
logging.info(f"时间范围: {start} 到 {end}")
logging.info(f"Sheet1: 获取到 {len(summary_rows)} 条汇总数据")
logging.info(f"Sheet2: 共收集到 {len(cells_4g_all)} 个4G小区")
logging.info(f"Sheet2: 有效CGI数量: {len(cgis_4g)}")
logging.info(f"Sheet2: 查询到 {len(rows_4g)} 条4G指标数据")
# ... 5G 部分类似
```

### 添加的异常处理
```python
try:
    # 原有代码
    ...
except Exception as e:
    logging.error(f"导出保障监控数据失败: {str(e)}", exc_info=True)
    flash(f"导出失败: {str(e)}", "danger")
    return redirect(url_for("monitor"))
```

## 测试验证
创建了 `test_export_fix.py` 测试脚本，验证 `None` 值处理逻辑正确。

## 预期效果
1. 导出功能不再因为 `None` 值而崩溃
2. 即使数据库中某些字段为空，也能正常生成 Excel 文件
3. 通过日志可以追踪导出过程，便于问题诊断
4. 用户会看到友好的错误提示（如果仍有其他问题）

## 建议
1. 重启 Flask 服务以应用修改
2. 测试导出功能，特别是包含无数据小区的场景
3. 检查日志文件，确认导出过程正常

## 相关文件
- `app.py` - 主应用文件（已修复）
- `test_export_fix.py` - 测试脚本
- `logs/service.log` - 服务日志（查看详细错误信息）
