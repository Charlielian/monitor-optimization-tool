# CGI 匹配策略统一说明

## 更新日期
2025-12-29

## 背景

在保障监控的场景小区关联功能中，之前存在 4G 和 5G 匹配逻辑不一致的问题：
- **4G**：使用双重匹配（cell_id OR cgi）
- **5G**：只使用单一匹配（Ncgi）

这种不一致可能导致部分小区匹配不到数据。

## 统一方案

**采用：统一使用 CGI 匹配**

### 理由

1. **CGI 是标准的全局唯一标识**
   - CGI (Cell Global Identity) 是 3GPP 标准定义的小区全局标识
   - 具有唯一性和规范性

2. **避免数据不一致**
   - cell_id 可能在不同区域重复
   - CGI 确保全局唯一

3. **统一性**
   - 4G 和 5G 使用相同的匹配逻辑
   - 代码更清晰，维护更简单

## 修改内容

### 1. 场景小区指标查询 (`scenario_cell_metrics`)

**4G 修改：**
```python
# 修改前
WHERE start_time = %s AND (cell_id IN (...) OR cgi IN (...))

# 修改后
WHERE start_time = %s AND cgi IN (...)
```

**5G 保持：**
```python
WHERE start_time = %s AND "Ncgi" IN (...)
```

### 2. 场景统计 (`scenario_stats`)

**4G 修改：**
```python
# 修改前
WHERE start_time = %s AND (cell_id IN (...) OR cgi IN (...))

# 修改后
WHERE start_time = %s AND cgi IN (...)
```

**5G 保持：**
```python
WHERE start_time = %s AND "Ncgi" IN (...)
```

### 3. 场景流量趋势 (`traffic_trend`)

**4G 修改：**
```python
# 修改前
WHERE start_time BETWEEN %s AND %s AND cell_id IN (...)

# 修改后
WHERE start_time BETWEEN %s AND %s AND cgi IN (...)
```

**5G 保持：**
```python
WHERE start_time BETWEEN %s AND %s AND "Ncgi" IN (...)
```

### 4. 接通率趋势 (`connect_rate_trend`)

**4G 修改：**
```python
# 修改前
WHERE start_time BETWEEN %s AND %s AND cell_id IN (...)

# 修改后
WHERE start_time BETWEEN %s AND %s AND cgi IN (...)
```

**5G 保持：**
```python
WHERE start_time BETWEEN %s AND %s AND "Ncgi" IN (...)
```

### 5. PRB 利用率趋势 (`util_trend`)

**4G 修改：**
```python
# 修改前
WHERE start_time BETWEEN %s AND %s AND cell_id IN (...)

# 修改后
WHERE start_time BETWEEN %s AND %s AND cgi IN (...)
```

**5G 保持：**
```python
WHERE start_time BETWEEN %s AND %s AND "Ncgi" IN (...)
```

### 6. PRB 统计 (`prb_stats`)

**4G 修改：**
```python
# 修改前
WHERE start_time = %s AND cell_id IN (...)

# 修改后
WHERE start_time = %s AND cgi IN (...)
```

**5G 保持：**
```python
WHERE start_time = %s AND "Ncgi" IN (...)
```

## 数据表字段说明

### 4G 表 (`cell_4g_metrics`)
- `cell_id`: 小区ID（可能重复）
- `cgi`: 小区全局标识（唯一）
- **使用字段**：`cgi`

### 5G 表 (`cell_5g_metrics`)
- `Ncgi`: 5G 小区全局标识（唯一）
- **使用字段**：`Ncgi`

### 场景表 (`scenario_cells`)
- `cell_id`: 存储小区ID
- `cgi`: 存储CGI
- **唯一约束**：`(scenario_id, cell_id, network_type)`
- **匹配字段**：`cgi`

## 注意事项

### 1. CGI 字段必须存在

在添加场景小区时，必须确保 `cgi` 字段有值：

```python
scenario_service.add_cells(
    scenario_id,
    [{
        "cell_id": "123456",
        "cell_name": "某某小区",
        "cgi": "460000123456789",  # 必须提供
        "network_type": "4G"
    }]
)
```

### 2. 导入小区时的处理

如果导入的数据中没有 CGI，需要：
- 从数据表中查询获取 CGI
- 或者使用 cell_id 作为 CGI 的默认值

```python
# 如果没有 CGI，使用 cell_id
cgi = row.get("cgi") or row.get("cell_id")
```

### 3. 数据验证

添加小区前应验证：
```python
if not cgi:
    raise ValueError("CGI 不能为空")
```

## 影响范围

### 受影响的功能

1. ✅ 保障监控 - 场景小区指标查询
2. ✅ 保障监控 - 场景统计
3. ✅ 保障监控 - 流量趋势图
4. ✅ 保障监控 - 接通率趋势图
5. ✅ 保障监控 - PRB 利用率趋势图
6. ✅ 保障监控 - 导出功能

### 不受影响的功能

- ❌ 全网监控（不涉及场景）
- ❌ 小区指标查询（使用 cell_id OR cgi 双重匹配）
- ❌ Top 小区（不涉及场景）

## 测试建议

### 1. 功能测试

1. **添加场景小区**
   - 确保 CGI 字段正确存储
   - 验证小区能正常显示

2. **场景统计**
   - 检查流量、PRB、接通率等指标
   - 确认数据正确

3. **趋势图**
   - 查看流量趋势
   - 查看接通率趋势
   - 查看 PRB 趋势

4. **导出功能**
   - 导出场景小区清单
   - 导出保障监控数据

### 2. 数据验证

```sql
-- 检查场景表中 CGI 为空的记录
SELECT * FROM scenario_cells WHERE cgi IS NULL OR cgi = '';

-- 检查 4G 数据表中 CGI 为空的记录
SELECT COUNT(*) FROM cell_4g_metrics WHERE cgi IS NULL OR cgi = '';

-- 检查 5G 数据表中 Ncgi 为空的记录
SELECT COUNT(*) FROM cell_5g_metrics WHERE "Ncgi" IS NULL OR "Ncgi" = '';
```

### 3. 性能测试

```sql
-- 测试 CGI 查询性能
EXPLAIN ANALYZE
SELECT * FROM cell_4g_metrics
WHERE start_time = '2025-12-29 14:00:00'
  AND cgi IN ('460000123456789', '460000123456790');

-- 建议添加索引
CREATE INDEX IF NOT EXISTS idx_cell_4g_metrics_cgi 
ON cell_4g_metrics(cgi);

CREATE INDEX IF NOT EXISTS idx_cell_5g_metrics_ncgi 
ON cell_5g_metrics("Ncgi");
```

## 回滚方案

如果需要回滚到双重匹配，修改查询条件：

```python
# 4G 回滚到双重匹配
WHERE start_time = %s AND (cell_id IN (...) OR cgi IN (...))

# 5G 回滚到双重匹配
WHERE start_time = %s AND ("Ncgi" IN (...) OR "Ncgi" IN (...))
```

## 相关文档

- `services/scenario_service.py` - 场景服务实现
- `services/metrics_service.py` - 指标服务实现
- `README.md` - 项目说明

## 版本信息

- **修改日期**: 2025-12-29
- **修改人**: System
- **版本**: v2.2
- **主要变更**: 统一使用 CGI 匹配
